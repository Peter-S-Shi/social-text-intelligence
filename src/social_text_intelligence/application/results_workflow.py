"""Results workflow for a presentation layer: validation detail, rows, export.

A thin, typed seam over the stored batch workspace. It restates nothing: CSV validation,
the row outcomes, the aggregates, the language check, and the spreadsheet-safe export
all stay in the batch services, and this module only turns a project id into read
models. A read model carries a record's text only as a sanitized one-line excerpt of
at most 100 characters (see ``text_excerpt``; a shorter record appears in full), plus
its identity, labels, and the fixed reason a row did not make it through.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..contracts import EmotionLabel, SentimentLabel
from ..contracts.errors import SocialTextIntelligenceError
from ..contracts.language import LanguageAssessment
from ..services.batch import ActivationRate, BatchAggregates, BatchOutcome
from ..services.language import LanguageSummary, summarize_result
from .project_workflow import ProjectNotFoundError
from .projects import BatchWorkspace, ProjectRepository
from .text_excerpt import excerpt
from .use_cases import ApplicationUseCases


class ResultsUnavailableError(SocialTextIntelligenceError):
    """The project has no analysed result to show or export yet."""

    def __init__(self) -> None:
        message = "This project has not been analysed yet, so it has no results."
        super().__init__(message)
        self.code = "results_unavailable"
        self.message = message


class ValidationUnavailableError(SocialTextIntelligenceError):
    """No text column has been chosen, so no row has been validated yet."""

    def __init__(self) -> None:
        message = "Choose the text column first; rows are validated after that."
        super().__init__(message)
        self.code = "validation_unavailable"
        self.message = message


class ResultsStatus(StrEnum):
    """The status filter of the results table (the same values V1 used)."""

    ALL = "all"
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ResultsFilters:
    status: ResultsStatus = ResultsStatus.ALL
    sentiment: SentimentLabel | None = None  # the AI label
    emotion: EmotionLabel | None = None  # the AI dominant emotion


@dataclass(frozen=True, slots=True)
class RowProblem:
    """A row that could not be prepared, or whose analysis failed, and why."""

    row_number: int
    record_id: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationRow:
    """One row of the import preview: where it is, a short text, and its check."""

    row_number: int
    record_id: str
    excerpt: str
    rejected: bool
    code: str | None = None  # why it was rejected, when it was
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationSnapshot:
    project_id: str
    text_column: str
    headers: tuple[str, ...]
    ignored_columns: tuple[str, ...]
    total_rows: int
    valid_rows: int
    invalid_rows: tuple[RowProblem, ...]  # rejected when the CSV was prepared
    analysed: bool
    failed_rows: tuple[RowProblem, ...]  # valid rows whose analysis failed
    rows: tuple[ValidationRow, ...] = ()  # every row, in file order


@dataclass(frozen=True, slots=True)
class ResultRow:
    row_number: int
    record_id: str
    status: str  # "ok" or "error", as the batch recorded it
    sentiment: SentimentLabel | None = None
    dominant_emotion: EmotionLabel | None = None
    secondary_emotions: tuple[EmotionLabel, ...] = ()
    language: LanguageAssessment | None = None
    error_code: str | None = None
    error_message: str | None = None
    # True for a row the CSV preparation rejected: it never reached the models.
    rejected_at_import: bool = False
    excerpt: str = (
        ""  # the start of the record's text: sanitized, at most 100 characters
    )


@dataclass(frozen=True, slots=True)
class ResultsSnapshot:
    project_id: str
    filters: ResultsFilters
    aggregates: BatchAggregates
    language: LanguageSummary
    total_rows: int  # every row of the batch, whatever the filters
    rows: tuple[ResultRow, ...]  # the rows the filters keep, in file order


def _row(outcome: BatchOutcome) -> ResultRow:
    prepared = outcome.prepared
    report = outcome.report
    if report is None:
        return ResultRow(
            row_number=prepared.row_number,
            record_id=prepared.identity,
            status=outcome.status,
            error_code=outcome.error_code,
            error_message=outcome.error_message,
            rejected_at_import=prepared.record is None,
            excerpt=excerpt(prepared.value_map.get("text", "")),
        )
    return ResultRow(
        row_number=prepared.row_number,
        record_id=prepared.identity,
        status=outcome.status,
        sentiment=report.sentiment.label,
        dominant_emotion=report.emotion.dominant_emotion,
        secondary_emotions=report.emotion.secondary_emotions,
        language=report.language,
        excerpt=excerpt(prepared.value_map.get("text", "")),
    )


def _kept(row: ResultRow, filters: ResultsFilters) -> bool:
    if filters.status is not ResultsStatus.ALL and row.status != filters.status:
        return False
    if filters.sentiment is not None and row.sentiment is not filters.sentiment:
        return False
    return filters.emotion is None or row.dominant_emotion is filters.emotion


class ResultsWorkflow:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def validation(self, project_id: str) -> ValidationSnapshot:
        """Per-row validation and, once analysed, failure reasons."""

        workspace = self._workspace(project_id)
        preview = workspace.preview
        if preview is None:
            raise ValidationUnavailableError
        result = workspace.result
        failed = (
            tuple(
                RowProblem(
                    outcome.prepared.row_number,
                    outcome.prepared.identity,
                    outcome.error_code or "analysis_failed",
                    outcome.error_message or "Analysis failed safely for this row.",
                )
                for outcome in result.outcomes
                if outcome.prepared.record is not None and outcome.report is None
            )
            if result is not None
            else ()
        )
        return ValidationSnapshot(
            project_id=project_id,
            text_column=preview.text_column,
            headers=preview.headers,
            ignored_columns=preview.ignored_columns,
            total_rows=len(preview.rows),
            valid_rows=preview.valid_count,
            invalid_rows=tuple(
                RowProblem(
                    row.row_number,
                    row.identity,
                    row.error_code or "invalid_row",
                    row.error_message or "This row could not be prepared.",
                )
                for row in preview.rows
                if row.record is None
            ),
            analysed=result is not None,
            failed_rows=failed,
            rows=tuple(
                ValidationRow(
                    row.row_number,
                    row.identity,
                    excerpt(row.value_map.get("text", "")),
                    rejected=row.record is None,
                    code=(row.error_code or "invalid_row")
                    if row.record is None
                    else None,
                    message=(
                        (row.error_message or "This row could not be prepared.")
                        if row.record is None
                        else None
                    ),
                )
                for row in preview.rows
            ),
        )

    def results(
        self,
        project_id: str,
        filters: ResultsFilters = ResultsFilters(),  # noqa: B008 (frozen value)
    ) -> ResultsSnapshot:
        """The aggregates, and the rows the filters keep (aggregates never change)."""

        workspace = self._analysed(project_id)
        result = workspace.result
        assert result is not None
        rows = tuple(_row(outcome) for outcome in result.outcomes)
        return ResultsSnapshot(
            project_id=project_id,
            filters=filters,
            aggregates=result.aggregates,
            language=summarize_result(result),
            total_rows=len(rows),
            rows=tuple(row for row in rows if _kept(row, filters)),
        )

    def export_csv(self, project_id: str, *, include_native: bool = False) -> str:
        """The normalized batch CSV exactly as the shared export defines it."""

        return ApplicationUseCases.export_batch(
            self._analysed(project_id), include_native=include_native
        )

    # -- internals ----------------------------------------------------------

    def _workspace(self, project_id: str) -> BatchWorkspace:
        workspace = self._repository.get(project_id)
        if workspace is None:
            raise ProjectNotFoundError
        return workspace

    def _analysed(self, project_id: str) -> BatchWorkspace:
        workspace = self._workspace(project_id)
        if workspace.result is None:
            raise ResultsUnavailableError
        return workspace


__all__ = [
    "ActivationRate",
    "BatchAggregates",
    "ResultRow",
    "ResultsFilters",
    "ResultsSnapshot",
    "ResultsStatus",
    "ResultsUnavailableError",
    "ResultsWorkflow",
    "RowProblem",
    "ValidationRow",
    "ValidationSnapshot",
    "ValidationUnavailableError",
]
