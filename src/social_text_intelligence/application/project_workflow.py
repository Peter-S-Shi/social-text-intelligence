"""Project workflow for a presentation layer: import, open, analyse, delete.

One project is one imported CSV and everything derived from it. This module only
orchestrates the existing pieces (CSV validation and batch analysis in the services,
leases and atomic commit in the repository) and adds typed, content-free errors and
a small read model of a project's state. Validation limits, leases, and the
no-partial-commit rule are not re-implemented here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum

from ..contracts.errors import SocialTextIntelligenceError, ValidationError
from ..services.batch import BatchCancelled, BatchProgress
from ..services.language import LanguageSummary, summarize_result
from .projects import (
    BatchWorkspace,
    PersistentProjectRepository,
    ProjectBusy,
    ProjectBusyElsewhere,
    ProjectSummary,
    WorkspaceMutationConflict,
)
from .settings import AnalysisGateway, AppSettings
from .use_cases import ApplicationUseCases

DEFAULT_PROJECT_NAME = "Untitled project"


class ProjectBusyError(SocialTextIntelligenceError):
    """The project is held by a running analysis (here, or in another window)."""

    def __init__(self, *, elsewhere: bool = False) -> None:
        message = (
            "This project is in use in another window of the app, for example "
            "being analysed there. Wait for it to finish there, or close that "
            "window, then try again. Nothing was changed."
            if elsewhere
            else "This project is busy with an analysis. Wait for it to finish, or "
            "cancel it first."
        )
        super().__init__(message)
        self.code = "project_busy"
        self.message = message


def busy_error(error: BaseException) -> ProjectBusyError:
    """The user-facing busy error for a repository hold (local or another window)."""

    return ProjectBusyError(elsewhere=isinstance(error, ProjectBusyElsewhere))


class ProjectChangedError(SocialTextIntelligenceError):
    """The stored project no longer matches what the caller was looking at."""

    def __init__(self) -> None:
        message = "This project changed. Reopen it and try again."
        super().__init__(message)
        self.code = "project_changed"
        self.message = message


class ProjectNotFoundError(SocialTextIntelligenceError):
    def __init__(self) -> None:
        message = "This project is no longer available."
        super().__init__(message)
        self.code = "project_not_found"
        self.message = message


@dataclass(frozen=True, slots=True)
class CsvLimits:
    max_bytes: int
    max_rows: int
    max_text_length: int

    @classmethod
    def from_settings(cls, settings: AppSettings) -> CsvLimits:
        return cls(
            max_bytes=settings.max_batch_bytes,
            max_rows=settings.max_batch_rows,
            max_text_length=settings.max_text_length,
        )


class ProjectPhase(StrEnum):
    NEEDS_COLUMN = "needs_column"
    READY = "ready"
    ANALYZED = "analyzed"
    EMPTY = "empty"


class AnalysisRun(StrEnum):
    COMMITTED = "committed"
    CANCELLED = "cancelled"
    STALE = "stale"
    NOTHING_TO_ANALYZE = "nothing_to_analyze"


@dataclass(frozen=True, slots=True)
class ProjectDetails:
    """What an open project shows: counts and state, never row text."""

    summary: ProjectSummary
    phase: ProjectPhase
    headers: tuple[str, ...] = ()
    text_column: str | None = None
    row_count: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    analyzed_rows: int | None = None
    # Valid rows whose analysis failed (not the rows rejected at import).
    failed_rows: int | None = None
    sentiment_counts: tuple[tuple[str, int], ...] = ()
    # How the analysed texts fared in the language check (None until analysed).
    language: LanguageSummary | None = None


def describe(summary: ProjectSummary, workspace: BatchWorkspace) -> ProjectDetails:
    if workspace.pending is not None:
        return ProjectDetails(
            summary, ProjectPhase.NEEDS_COLUMN, headers=workspace.pending.headers
        )
    preview = workspace.preview
    if preview is None:
        return ProjectDetails(summary, ProjectPhase.EMPTY)
    ready = ProjectDetails(
        summary,
        ProjectPhase.READY,
        headers=preview.headers,
        text_column=preview.text_column,
        row_count=len(preview.rows),
        valid_rows=preview.valid_count,
        invalid_rows=preview.invalid_count,
    )
    result = workspace.result
    if result is None:
        return ready
    aggregates = result.aggregates
    return replace(
        ready,
        phase=ProjectPhase.ANALYZED,
        analyzed_rows=aggregates.analyzed_count,
        # Rows rejected at import never reached analysis: they are counted as
        # invalid_rows, not as analysis failures, so analysed + failed == valid.
        failed_rows=aggregates.failed_count - preview.invalid_count,
        sentiment_counts=tuple(
            (label.value, count) for label, count in aggregates.sentiment_counts
        ),
        language=summarize_result(result),
    )


class ProjectWorkflow:
    def __init__(
        self,
        repository: PersistentProjectRepository,
        analysis_gateway: AnalysisGateway,
        limits: CsvLimits,
    ) -> None:
        self._repository = repository
        self._use_cases = ApplicationUseCases(repository, analysis_gateway)
        self._limits = limits

    def list_projects(self) -> tuple[ProjectSummary, ...]:
        return self._repository.list_projects()

    def import_csv(self, content: bytes, *, name: str) -> ProjectDetails:
        """Validate one CSV and create a durable project; invalid input creates none."""

        workspace = self._use_cases.prepare_upload(
            content,
            max_bytes=self._limits.max_bytes,
            max_rows=self._limits.max_rows,
            max_text_length=self._limits.max_text_length,
        )
        try:
            summary = self._repository.create_project(workspace, name=name)
        except ValidationError as error:
            if error.code != "invalid_name":
                raise
            summary = self._repository.create_project(
                workspace, name=DEFAULT_PROJECT_NAME
            )
        return describe(summary, workspace)

    def open_project(self, project_id: str) -> ProjectDetails:
        workspace = self._repository.get(project_id)
        summary = self._summary(project_id)
        if workspace is None or summary is None:
            raise ProjectNotFoundError
        return describe(summary, workspace)

    def choose_column(self, project_id: str, column: str) -> ProjectDetails:
        try:
            workspace = self._use_cases.select_batch_column(
                project_id,
                column,
                max_rows=self._limits.max_rows,
                max_text_length=self._limits.max_text_length,
            )
        except WorkspaceMutationConflict:
            raise ProjectChangedError from None
        if workspace is None:
            raise ProjectNotFoundError
        return self.open_project(project_id)

    def analyze(
        self,
        project_id: str,
        *,
        progress: Callable[[BatchProgress], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> AnalysisRun:
        """Analyse through the shared use case; cancellation or failure commits nothing.

        Raises ``ProjectBusyError`` if the project is already held, and lets
        ``AnalysisUnavailableError`` (models not ready, or the H2 session block)
        propagate: the lease is released and no partial result is stored.
        """

        details = self.open_project(project_id)
        if details.phase is not ProjectPhase.READY or details.valid_rows == 0:
            # a fast path only: the shared use case re-checks the leased workspace,
            # which is what stops a project analysed elsewhere since this look
            return AnalysisRun.NOTHING_TO_ANALYZE
        try:
            committed = self._use_cases.analyze_workspace(
                project_id, progress=progress, cancelled=cancelled
            )
        except BatchCancelled:
            return AnalysisRun.CANCELLED
        except ProjectBusy as error:
            raise busy_error(error) from None
        if committed is None:
            if self._repository.get(project_id) is None:
                raise ProjectNotFoundError
            return AnalysisRun.NOTHING_TO_ANALYZE
        return AnalysisRun.COMMITTED if committed else AnalysisRun.STALE

    def delete_project(self, project_id: str) -> bool:
        """Remove the project from the application's data files (not secure erasure)."""

        try:
            return self._repository.delete(project_id)
        except ProjectBusy as error:
            raise busy_error(error) from None

    def _summary(self, project_id: str) -> ProjectSummary | None:
        for summary in self._repository.list_projects():
            if summary.project_id == project_id:
                return summary
        return None


__all__ = [
    "DEFAULT_PROJECT_NAME",
    "AnalysisRun",
    "BatchProgress",
    "CsvLimits",
    "ProjectBusyError",
    "ProjectChangedError",
    "ProjectDetails",
    "ProjectNotFoundError",
    "ProjectPhase",
    "ProjectWorkflow",
    "busy_error",
    "describe",
]
