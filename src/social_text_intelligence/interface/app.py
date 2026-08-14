"""Privacy-conscious local Flask interface for direct text analysis."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from flask import Flask, Response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ..contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from ..contracts.errors import (
    ProviderError,
    SocialTextIntelligenceError,
    ValidationError,
)
from ..providers import CardiffSentimentProvider, SamLoweEmotionProvider
from ..providers.samlowe_emotion import DEFAULT_EMOTION_THRESHOLD
from ..services import (
    AnalysisService,
    ContextAssociation,
    ContextTag,
    ExampleMode,
    GroupingDimension,
    HumanReview,
    InsightMetric,
    InsightPerspective,
    InsightSelection,
    InsightState,
    LazyAnalysisService,
    ModerationLimits,
    TriageLimits,
    accept_both,
    add_context_note,
    analyze_batch,
    available_group_values,
    build_group_metrics,
    create_review_state,
    delete_context_note,
    export_batch_csv,
    export_insights_csv,
    export_reviewed_csv,
    filter_review_cases,
    inspect_csv_upload,
    load_moderation_cases,
    load_moderation_policy,
    load_support_tickets,
    load_triage_guide,
    parse_insight_filters,
    prepare_csv_batch,
    review_cases,
    review_navigation,
    select_representative_examples,
    summarize_reviews,
    update_review,
)
from ..services.batch import DEFAULT_MAX_BATCH_BYTES, DEFAULT_MAX_BATCH_ROWS
from ..services.insights import METRIC_DEFINITIONS
from .batch_state import BatchWorkspace, EphemeralBatchStore
from .moderation_routes import moderation
from .moderation_state import EphemeralModerationStore
from .triage_routes import triage
from .triage_state import EphemeralTriageStore

INSIGHT_METRICS_BY_PERSPECTIVE = {
    InsightPerspective.AI: (
        InsightMetric.AI_SENTIMENT,
        InsightMetric.AI_DOMINANT_EMOTION,
        InsightMetric.AI_EMOTION_ACTIVATION,
    ),
    InsightPerspective.HUMAN: (
        InsightMetric.HUMAN_SENTIMENT,
        InsightMetric.HUMAN_DOMINANT_EMOTION,
        InsightMetric.HUMAN_EMOTION_INCLUSION,
    ),
    InsightPerspective.AGREEMENT: (
        InsightMetric.SENTIMENT_DISAGREEMENT,
        InsightMetric.DOMINANT_EMOTION_DISAGREEMENT,
        InsightMetric.EMOTION_SET_DISAGREEMENT,
        InsightMetric.REVIEW_COVERAGE,
    ),
}


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
    moderation_policy = load_moderation_policy()
    app.extensions["sti_moderation_policy"] = moderation_policy
    app.extensions["sti_moderation_cases"] = load_moderation_cases(
        moderation_policy
    )
    app.extensions["sti_moderation_limits"] = ModerationLimits(
        max_prepared_cases=int(
            app.config["MAX_MODERATION_PREPARED_CASES"]
        ),
        max_session_cases=int(app.config["MAX_MODERATION_SESSION_CASES"]),
        max_session_attempts=int(
            app.config["MAX_MODERATION_SESSION_ATTEMPTS"]
        ),
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
                insights=InsightState(),
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
            insights=workspace.insights,
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

    def requested_insight_selection(
        workspace: BatchWorkspace, *, comparison: bool
    ) -> tuple[InsightSelection, tuple[str, ...]]:
        assert workspace.result is not None
        saved = workspace.insights.selection if workspace.insights else None
        default_grouping = saved.grouping if saved else GroupingDimension.TOPIC
        grouping_value = request.values.get("grouping", default_grouping)
        try:
            grouping = GroupingDimension(grouping_value)
        except ValueError as error:
            raise ValidationError(
                field="grouping",
                code="unsupported_grouping",
                message="Select a supported trusted metadata grouping.",
            ) from error
        group_values = available_group_values(workspace.result, grouping)
        if not group_values:
            raise ValidationError(
                field="groups",
                code="no_groups",
                message="No successful rows are available for this grouping.",
            )
        groups = tuple(request.values.getlist("group"))
        if not groups:
            saved_groups = (
                tuple(group for group in saved.groups if group in group_values)
                if saved is not None and saved.grouping is grouping
                else ()
            )
            if comparison and not 2 <= len(saved_groups) <= 4:
                groups = group_values[:2]
            else:
                groups = saved_groups or group_values[:1]

        default_perspective = (
            InsightPerspective.AGREEMENT
            if request.values.get("view") == "agreement"
            else (saved.perspective if saved else InsightPerspective.AI)
        )
        perspective_value = request.values.get("perspective", default_perspective)
        try:
            perspective = InsightPerspective(perspective_value)
        except ValueError as error:
            raise ValidationError(
                field="perspective",
                code="invalid_perspective",
                message="Select AI, human-reviewed, or agreement perspective.",
            ) from error
        default_metric = (
            saved.metric
            if saved is not None
            and saved.metric in INSIGHT_METRICS_BY_PERSPECTIVE[perspective]
            else INSIGHT_METRICS_BY_PERSPECTIVE[perspective][0]
        )
        try:
            metric = InsightMetric(request.values.get("metric", default_metric))
        except ValueError as error:
            raise ValidationError(
                field="metric",
                code="invalid_metric",
                message="Select a supported insight metric.",
            ) from error
        filters = parse_insight_filters(
            sentiment=request.values.get(
                "sentiment",
                saved.filters.sentiment.value
                if saved and saved.filters.sentiment
                else "",
            ),
            emotion=request.values.get(
                "emotion",
                saved.filters.emotion.value if saved and saved.filters.emotion else "",
            ),
            date_from=request.values.get(
                "date_from",
                saved.filters.date_from.isoformat()
                if saved and saved.filters.date_from
                else "",
            ),
            date_to=request.values.get(
                "date_to",
                saved.filters.date_to.isoformat()
                if saved and saved.filters.date_to
                else "",
            ),
        )
        return (
            InsightSelection(grouping, groups, perspective, metric, filters),
            group_values,
        )

    def render_insights(
        token: str,
        workspace: BatchWorkspace,
        *,
        error_message: str | None = None,
        status: int = 200,
    ) -> ResponseReturnValue:
        result = workspace.result
        reviews = workspace.reviews
        insight_state = workspace.insights
        if result is None or reviews is None or insight_state is None:
            return Response("Insight workspace not found.", status=404)
        if not any(outcome.report is not None for outcome in result.outcomes):
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
        comparison = view == "comparison"
        try:
            selection, group_values = requested_insight_selection(
                workspace, comparison=comparison
            )
        except ValidationError as error:
            error_message = error_message or error.message
            grouping = GroupingDimension.SOURCE_TYPE
            group_values = available_group_values(result, grouping)
            selection = InsightSelection(
                grouping=grouping,
                groups=group_values[:1],
                perspective=InsightPerspective.AI,
                metric=InsightMetric.AI_SENTIMENT,
            )
        try:
            summaries = build_group_metrics(
                result, reviews, selection, comparison=comparison
            )
        except ValidationError as error:
            error_message = error_message or error.message
            summaries = ()

        updated_insight_state = InsightState(
            notes=insight_state.notes, selection=selection
        )
        if updated_insight_state != insight_state:
            batch_store.replace(
                token,
                BatchWorkspace(
                    preview=workspace.preview,
                    result=result,
                    reviews=reviews,
                    insights=updated_insight_state,
                ),
            )
            insight_state = updated_insight_state

        example_mode_value = request.values.get(
            "example_mode", ExampleMode.LOWEST_AI_CONFIDENCE
        )
        emotion_label_value = request.values.get(
            "example_emotion", EmotionLabel.ANGER
        )
        context_tag_value = request.values.get("example_tag", "")
        try:
            example_mode = ExampleMode(example_mode_value)
            example_emotion = EmotionLabel(emotion_label_value)
            example_tag = ContextTag(context_tag_value) if context_tag_value else None
        except ValueError:
            example_mode = ExampleMode.LOWEST_AI_CONFIDENCE
            example_emotion = EmotionLabel.ANGER
            example_tag = None
            error_message = error_message or "Select a supported example rule."
        examples = select_representative_examples(
            result,
            reviews,
            insight_state,
            mode=example_mode,
            emotion_label=example_emotion,
            context_tag=example_tag,
            record_ids=request.values.getlist("record_id"),
        )
        first_report = next(
            outcome.report for outcome in result.outcomes if outcome.report is not None
        )
        association_values = {
            "record": tuple(
                outcome.prepared.identity
                for outcome in result.outcomes
                if outcome.report is not None
            ),
            "topic": available_group_values(result, GroupingDimension.TOPIC),
            "community": available_group_values(
                result, GroupingDimension.COMMUNITY
            ),
            "source_label": available_group_values(
                result, GroupingDimension.SOURCE_LABEL
            ),
        }
        return (
            render_template(
                "insights.html",
                token=token,
                view=view,
                selection=selection,
                group_values=group_values,
                summaries=summaries,
                metric_definition=METRIC_DEFINITIONS[selection.metric],
                metrics_by_perspective=INSIGHT_METRICS_BY_PERSPECTIVE,
                grouping_options=tuple(GroupingDimension),
                perspectives=tuple(InsightPerspective),
                context_associations=tuple(ContextAssociation),
                context_tags=tuple(ContextTag),
                association_values=association_values,
                insight_state=insight_state,
                examples=examples,
                example_modes=tuple(ExampleMode),
                example_mode=example_mode,
                example_emotion=example_emotion,
                example_tag=example_tag,
                emotion_labels=tuple(EmotionLabel),
                sentiment_labels=tuple(SentimentLabel),
                first_report=first_report,
                successful_outcomes=tuple(
                    outcome for outcome in result.outcomes if outcome.report is not None
                ),
                error_message=error_message,
                query_sentiment=selection.filters.sentiment or "",
                query_emotion=selection.filters.emotion or "",
                query_date_from=selection.filters.date_from or "",
                query_date_to=selection.filters.date_to or "",
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
            updated = add_context_note(
                workspace.insights,
                workspace.result,
                association=request.form.get("association", ""),
                association_value=request.form.get("association_value", ""),
                phrase=request.form.get("phrase", ""),
                explanation=request.form.get("explanation", ""),
                context_importance=request.form.get("context_importance", ""),
                tags=request.form.getlist("tags"),
            )
        except ValidationError as error:
            return render_insights(
                token, workspace, error_message=error.message, status=400
            )
        replacement = BatchWorkspace(
            preview=workspace.preview,
            result=workspace.result,
            reviews=workspace.reviews,
            insights=updated,
        )
        if not batch_store.replace(token, replacement):
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
            updated = delete_context_note(workspace.insights, note_id=note_id)
        except ValidationError as error:
            return render_insights(
                token, workspace, error_message=error.message, status=404
            )
        replacement = BatchWorkspace(
            pending=workspace.pending,
            preview=workspace.preview,
            result=workspace.result,
            reviews=workspace.reviews,
            insights=updated,
        )
        if not batch_store.replace(token, replacement):
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
            if request.args.get("view") == "comparison":
                build_group_metrics(
                    workspace.result,
                    workspace.reviews,
                    selection,
                    comparison=True,
                )
            content = export_insights_csv(
                workspace.result,
                workspace.reviews,
                workspace.insights,
                selection,
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

    @app.get("/batch/<token>/review/export.csv")
    def review_export(token: str) -> ResponseReturnValue:
        workspace = batch_store.get(token)
        if (
            workspace is None
            or workspace.result is None
            or workspace.reviews is None
        ):
            return Response("Reviewed batch result not found.", status=404)
        include_native = request.args.get("native") == "1"
        content = export_reviewed_csv(
            workspace.result,
            workspace.reviews,
            include_native=include_native,
        )
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
            args.max_batch_rows,
            args.max_text_length,
            args.max_prepared_cases,
            args.max_session_cases,
            args.max_session_attempts,
        )
        < 1
    ):
        parser.error("Batch, text, and moderation limits must be positive.")
    app = create_app(
        {
            "CACHE_DIR": args.cache_dir,
            "OFFLINE": args.offline,
            "EMOTION_THRESHOLD": args.emotion_threshold,
            "MAX_BATCH_BYTES": args.max_batch_bytes,
            "MAX_BATCH_ROWS": args.max_batch_rows,
            "MAX_TEXT_LENGTH": args.max_text_length,
            "MAX_MODERATION_PREPARED_CASES": args.max_prepared_cases,
            "MAX_MODERATION_SESSION_CASES": args.max_session_cases,
            "MAX_MODERATION_SESSION_ATTEMPTS": args.max_session_attempts,
        }
    )
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0
