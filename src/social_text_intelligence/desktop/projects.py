"""Qt-free controller for the Projects surface: import, open, analyse, delete.

Everything here goes through ``ProjectWorkflow``: CSV validation, leases, the
no-partial-commit rule, and the analysis gate stay in the application layer. The
controller runs each operation off the UI thread, allows one at a time (Cancel is
the only command that may arrive while one runs), and turns errors into fixed,
content-free notices that never contain CSV text or file paths.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..application.project_workflow import (
    AnalysisRun,
    BatchProgress,
    ProjectBusyError,
    ProjectChangedError,
    ProjectDetails,
    ProjectNotFoundError,
    ProjectWorkflow,
)
from ..application.projects import ProjectSummary
from ..contracts.errors import (
    AnalysisSessionBlockedError,
    AnalysisSetupError,
    ModelsNotReadyError,
    ProjectStorageError,
    ProviderError,
    ValidationError,
)
from . import copy
from .controller import JobRunner
from .progress import CoalescedUpdates

FILE_UNREADABLE = "The file could not be read."
DELETE_NOTE = (
    "The project was removed from this application's data files. Copies you "
    "exported and operating-system backups are not affected."
)


class ProjectsActivity(StrEnum):
    IDLE = "idle"
    LISTING = "listing"
    IMPORTING = "importing"
    OPENING = "opening"
    CHOOSING = "choosing"
    ANALYZING = "analyzing"
    DELETING = "deleting"


class NoticeKind(StrEnum):
    INFO = "info"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProjectsNotice:
    kind: NoticeKind
    code: str
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class ProjectsState:
    projects: tuple[ProjectSummary, ...] = ()
    listed: bool = False
    list_failed: bool = False
    activity: ProjectsActivity = ProjectsActivity.IDLE
    current: ProjectDetails | None = None
    progress: BatchProgress | None = None
    cancelling: bool = False
    notice: ProjectsNotice | None = None

    @property
    def busy(self) -> bool:
        return self.activity is not ProjectsActivity.IDLE


Listener = Callable[[ProjectsState], None]


_DELETED = ProjectsNotice(
    NoticeKind.INFO, "project_deleted", "Project deleted", DELETE_NOTE
)
_ALREADY_GONE = ProjectsNotice(
    NoticeKind.INFO,
    "project_not_found",
    "Already removed",
    "That project was already gone. The list is up to date.",
)
_CANCELLED = ProjectsNotice(
    NoticeKind.INFO,
    "analysis_cancelled",
    "Analysis cancelled",
    "Nothing was saved from this run. You can analyse again.",
)
_NOTHING_TO_ANALYZE = ProjectsNotice(
    NoticeKind.INFO,
    "nothing_to_analyze",
    "Nothing to analyse",
    "This project has no rows ready to analyse, or it has already been analysed.",
)
_SAVED_BEFORE_CANCEL = ProjectsNotice(
    NoticeKind.INFO,
    "analysis_saved",
    "Analysis finished",
    "The analysis had already finished and was saved before Cancel took effect.",
)


def read_limited(path: Path, max_bytes: int) -> bytes:
    """Read at most ``max_bytes + 1`` bytes, so a huge file is never loaded whole."""

    with path.open("rb") as handle:
        return handle.read(max_bytes + 1)


def project_name_from(path: Path) -> str:
    return path.stem


def notice_for(error: BaseException) -> ProjectsNotice:
    """A fixed, content-free notice for ``error``; never uses its own text blindly."""

    kind = NoticeKind.ERROR
    if isinstance(error, AnalysisSessionBlockedError):
        return ProjectsNotice(kind, error.code, copy.SESSION_BLOCK_TITLE, error.message)
    if isinstance(error, ModelsNotReadyError):
        return ProjectsNotice(
            kind, error.code, copy.MODELS_NOT_READY_TITLE, error.message
        )
    if isinstance(error, ProviderError | AnalysisSetupError) and (
        error.code == "model_load_failed"
    ):
        return ProjectsNotice(
            kind,
            error.code,
            copy.ERROR_TITLES["model_load_failed"],
            copy.ERROR_BODIES["model_load_failed"],
        )
    if isinstance(error, AnalysisSetupError):
        return ProjectsNotice(
            kind, error.code, copy.MODELS_NOT_READY_TITLE, error.message
        )
    if isinstance(error, ValidationError):
        return ProjectsNotice(kind, error.code, "This CSV can't be used", error.message)
    if isinstance(error, ProjectBusyError | ProjectChangedError | ProjectNotFoundError):
        titles = {
            "project_busy": "The project is busy",
            "project_changed": "The project changed",
            "project_not_found": "The project is gone",
        }
        return ProjectsNotice(kind, error.code, titles[error.code], error.message)
    if isinstance(error, ProjectStorageError):
        code = (
            "unsupported_project"
            if error.code == "unsupported_schema_version"
            else "unreadable_project"
        )
        return ProjectsNotice(kind, code, "This project can't be opened", error.message)
    if isinstance(error, OSError):
        return ProjectsNotice(
            kind, "file_unreadable", "Couldn't read that file", FILE_UNREADABLE
        )
    return ProjectsNotice(
        kind,
        "unexpected_error",
        "The operation did not finish",
        "The operation could not be completed. Try again, or restart the app.",
    )


class ProjectsController:
    def __init__(
        self,
        workflow: ProjectWorkflow,
        runner: JobRunner,
        *,
        max_file_bytes: int,
        read_file: Callable[[Path, int], bytes] = read_limited,
    ) -> None:
        self._workflow = workflow
        self._runner = runner
        self._max_file_bytes = max_file_bytes
        self._read_file = read_file
        self._state = ProjectsState()
        self._listeners: list[Listener] = []
        self._cancel = threading.Event()
        self._progress = CoalescedUpdates(runner.post, self._apply_progress)
        self._idle_callbacks: list[Callable[[], None]] = []

    @property
    def state(self) -> ProjectsState:
        return self._state

    @property
    def can_cancel(self) -> bool:
        return (
            self._state.activity is ProjectsActivity.ANALYZING
            and not self._state.cancelling
        )

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def when_idle(self, callback: Callable[[], None]) -> None:
        if self._state.busy:
            self._idle_callbacks.append(callback)
        else:
            callback()

    # -- commands -----------------------------------------------------------

    def refresh(self) -> bool:
        def done(outcome: Any) -> None:
            self._end(**self._listing_changes(outcome))

        return self._start(ProjectsActivity.LISTING, self._workflow.list_projects, done)

    def import_csv(self, path: Path) -> bool:
        def work() -> tuple[ProjectDetails, Any]:
            content = self._read_file(path, self._max_file_bytes)
            details = self._workflow.import_csv(content, name=project_name_from(path))
            return details, self._list_quietly()

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._end(notice=notice_for(outcome))
                return
            details, listing = outcome
            self._end(current=details, **self._listing_changes(listing))

        return self._start(ProjectsActivity.IMPORTING, work, done)

    def open_project(self, project_id: str) -> bool:
        def work() -> ProjectDetails:
            return self._workflow.open_project(project_id)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome, project_id)
                return
            self._end(current=outcome)

        return self._start(ProjectsActivity.OPENING, work, done)

    def choose_column(self, column: str) -> bool:
        current = self._state.current
        if current is None:
            return False
        project_id = current.summary.project_id

        def work() -> tuple[ProjectDetails, Any]:
            details = self._workflow.choose_column(project_id, column)
            return details, self._list_quietly()

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome, project_id)
                return
            details, listing = outcome
            self._end(current=details, **self._listing_changes(listing))

        return self._start(ProjectsActivity.CHOOSING, work, done)

    def analyze(self) -> bool:
        current = self._state.current
        if current is None:
            return False
        project_id = current.summary.project_id

        def work() -> tuple[AnalysisRun, ProjectDetails, Any]:
            run = self._workflow.analyze(
                project_id,
                progress=self._progress.push,
                cancelled=self._cancel.is_set,
            )
            return run, self._workflow.open_project(project_id), self._list_quietly()

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome, project_id)
                return
            run, details, listing = outcome
            changes: dict[str, Any] = {
                "current": details,
                **self._listing_changes(listing),
            }
            notice = self._analysis_notice(run)
            if notice is not None:
                changes["notice"] = notice
            self._end(**changes)

        return self._start(ProjectsActivity.ANALYZING, work, done)

    def cancel(self) -> None:
        if self.can_cancel:
            self._cancel.set()
            self._set(cancelling=True)

    def delete(self, project_id: str) -> bool:
        def work() -> tuple[bool, Any]:
            deleted = self._workflow.delete_project(project_id)
            return deleted, self._list_quietly()

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome, project_id)
                return
            deleted, listing = outcome
            changes: dict[str, Any] = {
                **self._listing_changes(listing),
                "notice": _DELETED if deleted else _ALREADY_GONE,
            }
            current = self._state.current
            if current is not None and current.summary.project_id == project_id:
                changes["current"] = None
            self._end(**changes)

        return self._start(ProjectsActivity.DELETING, work, done)

    def close_project(self) -> None:
        if not self._state.busy:
            self._set(current=None, notice=None)
            self.refresh()

    def dismiss_notice(self) -> None:
        self._set(notice=None)

    # -- internals ----------------------------------------------------------

    def _list_quietly(self) -> tuple[ProjectSummary, ...] | BaseException:
        """List after a change; a listing failure must not hide the change itself."""

        try:
            return self._workflow.list_projects()
        except Exception as error:
            return error

    def _listing_changes(self, listing: Any) -> dict[str, Any]:
        if isinstance(listing, BaseException):
            return {"listed": True, "list_failed": True}
        return {"projects": listing, "listed": True, "list_failed": False}

    def _analysis_notice(self, run: AnalysisRun) -> ProjectsNotice | None:
        if run is AnalysisRun.CANCELLED:
            return _CANCELLED
        if run is AnalysisRun.NOTHING_TO_ANALYZE:
            return _NOTHING_TO_ANALYZE
        if run is AnalysisRun.STALE:
            return notice_for(ProjectChangedError())
        if self._state.cancelling:
            return _SAVED_BEFORE_CANCEL  # Cancel arrived after the commit point
        return None

    def _failed(self, error: BaseException, project_id: str) -> None:
        """Show the error; if the stored project is gone or changed, resync from disk.

        The resync is chained without going idle, so a pending close cannot slip in
        between the failure and the re-list.
        """

        notice = notice_for(error)
        stale = isinstance(
            error, ProjectNotFoundError | ProjectChangedError | ProjectStorageError
        )
        if not stale:
            self._end(notice=notice)
            return
        current = self._state.current
        was_open = current is not None and current.summary.project_id == project_id

        def work() -> tuple[ProjectDetails | None, Any]:
            listing = self._list_quietly()
            if not was_open:
                return None, listing
            try:
                return self._workflow.open_project(project_id), listing
            except Exception:
                return None, listing

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._end(notice=notice)
                return
            details, listing = outcome
            changes: dict[str, Any] = {
                "notice": notice,
                **self._listing_changes(listing),
            }
            if was_open:
                changes["current"] = details
            self._end(**changes)

        self._set(activity=ProjectsActivity.LISTING, progress=None, notice=notice)
        self._runner.run(work, done)

    def _start(
        self,
        activity: ProjectsActivity,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        *,
        keep_notice: bool = False,
    ) -> bool:
        if self._state.busy:
            return False
        self._cancel.clear()
        self._progress.reset()
        changes: dict[str, Any] = {
            "activity": activity,
            "progress": None,
            "cancelling": False,
        }
        if not keep_notice:
            changes["notice"] = None
        self._set(**changes)
        self._runner.run(work, done)
        return True

    def _apply_progress(self, progress: BatchProgress) -> None:
        if self._state.activity is ProjectsActivity.ANALYZING:
            self._set(progress=progress)

    def _end(self, **changes: Any) -> None:
        self._progress.reset()
        self._set(
            activity=ProjectsActivity.IDLE,
            progress=None,
            cancelling=False,
            **changes,
        )
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
