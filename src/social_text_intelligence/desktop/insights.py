"""Qt-free controller for the Insights surface: view, notes, cases, export.

Group membership, denominators, eligibility, agreement, sample-size assessment, case
selection, note validation, and export all come from ``InsightsWorkflow`` and the
insight service. This controller runs each operation off the UI thread, allows one at
a time, keeps the person's not-yet-applied controls and unsaved note apart from what
is saved, and turns errors into fixed notices that never carry record text, notes, or
file paths.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..application.insights_workflow import (
    INSIGHT_METRICS_BY_PERSPECTIVE,
    ExampleControls,
    GroupingDimension,
    InsightControls,
    InsightMetric,
    InsightPerspective,
    InsightsSnapshot,
    InsightsUnavailableError,
    InsightsWorkflow,
    NoteDraft,
)
from ..application.project_workflow import ProjectNotFoundError
from ..contracts import EmotionLabel, SentimentLabel
from ..contracts.errors import ValidationError
from .controller import JobRunner
from .exporting import EXPORT_FAILED_BODY, EXPORT_FAILED_TITLE, write_atomic
from .projects import NoticeKind, ProjectsNotice, notice_for

EXPORT_SAVED_BODY = (
    "The insights CSV was saved where you chose. It can contain record text, your "
    "notes, and review labels, so keep it as private as the original CSV."
)


class InsightsActivity(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    APPLYING = "applying"
    SELECTING = "selecting"
    ADDING_NOTE = "adding_note"
    REMOVING_NOTE = "removing_note"
    EXPORTING = "exporting"


@dataclass(frozen=True, slots=True)
class InsightsNotice(ProjectsNotice):
    """A project notice that may also name the control it belongs to."""

    field: str | None = None


@dataclass(frozen=True, slots=True)
class InsightsState:
    project_id: str | None = None
    snapshot: InsightsSnapshot | None = None
    controls: InsightControls | None = None  # what the controls show, not yet applied
    examples: ExampleControls = ExampleControls()  # noqa: RUF009 (frozen value)
    note_draft: NoteDraft = NoteDraft()  # noqa: RUF009 (frozen value)
    activity: InsightsActivity = InsightsActivity.IDLE
    notice: InsightsNotice | None = None

    @property
    def active(self) -> bool:
        """The insights surface is showing (or loading) a project."""

        return self.project_id is not None

    @property
    def is_open(self) -> bool:
        return self.snapshot is not None

    @property
    def busy(self) -> bool:
        return self.activity is not InsightsActivity.IDLE

    @property
    def has_unsaved_changes(self) -> bool:
        """Only a note being written is work that would be lost."""

        draft = self.note_draft
        return bool(
            draft.phrase.strip()
            or draft.explanation.strip()
            or draft.context_importance.strip()
            or draft.tags
        )


Listener = Callable[[InsightsState], None]

_NOTE_ADDED = InsightsNotice(
    NoticeKind.INFO,
    "note_added",
    "Note added",
    "Your note was saved with this project. It is human-written context and does "
    "not change any AI or review result.",
)
_NOTE_REMOVED = InsightsNotice(
    NoticeKind.INFO, "note_removed", "Note deleted", "The note was deleted."
)
_EXPORT_SAVED = InsightsNotice(
    NoticeKind.INFO, "export_saved", "Insights CSV saved", EXPORT_SAVED_BODY
)
_EXPORT_FAILED = InsightsNotice(
    NoticeKind.ERROR, "export_failed", EXPORT_FAILED_TITLE, EXPORT_FAILED_BODY
)


def insights_notice_for(error: BaseException) -> InsightsNotice:
    """A fixed, content-free notice; an unknown error's own text is never shown."""

    if isinstance(error, ValidationError):
        return InsightsNotice(
            NoticeKind.ERROR,
            error.code,
            "Check this entry",
            error.message,
            field=error.field,
        )
    if isinstance(error, InsightsUnavailableError):
        return InsightsNotice(
            NoticeKind.ERROR, error.code, "No insights yet", error.message
        )
    shared = notice_for(error)  # busy, missing, storage; else its generic fallback
    return InsightsNotice(shared.kind, shared.code, shared.title, shared.body)


class InsightsController:
    def __init__(
        self,
        workflow: InsightsWorkflow,
        runner: JobRunner,
        *,
        write_file: Callable[[Path, str], None] = write_atomic,
    ) -> None:
        self._workflow = workflow
        self._runner = runner
        self._write_file = write_file
        self._state = InsightsState()
        self._listeners: list[Listener] = []
        self._idle_callbacks: list[Callable[[], None]] = []

    @property
    def state(self) -> InsightsState:
        return self._state

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def when_idle(self, callback: Callable[[], None]) -> None:
        if self._state.busy:
            self._idle_callbacks.append(callback)
        else:
            callback()

    # -- opening and closing ------------------------------------------------

    def open(self, project_id: str) -> bool:
        """Open the saved view (or the default one) of an analysed project."""

        examples = self._state.examples

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(
                snapshot=outcome,
                controls=InsightControls.from_selection(
                    outcome.selection, comparison=outcome.comparison
                ),
                notice=None,
            )

        return self._start(
            InsightsActivity.LOADING,
            lambda: self._workflow.open_insights(project_id, examples=examples),
            done,
            project_id=project_id,
        )

    def close(self) -> bool:
        """Leave the insights; an unsaved note is dropped (the page confirms first)."""

        if self._state.busy:
            return False
        self._set(
            project_id=None,
            snapshot=None,
            controls=None,
            examples=ExampleControls(),
            note_draft=NoteDraft(),
            notice=None,
        )
        return True

    def discard_changes(self) -> None:
        """Drop the unsaved note; the view and its saved state stay as they are."""

        if not self._state.busy:
            self._set(note_draft=NoteDraft(), notice=None)

    # -- the grouped view ---------------------------------------------------

    def set_grouping(self, grouping: GroupingDimension) -> None:
        controls, snapshot = self._state.controls, self._state.snapshot
        if controls is None or snapshot is None or self._state.busy:
            return
        groups = snapshot.groups_for(grouping)
        self._set(
            controls=replace(controls, grouping=grouping, groups=groups[:1]),
            notice=None,
        )

    def set_perspective(self, perspective: InsightPerspective) -> None:
        controls = self._state.controls
        if controls is None or self._state.busy:
            return
        metrics = INSIGHT_METRICS_BY_PERSPECTIVE[perspective]
        metric = controls.metric if controls.metric in metrics else metrics[0]
        self._set(
            controls=replace(controls, perspective=perspective, metric=metric),
            notice=None,
        )

    def set_groups(self, groups: tuple[str, ...]) -> None:
        self._edit(groups=groups)

    def set_comparison(self, comparison: bool) -> None:
        self._edit(comparison=comparison)

    def set_filters(
        self,
        *,
        metric: InsightMetric | None = None,
        sentiment: SentimentLabel | None = None,
        emotion: EmotionLabel | None = None,
        date_from: str = "",
        date_to: str = "",
    ) -> None:
        changes: dict[str, Any] = {
            "sentiment": sentiment,
            "emotion": emotion,
            "date_from": date_from,
            "date_to": date_to,
        }
        if metric is not None:
            changes["metric"] = metric
        self._edit(**changes)

    def apply(self) -> bool:
        """Validate the controls, save them as the project's view, and show it."""

        controls, project_id = self._state.controls, self._state.project_id
        if controls is None or project_id is None or not self._state.is_open:
            return False
        examples = self._state.examples

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(
                snapshot=outcome,
                controls=InsightControls.from_selection(
                    outcome.selection, comparison=controls.comparison
                ),
                notice=None,
            )

        return self._start(
            InsightsActivity.APPLYING,
            lambda: self._workflow.apply(project_id, controls, examples),
            done,
        )

    # -- representative cases -----------------------------------------------

    def set_examples(self, examples: ExampleControls) -> None:
        if self._state.is_open and not self._state.busy:
            self._set(examples=examples)

    def select_cases(self) -> bool:
        """Re-select cases by the chosen rule; the saved view is not changed."""

        return self._refresh(InsightsActivity.SELECTING)

    # -- context notes ------------------------------------------------------

    def set_note_draft(self, draft: NoteDraft) -> None:
        if self._state.is_open and not self._state.busy:
            self._set(note_draft=draft)

    def add_note(self) -> bool:
        project_id, draft = self._state.project_id, self._state.note_draft
        snapshot = self._state.snapshot
        if project_id is None or snapshot is None:
            return False
        examples, comparison = self._state.examples, snapshot.comparison

        def work() -> InsightsSnapshot:
            self._workflow.add_note(project_id, draft)
            return self._workflow.open_insights(
                project_id, examples=examples, comparison=comparison
            )

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(snapshot=outcome, note_draft=NoteDraft(), notice=_NOTE_ADDED)

        return self._start(InsightsActivity.ADDING_NOTE, work, done)

    def remove_note(self, note_id: str) -> bool:
        project_id, snapshot = self._state.project_id, self._state.snapshot
        if project_id is None or snapshot is None:
            return False
        examples, comparison = self._state.examples, snapshot.comparison

        def work() -> InsightsSnapshot:
            self._workflow.remove_note(project_id, note_id)
            return self._workflow.open_insights(
                project_id, examples=examples, comparison=comparison
            )

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome, resync_on="note_not_found")
                return
            self._end(snapshot=outcome, notice=_NOTE_REMOVED)

        return self._start(InsightsActivity.REMOVING_NOTE, work, done)

    # -- export -------------------------------------------------------------

    def export(
        self, path: Path, *, include_records: bool, include_native: bool
    ) -> bool:
        project_id, snapshot = self._state.project_id, self._state.snapshot
        if project_id is None or snapshot is None:
            return False
        comparison = snapshot.comparison

        def work() -> None:
            text = self._workflow.export_csv(
                project_id,
                comparison=comparison,
                include_records=include_records,
                include_native=include_native,
            )
            self._write_file(path, text)

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                failed = (
                    _EXPORT_FAILED
                    if isinstance(outcome, OSError)
                    else insights_notice_for(outcome)
                )
                self._end(notice=failed)
                return
            self._end(notice=_EXPORT_SAVED)

        return self._start(InsightsActivity.EXPORTING, work, done)

    # -- internals ----------------------------------------------------------

    def _edit(self, **changes: Any) -> None:
        controls = self._state.controls
        if controls is not None and not self._state.busy:
            self._set(controls=replace(controls, **changes), notice=None)

    def _refresh(self, activity: InsightsActivity) -> bool:
        project_id, snapshot = self._state.project_id, self._state.snapshot
        if project_id is None or snapshot is None:
            return False
        examples, comparison = self._state.examples, snapshot.comparison

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._failed(outcome)
                return
            self._end(snapshot=outcome, notice=None)

        return self._start(
            activity,
            lambda: self._workflow.open_insights(
                project_id, examples=examples, comparison=comparison
            ),
            done,
        )

    def _failed(self, error: BaseException, *, resync_on: str | None = None) -> None:
        """Show the error. Where the stored state is the truth (a note that is already
        gone) show it instead of the stale list, without going idle in between."""

        notice = insights_notice_for(error)
        if isinstance(error, ProjectNotFoundError | InsightsUnavailableError):
            self._end(
                project_id=None,
                snapshot=None,
                controls=None,
                examples=ExampleControls(),
                note_draft=NoteDraft(),
                notice=notice,
            )
            return
        project_id, snapshot = self._state.project_id, self._state.snapshot
        stale = (
            resync_on is not None
            and isinstance(error, ValidationError)
            and error.code == resync_on
        )
        if not stale or project_id is None or snapshot is None:
            self._end(notice=notice)  # validation, busy, storage: keep the work
            return
        examples, comparison = self._state.examples, snapshot.comparison

        def done(outcome: Any) -> None:
            if isinstance(outcome, BaseException):
                self._end(
                    project_id=None,
                    snapshot=None,
                    controls=None,
                    examples=ExampleControls(),
                    note_draft=NoteDraft(),
                    notice=insights_notice_for(outcome),
                )
                return
            self._end(snapshot=outcome, notice=notice)

        self._set(activity=InsightsActivity.LOADING, notice=notice)
        self._runner.run(
            lambda: self._workflow.open_insights(
                project_id, examples=examples, comparison=comparison
            ),
            done,
        )

    def _start(
        self,
        activity: InsightsActivity,
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
        self._set(activity=InsightsActivity.IDLE, **changes)
        callbacks, self._idle_callbacks = self._idle_callbacks, []
        for callback in callbacks:
            callback()

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
