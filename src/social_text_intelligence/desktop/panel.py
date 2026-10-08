"""Pure view models for the provisioning surfaces (no Qt).

``build_panel`` turns controller state into exactly what the setup window and the
Models window show: model cards, the actions that are enabled, progress, and the
result of the last operation. The Qt widgets only render these values and route
action ids back to the controller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from ..application.model_provisioning import (
    FolderFinding,
    FolderInspection,
    ModelsStatus,
    ModelStatus,
    ProvisioningOutcome,
    ProvisioningProgress,
    Readiness,
)
from ..contracts.errors import ModelsNotReadyError
from . import copy
from .controller import (
    REPORTING_PROGRESS,
    STOPPABLE,
    Activity,
    ControllerState,
    FolderState,
    OperationReport,
)
from .formatting import format_bytes
from .gate import SESSION_BLOCK_MESSAGE, AnalysisAvailability


class ActionId(StrEnum):
    DOWNLOAD = "download"
    STOP = "stop"
    DISCARD = "discard"
    USE_FOLDER = "use_folder"
    VERIFY = "verify"
    OPEN_FOLDER = "open_folder"
    RETRY = "retry"
    DISMISS = "dismiss"
    CHOOSE_FOLDER = "choose_folder"
    IMPORT = "import"
    OPEN_MODELS = "open_models"


@dataclass(frozen=True, slots=True)
class ActionView:
    action: ActionId
    label: str
    enabled: bool = True
    keys: tuple[str, ...] | None = None
    primary: bool = False


@dataclass(frozen=True, slots=True)
class CardView:
    key: str
    title: str
    chip_icon: str
    chip_word: str
    sentence: str
    problem_files: tuple[str, ...]
    also_found: str | None
    actions: tuple[ActionView, ...]
    details: tuple[tuple[str, str], ...]

    @property
    def chip(self) -> str:
        return f"{self.chip_icon} {self.chip_word}"

    @property
    def accessible_name(self) -> str:
        return f"{self.title}: {self.chip_word}. {self.sentence}"


@dataclass(frozen=True, slots=True)
class BarView:
    label: str
    fraction: float
    text: str


@dataclass(frozen=True, slots=True)
class ProgressView:
    title: str
    bars: tuple[BarView, ...]
    file_name: str
    note: str
    can_stop: bool
    stopping: bool

    @property
    def accessible_text(self) -> str:
        overall = self.bars[-1]
        return f"{self.title}. {overall.label}: {overall.text}"


class ReportKind(StrEnum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ReportView:
    kind: ReportKind
    title: str
    body: str
    code: str | None
    actions: tuple[ActionView, ...]

    @property
    def assertive(self) -> bool:
        return self.kind in (ReportKind.ERROR, ReportKind.WARNING)


@dataclass(frozen=True, slots=True)
class PanelView:
    headline: str
    subline: str
    cards: tuple[CardView, ...]
    actions: tuple[ActionView, ...]
    progress: ProgressView | None
    report: ReportView | None
    busy_note: str | None
    session_note: str | None
    folder_note: str | None


def model_title(key: str) -> str:
    return copy.MODEL_NAMES.get(key, f"{key.title()} model")


def _short(revision: str) -> str:
    return revision[:7]


def _remaining(model: ModelStatus) -> int:
    """Bytes that still have to be obtained (the problem files)."""

    return max(model.total_bytes - model.installed_bytes, 0)


def _left(model: ModelStatus) -> int:
    """Bytes still to fetch once any partial download is counted."""

    return max(_remaining(model) - model.resumable_bytes, 0)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


# -- model cards ------------------------------------------------------------


def _card_sentence(model: ModelStatus) -> str:
    readiness = model.readiness
    if readiness is Readiness.READY:
        return "All files installed and checksum-verified when installed."
    if readiness is Readiness.NOT_INSTALLED:
        return f"Not downloaded yet · {format_bytes(model.total_bytes)}."
    if readiness is Readiness.INCOMPLETE:
        if model.resumable_bytes:
            return (
                f"Interrupted: {format_bytes(model.resumable_bytes)} kept, "
                f"{format_bytes(_left(model))} left."
            )
        return f"{_plural(len(model.problem_files), 'required file')} missing."
    if readiness is Readiness.CORRUPT:
        return (
            f"{_plural(len(model.problem_files), 'file')} damaged or the wrong "
            "size. Analysis stays off until they are replaced or verified again."
        )
    other = _short(model.other_revisions[0]) if model.other_revisions else "unknown"
    return (
        f"Only a different version is installed (version {other}). It is never "
        "used and is left alone."
    )


def _download_label(model: ModelStatus) -> str | None:
    readiness = model.readiness
    if readiness is Readiness.NOT_INSTALLED:
        return f"Download this model · {format_bytes(model.total_bytes)}"
    if readiness is Readiness.INCOMPLETE:
        if model.resumable_bytes:
            return f"Download · resume, {format_bytes(_left(model))} left"
        return "Download missing files"
    if readiness is Readiness.CORRUPT:
        return (
            f"Download replacement · {_plural(len(model.problem_files), 'file')}, "
            f"{format_bytes(_remaining(model))}"
        )
    if readiness is Readiness.WRONG_REVISION:
        return f"Download approved version · {format_bytes(model.total_bytes)}"
    return None


def _card(model: ModelStatus, *, busy: bool) -> CardView:
    icon, word = copy.CHIPS[model.readiness]
    actions: list[ActionView] = []
    label = _download_label(model)
    if label is not None:
        actions.append(
            ActionView(ActionId.DOWNLOAD, label, not busy, (model.key,), primary=True)
        )
    if model.readiness is Readiness.INCOMPLETE and model.resumable_bytes:
        actions.append(
            ActionView(
                ActionId.DISCARD,
                "Discard partial download",
                not busy,
                (model.key,),
            )
        )
    if model.readiness is Readiness.CORRUPT:
        actions.append(ActionView(ActionId.VERIFY, "Verify again", not busy))
    show_problems = model.readiness in (Readiness.INCOMPLETE, Readiness.CORRUPT)
    also = None
    if model.readiness is Readiness.READY and model.other_revisions:
        also = (
            f"Also found: version {_short(model.other_revisions[0])} · "
            "never used, left alone"
        )
    details = (
        ("Model", model.model_id),
        ("Revision", model.revision),
        ("Licence", model.license),
        ("Size", format_bytes(model.total_bytes)),
        ("Installed", format_bytes(model.total_bytes - _remaining(model))),
    )
    return CardView(
        key=model.key,
        title=model_title(model.key),
        chip_icon=icon,
        chip_word=word,
        sentence=_card_sentence(model),
        problem_files=model.problem_files if show_problems else (),
        also_found=also,
        actions=tuple(actions),
        details=details,
    )


# -- headline ---------------------------------------------------------------


def _headline(status: ModelsStatus, *, window: Literal["setup", "models"]) -> str:
    models = status.models
    if window == "models" or status.ready:
        return "Language models"
    if any(m.readiness is Readiness.CORRUPT for m in models):
        return "A model file is damaged"
    if any(m.readiness is Readiness.WRONG_REVISION for m in models):
        return "A different model version was found"
    if any(m.readiness is Readiness.INCOMPLETE for m in models):
        if any(m.resumable_bytes for m in models):
            return "Setup was interrupted"
        return "Some model files are missing"
    return "Set up the language models"


def _subline(status: ModelsStatus) -> str:
    ready = sum(1 for m in status.models if m.ready)
    total = len(status.models)
    return f"{ready} of {total} models ready"


# -- progress ---------------------------------------------------------------


def _fraction(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(max(done / total, 0.0), 1.0)


def _bar(label: str, done: int, total: int) -> BarView:
    return BarView(
        label=label,
        fraction=_fraction(done, total),
        text=f"{format_bytes(done)} of {format_bytes(total)}",
    )


def _progress_view(
    activity: Activity, progress: ProvisioningProgress | None, *, stopping: bool
) -> ProgressView:
    stoppable = activity in STOPPABLE
    title, note = {
        Activity.VERIFYING: ("Checking files", copy.VERIFY_NOTE),
        Activity.IMPORTING: ("Importing models", copy.STOP_KEEPS_NOTHING),
        Activity.DOWNLOADING: ("Downloading models", copy.STOP_KEEPS_DOWNLOAD),
    }[activity]
    if progress is not None:
        title = copy.PHASE_WORDS[progress.phase]
        bars = (
            _bar("This file", progress.file_bytes_done, progress.file_bytes_total),
            _bar("This model", progress.model_bytes_done, progress.model_bytes_total),
            _bar(
                "All selected",
                progress.overall_bytes_done,
                progress.overall_bytes_total,
            ),
        )
        file_name = f"{model_title(progress.model_key)} · {progress.file_name}"
    else:
        bars = (
            BarView("This file", 0.0, "Starting…"),
            BarView("This model", 0.0, "Starting…"),
            BarView("All selected", 0.0, "Starting…"),
        )
        file_name = ""
    if stopping:
        note = "Stopping… finishing the current step."
    return ProgressView(
        title=title,
        bars=bars,
        file_name=file_name,
        note=note,
        can_stop=stoppable and not stopping,
        stopping=stopping,
    )


# -- reports ----------------------------------------------------------------


def _recovery(report: OperationReport) -> tuple[ActionView, ...]:
    code = report.error_code
    again = ActionView(ActionId.DOWNLOAD, "Download again", keys=None, primary=True)
    use_folder = ActionView(ActionId.USE_FOLDER, "Use a models folder…")
    if code == "network_unavailable":
        return (
            ActionView(ActionId.DOWNLOAD, "Download again · resumes", primary=True),
            use_folder,
        )
    if code == "download_rejected":
        return (again, use_folder)
    if code == "checksum_mismatch":
        if report.kind is Activity.IMPORTING:
            return (
                ActionView(
                    ActionId.CHOOSE_FOLDER, "Choose a different folder", primary=True
                ),
                again,
            )
        return (again, use_folder)
    if code == "storage_failed":
        return (
            ActionView(ActionId.RETRY, "Try again", primary=True),
            ActionView(ActionId.OPEN_FOLDER, "Open models folder"),
        )
    if code == "source_unreadable":
        return (
            ActionView(ActionId.CHOOSE_FOLDER, "Choose another folder", primary=True),
        )
    if code == "provisioning_in_progress":
        return (ActionView(ActionId.DISMISS, "OK", primary=True),)
    return (ActionView(ActionId.RETRY, "Try again", primary=True),)


def _kept_text(status: ModelsStatus) -> str:
    kept = sum(m.resumable_bytes for m in status.models)
    if kept:
        return f"{format_bytes(kept)} of partial download is kept. Download resumes it."
    return "Finished files are kept."


def _report_view(
    report: OperationReport,
    status: ModelsStatus,
    availability: AnalysisAvailability,
) -> ReportView:
    if report.outcome is ProvisioningOutcome.FAILED:
        code = report.error_code or "unexpected_error"
        title = copy.ERROR_TITLES.get(code, copy.ERROR_TITLES["unexpected_error"])
        body = copy.ERROR_BODIES.get(code, report.error_message or "")
        if report.kind is Activity.VERIFYING and code == "storage_failed":
            title = copy.VERIFY_STORAGE_TITLE
            body = f"{body} {copy.VERIFY_STORAGE_NOTE}"
        elif code == "network_unavailable" and any(
            m.resumable_bytes for m in status.models
        ):
            body = f"{body} {_kept_text(status)}"
        return ReportView(ReportKind.ERROR, title, body, code, _recovery(report))
    if report.outcome is ProvisioningOutcome.CANCELLED:
        if report.kind is Activity.IMPORTING:
            body = "The import was stopped. Nothing partial was kept."
        else:
            body = _kept_text(status)
        return ReportView(ReportKind.INFO, "Stopped", body, None, ())
    if report.kind is Activity.VERIFYING:
        if report.found_damage:
            body = (
                "At least one installed file does not match its approved checksum. "
                "This is remembered, also after restarting, until the file is "
                "replaced or verified again."
            )
            if availability is AnalysisAvailability.SESSION_BLOCKED:
                body = f"{body} {SESSION_BLOCK_MESSAGE}"
            return ReportView(
                ReportKind.WARNING, "Verify found damaged files", body, None, ()
            )
        return ReportView(
            ReportKind.SUCCESS,
            "Verify finished",
            "Every installed file matches its approved checksum.",
            None,
            (),
        )
    if report.kind is Activity.DISCARDING:
        return ReportView(
            ReportKind.INFO,
            "Partial download discarded",
            "Nothing else changed.",
            None,
            (),
        )
    ready = sum(1 for m in status.models if m.ready)
    if status.ready:
        title = "Models are ready"
        body = "Both models are installed and checksum-verified."
        if availability is AnalysisAvailability.SESSION_BLOCKED:
            body = (
                "Both models are repaired. Analysis stays off in this session: "
                "close and reopen the app to load them fresh."
            )
        return ReportView(ReportKind.SUCCESS, title, body, None, ())
    return ReportView(
        ReportKind.INFO,
        "Finished",
        f"{ready} of {len(status.models)} models are ready.",
        None,
        (),
    )


# -- panel ------------------------------------------------------------------


def progress_for(state: ControllerState) -> ProgressView | None:
    if state.activity not in REPORTING_PROGRESS:
        return None
    return _progress_view(state.activity, state.progress, stopping=state.stopping)


def report_for(
    state: ControllerState, availability: AnalysisAvailability
) -> ReportView | None:
    if state.report is None or state.busy:
        return None
    return _report_view(state.report, state.status, availability)


def build_panel(
    state: ControllerState,
    availability: AnalysisAvailability,
    *,
    window: Literal["setup", "models"],
) -> PanelView:
    status = state.status
    busy = state.busy
    cards = tuple(_card(model, busy=busy) for model in status.models)

    actions: list[ActionView] = []
    not_ready = [m for m in status.models if not m.ready]
    if len(not_ready) > 1:
        remaining = sum(
            m.total_bytes if m.readiness is Readiness.NOT_INSTALLED else _left(m)
            for m in not_ready
        )
        actions.append(
            ActionView(
                ActionId.DOWNLOAD,
                f"Download both models · {format_bytes(remaining)}",
                not busy,
                tuple(m.key for m in not_ready),
                primary=True,
            )
        )
    if not_ready:
        actions.append(
            ActionView(ActionId.USE_FOLDER, "Use a models folder…", not busy)
        )
    if window == "models":
        if any(
            m.readiness in (Readiness.READY, Readiness.CORRUPT) for m in status.models
        ):
            actions.append(ActionView(ActionId.VERIFY, "Verify files", not busy))
        actions.append(ActionView(ActionId.OPEN_FOLDER, "Open models folder", not busy))

    progress = progress_for(state)
    report = report_for(state, availability)
    session_note = (
        f"{copy.SESSION_BLOCK_TITLE}. Repairing does not turn it back on in this "
        "session."
        if availability is AnalysisAvailability.SESSION_BLOCKED
        else None
    )
    return PanelView(
        headline=_headline(status, window=window),
        subline=_subline(status),
        cards=cards,
        actions=tuple(actions),
        progress=progress,
        report=report,
        busy_note=copy.BUSY_NOTE
        if busy and state.activity is not Activity.VERIFYING
        else None,
        session_note=session_note,
        folder_note=copy.FOLDER_NOTE if window == "models" else None,
    )


# -- sidebar ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SidebarStatusView:
    title: str
    line: str
    meter: float | None
    accessible_name: str


def build_sidebar_status(
    state: ControllerState, availability: AnalysisAvailability
) -> SidebarStatusView:
    status = state.status
    ready = sum(1 for m in status.models if m.ready)
    total = len(status.models)
    count = f"{ready} of {total} models ready"
    if state.activity in REPORTING_PROGRESS:
        verb = {
            Activity.DOWNLOADING: "Downloading models",
            Activity.IMPORTING: "Importing models",
            Activity.VERIFYING: "Checking model files",
        }[state.activity]
        progress = state.progress
        fraction = (
            _fraction(progress.overall_bytes_done, progress.overall_bytes_total)
            if progress is not None
            else 0.0
        )
        line = f"{int(fraction * 100)}% · {count}"
        return SidebarStatusView(
            f"◉ {verb}…",
            line,
            fraction,
            f"{verb}, {int(fraction * 100)} percent. Open models.",
        )
    if availability is AnalysisAvailability.SESSION_BLOCKED:
        line = copy.SESSION_BLOCK_REPAIRED if status.ready else "damaged files found"
        return SidebarStatusView(
            f"✕ {copy.SESSION_BLOCK_STATUS}",
            line,
            None,
            f"{copy.SESSION_BLOCK_STATUS}. {line}. Open models.",
        )
    if status.ready:
        return SidebarStatusView(
            "✓ Models ready", count, None, f"Models ready. {count}. Open models."
        )
    worst = max(
        (m for m in status.models if not m.ready),
        key=lambda m: _SEVERITY[m.readiness],
    )
    icon, word = copy.CHIPS[worst.readiness]
    title = f"{icon} {model_title(worst.key)} {word.lower()}"
    return SidebarStatusView(
        title,
        count,
        None,
        f"{model_title(worst.key)} {word.lower()}. {count}. Analysis unavailable. "
        "Open models.",
    )


_SEVERITY = {
    Readiness.READY: 0,
    Readiness.NOT_INSTALLED: 1,
    Readiness.INCOMPLETE: 2,
    Readiness.WRONG_REVISION: 3,
    Readiness.CORRUPT: 4,
}


# -- analysis block ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnalysisBlockView:
    title: str
    body: str
    detail: tuple[str, ...]
    action: ActionView


def build_analysis_block(
    status: ModelsStatus, availability: AnalysisAvailability
) -> AnalysisBlockView | None:
    if availability is AnalysisAvailability.AVAILABLE:
        return None
    if availability is AnalysisAvailability.SESSION_BLOCKED:
        return AnalysisBlockView(
            copy.SESSION_BLOCK_TITLE,
            SESSION_BLOCK_MESSAGE,
            (),
            ActionView(ActionId.OPEN_MODELS, "Open models…", primary=True),
        )
    detail = tuple(
        f"{model_title(m.key)}: {copy.CHIPS[m.readiness][1]}"
        for m in status.models
        if not m.ready
    )
    return AnalysisBlockView(
        copy.MODELS_NOT_READY_TITLE,
        ModelsNotReadyError(status.not_ready_keys).message,
        detail,
        ActionView(ActionId.OPEN_MODELS, "Set up models…", primary=True),
    )


# -- folder dialog ----------------------------------------------------------

_FINDING_TEXT = {
    FolderFinding.FOUND: "Ready to import. The files are copied and checked.",
    FolderFinding.INCOMPLETE: "Incomplete: some files are missing.",
    FolderFinding.MISMATCHED: (
        "The file names match but the sizes do not: damaged, or a different version."
    ),
    FolderFinding.WRONG_REVISION: "Only a different version was found here.",
    FolderFinding.NOT_FOUND: "Not found in this folder.",
}


@dataclass(frozen=True, slots=True)
class FolderRow:
    title: str
    finding: str
    problems: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FolderView:
    path_text: str
    status_line: str
    rows: tuple[FolderRow, ...]
    actions: tuple[ActionView, ...]
    error: ReportView | None


def _folder_rows(inspection: FolderInspection) -> tuple[FolderRow, ...]:
    return tuple(
        FolderRow(model_title(f.key), _FINDING_TEXT[f.finding], f.problem_files)
        for f in inspection.models
    )


def build_folder_view(folder: FolderState | None, *, busy: bool) -> FolderView:
    choose = ActionView(ActionId.CHOOSE_FOLDER, "Choose a folder…", not busy)
    if folder is None:
        return FolderView(
            "",
            "Choose a folder that already holds the approved models. "
            "Checking it is read-only and copies nothing.",
            (),
            (choose,),
            None,
        )
    path_text = str(folder.path)
    if folder.checking:
        return FolderView(path_text, "Checking this folder…", (), (), None)
    if folder.error_code is not None:
        code = folder.error_code
        error = ReportView(
            ReportKind.ERROR,
            copy.ERROR_TITLES.get(code, copy.ERROR_TITLES["unexpected_error"]),
            folder.error_message or "",
            code,
            (),
        )
        return FolderView(path_text, "", (), (choose,), error)
    inspection = folder.inspection
    assert inspection is not None
    rows = _folder_rows(inspection)
    actions: list[ActionView] = []
    importable = inspection.importable_keys
    if importable:
        label = (
            "Import both models"
            if len(importable) > 1
            else f"Import {model_title(importable[0]).lower()}"
        )
        actions.append(ActionView(ActionId.IMPORT, label, not busy, importable, True))
    actions.append(
        ActionView(ActionId.CHOOSE_FOLDER, "Choose another folder…", not busy)
    )
    line = (
        "Read-only check. Nothing was copied."
        if inspection.supported
        else "This folder does not look like a models folder. Nothing was copied."
    )
    return FolderView(path_text, line, rows, tuple(actions), None)
