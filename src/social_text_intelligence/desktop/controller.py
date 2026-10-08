"""Qt-free controller: routes provisioning actions and owns the operation state.

Every long call runs through a ``JobRunner`` so it never blocks the UI thread,
and results reach listeners only on the UI thread. The controller talks to the
``ModelProvisioning`` port alone; it holds no backend rules of its own.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from ..application.model_provisioning import (
    FolderInspection,
    ModelProvisioning,
    ModelsStatus,
    ProvisioningOutcome,
    ProvisioningProgress,
    ProvisioningResult,
    Readiness,
)
from ..contracts.errors import ModelProvisioningError
from .progress import CoalescedUpdates

UNEXPECTED_ERROR_CODE = "unexpected_error"
UNEXPECTED_ERROR_MESSAGE = (
    "The operation could not be completed. Try again, or restart the app."
)


def _error_parts(error: BaseException) -> tuple[str, str]:
    """The fixed code and message; unexpected errors never expose their own text."""

    if isinstance(error, ModelProvisioningError):
        return error.code, error.message
    return UNEXPECTED_ERROR_CODE, UNEXPECTED_ERROR_MESSAGE


class JobRunner(Protocol):
    """Runs work off the UI thread and brings results back to it."""

    def run(self, work: Callable[[], Any], deliver: Callable[[Any], None]) -> None:
        """Run ``work`` on a worker; call ``deliver(result_or_exception)`` on the UI."""
        ...

    def post(self, call: Callable[[], None]) -> None:
        """Call ``call`` on the UI thread; safe to call from any thread."""
        ...

    def wait_idle(self, timeout: float = 10.0) -> bool:
        """Wait for running workers (shutdown); False if one is still running."""
        ...


class Activity(StrEnum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    IMPORTING = "importing"
    VERIFYING = "verifying"
    INSPECTING = "inspecting"
    DISCARDING = "discarding"


STOPPABLE = frozenset({Activity.DOWNLOADING, Activity.IMPORTING})
# Activities that report progress (and have a progress block in the UI).
REPORTING_PROGRESS = (Activity.DOWNLOADING, Activity.IMPORTING, Activity.VERIFYING)


@dataclass(frozen=True, slots=True)
class OperationReport:
    """The last finished operation, for the panel to explain and offer recovery."""

    kind: Activity
    outcome: ProvisioningOutcome
    error_code: str | None = None
    error_message: str | None = None
    found_damage: bool = False


@dataclass(frozen=True, slots=True)
class FolderState:
    path: Path
    checking: bool = False
    inspection: FolderInspection | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ControllerState:
    status: ModelsStatus
    activity: Activity = Activity.IDLE
    progress: ProvisioningProgress | None = None
    stopping: bool = False
    report: OperationReport | None = None
    folder: FolderState | None = None

    @property
    def busy(self) -> bool:
        return self.activity is not Activity.IDLE


Listener = Callable[[ControllerState], None]


class ProvisioningController:
    def __init__(self, provisioning: ModelProvisioning, runner: JobRunner) -> None:
        self._provisioning = provisioning
        self._runner = runner
        self._state = ControllerState(status=ModelsStatus(()))
        self._listeners: list[Listener] = []
        self._verify_observers: list[Callable[[ModelsStatus], None]] = []
        self._idle_callbacks: list[Callable[[], None]] = []
        self._cancel = threading.Event()
        self._progress = CoalescedUpdates(runner.post, self._apply_progress)
        self._retry: Callable[[], bool] | None = None

    @property
    def state(self) -> ControllerState:
        return self._state

    @property
    def can_stop(self) -> bool:
        return self._state.activity in STOPPABLE and not self._state.stopping

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def add_verify_observer(self, observer: Callable[[ModelsStatus], None]) -> None:
        """Called with the fresh status after a successful Verify, before listeners."""

        self._verify_observers.append(observer)

    def refresh(self) -> None:
        """Quick, read-only status (also the launch check)."""

        self._set(status=self._provisioning.status())

    def when_idle(self, callback: Callable[[], None]) -> None:
        if self._state.busy:
            self._idle_callbacks.append(callback)
        else:
            callback()

    # -- commands -----------------------------------------------------------

    def download(self, keys: tuple[str, ...] | None = None) -> bool:
        def work() -> ProvisioningResult:
            return self._provisioning.download(
                keys, on_progress=self._progress.push, cancelled=self._cancel.is_set
            )

        return self._start(
            Activity.DOWNLOADING,
            work,
            self._finish_result,
            retry=lambda: self.download(keys),
        )

    def import_folder(self, keys: tuple[str, ...] | None = None) -> bool:
        folder = self._state.folder
        if folder is None or folder.inspection is None:
            return False
        importable = folder.inspection.importable_keys
        chosen = (
            importable if keys is None else tuple(k for k in keys if k in importable)
        )
        if not chosen:
            return False
        path = folder.path

        def work() -> ProvisioningResult:
            return self._provisioning.import_folder(
                path,
                chosen,
                on_progress=self._progress.push,
                cancelled=self._cancel.is_set,
            )

        def done(outcome: Any) -> None:
            self._finish_result(outcome, clear_folder_when_completed=True)

        return self._start(
            Activity.IMPORTING,
            work,
            done,
            retry=lambda: self.import_folder(chosen),
        )

    def verify(self) -> bool:
        def work() -> ModelsStatus:
            return self._provisioning.verify(on_progress=self._progress.push)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._finish_error(Activity.VERIFYING, outcome)
                return
            damaged = any(m.readiness is Readiness.CORRUPT for m in outcome.models)
            for observer in self._verify_observers:
                observer(outcome)
            report = OperationReport(
                Activity.VERIFYING, ProvisioningOutcome.COMPLETED, found_damage=damaged
            )
            self._end(status=outcome, report=report)

        return self._start(Activity.VERIFYING, work, done, retry=self.verify)

    def discard(self, keys: tuple[str, ...] | None = None) -> bool:
        def work() -> ModelsStatus:
            return self._provisioning.discard_partial_downloads(keys)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._finish_error(Activity.DISCARDING, outcome)
                return
            self._end(
                status=outcome,
                report=OperationReport(
                    Activity.DISCARDING, ProvisioningOutcome.COMPLETED
                ),
            )

        return self._start(
            Activity.DISCARDING, work, done, retry=lambda: self.discard(keys)
        )

    def inspect_folder(self, path: Path) -> bool:
        def work() -> FolderInspection:
            return self._provisioning.inspect_folder(path)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                code, message = _error_parts(outcome)
                folder = FolderState(path, error_code=code, error_message=message)
            else:
                folder = FolderState(path, inspection=outcome)
            self._end(folder=folder)

        return self._start(
            Activity.INSPECTING,
            work,
            done,
            folder=FolderState(path, checking=True),
        )

    def stop(self) -> None:
        if self.can_stop:
            self._cancel.set()
            self._set(stopping=True)

    def retry(self) -> bool:
        report = self._state.report
        if self._retry is None or report is None:
            return False
        if report.outcome is not ProvisioningOutcome.FAILED:
            return False
        return self._retry()

    def dismiss_report(self) -> None:
        self._set(report=None)

    def close_folder(self) -> None:
        if not self._state.busy:
            self._set(folder=None)

    # -- internals ----------------------------------------------------------

    def _start(
        self,
        activity: Activity,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        *,
        retry: Callable[[], bool] | None = None,
        folder: FolderState | None = None,
    ) -> bool:
        if self._state.busy:
            return False
        self._cancel.clear()
        self._progress.reset()
        changes: dict[str, Any] = {
            "activity": activity,
            "progress": None,
            "stopping": False,
        }
        if activity is Activity.INSPECTING:
            # a folder check keeps the last report (and its Try again target)
            changes["folder"] = folder
        else:
            self._retry = retry
            changes["report"] = None
        self._set(**changes)
        self._runner.run(work, done)
        return True

    def _apply_progress(self, progress: ProvisioningProgress) -> None:
        if self._state.busy:
            self._set(progress=progress)

    def _finish_result(
        self, outcome: Any, *, clear_folder_when_completed: bool = False
    ) -> None:
        if isinstance(outcome, BaseException):
            self._finish_error(self._state.activity, outcome)
            return
        assert isinstance(outcome, ProvisioningResult)
        report = OperationReport(
            self._state.activity,
            outcome.outcome,
            outcome.error_code,
            outcome.error_message,
        )
        changes: dict[str, Any] = {"status": outcome.status, "report": report}
        if (
            clear_folder_when_completed
            and outcome.outcome is ProvisioningOutcome.COMPLETED
        ):
            changes["folder"] = None  # imported: nothing left to import from it
        self._end(**changes)

    def _finish_error(self, kind: Activity, error: BaseException) -> None:
        code, message = _error_parts(error)
        report = OperationReport(kind, ProvisioningOutcome.FAILED, code, message)
        self._end(report=report)

    def _end(self, **changes: Any) -> None:
        self._progress.reset()
        self._set(activity=Activity.IDLE, progress=None, stopping=False, **changes)
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
