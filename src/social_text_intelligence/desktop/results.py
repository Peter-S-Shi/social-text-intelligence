"""Qt-free controller for the Import & validation and Results pages.

Validation detail, the result rows, and the normalized export all come from
``ResultsWorkflow``. This controller runs each operation off the UI thread, allows one
at a time, and turns errors into fixed notices that never contain record text or file
paths. The same state feeds both pages, so they cannot disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..application.project_workflow import ProjectBusyError, ProjectNotFoundError
from ..application.results_workflow import (
    ResultsFilters,
    ResultsSnapshot,
    ResultsUnavailableError,
    ResultsWorkflow,
    ValidationSnapshot,
    ValidationUnavailableError,
)
from ..contracts.errors import ProjectStorageError
from .controller import JobRunner
from .exporting import EXPORT_FAILED_BODY, EXPORT_FAILED_TITLE, write_atomic
from .projects import NoticeKind, ProjectsNotice, notice_for

EXPORT_SAVED_BODY = (
    "The normalized CSV was saved where you chose. It contains the text of your "
    "records, so keep it as private as the original CSV."
)


class ResultsActivity(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    EXPORTING = "exporting"


@dataclass(frozen=True, slots=True)
class ResultsState:
    project_id: str | None = None
    validation: ValidationSnapshot | None = None
    results: ResultsSnapshot | None = None
    filters: ResultsFilters = ResultsFilters()  # noqa: RUF009 (frozen value)
    activity: ResultsActivity = ResultsActivity.IDLE
    notice: ProjectsNotice | None = None

    @property
    def active(self) -> bool:
        return self.project_id is not None

    @property
    def loaded(self) -> bool:
        return self.validation is not None or self.results is not None

    @property
    def busy(self) -> bool:
        return self.activity is not ResultsActivity.IDLE


Listener = Callable[[ResultsState], None]

_EXPORT_SAVED = ProjectsNotice(
    NoticeKind.INFO, "export_saved", "Normalized CSV saved", EXPORT_SAVED_BODY
)
_EXPORT_FAILED = ProjectsNotice(
    NoticeKind.ERROR, "export_failed", EXPORT_FAILED_TITLE, EXPORT_FAILED_BODY
)


def results_notice_for(error: BaseException) -> ProjectsNotice:
    """A fixed, content-free notice; an unknown error's own text is never shown."""

    if isinstance(error, ResultsUnavailableError | ValidationUnavailableError):
        return ProjectsNotice(
            NoticeKind.ERROR, error.code, "Nothing to show yet", error.message
        )
    if isinstance(error, ProjectBusyError | ProjectNotFoundError | ProjectStorageError):
        return notice_for(error)
    return notice_for(RuntimeError())  # the generic, fixed "did not finish" notice


class ResultsController:
    def __init__(
        self,
        workflow: ResultsWorkflow,
        runner: JobRunner,
        *,
        write_file: Callable[[Path, str], None] = write_atomic,
    ) -> None:
        self._workflow = workflow
        self._runner = runner
        self._write_file = write_file
        self._state = ResultsState()
        self._listeners: list[Listener] = []
        self._idle_callbacks: list[Callable[[], None]] = []

    @property
    def state(self) -> ResultsState:
        return self._state

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def when_idle(self, callback: Callable[[], None]) -> None:
        if self._state.busy:
            self._idle_callbacks.append(callback)
        else:
            callback()

    # -- commands -----------------------------------------------------------

    def open(self, project_id: str) -> bool:
        """Load a project's validation detail and, if analysed, its results."""

        return self._load(
            project_id,
            ResultsFilters(),
            fresh=self._state.project_id != project_id,
        )

    def refresh(self) -> bool:
        project_id = self._state.project_id
        if project_id is None:
            return False
        return self._load(project_id, self._state.filters, fresh=False)

    def set_filters(self, filters: ResultsFilters) -> bool:
        project_id = self._state.project_id
        if project_id is None or self._state.results is None:
            return False
        return self._load(project_id, filters, fresh=False)

    def export(self, path: Path, *, include_native: bool) -> bool:
        project_id = self._state.project_id
        if project_id is None or self._state.results is None:
            return False

        def work() -> None:
            text = self._workflow.export_csv(project_id, include_native=include_native)
            self._write_file(path, text)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                failed = (
                    _EXPORT_FAILED
                    if isinstance(outcome, OSError)
                    else results_notice_for(outcome)
                )
                self._end(notice=failed)
                return
            self._end(notice=_EXPORT_SAVED)

        return self._start(ResultsActivity.EXPORTING, work, done)

    def dismiss_notice(self) -> None:
        self._set(notice=None)

    def close(self) -> bool:
        if self._state.busy:
            return False
        self._set(
            project_id=None,
            validation=None,
            results=None,
            filters=ResultsFilters(),
            notice=None,
        )
        return True

    # -- internals ----------------------------------------------------------

    def _load(self, project_id: str, filters: ResultsFilters, *, fresh: bool) -> bool:
        def work() -> tuple[ValidationSnapshot | None, ResultsSnapshot | None]:
            try:
                validation: ValidationSnapshot | None = self._workflow.validation(
                    project_id
                )
            except ValidationUnavailableError:
                validation = None
            try:
                results: ResultsSnapshot | None = self._workflow.results(
                    project_id, filters
                )
            except ResultsUnavailableError:
                results = None
            return validation, results

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            validation, results = outcome
            self._end(
                project_id=project_id,
                validation=validation,
                results=results,
                filters=filters,
                notice=None,
            )

        pending: dict[str, Any] = {"project_id": project_id}
        if fresh:
            pending.update(validation=None, results=None, notice=None)
        return self._start(ResultsActivity.LOADING, work, done, **pending)

    def _failed(self, error: BaseException) -> None:
        notice = results_notice_for(error)
        if isinstance(error, ProjectNotFoundError):
            self._end(
                project_id=None,
                validation=None,
                results=None,
                filters=ResultsFilters(),
                notice=notice,
            )
            return
        self._end(notice=notice)

    def _start(
        self,
        activity: ResultsActivity,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        **changes: Any,
    ) -> bool:
        if self._state.busy:
            return False
        self._set(**{"activity": activity, "notice": None, **changes})
        self._runner.run(work, done)
        return True

    def _end(self, **changes: Any) -> None:
        self._set(activity=ResultsActivity.IDLE, **changes)
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
