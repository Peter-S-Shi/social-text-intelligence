"""Privacy-conscious local Flask interface for direct text analysis."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, Response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import RequestEntityTooLarge, SecurityError

from ..application.language import (
    describe_language,
    describe_summary,
    language_short,
    summarize_languages,
    summarize_result,
)
from ..application.projects import InMemoryProjectRepository
from ..application.settings import AnalysisGateway, AppSettings, build_analysis_service
from ..application.use_cases import (
    INSIGHT_METRICS_BY_PERSPECTIVE,
    ApplicationUseCases,
)
from ..contracts import (
    AnalysisReport,
    EmotionLabel,
    SentimentLabel,
)
from ..contracts.errors import (
    SocialTextIntelligenceError,
    ValidationError,
)
from ..providers.samlowe_emotion import DEFAULT_EMOTION_THRESHOLD
from ..services import (
    ContextAssociation,
    ContextTag,
    ExampleMode,
    GroupingDimension,
    HumanReview,
    InsightPerspective,
    InsightSelection,
    ModerationLimits,
    TriageLimits,
    load_moderation_cases,
    load_moderation_policy,
    load_support_tickets,
    load_triage_guide,
)
from ..services.batch import DEFAULT_MAX_BATCH_BYTES, DEFAULT_MAX_BATCH_ROWS
from ..services.insights import METRIC_DEFINITIONS
from .batch_state import BatchWorkspace
from .moderation_routes import moderation
from .moderation_state import EphemeralModerationStore
from .triage_routes import triage
from .triage_state import EphemeralTriageStore
from .workspace_mutation import WorkspaceMutationConflict

TRUSTED_LOCAL_HOSTS = ("127.0.0.1", "localhost")
UNSAFE_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "connect-src 'self'",
        "font-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "img-src 'self'",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
    )
)


def _effective_origin(value: str, *, allow_path: bool) -> tuple[str, str, int] | None:
    """Return a strict HTTP origin tuple without trusting proxy headers."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (not allow_path and (parsed.path not in {"", "/"} or parsed.query))
    ):
        return None
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname.lower(), port


def _same_request_origin(value: str, *, allow_path: bool) -> bool:
    candidate = _effective_origin(value, allow_path=allow_path)
    current = _effective_origin(request.host_url, allow_path=False)
    return candidate is not None and candidate == current


DEFAULT_MAX_REQUEST_BYTES = 3 * 1024 * 1024


def create_app(
    config: Mapping[str, Any] | None = None,
    *,
    analysis_gateway: AnalysisGateway | None = None,
) -> Flask:
    """Create the local app without loading either model."""

    app = Flask(__name__)
    # The same wording the desktop shows for the language check.
    app.jinja_env.globals["language_notice"] = describe_language
    app.jinja_env.globals["language_summary_notice"] = lambda result: describe_summary(
        summarize_result(result)
    )
    app.jinja_env.globals["language_outcomes_notice"] = lambda outcomes: (
        describe_summary(
            summarize_languages(o.report.language for o in outcomes if o.report)
        )
    )
    app.jinja_env.globals["language_short"] = language_short
    app.config.from_mapping(
        CACHE_DIR="model_cache",
        OFFLINE=False,
        EMOTION_THRESHOLD=DEFAULT_EMOTION_THRESHOLD,
        MAX_TEXT_LENGTH=20_000,
        MAX_CONTENT_LENGTH=DEFAULT_MAX_REQUEST_BYTES,
        TRUSTED_HOSTS=TRUSTED_LOCAL_HOSTS,
        MAX_BATCH_BYTES=DEFAULT_MAX_BATCH_BYTES,
        MAX_BATCH_ROWS=DEFAULT_MAX_BATCH_ROWS,
        BATCH_WORKSPACE_TTL_SECONDS=30 * 60,
        BATCH_WORKSPACE_CAPACITY=8,
        MODERATION_WORKSPACE_TTL_SECONDS=30 * 60,
        MODERATION_WORKSPACE_CAPACITY=8,
        MAX_MODERATION_PREPARED_CASES=100,
        MAX_MODERATION_SESSION_CASES=50,
        MAX_MODERATION_SESSION_ATTEMPTS=20,
        TRIAGE_WORKSPACE_TTL_SECONDS=30 * 60,
        TRIAGE_WORKSPACE_CAPACITY=8,
        MAX_TRIAGE_TICKETS=200,
    )
    if config is not None:
        app.config.update(config)

    settings = AppSettings(
        cache_dir=Path(str(app.config["CACHE_DIR"])),
        offline=bool(app.config["OFFLINE"]),
        emotion_threshold=float(app.config["EMOTION_THRESHOLD"]),
        max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
        max_request_bytes=int(app.config["MAX_CONTENT_LENGTH"]),
        max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
        max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
        workspace_ttl_seconds=int(app.config["BATCH_WORKSPACE_TTL_SECONDS"]),
        workspace_capacity=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
    )

    if analysis_gateway is None:
        analysis_gateway = build_analysis_service(settings)
    app.extensions["sti_analysis_gateway"] = analysis_gateway
    batch_store = InMemoryProjectRepository(
        ttl_seconds=settings.workspace_ttl_seconds,
        capacity=settings.workspace_capacity,
    )
    app.extensions["sti_batch_store"] = batch_store
    use_cases = ApplicationUseCases(batch_store, analysis_gateway)
    app.extensions["sti_use_cases"] = use_cases
    moderation_policy = load_moderation_policy()
    app.extensions["sti_moderation_policy"] = moderation_policy
    app.extensions["sti_moderation_cases"] = load_moderation_cases(moderation_policy)
    app.extensions["sti_moderation_limits"] = ModerationLimits(
        max_prepared_cases=int(app.config["MAX_MODERATION_PREPARED_CASES"]),
        max_session_cases=int(app.config["MAX_MODERATION_SESSION_CASES"]),
        max_session_attempts=int(app.config["MAX_MODERATION_SESSION_ATTEMPTS"]),
    )
    app.extensions["sti_moderation_store"] = EphemeralModerationStore(
        ttl_seconds=int(app.config["MODERATION_WORKSPACE_TTL_SECONDS"]),
        capacity=int(app.config["MODERATION_WORKSPACE_CAPACITY"]),
    )
    app.register_blueprint(moderation)
    triage_guide = load_triage_guide()
    app.extensions["sti_triage_guide"] = triage_guide
    app.extensions["sti_support_tickets"] = load_support_tickets(triage_guide)
    app.extensions["sti_triage_limits"] = TriageLimits(
        max_tickets=int(app.config["MAX_TRIAGE_TICKETS"])
    )
    app.extensions["sti_triage_store"] = EphemeralTriageStore(
        ttl_seconds=int(app.config["TRIAGE_WORKSPACE_TTL_SECONDS"]),
        capacity=int(app.config["TRIAGE_WORKSPACE_CAPACITY"]),
    )
    app.register_blueprint(triage)

    @app.after_request
    def apply_browser_response_boundaries(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.before_request
    def enforce_local_browser_boundary() -> Response | None:
        routing_error = request.routing_exception
        if isinstance(routing_error, SecurityError):
            raise routing_error
        if request.method not in UNSAFE_HTTP_METHODS:
            return None

        origin = request.headers.get("Origin")
        if origin is not None:
            if origin.strip().lower() == "null" or not _same_request_origin(
                origin.strip(), allow_path=False
            ):
                return Response(
                    "Cross-origin unsafe request rejected. No submitted "
                    "content was processed or saved.",
                    status=403,
                    mimetype="text/plain",
                )
            return None

        referer = request.headers.get("Referer")
        if referer is not None and not _same_request_origin(
            referer.strip(), allow_path=True
        ):
            return Response(
                "Cross-origin unsafe request rejected. No submitted content "
                "was processed or saved.",
                status=403,
                mimetype="text/plain",
            )
        # A request with neither header is treated as a local non-browser client.
        # The trusted Host boundary still applies.
        return None

    @app.before_request
    def enforce_declared_request_body_limit() -> None:
        content_length = request.content_length
        if content_length is not None and content_length > settings.max_request_bytes:
            raise RequestEntityTooLarge()

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error: RequestEntityTooLarge) -> Response:
        return Response(
            "Request too large. The submitted HTTP request exceeded the "
            f"{settings.max_request_bytes}-byte request-body limit. No submitted "
            "content was processed or saved.",
            status=413,
            mimetype="text/plain",
        )

    @app.errorhandler(SecurityError)
    def untrusted_host(_error: SecurityError) -> Response:
        return Response(
            "Request rejected because the Host is not an approved loopback "
            "host. No submitted content was processed or saved.",
            status=400,
            mimetype="text/plain",
        )

    @app.route("/", methods=["GET", "POST"])
    def analyze_text() -> str:
        report: AnalysisReport | None = None
        error_message: str | None = None
        text = ""
        if request.method == "POST":
            text = request.form.get("text", "")
            try:
                report = use_cases.analyze_text(
                    text, max_text_length=settings.max_text_length
                )
            # The interface boundary must never expose traceback text.
            except Exception as error:
                error_message = use_cases.safe_error(error)

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
            max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
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
                max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
            )
        try:
            content = upload.stream.read(int(app.config["MAX_BATCH_BYTES"]) + 1)
            token = use_cases.upload_batch(
                content,
                max_bytes=settings.max_batch_bytes,
                max_rows=settings.max_batch_rows,
                max_text_length=settings.max_text_length,
            )
        except RuntimeError as error:
            return (
                render_template(
                    "batch.html",
                    error_message=str(error),
                    offline=bool(app.config["OFFLINE"]),
                    max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
                    max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
                    max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                    max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
                ),
                409,
            )
        except Exception as error:
            return render_template(
                "batch.html",
                error_message=use_cases.safe_error(error),
                offline=bool(app.config["OFFLINE"]),
                max_batch_bytes=int(app.config["MAX_BATCH_BYTES"]),
                max_batch_rows=int(app.config["MAX_BATCH_ROWS"]),
                max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
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
                    max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
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
            max_batch_workspaces=int(app.config["BATCH_WORKSPACE_CAPACITY"]),
        )

    @app.post("/batch/<token>/select")
    def batch_select_column(token: str) -> ResponseReturnValue:
        try:
            updated = use_cases.select_batch_column(
                token,
                request.form.get("text_column", ""),
                max_rows=settings.max_batch_rows,
                max_text_length=settings.max_text_length,
            )
        except WorkspaceMutationConflict as error:
            return Response(str(error), status=409)
        except SocialTextIntelligenceError:
            return redirect(url_for("batch_workspace", token=token))
        if updated is None:
            return redirect(url_for("batch_workspace", token=token))
        return redirect(url_for("batch_workspace", token=token))

    @app.post("/batch/<token>/analyze")
    def batch_analyze(token: str) -> ResponseReturnValue:
        try:
            committed = use_cases.analyze_workspace(token)
        except RuntimeError as error:
            return Response(str(error), status=409)
        if committed is None:
            return redirect(url_for("batch_workspace", token=token))
        if not committed:
            return Response(
                "Batch analysis finished, but its result could not be saved "
                "because the workspace state changed. No success was recorded; "
                "return to Batch CSV and retry with a current workspace.",
                status=409,
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
                "sentiment_judgment": request.form.get("sentiment_judgment", ""),
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
        review_filter, sentiment_filter, emotion_filter = review_filters()
        details = use_cases.review_details(
            workspace,
            row_number,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if details is None:
            return Response("Review record not found.", status=404)
        return (
            render_template(
                "review.html",
                token=token,
                current=details.current,
                position=details.position,
                queue_total=details.queue_total,
                filtered_count=details.filtered_count,
                navigation=details.navigation,
                summary=details.summary,
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
                form_values=review_form_values(
                    details.current.review, submitted=submitted
                ),
                error_message=error_message,
                max_review_note_length=2_000,
            ),
            status,
        )

    @app.get("/batch/<token>/review")
    def review_index(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.result is None or workspace.reviews is None:
            return Response("Review workspace not found.", status=404)
        review_filter, sentiment_filter, emotion_filter = review_filters()
        row_number = use_cases.review_index(
            token,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if row_number is None:
            return Response("No successful batch rows are available for review.", 404)
        return redirect(
            url_for(
                "review_record",
                token=token,
                row_number=row_number,
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
        if workspace is None or workspace.result is None or workspace.reviews is None:
            return Response("This temporary review expired or was cleared.", 404)
        if (
            use_cases.review_details(
                workspace,
                row_number,
                review_filter="all",
                sentiment_filter="all",
                emotion_filter="all",
            )
            is None
        ):
            return Response("Review record not found.", status=404)
        action = request.form.get("action", "save_next")
        review_filter, sentiment_filter, emotion_filter = review_filters()
        try:
            target = use_cases.save_review(
                token,
                row_number,
                action=action,
                values=request.form,
                secondary_emotions=request.form.getlist("human_secondary_emotions"),
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
            )
        except WorkspaceMutationConflict as error:
            return Response(str(error), status=409)
        except ValidationError as error:
            current_workspace = batch_store.get(token)
            if current_workspace is None:
                return Response("This temporary review expired or was cleared.", 404)
            return render_review(
                token,
                current_workspace,
                row_number,
                error_message=error.message,
                submitted=True,
                status=400,
            )
        if target is None:
            return Response("This temporary review expired or was cleared.", 404)
        return redirect(
            url_for(
                "review_record",
                token=token,
                row_number=target,
                review=review_filter,
                sentiment=sentiment_filter,
                emotion=emotion_filter,
            )
        )

    def requested_insight_selection(
        workspace: BatchWorkspace, *, comparison: bool
    ) -> tuple[InsightSelection, tuple[str, ...]]:
        return use_cases.requested_insight_selection(
            workspace,
            request.values,
            request.values.getlist("group"),
            comparison=comparison,
            default_agreement=request.values.get("view") == "agreement",
        )

    def render_insights(
        token: str,
        workspace: BatchWorkspace,
        *,
        error_message: str | None = None,
        status: int = 200,
    ) -> ResponseReturnValue:
        if (
            workspace.result is None
            or workspace.reviews is None
            or workspace.insights is None
        ):
            return Response("Insight workspace not found.", status=404)
        if not any(outcome.report is not None for outcome in workspace.result.outcomes):
            return Response("No successful rows are available for insights.", 404)
        view = request.values.get("view", "explorer")
        if view not in {
            "explorer",
            "comparison",
            "agreement",
            "notes",
            "examples",
            "export",
        }:
            view = "explorer"
        try:
            resolved = use_cases.resolve_insights(
                token,
                workspace,
                request.values,
                request.values.getlist("group"),
                request.values.getlist("record_id"),
                comparison=view == "comparison",
                default_agreement=view == "agreement",
                error_message=error_message,
            )
        except WorkspaceMutationConflict as error:
            return Response(str(error), status=409)
        if resolved is None:
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        return (
            render_template(
                "insights.html",
                token=token,
                view=view,
                selection=resolved.selection,
                group_values=resolved.group_values,
                summaries=resolved.summaries,
                metric_definition=METRIC_DEFINITIONS[resolved.selection.metric],
                metrics_by_perspective=INSIGHT_METRICS_BY_PERSPECTIVE,
                grouping_options=tuple(GroupingDimension),
                perspectives=tuple(InsightPerspective),
                context_associations=tuple(ContextAssociation),
                context_tags=tuple(ContextTag),
                association_values=resolved.association_values,
                insight_state=resolved.insight_state,
                examples=resolved.examples,
                example_modes=tuple(ExampleMode),
                example_mode=resolved.example_mode,
                example_emotion=resolved.example_emotion,
                example_tag=resolved.example_tag,
                selected_record_ids=resolved.selected_record_ids,
                emotion_labels=tuple(EmotionLabel),
                sentiment_labels=tuple(SentimentLabel),
                first_report=resolved.first_report,
                successful_outcomes=resolved.successful_outcomes,
                error_message=resolved.error_message,
                query_sentiment=resolved.selection.filters.sentiment or "",
                query_emotion=resolved.selection.filters.emotion or "",
                query_date_from=resolved.selection.filters.date_from or "",
                query_date_to=resolved.selection.filters.date_to or "",
            ),
            status,
        )

    @app.get("/batch/<token>/insights")
    def insights(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None:
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        return render_insights(token, workspace)

    @app.post("/batch/<token>/insights/notes")
    def save_context_note(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if (
            workspace is None
            or workspace.result is None
            or workspace.reviews is None
            or workspace.insights is None
        ):
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        try:
            replacement = use_cases.add_note(
                token, request.form, request.form.getlist("tags")
            )
        except WorkspaceMutationConflict as error:
            return Response(str(error), status=409)
        except ValidationError as error:
            current_workspace = batch_store.get(token)
            if current_workspace is None:
                return Response(
                    "This temporary insight workspace expired or was cleared.",
                    404,
                )
            return render_insights(
                token,
                current_workspace,
                error_message=error.message,
                status=400,
            )
        if replacement is None:
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        return redirect(url_for("insights", token=token, view="notes"))

    @app.post("/batch/<token>/insights/notes/<note_id>/delete")
    def remove_context_note(token: str, note_id: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.insights is None:
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        try:
            replacement = use_cases.remove_note(token, note_id)
        except WorkspaceMutationConflict as error:
            return Response(str(error), status=409)
        except ValidationError as error:
            current_workspace = batch_store.get(token)
            if current_workspace is None:
                return Response(
                    "This temporary insight workspace expired or was cleared.",
                    404,
                )
            return render_insights(
                token,
                current_workspace,
                error_message=error.message,
                status=404,
            )
        if replacement is None:
            return Response(
                "This temporary insight workspace expired or was cleared.", 404
            )
        return redirect(url_for("insights", token=token, view="notes"))

    @app.get("/batch/<token>/insights/export.csv")
    def insights_export(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if (
            workspace is None
            or workspace.result is None
            or workspace.reviews is None
            or workspace.insights is None
        ):
            return Response("Insight workspace not found.", status=404)
        try:
            selection, _ = requested_insight_selection(
                workspace, comparison=request.args.get("view") == "comparison"
            )
            content = use_cases.export_insights(
                workspace,
                selection,
                comparison=request.args.get("view") == "comparison",
                include_records=request.args.get("records") == "1",
                include_native=request.args.get("native") == "1",
            )
        except ValidationError as error:
            return Response(error.message, status=400)
        response = Response(content, mimetype="text/csv")
        response.headers["Content-Disposition"] = (
            "attachment; filename=sti-insights.csv"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/batch/<token>/export.csv")
    def batch_export(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.result is None:
            return Response("Batch result not found.", status=404)
        include_native = request.args.get("native") == "1"
        content = use_cases.export_batch(workspace, include_native=include_native)
        response = Response(content, mimetype="text/csv")
        response.headers["Content-Disposition"] = (
            "attachment; filename=sti-batch-results.csv"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/batch/<token>/review/export.csv")
    def review_export(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if workspace is None or workspace.result is None or workspace.reviews is None:
            return Response("Reviewed batch result not found.", status=404)
        include_native = request.args.get("native") == "1"
        content = use_cases.export_reviews(workspace, include_native=include_native)
        response = Response(content, mimetype="text/csv")
        response.headers["Content-Disposition"] = (
            "attachment; filename=sti-reviewed-results.csv"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/batch/<token>/clear")
    def batch_clear(token: str) -> ResponseReturnValue:
        if request.form.get("confirm") != "clear":
            return Response(
                "Confirm the destructive clear action before removing this "
                "temporary batch.",
                status=400,
            )
        try:
            batch_store.delete(token)
        except RuntimeError as error:
            return Response(str(error), status=409)
        return redirect(url_for("batch_home"))

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local STI Flask interface.")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cache-dir", default="model_cache")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--max-batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    parser.add_argument(
        "--max-request-bytes", type=int, default=DEFAULT_MAX_REQUEST_BYTES
    )
    parser.add_argument("--max-batch-rows", type=int, default=DEFAULT_MAX_BATCH_ROWS)
    parser.add_argument("--max-text-length", type=int, default=20_000)
    parser.add_argument("--max-prepared-cases", type=int, default=100)
    parser.add_argument("--max-session-cases", type=int, default=50)
    parser.add_argument("--max-session-attempts", type=int, default=20)
    parser.add_argument(
        "--emotion-threshold", type=float, default=DEFAULT_EMOTION_THRESHOLD
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65_535:
        parser.error("--port must be between 1 and 65535.")
    if (
        min(
            args.max_batch_bytes,
            args.max_request_bytes,
            args.max_batch_rows,
            args.max_text_length,
            args.max_prepared_cases,
            args.max_session_cases,
            args.max_session_attempts,
        )
        < 1
    ):
        parser.error("Batch, text, and moderation limits must be positive.")
    if args.max_request_bytes <= args.max_batch_bytes:
        parser.error(
            "--max-request-bytes must be greater than --max-batch-bytes "
            "to allow multipart encoding overhead."
        )
    app = create_app(
        {
            "CACHE_DIR": args.cache_dir,
            "OFFLINE": args.offline,
            "EMOTION_THRESHOLD": args.emotion_threshold,
            "MAX_BATCH_BYTES": args.max_batch_bytes,
            "MAX_CONTENT_LENGTH": args.max_request_bytes,
            "MAX_BATCH_ROWS": args.max_batch_rows,
            "MAX_TEXT_LENGTH": args.max_text_length,
            "MAX_MODERATION_PREPARED_CASES": args.max_prepared_cases,
            "MAX_MODERATION_SESSION_CASES": args.max_session_cases,
            "MAX_MODERATION_SESSION_ATTEMPTS": args.max_session_attempts,
        }
    )
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0
