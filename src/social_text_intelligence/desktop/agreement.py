"""Qt-free controller for the Agreement page.

The agreement summary (rates over definitive reviews, confusion, label comparison,
corrections, confidence bands) is computed by the review service; this controller only
loads it for a project, runs the reviewed export, and keeps fixed, content-free
notices. It never reads or changes a judgment.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..application.project_workflow import ProjectNotFoundError
from ..application.review_workflow import ReviewSummary, ReviewWorkflow
from .controller import JobRunner
from .exporting import EXPORT_FAILED_BODY, EXPORT_FAILED_TITLE, write_atomic
from .projects import NoticeKind, ProjectsNotice
from .review import EXPORT_SAVED_BODY, review_notice_for


class AgreementActivity(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    EXPORTING = "exporting"


@dataclass(frozen=True, slots=True)
class AgreementState:
    project_id: str | None = None
    summary: ReviewSummary | None = None
    activity: AgreementActivity = AgreementActivity.IDLE
    notice: ProjectsNotice | None = None

    @property
    def active(self) -> bool:
        return self.project_id is not None

    @property
    def busy(self) -> bool:
        return self.activity is not AgreementActivity.IDLE


Listener = Callable[[AgreementState], None]

_EXPORT_SAVED = ProjectsNotice(
    NoticeKind.INFO, "export_saved", "Reviewed CSV saved", EXPORT_SAVED_BODY
)
_EXPORT_FAILED = ProjectsNotice(
    NoticeKind.ERROR, "export_failed", EXPORT_FAILED_TITLE, EXPORT_FAILED_BODY
)


class AgreementController:
    def __init__(
        self,
        workflow: ReviewWorkflow,
        runner: JobRunner,
        *,
        write_file: Callable[[Path, str], None] = write_atomic,
    ) -> None:
        self._workflow = workflow
        self._runner = runner
        self._write_file = write_file
        self._state = AgreementState()
        self._listeners: list[Listener] = []
        self._idle_callbacks: list[Callable[[], None]] = []

    @property
    def state(self) -> AgreementState:
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
        """Load (or reload) a project's agreement summary."""

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                notice = review_notice_for(outcome)
                gone = isinstance(outcome, ProjectNotFoundError)
                self._end(
                    project_id=None if gone else project_id,
                    summary=None,
                    notice=ProjectsNotice(
                        notice.kind, notice.code, notice.title, notice.body
                    ),
                )
                return
            self._end(project_id=project_id, summary=outcome, notice=None)

        return self._start(
            AgreementActivity.LOADING,
            lambda: self._workflow.agreement(project_id),
            done,
            project_id=project_id,
        )

    def export(self, path: Path, *, include_native: bool) -> bool:
        project_id = self._state.project_id
        if project_id is None or self._state.summary is None:
            return False

        def work() -> None:
            text = self._workflow.export_csv(project_id, include_native=include_native)
            self._write_file(path, text)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                if isinstance(outcome, OSError):
                    self._end(notice=_EXPORT_FAILED)
                else:
                    shared = review_notice_for(outcome)
                    self._end(
                        notice=ProjectsNotice(
                            shared.kind, shared.code, shared.title, shared.body
                        )
                    )
                return
            self._end(notice=_EXPORT_SAVED)

        return self._start(AgreementActivity.EXPORTING, work, done)

    def dismiss_notice(self) -> None:
        self._set(notice=None)

    def close(self) -> bool:
        if self._state.busy:
            return False
        self._set(project_id=None, summary=None, notice=None)
        return True

    # -- internals ----------------------------------------------------------

    def _start(
        self,
        activity: AgreementActivity,
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
        self._set(activity=AgreementActivity.IDLE, **changes)
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
