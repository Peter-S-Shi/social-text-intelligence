"""Qt-free controller for the Review surface: judge, navigate, export.

All review rules, the stored human review, and the stale-write protection live in
``ReviewWorkflow``. This controller runs each operation off the UI thread, allows one
at a time, keeps the human's unsaved draft separate from the saved review, and turns
errors into fixed notices that never contain record text, notes, or file paths.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..application.project_workflow import (
    ProjectBusyError,
    ProjectNotFoundError,
)
from ..application.review_workflow import (
    Advance,
    ReviewConflictError,
    ReviewDraft,
    ReviewFilters,
    ReviewSnapshot,
    ReviewUnavailableError,
    ReviewWorkflow,
)
from ..contracts.errors import ProjectStorageError, ValidationError
from .controller import JobRunner
from .exporting import EXPORT_FAILED_BODY, EXPORT_FAILED_TITLE, write_atomic
from .projects import NoticeKind, ProjectsNotice, notice_for

EXPORT_SAVED_BODY = (
    "The reviewed CSV was saved where you chose. It contains the text of your "
    "records and your notes, so keep it as private as the original CSV."
)


class ReviewActivity(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    SAVING = "saving"
    EXPORTING = "exporting"


@dataclass(frozen=True, slots=True)
class ReviewNotice(ProjectsNotice):
    """A project notice that may also name the form field it belongs to."""

    field: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewState:
    project_id: str | None = None
    snapshot: ReviewSnapshot | None = None
    filters: ReviewFilters = ReviewFilters()  # noqa: RUF009 (frozen value)
    draft: ReviewDraft = ReviewDraft()  # noqa: RUF009 (frozen value)
    activity: ReviewActivity = ReviewActivity.IDLE
    notice: ReviewNotice | None = None

    @property
    def active(self) -> bool:
        """The review surface is showing (or loading) a project."""

        return self.project_id is not None

    @property
    def is_open(self) -> bool:
        return self.snapshot is not None

    @property
    def busy(self) -> bool:
        return self.activity is not ReviewActivity.IDLE

    @property
    def has_unsaved_changes(self) -> bool:
        record = self.snapshot.record if self.snapshot else None
        return record is not None and self.draft != ReviewDraft.from_review(
            record.review
        )


Listener = Callable[[ReviewState], None]

_SAVED = ReviewNotice(
    NoticeKind.INFO, "review_saved", "Review saved", "Your judgment was saved."
)
_SAVED_PARTIAL = ReviewNotice(
    NoticeKind.INFO,
    "review_saved_partial",
    "Partly reviewed",
    "Saved. A record counts as reviewed once both sentiment and emotion have a "
    "judgment.",
)
_SAVED_NEXT = ReviewNotice(
    NoticeKind.INFO,
    "review_saved_next",
    "Review saved",
    "Your judgment was saved. The next record is shown.",
)
_SAVED_PARTIAL_NEXT = ReviewNotice(
    NoticeKind.INFO,
    "review_saved_partial_next",
    "Partly reviewed",
    "The previous record was saved, but it counts as reviewed only once both "
    "sentiment and emotion have a judgment. The next record is shown.",
)
_EXPORT_SAVED = ReviewNotice(
    NoticeKind.INFO, "export_saved", "Reviewed CSV saved", EXPORT_SAVED_BODY
)
_EXPORT_FAILED = ReviewNotice(
    NoticeKind.ERROR, "export_failed", EXPORT_FAILED_TITLE, EXPORT_FAILED_BODY
)


def review_notice_for(error: BaseException) -> ReviewNotice:
    """A fixed, content-free notice; an unknown error's own text is never shown."""

    if isinstance(error, ValidationError):
        return ReviewNotice(
            NoticeKind.ERROR,
            error.code,
            "Check this judgment",
            error.message,
            field=error.field,
        )
    if isinstance(error, ReviewConflictError):
        return ReviewNotice(
            NoticeKind.ERROR, error.code, "Changed elsewhere", error.message
        )
    if isinstance(error, ReviewUnavailableError):
        return ReviewNotice(
            NoticeKind.ERROR, error.code, "Nothing to review here", error.message
        )
    if isinstance(error, ProjectBusyError | ProjectNotFoundError | ProjectStorageError):
        shared = notice_for(error)
        return ReviewNotice(shared.kind, shared.code, shared.title, shared.body)
    return ReviewNotice(
        NoticeKind.ERROR,
        "unexpected_error",
        "The operation did not finish",
        "The operation could not be completed. Try again, or restart the app.",
    )


class ReviewController:
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
        self._state = ReviewState()
        self._listeners: list[Listener] = []
        self._idle_callbacks: list[Callable[[], None]] = []

    @property
    def state(self) -> ReviewState:
        return self._state

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def when_idle(self, callback: Callable[[], None]) -> None:
        if self._state.busy:
            self._idle_callbacks.append(callback)
        else:
            callback()

    # -- commands -----------------------------------------------------------

    def open(
        self,
        project_id: str,
        filters: ReviewFilters | None = None,
        *,
        row: int | None = None,
    ) -> bool:
        """Open the review of an analysed project (the first record, or ``row``)."""

        wanted = filters or ReviewFilters()
        return self._load(
            lambda: self._workflow.open_review(project_id, wanted, row=row),
            project_id=project_id,
            filters=wanted,
        )

    def set_filters(self, filters: ReviewFilters) -> bool:
        project_id = self._state.project_id
        if project_id is None:
            return False
        return self._load(
            lambda: self._workflow.open_review(project_id, filters), filters=filters
        )

    def previous(self) -> bool:
        return self._go(lambda s: s.previous_row)

    def next(self) -> bool:
        return self._go(lambda s: s.next_row)

    def next_unreviewed(self) -> bool:
        return self._go(lambda s: s.next_unreviewed_row)

    def set_draft(self, draft: ReviewDraft) -> None:
        if self._state.is_open and not self._state.busy:
            self._set(draft=draft)

    def discard_changes(self) -> None:
        """Drop the unsaved draft: the form shows the saved review again.

        The record and position stay where they are, so leaving the page after a
        confirmed discard cannot bring the draft back or let it be saved later.
        """

        record = self._state.snapshot.record if self._state.snapshot else None
        if record is not None and not self._state.busy:
            self._set(draft=ReviewDraft.from_review(record.review), notice=None)

    def save(self, advance: Advance = Advance.STAY) -> bool:
        return self._save(advance, accept=False)

    def accept_both(self, advance: Advance = Advance.STAY) -> bool:
        return self._save(advance, accept=True)

    def export(self, path: Path, *, include_native: bool) -> bool:
        project_id = self._state.project_id
        if project_id is None or not self._state.is_open:
            return False

        def work() -> None:
            text = self._workflow.export_csv(project_id, include_native=include_native)
            self._write_file(path, text)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                failed = (
                    _EXPORT_FAILED
                    if isinstance(outcome, OSError)
                    else review_notice_for(outcome)
                )
                self._end(notice=failed)
                return
            self._end(notice=_EXPORT_SAVED)

        return self._start(ReviewActivity.EXPORTING, work, done)

    def close(self) -> bool:
        """Leave the review; an unsaved draft is discarded (the page confirms first)."""

        if self._state.busy:
            return False
        self._set(
            project_id=None,
            snapshot=None,
            filters=ReviewFilters(),
            draft=ReviewDraft(),
            notice=None,
        )
        return True

    # -- internals ----------------------------------------------------------

    def _go(self, row: Callable[[ReviewSnapshot], int | None]) -> bool:
        snapshot, project_id = self._state.snapshot, self._state.project_id
        target = row(snapshot) if snapshot is not None else None
        if snapshot is None or project_id is None or target is None:
            return False
        filters = self._state.filters
        return self._load(
            lambda: self._workflow.open_review(project_id, filters, row=target)
        )

    def _load(
        self,
        work: Callable[[], ReviewSnapshot],
        *,
        project_id: str | None = None,
        filters: ReviewFilters | None = None,
    ) -> bool:
        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(**self._shown(outcome), notice=None)

        pending: dict[str, Any] = {}
        if project_id is not None:
            pending["project_id"] = project_id
        if filters is not None:
            pending["filters"] = filters
        return self._start(ReviewActivity.LOADING, work, done, **pending)

    def _save(self, advance: Advance, *, accept: bool) -> bool:
        state = self._state
        record = state.snapshot.record if state.snapshot else None
        project_id = state.project_id
        if record is None or project_id is None:
            return False
        draft, filters, row = state.draft, state.filters, record.row_number

        def work() -> ReviewSnapshot:
            if accept:
                return self._workflow.accept_both(
                    project_id,
                    row,
                    draft.note,
                    expected=record.review,
                    filters=filters,
                    advance=advance,
                )
            return self._workflow.save(
                project_id,
                row,
                draft,
                expected=record.review,
                filters=filters,
                advance=advance,
            )

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(**self._shown(outcome), notice=self._saved_notice(outcome))

        return self._start(ReviewActivity.SAVING, work, done)

    @staticmethod
    def _saved_notice(outcome: ReviewSnapshot) -> ReviewNotice | None:
        """What was saved, said truthfully, whether or not the view moved on."""

        saved, shown = outcome.saved, outcome.record
        if saved is None:
            return None
        moved = shown is not None and shown.row_number != saved.row_number
        if saved.review.is_reviewed:
            return _SAVED_NEXT if moved else _SAVED
        return _SAVED_PARTIAL_NEXT if moved else _SAVED_PARTIAL

    def _shown(self, snapshot: ReviewSnapshot) -> dict[str, Any]:
        record = snapshot.record
        return {
            "snapshot": snapshot,
            "draft": ReviewDraft.from_review(record.review)
            if record is not None
            else ReviewDraft(),
        }

    def _failed(self, error: BaseException) -> None:
        """Show the error. Where the stored state is the truth (a conflict, a vanished
        row, a removed project) show it instead of the stale view, without going idle
        in between."""

        notice = review_notice_for(error)
        if isinstance(error, ProjectNotFoundError):
            self._end(
                project_id=None,
                snapshot=None,
                filters=ReviewFilters(),
                draft=ReviewDraft(),
                notice=notice,
            )
            return
        snapshot = self._state.snapshot
        if snapshot is None:  # the review never opened: leave it, with the reason
            self._end(project_id=None, filters=ReviewFilters(), notice=notice)
            return
        if not isinstance(error, ReviewConflictError | ReviewUnavailableError):
            self._end(notice=notice)  # validation, busy, storage: keep the draft
            return
        project_id, filters = self._state.project_id, self._state.filters
        row = snapshot.record.row_number if snapshot.record else None
        if project_id is None:
            self._end(notice=notice)
            return

        def work() -> ReviewSnapshot:
            if row is not None:
                try:
                    return self._workflow.open_review(project_id, filters, row=row)
                except ReviewUnavailableError:
                    pass
            return self._workflow.open_review(project_id, filters)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._end(
                    project_id=None,
                    snapshot=None,
                    filters=ReviewFilters(),
                    draft=ReviewDraft(),
                    notice=review_notice_for(outcome),
                )
                return
            self._end(**self._shown(outcome), notice=notice)

        self._set(activity=ReviewActivity.LOADING, notice=notice)
        self._runner.run(work, done)

    def _start(
        self,
        activity: ReviewActivity,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        **changes: Any,
    ) -> bool:
        if self._state.busy:
            return False
        self._set(activity=activity, notice=None, **changes)
        self._runner.run(work, done)
        return True

    def _end(self, **changes: Any) -> None:
        self._set(activity=ReviewActivity.IDLE, **changes)
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
