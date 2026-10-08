"""Insights workflow for a presentation layer: view, notes, cases, export.

A thin, typed seam over the shared insight use cases and the insight service. Group
membership, metric denominators, review eligibility, agreement, sample-size
assessment, representative-case selection, note validation, and spreadsheet-safe
export all stay in the service; this module turns a project id and the person's
choices into a read model, validates a request before anything is saved, and maps
errors to typed, content-free ones.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..contracts import AnalysisReport, EmotionLabel, SentimentLabel
from ..contracts.errors import SocialTextIntelligenceError
from ..services.batch import BatchOutcome
from ..services.insights import (
    METRIC_DEFINITIONS,
    ContextAssociation,
    ContextNote,
    ContextTag,
    ExampleMode,
    GroupingDimension,
    GroupMetricSummary,
    InsightMetric,
    InsightPerspective,
    InsightSelection,
    RepresentativeExample,
    SampleSizeLevel,
    available_group_values,
    build_group_metrics,
)
from .project_workflow import ProjectBusyError, ProjectNotFoundError
from .projects import BatchWorkspace, ProjectRepository, WorkspaceMutationConflict
from .use_cases import INSIGHT_METRICS_BY_PERSPECTIVE, ApplicationUseCases


class InsightsUnavailableError(SocialTextIntelligenceError):
    """The project is not analysed, or no row was analysed successfully."""

    def __init__(self) -> None:
        message = (
            "Insights need at least one successfully analysed row. Analyse the "
            "project first."
        )
        super().__init__(message)
        self.code = "insights_unavailable"
        self.message = message


@dataclass(frozen=True, slots=True)
class InsightControls:
    """What the person chose for the grouped view (every field is explicit)."""

    grouping: GroupingDimension
    groups: tuple[str, ...]
    perspective: InsightPerspective
    metric: InsightMetric
    sentiment: SentimentLabel | None = None  # filters on the AI label
    emotion: EmotionLabel | None = None  # filters on the AI dominant emotion
    date_from: str = ""  # YYYY-MM-DD; the service parses and validates it
    date_to: str = ""
    comparison: bool = False

    def as_values(self) -> dict[str, str]:
        return {
            "grouping": self.grouping.value,
            "perspective": self.perspective.value,
            "metric": self.metric.value,
            "sentiment": self.sentiment.value if self.sentiment else "",
            "emotion": self.emotion.value if self.emotion else "",
            "date_from": self.date_from,
            "date_to": self.date_to,
        }

    @classmethod
    def from_selection(
        cls, selection: InsightSelection, *, comparison: bool
    ) -> InsightControls:
        filters = selection.filters
        return cls(
            grouping=selection.grouping,
            groups=selection.groups,
            perspective=selection.perspective,
            metric=selection.metric,
            sentiment=filters.sentiment,
            emotion=filters.emotion,
            date_from=filters.date_from.isoformat() if filters.date_from else "",
            date_to=filters.date_to.isoformat() if filters.date_to else "",
            comparison=comparison,
        )


@dataclass(frozen=True, slots=True)
class ExampleControls:
    """The representative-case rule and its parameters."""

    mode: ExampleMode = ExampleMode.LOWEST_AI_CONFIDENCE
    emotion: EmotionLabel = EmotionLabel.ANGER
    tag: ContextTag | None = None
    record_ids: tuple[str, ...] = ()

    def as_values(self) -> dict[str, str]:
        return {
            "example_mode": self.mode.value,
            "example_emotion": self.emotion.value,
            "example_tag": self.tag.value if self.tag else "",
        }


@dataclass(frozen=True, slots=True)
class NoteDraft:
    """A human-authored context note; the service validates every field."""

    association: ContextAssociation = ContextAssociation.TOPIC
    association_value: str = ""
    phrase: str = ""
    explanation: str = ""
    context_importance: str = ""
    tags: tuple[ContextTag, ...] = ()

    def as_values(self) -> dict[str, str]:
        return {
            "association": self.association.value,
            "association_value": self.association_value,
            "phrase": self.phrase,
            "explanation": self.explanation,
            "context_importance": self.context_importance,
        }


@dataclass(frozen=True, slots=True)
class InsightsSnapshot:
    project_id: str
    selection: InsightSelection
    comparison: bool
    summaries: tuple[GroupMetricSummary, ...]
    metric_definition: str
    notes: tuple[ContextNote, ...]
    examples: tuple[RepresentativeExample, ...]
    example_mode: ExampleMode
    example_emotion: EmotionLabel
    example_tag: ContextTag | None
    selected_record_ids: frozenset[str]
    record_ids: tuple[str, ...]  # every successfully analysed record
    groupings: tuple[tuple[GroupingDimension, tuple[str, ...]], ...]
    association_values: tuple[tuple[str, tuple[str, ...]], ...]
    provenance: AnalysisReport
    error_message: str | None

    def groups_for(self, grouping: GroupingDimension) -> tuple[str, ...]:
        return next(values for key, values in self.groupings if key is grouping)

    def association_choices(self, association: ContextAssociation) -> tuple[str, ...]:
        return next(
            (values for key, values in self.association_values if key == association),
            (),
        )


class InsightsWorkflow:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository
        self._use_cases = ApplicationUseCases(repository, None)

    def open_insights(
        self,
        project_id: str,
        *,
        examples: ExampleControls = ExampleControls(),  # noqa: B008 (frozen value)
        comparison: bool = False,
    ) -> InsightsSnapshot:
        """The saved view (or the default one) with the chosen example rule."""

        workspace = self._analysed(project_id)
        return self._resolve(project_id, workspace, {}, (), examples, comparison)

    def apply(
        self,
        project_id: str,
        controls: InsightControls,
        examples: ExampleControls = ExampleControls(),  # noqa: B008 (frozen value)
    ) -> InsightsSnapshot:
        """Validate the request, save it as the project's view, and resolve it.

        A request the service would refuse is raised as a ``ValidationError`` before
        anything is saved, so a typo can never replace the saved view.
        """

        workspace = self._analysed(project_id)
        values = controls.as_values()
        selection, _ = self._use_cases.requested_insight_selection(
            workspace, values, controls.groups, comparison=controls.comparison
        )
        assert workspace.result is not None and workspace.reviews is not None
        build_group_metrics(
            workspace.result,
            workspace.reviews,
            selection,
            comparison=controls.comparison,
        )
        return self._resolve(
            project_id,
            workspace,
            values,
            controls.groups,
            examples,
            controls.comparison,
        )

    def add_note(self, project_id: str, draft: NoteDraft) -> None:
        self._mutate(
            project_id,
            lambda: self._use_cases.add_note(
                project_id, draft.as_values(), [tag.value for tag in draft.tags]
            ),
        )

    def remove_note(self, project_id: str, note_id: str) -> None:
        self._mutate(
            project_id, lambda: self._use_cases.remove_note(project_id, note_id)
        )

    def export_csv(
        self,
        project_id: str,
        *,
        comparison: bool = False,
        include_records: bool = False,
        include_native: bool = False,
    ) -> str:
        """The insights CSV for the saved view, as the shared export defines it."""

        workspace = self._analysed(project_id)
        assert workspace.insights is not None
        selection = workspace.insights.selection
        if selection is None:
            raise InsightsUnavailableError
        return self._use_cases.export_insights(
            workspace,
            selection,
            comparison=comparison,
            include_records=include_records,
            include_native=include_native,
        )

    # -- internals ----------------------------------------------------------

    def _analysed(self, project_id: str) -> BatchWorkspace:
        workspace = self._repository.get(project_id)
        if workspace is None:
            raise ProjectNotFoundError
        result = workspace.result
        if (
            result is None
            or workspace.reviews is None
            or workspace.insights is None
            or not any(outcome.report is not None for outcome in result.outcomes)
        ):
            raise InsightsUnavailableError
        return workspace

    def _mutate(
        self, project_id: str, change: Callable[[], BatchWorkspace | None]
    ) -> None:
        try:
            replacement = change()
        except WorkspaceMutationConflict:
            raise ProjectBusyError from None
        if replacement is None:
            raise ProjectNotFoundError

    def _resolve(
        self,
        project_id: str,
        workspace: BatchWorkspace,
        values: dict[str, str],
        groups: tuple[str, ...],
        examples: ExampleControls,
        comparison: bool,
    ) -> InsightsSnapshot:
        try:
            view = self._use_cases.resolve_insights(
                project_id,
                workspace,
                {**values, **examples.as_values()},
                groups,
                examples.record_ids,
                comparison=comparison,
            )
        except WorkspaceMutationConflict:
            raise ProjectBusyError from None
        if view is None:
            raise ProjectNotFoundError
        assert workspace.result is not None
        return InsightsSnapshot(
            project_id=project_id,
            selection=view.selection,
            comparison=comparison,
            summaries=view.summaries,
            metric_definition=METRIC_DEFINITIONS[view.selection.metric],
            notes=view.insight_state.notes,
            examples=view.examples,
            example_mode=view.example_mode,
            example_emotion=view.example_emotion,
            example_tag=view.example_tag,
            selected_record_ids=view.selected_record_ids,
            record_ids=view.association_values["record"],
            groupings=tuple(
                (grouping, available_group_values(workspace.result, grouping))
                for grouping in GroupingDimension
            ),
            association_values=tuple(view.association_values.items()),
            provenance=view.first_report,
            error_message=view.error_message,
        )


def outcome_report(outcome: BatchOutcome) -> AnalysisReport:
    """The immutable AI report of an example's outcome (always present for cases)."""

    assert outcome.report is not None
    return outcome.report


__all__ = [
    "INSIGHT_METRICS_BY_PERSPECTIVE",
    "ContextAssociation",
    "ContextNote",
    "ContextTag",
    "ExampleControls",
    "ExampleMode",
    "GroupMetricSummary",
    "GroupingDimension",
    "InsightControls",
    "InsightMetric",
    "InsightPerspective",
    "InsightSelection",
    "InsightsSnapshot",
    "InsightsUnavailableError",
    "InsightsWorkflow",
    "NoteDraft",
    "RepresentativeExample",
    "SampleSizeLevel",
    "outcome_report",
]
