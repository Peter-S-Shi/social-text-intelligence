"""Privacy-conscious local Flask interface for direct text analysis."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from flask import Flask, Response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ..contracts import AnalysisReport, NormalizedTextInput
from ..contracts.errors import (
    ProviderError,
    SocialTextIntelligenceError,
    ValidationError,
)
from ..providers import CardiffSentimentProvider, SamLoweEmotionProvider
from ..providers.samlowe_emotion import DEFAULT_EMOTION_THRESHOLD
from ..services import (
    AnalysisService,
    HumanReview,
    LazyAnalysisService,
    accept_both,
    analyze_batch,
    create_review_state,
    export_batch_csv,
    filter_review_cases,
    inspect_csv_upload,
    prepare_csv_batch,
    review_cases,
    review_navigation,
    summarize_reviews,
    update_review,
)
from ..services.batch import DEFAULT_MAX_BATCH_BYTES, DEFAULT_MAX_BATCH_ROWS
from .batch_state import BatchWorkspace, EphemeralBatchStore


class AnalysisGateway(Protocol):
    @property
    def initialized(self) -> bool: ...

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport: ...


def _real_analysis_service(
    *, cache_dir: Path, offline: bool, emotion_threshold: float
) -> AnalysisService:
    return AnalysisService(
        sentiment_provider=CardiffSentimentProvider(
            cache_dir=cache_dir,
            offline=offline,
        ),
        emotion_provider=SamLoweEmotionProvider(
            cache_dir=cache_dir,
            offline=offline,
            threshold=emotion_threshold,
        ),
    )


def _safe_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return error.message
    if isinstance(error, ProviderError):
        if error.code == "missing_model_dependencies":
            return (
                "Local model dependencies are not installed. "
                "Install the model extras."
            )
        if error.code == "model_load_failed":
            return (
                "The approved model files could not be loaded. In offline mode, "
                "confirm that both pinned revisions are already cached."
            )
        return error.message
    if isinstance(error, SocialTextIntelligenceError):
        return str(error)
    return "Analysis failed safely. Review the local setup and try again."


def create_app(
    config: Mapping[str, Any] | None = None,
    *,
    analysis_gateway: AnalysisGateway | None = None,
) -> Flask:
    """Create the local app without loading either model."""

    app = Flask(__name__)
    app.config.from_mapping(
        CACHE_DIR="model_cache",
        OFFLINE=False,
        EMOTION_THRESHOLD=DEFAULT_EMOTION_THRESHOLD,
        MAX_TEXT_LENGTH=20_000,
        MAX_BATCH_BYTES=DEFAULT_MAX_BATCH_BYTES,
        MAX_BATCH_ROWS=DEFAULT_MAX_BATCH_ROWS,
    )
    if config is not None:
        app.config.update(config)

    if analysis_gateway is None:
        cache_dir = Path(str(app.config["CACHE_DIR"]))
        offline = bool(app.config["OFFLINE"])
        threshold = float(app.config["EMOTION_THRESHOLD"])
        analysis_gateway = LazyAnalysisService(
            lambda: _real_analysis_service(
                cache_dir=cache_dir,
                offline=offline,
                emotion_threshold=threshold,
            )
        )
    app.extensions["sti_analysis_gateway"] = analysis_gateway
    batch_store = EphemeralBatchStore()
    app.extensions["sti_batch_store"] = batch_store

    @app.after_request
    def prevent_private_response_caching(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response

    @app.route("/", methods=["GET", "POST"])
    def analyze_text() -> str:
        report: AnalysisReport | None = None
        error_message: str | None = None
        text = ""
        if request.method == "POST":
            text = request.form.get("text", "")
            try:
                record = NormalizedTextInput.from_text(
                    text,
                    language="en",
                    max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                )
                report = analysis_gateway.analyze(record)
            # The interface boundary must never expose traceback text.
            except Exception as error:
                error_message = _safe_error(error)

        return render_template(
            "analyze.html",
            report=report,
            error_message=error_message,
            submitted_text=text,
            offline=bool(app.config["OFFLINE"]),
            initialized=analysis_gateway.initialized,
            max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
        )

    @app.get("/batch")
    def batch_home() -> str:
        return render_template(
            "batch.html",
            offline=bool(app.config["OFFLINE"]),
            max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
            max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
            max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
        )

    @app.post("/batch/upload")
    def batch_upload() -> ResponseReturnValue:
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return render_template(
                "batch.html",
                error_message="Choose a UTF-8 CSV file before previewing.",
                offline=bool(app.config["OFFLINE"]),
                max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
                max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
                max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
            )
        try:
            content = upload.stream.read(int(app.config["MAX_BATCH_BYTES"]) + 1)
            pending = inspect_csv_upload(
                content, max_bytes=int(app.config["MAX_BATCH_BYTES"])
            )
            if "text" in pending.headers:
                preview = prepare_csv_batch(
                    pending,
                    text_column="text",
                    max_rows=int(app.config["MAX_BATCH_ROWS"]),
                    max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                )
                token = batch_store.create(BatchWorkspace(preview=preview))
            else:
                token = batch_store.create(BatchWorkspace(pending=pending))
        except Exception as error:
            return render_template(
                "batch.html",
                error_message=_safe_error(error),
                offline=bool(app.config["OFFLINE"]),
                max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
                max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
                max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
            )
        return redirect(url_for("batch_workspace", token=token))

    @app.get("/batch/<token>")
    def batch_workspace(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None:
            return (
                render_template(
                    "batch.html",
                    error_message="This temporary batch expired or was cleared.",
                    offline=bool(app.config["OFFLINE"]),
                    max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
                    max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
                    max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                ),
                404,
            )
        outcomes = workspace.result.outcomes if workspace.result is not None else ()
        status_filter = request.args.get("status", "all")
        sentiment_filter = request.args.get("sentiment", "all")
        emotion_filter = request.args.get("emotion", "all")
        filtered = tuple(
            outcome
            for outcome in outcomes
            if (status_filter == "all" or outcome.status == status_filter)
            and (
                sentiment_filter == "all"
                or (
                    outcome.report is not None
                    and outcome.report.sentiment.label == sentiment_filter
                )
            )
            and (
                emotion_filter == "all"
                or (
                    outcome.report is not None
                    and outcome.report.emotion.dominant_emotion == emotion_filter
                )
            )
        )
        return render_template(
            "batch.html",
            token=token,
            workspace=workspace,
            filtered_outcomes=filtered,
            status_filter=status_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
            offline=bool(app.config["OFFLINE"]),
            max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
            max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
            max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
        )

    @app.post("/batch/<token>/select")
    def batch_select_column(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.pending is None:
            return redirect(url_for("batch_workspace", token=token))
        try:
            preview = prepare_csv_batch(
                workspace.pending,
                text_column=request.form.get("text_column", ""),
                max_rows=int(app.config["MAX_BATCH_ROWS"]),
                max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
            )
        except SocialTextIntelligenceError:
            return redirect(url_for("batch_workspace", token=token))
        batch_store.replace(token, BatchWorkspace(preview=preview))
        return redirect(url_for("batch_workspace", token=token))

    @app.post("/batch/<token>/analyze")
    def batch_analyze(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.preview is None:
            return redirect(url_for("batch_workspace", token=token))
        result = analyze_batch(workspace.preview, analysis_gateway)
        batch_store.replace(
            token,
            BatchWorkspace(
                preview=workspace.preview,
                result=result,
                reviews=create_review_state(result),
            ),
        )
        return redirect(url_for("batch_workspace", token=token))

    def review_filters() -> tuple[str, str, str]:
        return (
            request.values.get("review", "all"),
            request.values.get("sentiment", "all"),
            request.values.get("emotion", "all"),
        )

    def review_form_values(
        review: HumanReview, *, submitted: bool = False
    ) -> dict[str, object]:
        if submitted:
            return {
                "sentiment_judgment": request.form.get(
                    "sentiment_judgment", ""
                ),
                "human_sentiment": request.form.get("human_sentiment", ""),
                "emotion_judgment": request.form.get("emotion_judgment", ""),
                "human_dominant_emotion": request.form.get(
                    "human_dominant_emotion", ""
                ),
                "human_secondary_emotions": request.form.getlist(
                    "human_secondary_emotions"
                ),
                "note": request.form.get("review_note", ""),
            }
        return {
            "sentiment_judgment": (
                review.sentiment_judgment.value
                if review.sentiment_judgment is not None
                else ""
            ),
            "human_sentiment": (
                review.human_sentiment.value
                if review.human_sentiment is not None
                else ""
            ),
            "emotion_judgment": (
                review.emotion_judgment.value
                if review.emotion_judgment is not None
                else ""
            ),
            "human_dominant_emotion": (
                review.human_dominant_emotion.value
                if review.human_dominant_emotion is not None
                else ""
            ),
            "human_secondary_emotions": tuple(
                label.value for label in review.human_secondary_emotions
            ),
            "note": review.note or "",
        }

    def render_review(
        token: str,
        workspace: BatchWorkspace,
        row_number: int,
        *,
        error_message: str | None = None,
        submitted: bool = False,
        status: int = 200,
    ) -> ResponseReturnValue:
        result = workspace.result
        state = workspace.reviews
        if result is None or state is None:
            return Response("Review workspace not found.", status=404)
        all_cases = review_cases(result, state)
        current = next(
            (
                case
                for case in all_cases
                if case.outcome.prepared.row_number == row_number
            ),
            None,
        )
        if current is None:
            return Response("Review record not found.", status=404)
        review_filter, sentiment_filter, emotion_filter = review_filters()
        filtered = filter_review_cases(
            result,
            state,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        navigation = review_navigation(
            result,
            state,
            current_record_id=current.review.record_id,
            filtered_cases=filtered,
        )
        position = next(
            index
            for index, case in enumerate(all_cases, start=1)
            if case.review.record_id == current.review.record_id
        )
        return (
            render_template(
                "review.html",
                token=token,
                current=current,
                position=position,
                queue_total=len(all_cases),
                filtered_count=len(filtered),
                navigation=navigation,
                summary=summarize_reviews(result, state),
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
                form_values=review_form_values(
                    current.review, submitted=submitted
                ),
                error_message=error_message,
                max_review_note_length=2_000,
            ),
            status,
        )

    @app.get("/batch/<token>/review")
    def review_index(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if (
            workspace is None
            or workspace.result is None
            or workspace.reviews is None
        ):
            return Response("Review workspace not found.", status=404)
        review_filter, sentiment_filter, emotion_filter = review_filters()
        cases = filter_review_cases(
            workspace.result,
            workspace.reviews,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if not cases:
            cases = review_cases(workspace.result, workspace.reviews)
        if not cases:
            return Response("No successful batch rows are available for review.", 404)
        return redirect(
            url_for(
                "review_record",
                token=token,
                row_number=cases[0].outcome.prepared.row_number,
                review=review_filter,
                sentiment=sentiment_filter,
                emotion=emotion_filter,
            )
        )

    @app.get("/batch/<token>/review/<int:row_number>")
    def review_record(token: str, row_number: int) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None:
            return Response("This temporary review expired or was cleared.", 404)
        return render_review(token, workspace, row_number)

    @app.post("/batch/<token>/review/<int:row_number>")
    def save_review(token: str, row_number: int) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if (
            workspace is None
            or workspace.result is None
            or workspace.reviews is None
        ):
            return Response("This temporary review expired or was cleared.", 404)
        current = next(
            (
                case
                for case in review_cases(workspace.result, workspace.reviews)
                if case.outcome.prepared.row_number == row_number
            ),
            None,
        )
        if current is None:
            return Response("Review record not found.", status=404)
        action = request.form.get("action", "save_next")
        try:
            if action == "accept_both":
                updated = accept_both(
                    workspace.result,
                    workspace.reviews,
                    record_id=current.review.record_id,
                    note=request.form.get("review_note", ""),
                )
            else:
                updated = update_review(
                    workspace.result,
                    workspace.reviews,
                    record_id=current.review.record_id,
                    sentiment_judgment=request.form.get("sentiment_judgment"),
                    human_sentiment=request.form.get("human_sentiment"),
                    emotion_judgment=request.form.get("emotion_judgment"),
                    human_dominant_emotion=request.form.get(
                        "human_dominant_emotion"
                    ),
                    human_secondary_emotions=request.form.getlist(
                        "human_secondary_emotions"
                    ),
                    note=request.form.get("review_note", ""),
                )
        except ValidationError as error:
            return render_review(
                token,
                workspace,
                row_number,
                error_message=error.message,
                submitted=True,
                status=400,
            )

        replacement = BatchWorkspace(
            preview=workspace.preview,
            result=workspace.result,
            reviews=updated,
        )
        if not batch_store.replace(token, replacement):
            return Response("This temporary review expired or was cleared.", 404)
        review_filter, sentiment_filter, emotion_filter = review_filters()
        filtered = filter_review_cases(
            workspace.result,
            updated,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        navigation = review_navigation(
            workspace.result,
            updated,
            current_record_id=current.review.record_id,
            filtered_cases=filtered,
        )
        target = (
            navigation.next_unreviewed_row
            if action == "next_unreviewed"
            else navigation.next_row
        )
        return redirect(
            url_for(
                "review_record",
                token=token,
                row_number=target or row_number,
                review=review_filter,
                sentiment=sentiment_filter,
                emotion=emotion_filter,
            )
        )

    @app.get("/batch/<token>/export.csv")
    def batch_export(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.result is None:
            return Response("Batch result not found.", status=404)
        include_native = request.args.get("native") == "1"
        content = export_batch_csv(
            workspace.result,
            include_native=include_native,
        )
        response = Response(content, mimetype="text/csv")
        response.headers["Content-Disposition"] = (
            "attachment; filename=sti-batch-results.csv"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/batch/<token>/clear")
    def batch_clear(token: str) -> ResponseReturnValue:
        batch_store.delete(token)
        return redirect(url_for("batch_home"))

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local STI Flask interface.")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cache-dir", default="model_cache")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--max-batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    parser.add_argument("--max-batch-rows", type=int, default=DEFAULT_MAX_BATCH_ROWS)
    parser.add_argument("--max-text-length", type=int, default=20_000)
    parser.add_argument(
        "--emotion-threshold", type=float, default=DEFAULT_EMOTION_THRESHOLD
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65_535:
        parser.error("--port must be between 1 and 65535.")
    if min(args.max_batch_bytes, args.max_batch_rows, args.max_text_length) < 1:
        parser.error("Batch and text limits must be positive integers.")
    app = create_app(
        {
            "CACHE_DIR": args.cache_dir,
            "OFFLINE": args.offline,
            "EMOTION_THRESHOLD": args.emotion_threshold,
            "MAX_BATCH_BYTES": args.max_batch_bytes,
            "MAX_BATCH_ROWS": args.max_batch_rows,
            "MAX_TEXT_LENGTH": args.max_text_length,
        }
    )
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0
