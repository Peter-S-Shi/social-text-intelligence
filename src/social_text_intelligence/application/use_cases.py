"""Shared V2 application use cases, independent of a presentation framework."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from ..contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
)
from ..contracts.errors import (
    ProviderError,
    SocialTextIntelligenceError,
    ValidationError,
)
from ..services import (
    ContextTag,
    ExampleMode,
    GroupingDimension,
    GroupMetricSummary,
    InsightMetric,
    InsightPerspective,
    InsightSelection,
    InsightState,
    RepresentativeExample,
    ReviewCase,
    ReviewSummary,
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
    parse_insight_filters,
    prepare_csv_batch,
    review_cases,
    review_navigation,
    select_representative_examples,
    summarize_reviews,
    update_review,
)
from ..services.batch import BatchCancelled, BatchOutcome, BatchProgress
from ..services.review import ReviewNavigation
from .projects import BatchWorkspace, ProjectRepository, WorkspaceMutationConflict
from .settings import AnalysisGateway

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


@dataclass(frozen=True, slots=True)
class ReviewDetails:
    current: ReviewCase
    position: int
    queue_total: int
    filtered_count: int
    navigation: ReviewNavigation
    summary: ReviewSummary


@dataclass(frozen=True, slots=True)
class InsightView:
    """Resolved view state; a presentation adapter decides how to render it."""

    selection: InsightSelection
    group_values: tuple[str, ...]
    summaries: tuple[GroupMetricSummary, ...]
    insight_state: InsightState
    examples: tuple[RepresentativeExample, ...]
    example_mode: ExampleMode
    example_emotion: EmotionLabel
    example_tag: ContextTag | None
    selected_record_ids: frozenset[str]
    association_values: dict[str, tuple[str, ...]]
    first_report: AnalysisReport
    successful_outcomes: tuple[BatchOutcome, ...]
    error_message: str | None


class ApplicationUseCases:
    """One orchestration interface for current web and future presentation adapters."""

    def __init__(
        self, projects: ProjectRepository, analysis_gateway: AnalysisGateway | None
    ) -> None:
        self.projects = projects
        self.analysis_gateway = analysis_gateway

    @staticmethod
    def safe_error(error: Exception) -> str:
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

    def analyze_text(self, text: str, *, max_text_length: int) -> AnalysisReport:
        assert self.analysis_gateway is not None
        record = NormalizedTextInput.from_text(
            text, language="en", max_text_length=max_text_length
        )
        return self.analysis_gateway.analyze(record)

    def upload_batch(
        self,
        content: bytes,
        *,
        max_bytes: int,
        max_rows: int,
        max_text_length: int,
    ) -> str:
        pending = inspect_csv_upload(content, max_bytes=max_bytes)
        if "text" in pending.headers:
            preview = prepare_csv_batch(
                pending,
                text_column="text",
                max_rows=max_rows,
                max_text_length=max_text_length,
            )
            return self.projects.create(BatchWorkspace(preview=preview))
        return self.projects.create(BatchWorkspace(pending=pending))

    def select_batch_column(
        self, token: str, column: str, *, max_rows: int, max_text_length: int
    ) -> BatchWorkspace | None:
        def select(current: BatchWorkspace) -> BatchWorkspace:
            if current.pending is None:
                raise WorkspaceMutationConflict(
                    "This Batch setup changed in another request. Reload "
                    "the current workspace before selecting a column."
                )
            preview = prepare_csv_batch(
                current.pending,
                text_column=column,
                max_rows=max_rows,
                max_text_length=max_text_length,
            )
            return BatchWorkspace(preview=preview)

        return self.projects.mutate(token, select)

    def analyze_workspace(
        self,
        token: str,
        *,
        progress: Callable[[BatchProgress], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> bool | None:
        """Return None for missing preview, False for stale lease, True on commit."""

        assert self.analysis_gateway is not None
        lease = self.projects.begin_analysis(token)
        if lease is None:
            return None
        committed = False
        try:
            if lease.workspace.preview is None:
                return None
            result = analyze_batch(
                lease.workspace.preview,
                self.analysis_gateway,
                progress=progress,
                cancelled=cancelled,
            )
            if cancelled is not None and cancelled():
                raise BatchCancelled()
            committed = self.projects.complete_analysis(
                lease,
                BatchWorkspace(
                    preview=lease.workspace.preview,
                    result=result,
                    reviews=create_review_state(result),
                    insights=InsightState(),
                ),
            )
            return committed
        finally:
            if not committed:
                self.projects.cancel_analysis(lease)

    def review_index(
        self,
        token: str,
        *,
        review_filter: str,
        sentiment_filter: str,
        emotion_filter: str,
    ) -> int | None:
        workspace = self.projects.get(token)
        if workspace is None or workspace.result is None or workspace.reviews is None:
            return None
        cases = filter_review_cases(
            workspace.result,
            workspace.reviews,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if not cases:
            cases = review_cases(workspace.result, workspace.reviews)
        return cases[0].outcome.prepared.row_number if cases else None

    @staticmethod
    def review_details(
        workspace: BatchWorkspace,
        row_number: int,
        *,
        review_filter: str,
        sentiment_filter: str,
        emotion_filter: str,
    ) -> ReviewDetails | None:
        result = workspace.result
        state = workspace.reviews
        if result is None or state is None:
            return None
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
            return None
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
        return ReviewDetails(
            current=current,
            position=position,
            queue_total=len(all_cases),
            filtered_count=len(filtered),
            navigation=navigation,
            summary=summarize_reviews(result, state),
        )

    def save_review(
        self,
        token: str,
        row_number: int,
        *,
        action: str,
        values: Mapping[str, str],
        secondary_emotions: Sequence[str],
        review_filter: str,
        sentiment_filter: str,
        emotion_filter: str,
    ) -> int | None:
        workspace = self.projects.get(token)
        if workspace is None:
            return None
        details = self.review_details(
            workspace,
            row_number,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if details is None:
            return None
        record_id = details.current.review.record_id

        def change(current: BatchWorkspace) -> BatchWorkspace:
            assert current.result is not None and current.reviews is not None
            if action == "accept_both":
                updated = accept_both(
                    current.result,
                    current.reviews,
                    record_id=record_id,
                    note=values.get("review_note", ""),
                )
            else:
                updated = update_review(
                    current.result,
                    current.reviews,
                    record_id=record_id,
                    sentiment_judgment=values.get("sentiment_judgment"),
                    human_sentiment=values.get("human_sentiment"),
                    emotion_judgment=values.get("emotion_judgment"),
                    human_dominant_emotion=values.get("human_dominant_emotion"),
                    human_secondary_emotions=secondary_emotions,
                    note=values.get("review_note", ""),
                )
            return replace(current, reviews=updated)

        replacement = self.projects.mutate(token, change)
        if replacement is None:
            return None
        assert replacement.result is not None and replacement.reviews is not None
        filtered = filter_review_cases(
            replacement.result,
            replacement.reviews,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        navigation = review_navigation(
            replacement.result,
            replacement.reviews,
            current_record_id=record_id,
            filtered_cases=filtered,
        )
        target = (
            navigation.next_unreviewed_row
            if action == "next_unreviewed"
            else navigation.next_row
        )
        return target or row_number

    @staticmethod
    def requested_insight_selection(
        workspace: BatchWorkspace,
        values: Mapping[str, str],
        groups: Sequence[str],
        *,
        comparison: bool,
        default_agreement: bool = False,
    ) -> tuple[InsightSelection, tuple[str, ...]]:
        assert workspace.result is not None
        saved = workspace.insights.selection if workspace.insights else None
        default_grouping = saved.grouping if saved else GroupingDimension.TOPIC
        try:
            grouping = GroupingDimension(values.get("grouping", default_grouping))
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
        selected_groups = tuple(groups)
        if not selected_groups:
            saved_groups = (
                tuple(group for group in saved.groups if group in group_values)
                if saved is not None and saved.grouping is grouping
                else ()
            )
            if comparison and not 2 <= len(saved_groups) <= 4:
                selected_groups = group_values[:2]
            else:
                selected_groups = saved_groups or group_values[:1]

        default_perspective = (
            InsightPerspective.AGREEMENT
            if default_agreement
            else (saved.perspective if saved else InsightPerspective.AI)
        )
        try:
            perspective = InsightPerspective(
                values.get("perspective", default_perspective)
            )
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
            metric = InsightMetric(values.get("metric", default_metric))
        except ValueError as error:
            raise ValidationError(
                field="metric",
                code="invalid_metric",
                message="Select a supported insight metric.",
            ) from error
        filters = parse_insight_filters(
            sentiment=values.get(
                "sentiment",
                saved.filters.sentiment.value
                if saved and saved.filters.sentiment
                else "",
            ),
            emotion=values.get(
                "emotion",
                saved.filters.emotion.value if saved and saved.filters.emotion else "",
            ),
            date_from=values.get(
                "date_from",
                saved.filters.date_from.isoformat()
                if saved and saved.filters.date_from
                else "",
            ),
            date_to=values.get(
                "date_to",
                saved.filters.date_to.isoformat()
                if saved and saved.filters.date_to
                else "",
            ),
        )
        return (
            InsightSelection(grouping, selected_groups, perspective, metric, filters),
            group_values,
        )

    def save_insight_selection(
        self, token: str, selection: InsightSelection
    ) -> BatchWorkspace | None:
        def change(current: BatchWorkspace) -> BatchWorkspace:
            return replace(
                current,
                insights=InsightState(
                    notes=current.insights.notes
                    if current.insights is not None
                    else (),
                    selection=selection,
                ),
            )

        return self.projects.mutate(token, change)

    def add_note(
        self,
        token: str,
        values: Mapping[str, str],
        tags: Sequence[str],
    ) -> BatchWorkspace | None:
        def change(current: BatchWorkspace) -> BatchWorkspace:
            assert current.insights is not None and current.result is not None
            updated = add_context_note(
                current.insights,
                current.result,
                association=values.get("association", ""),
                association_value=values.get("association_value", ""),
                phrase=values.get("phrase", ""),
                explanation=values.get("explanation", ""),
                context_importance=values.get("context_importance", ""),
                tags=tags,
            )
            return replace(current, insights=updated)

        return self.projects.mutate(token, change)

    def remove_note(self, token: str, note_id: str) -> BatchWorkspace | None:
        def change(current: BatchWorkspace) -> BatchWorkspace:
            assert current.insights is not None
            return replace(
                current,
                insights=delete_context_note(current.insights, note_id=note_id),
            )

        return self.projects.mutate(token, change)

    @staticmethod
    def export_batch(workspace: BatchWorkspace, *, include_native: bool) -> str:
        assert workspace.result is not None
        return export_batch_csv(workspace.result, include_native=include_native)

    @staticmethod
    def export_reviews(workspace: BatchWorkspace, *, include_native: bool) -> str:
        assert workspace.result is not None and workspace.reviews is not None
        return export_reviewed_csv(
            workspace.result, workspace.reviews, include_native=include_native
        )

    @staticmethod
    def export_insights(
        workspace: BatchWorkspace,
        selection: InsightSelection,
        *,
        comparison: bool,
        include_records: bool,
        include_native: bool,
    ) -> str:
        assert workspace.result is not None
        assert workspace.reviews is not None
        assert workspace.insights is not None
        if comparison:
            build_group_metrics(
                workspace.result, workspace.reviews, selection, comparison=True
            )
        return export_insights_csv(
            workspace.result,
            workspace.reviews,
            workspace.insights,
            selection,
            include_records=include_records,
            include_native=include_native,
        )

    def resolve_insights(
        self,
        token: str,
        workspace: BatchWorkspace,
        values: Mapping[str, str],
        groups: Sequence[str],
        record_ids: Sequence[str],
        *,
        comparison: bool,
        default_agreement: bool = False,
        error_message: str | None = None,
    ) -> InsightView | None:
        result = workspace.result
        reviews = workspace.reviews
        insight_state = workspace.insights
        if result is None or reviews is None or insight_state is None:
            return None
        if not any(outcome.report is not None for outcome in result.outcomes):
            return None
        try:
            selection, group_values = self.requested_insight_selection(
                workspace,
                values,
                groups,
                comparison=comparison,
                default_agreement=default_agreement,
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

        if (
            InsightState(notes=insight_state.notes, selection=selection)
            != insight_state
        ):
            replacement = self.save_insight_selection(token, selection)
            if replacement is None:
                return None
            assert replacement.result is not None
            assert replacement.reviews is not None
            assert replacement.insights is not None
            result = replacement.result
            reviews = replacement.reviews
            insight_state = replacement.insights

        try:
            example_mode = ExampleMode(
                values.get("example_mode", ExampleMode.LOWEST_AI_CONFIDENCE)
            )
            example_emotion = EmotionLabel(
                values.get("example_emotion", EmotionLabel.ANGER)
            )
            tag_value = values.get("example_tag", "")
            example_tag = ContextTag(tag_value) if tag_value else None
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
            record_ids=record_ids,
        )
        selected_record_ids = (
            frozenset(record_ids)
            if example_mode is ExampleMode.USER_SELECTED
            else frozenset()
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
            "community": available_group_values(result, GroupingDimension.COMMUNITY),
            "source_label": available_group_values(
                result, GroupingDimension.SOURCE_LABEL
            ),
        }
        return InsightView(
            selection=selection,
            group_values=group_values,
            summaries=summaries,
            insight_state=insight_state,
            examples=examples,
            example_mode=example_mode,
            example_emotion=example_emotion,
            example_tag=example_tag,
            selected_record_ids=selected_record_ids,
            association_values=association_values,
            first_report=first_report,
            successful_outcomes=tuple(
                outcome for outcome in result.outcomes if outcome.report is not None
            ),
            error_message=error_message,
        )
