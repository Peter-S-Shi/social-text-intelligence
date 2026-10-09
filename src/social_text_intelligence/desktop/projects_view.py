"""Pure view models for the Projects surface (no Qt)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..application.language import describe_summary
from ..application.model_provisioning import ModelsStatus
from ..application.project_workflow import (
    DEFAULT_PROJECT_NAME,
    ProjectDetails,
    ProjectPhase,
)
from ..application.projects import ProjectStatus, ProjectSummary
from .gate import AnalysisAvailability
from .panel import AnalysisBlockView, build_analysis_block
from .projects import ProjectsActivity, ProjectsNotice, ProjectsState

IMPORT_LABEL = "Import CSV…"
# The optional columns a CSV may carry beside its text column. Insights groups come
# only from these (nothing is inferred); a test keeps this list equal to the batch
# service's own list of supported fields.
METADATA_COLUMNS = (
    "record_id",
    "source_type",
    "source_label",
    "language",
    "timestamp",
    "topic",
    "community",
    "parent_record_id",
    "notes",
)


def _when(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else "unknown"


@dataclass(frozen=True, slots=True)
class ProjectRowView:
    project_id: str
    title: str
    subtitle: str
    can_open: bool

    @property
    def accessible_name(self) -> str:
        return f"{self.title}. {self.subtitle}"


@dataclass(frozen=True, slots=True)
class ProjectsListView:
    rows: tuple[ProjectRowView, ...]
    summary: str
    import_enabled: bool
    row_actions_enabled: bool
    notice: ProjectsNotice | None


def row_view(summary: ProjectSummary) -> ProjectRowView:
    if summary.status is ProjectStatus.OK:
        return ProjectRowView(
            summary.project_id,
            summary.name or DEFAULT_PROJECT_NAME,
            f"Updated {_when(summary.updated_at)}",
            can_open=True,
        )
    if summary.status is ProjectStatus.UNSUPPORTED_VERSION:
        return ProjectRowView(
            summary.project_id,
            "Project from a newer version",
            "This version of the app cannot open it.",
            can_open=False,
        )
    return ProjectRowView(
        summary.project_id,
        "Unreadable project",
        "This project file cannot be read.",
        can_open=False,
    )


def build_list_view(state: ProjectsState) -> ProjectsListView:
    rows = tuple(row_view(item) for item in state.projects)
    if state.list_failed:
        summary = "The project list could not be read."
    elif not state.listed:
        summary = "Loading projects…"
    elif not rows:
        summary = "No projects yet. Import a CSV to start one."
    else:
        summary = f"{len(rows)} project(s) on this computer."
    return ProjectsListView(
        rows=rows,
        summary=summary,
        import_enabled=not state.busy,
        row_actions_enabled=not state.busy,
        notice=state.notice,
    )


@dataclass(frozen=True, slots=True)
class ProjectProgressView:
    text: str
    fraction: float
    can_cancel: bool
    stage: str  # "loading", "running", or "cancelling": drives the live announcements


@dataclass(frozen=True, slots=True)
class ProjectDetailView:
    title: str
    state_line: str
    facts: tuple[str, ...]
    column_choices: tuple[str, ...]
    choose_enabled: bool
    show_analyze: bool
    analyze_label: str
    analyze_enabled: bool
    progress: ProjectProgressView | None
    delete_enabled: bool
    block: AnalysisBlockView | None
    notice: ProjectsNotice | None
    language_headline: str | None = None
    language_detail: str = ""
    language_warns: bool = False
    # the figures of the CSV card: rows ready, rejected at import, and (once
    # analysed) texts not confirmed as a supported language
    ready_count: int | None = None
    rejected_count: int | None = None
    language_count: int | None = None
    metadata: tuple[tuple[str, bool], ...] = ()  # recognised column, present in file


_STATE_LINES = {
    ProjectPhase.NEEDS_COLUMN: "Choose which column holds the text to analyse.",
    ProjectPhase.READY: "Ready to analyse.",
    ProjectPhase.ANALYZED: "Analysed.",
    ProjectPhase.EMPTY: "This project has no data.",
}


def _facts(details: ProjectDetails) -> tuple[str, ...]:
    if details.phase is ProjectPhase.NEEDS_COLUMN:
        return (f"{len(details.headers)} columns found in the CSV.",)
    if details.phase is ProjectPhase.EMPTY:
        return ()
    rows = f"{details.row_count} rows · {details.valid_rows} ready"
    if details.invalid_rows:
        rows += f" · {details.invalid_rows} with problems"
    facts = [f"Text column: {details.text_column}", rows]
    if details.phase is ProjectPhase.ANALYZED:
        done = f"Analysed {details.analyzed_rows} rows"
        if details.failed_rows:
            done += f" · {details.failed_rows} rows failed"
        facts.append(done)
        counts = " · ".join(
            f"{label.title()} {count}" for label, count in details.sentiment_counts
        )
        if counts:
            facts.append(f"Sentiment: {counts}")
    return tuple(facts)


def _progress(state: ProjectsState) -> ProjectProgressView | None:
    if state.activity is not ProjectsActivity.ANALYZING:
        return None
    if state.cancelling:
        text = "Cancelling… finishing the current row. Nothing will be saved."
        fraction = state.progress.fraction if state.progress else 0.0
        return ProjectProgressView(text, fraction, can_cancel=False, stage="cancelling")
    if state.progress is None:
        return ProjectProgressView(
            "Loading the models and starting… the first analysis can take a while.",
            0.0,
            can_cancel=True,
            stage="loading",
        )
    done, total = state.progress.completed, state.progress.total
    return ProjectProgressView(
        f"Analyzing row {done} of {total}",
        state.progress.fraction,
        can_cancel=True,
        stage="running",
    )


def build_detail_view(
    state: ProjectsState,
    availability: AnalysisAvailability,
    models: ModelsStatus,
    *,
    other_analysis_running: bool = False,
) -> ProjectDetailView | None:
    details = state.current
    if details is None:
        return None
    ready = details.phase is ProjectPhase.READY
    block = build_analysis_block(models, availability) if ready else None
    busy = state.busy
    language = describe_summary(details.language) if details.language else None
    counted = details.phase in (ProjectPhase.READY, ProjectPhase.ANALYZED)
    return ProjectDetailView(
        title=details.summary.name or DEFAULT_PROJECT_NAME,
        state_line=_STATE_LINES[details.phase],
        facts=_facts(details),
        column_choices=(
            details.headers if details.phase is ProjectPhase.NEEDS_COLUMN else ()
        ),
        choose_enabled=not busy,
        show_analyze=ready,
        analyze_label=f"Analyze {details.valid_rows} rows",
        analyze_enabled=(
            ready
            and details.valid_rows > 0
            and availability is AnalysisAvailability.AVAILABLE
            and not busy
            and not other_analysis_running
        ),
        progress=_progress(state),
        delete_enabled=not busy,
        block=block,
        notice=state.notice,
        language_headline=None if language is None else language.headline,
        language_detail="" if language is None else language.detail,
        language_warns=language is not None and language.warns,
        ready_count=details.valid_rows if counted else None,
        rejected_count=details.invalid_rows if counted else None,
        language_count=(
            details.language.attention_count if details.language is not None else None
        ),
        metadata=(
            tuple((name, name in details.headers) for name in METADATA_COLUMNS)
            if counted
            else ()
        ),
    )


def delete_confirmation(title: str) -> tuple[str, str]:
    """The confirmation text: conservative, never a secure-erasure claim."""

    return (
        "Delete project",
        f"Delete “{title}”? It will be removed from this application's data "
        "files. Copies you exported and operating-system backups are not "
        "affected, and this cannot be undone.",
    )
