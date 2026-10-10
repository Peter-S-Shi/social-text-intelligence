"""The Qt-free review controller over a real SQLite project (synthetic data)."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import pytest
from persistence.workflow_samples import SENTINEL, ScriptedGateway, csv_text

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    Advance,
    ReviewDraft,
    ReviewFilter,
    ReviewFilters,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.desktop.projects import NoticeKind
from social_text_intelligence.desktop.review import (
    ReviewActivity,
    ReviewController,
    ReviewState,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner, ManualRunner

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
ACCEPT, CORRECT = ReviewJudgment.ACCEPT, ReviewJudgment.CORRECT


class Env:
    def __init__(self, root: Path, rows: int = 3) -> None:
        self.root = root
        self.repository = SqliteProjectRepository(AppDataLocations(root))
        flow = ProjectWorkflow(self.repository, ScriptedGateway(), LIMITS)
        self.project_id = flow.import_csv(csv_text(rows), name="P").summary.project_id
        flow.analyze(self.project_id)
        self.written: dict[Path, str] = {}

    def workflow(self) -> ReviewWorkflow:
        return ReviewWorkflow(SqliteProjectRepository(AppDataLocations(self.root)))

    def write(self, path: Path, text: str) -> None:
        self.written[path] = text

    def controller(self, runner: Any = None, workflow: Any = None) -> ReviewController:
        return ReviewController(
            workflow or self.workflow(),
            runner or ImmediateRunner(),
            write_file=self.write,
        )


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def opened(env: Env, **kwargs: Any) -> ReviewController:
    controller = env.controller(**kwargs)
    assert controller.open(env.project_id)
    return controller


def snapshot_of(state: ReviewState) -> Any:
    assert state.snapshot is not None and state.snapshot.record is not None
    return state.snapshot.record


def judge_both(note: str = "") -> ReviewDraft:
    return ReviewDraft(
        sentiment_judgment=CORRECT,
        human_sentiment=SentimentLabel.NEGATIVE,
        emotion_judgment=CORRECT,
        human_dominant_emotion=EmotionLabel.ANGER,
        note=note,
    )


def test_opening_loads_the_first_record_off_the_caller_until_pumped(
    env: Env,
) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)

    assert controller.open(env.project_id) is True

    assert controller.state.activity is ReviewActivity.LOADING
    assert controller.state.busy and controller.state.snapshot is None
    assert controller.open(env.project_id) is False  # one operation at a time
    runner.run_next()
    state = controller.state
    assert state.activity is ReviewActivity.IDLE and state.is_open
    assert snapshot_of(state).row_number == 1
    assert state.draft == ReviewDraft()
    assert state.has_unsaved_changes is False


def test_editing_marks_unsaved_changes_and_saving_clears_them(env: Env) -> None:
    controller = opened(env)

    controller.set_draft(judge_both("checked"))
    assert controller.state.has_unsaved_changes
    assert controller.save() is True

    state = controller.state
    review = snapshot_of(state).review
    assert review.is_reviewed and review.note == "checked"
    assert state.draft == ReviewDraft.from_review(review)
    assert state.has_unsaved_changes is False
    assert state.notice is not None and state.notice.code == "review_saved"
    assert state.snapshot is not None and state.snapshot.summary.progress.reviewed == 1


def test_a_partial_review_is_saved_and_explained_as_partial(env: Env) -> None:
    controller = opened(env)

    controller.set_draft(ReviewDraft(sentiment_judgment=ACCEPT))
    controller.save()

    state = controller.state
    assert not snapshot_of(state).review.is_reviewed
    assert state.notice is not None and state.notice.code == "review_saved_partial"
    assert "both" in state.notice.body
    assert state.snapshot is not None and state.snapshot.summary.progress.reviewed == 0


def test_accept_both_saves_a_complete_review_and_can_advance(env: Env) -> None:
    controller = opened(env)
    controller.set_draft(ReviewDraft(note="fine"))

    assert controller.accept_both(Advance.NEXT) is True

    state = controller.state
    assert snapshot_of(state).row_number == 2  # moved on
    assert state.snapshot is not None and state.snapshot.summary.progress.reviewed == 1
    controller.previous()
    first = snapshot_of(controller.state).review
    assert first.is_reviewed and first.note == "fine"
    assert first.sentiment_judgment is ACCEPT


def test_advancing_still_confirms_what_was_saved(env: Env) -> None:
    controller = opened(env)
    controller.set_draft(judge_both())

    controller.save(Advance.NEXT)

    state = controller.state
    assert snapshot_of(state).row_number == 2
    assert state.notice is not None and state.notice.code == "review_saved_next"
    assert "next record" in state.notice.body

    controller.set_draft(ReviewDraft(sentiment_judgment=ACCEPT))
    controller.save(Advance.NEXT)

    notice = controller.state.notice
    assert notice is not None and notice.code == "review_saved_partial_next"
    assert "both" in notice.body  # the previous record is still only partly reviewed


def test_an_invalid_draft_shows_the_field_message_and_keeps_the_draft(
    env: Env,
) -> None:
    controller = opened(env)
    bad = ReviewDraft(
        sentiment_judgment=ACCEPT,
        emotion_judgment=CORRECT,
        human_dominant_emotion=EmotionLabel.JOY,
        human_secondary_emotions=(EmotionLabel.JOY,),
    )
    controller.set_draft(bad)

    controller.save()

    state = controller.state
    assert state.notice is not None and state.notice.kind is NoticeKind.ERROR
    assert state.notice.field == "human_secondary_emotions"
    assert state.notice.code == "dominant_repeated"
    assert state.draft == bad and state.has_unsaved_changes  # nothing was lost
    assert not snapshot_of(state).review.is_reviewed  # and nothing was stored


def test_a_conflict_shows_the_newer_saved_review_and_keeps_it(env: Env) -> None:
    controller = opened(env)
    other = env.workflow()
    seen = other.open_review(env.project_id)
    assert seen.record is not None
    kept = other.save(
        env.project_id, 1, judge_both("theirs"), expected=seen.record.review
    )
    controller.set_draft(ReviewDraft(note="mine"))

    controller.accept_both()

    state = controller.state
    assert state.notice is not None and state.notice.code == "review_conflict"
    assert kept.record is not None
    assert snapshot_of(state).review == kept.record.review  # theirs is shown
    assert state.draft == ReviewDraft.from_review(kept.record.review)
    stored = env.workflow().open_review(env.project_id)
    assert stored.record is not None and stored.record.review == kept.record.review


def test_navigation_moves_through_the_queue_and_next_unreviewed_wraps(
    env: Env,
) -> None:
    controller = opened(env)
    assert controller.previous() is False  # nothing before the first record

    controller.next()
    assert snapshot_of(controller.state).row_number == 2
    controller.set_draft(ReviewDraft(note=""))
    controller.accept_both()
    controller.next()
    assert snapshot_of(controller.state).row_number == 3
    controller.next_unreviewed()
    assert snapshot_of(controller.state).row_number == 1  # wrapped past reviewed row 2
    controller.previous()  # nothing before row 1
    assert snapshot_of(controller.state).row_number == 1


def test_a_filter_change_reloads_the_queue(env: Env) -> None:
    controller = opened(env)
    controller.set_draft(ReviewDraft(note=""))
    controller.accept_both()

    controller.set_filters(ReviewFilters(status=ReviewFilter.UNREVIEWED))

    state = controller.state
    assert state.snapshot is not None and state.snapshot.filtered_count == 2
    assert snapshot_of(state).row_number == 2  # first of the filtered queue
    assert state.filters.status is ReviewFilter.UNREVIEWED


def test_export_writes_the_reviewed_csv_only_when_asked(env: Env) -> None:
    controller = opened(env)
    controller.set_draft(judge_both("=SUM(1)"))
    controller.save()
    target = env.root / "out" / "reviewed.csv"
    assert env.written == {}  # reviewing never exports by itself

    assert controller.export(target, include_native=False) is True

    text = env.written[target]
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["review_status"] == "reviewed"
    assert rows[0]["review_note"] == "'=SUM(1)"
    assert "emotion_native_" not in text.splitlines()[0]
    state = controller.state
    assert state.notice is not None and state.notice.code == "export_saved"
    assert str(env.root) not in state.notice.body and SENTINEL not in state.notice.body


def test_export_can_include_native_scores_when_chosen(env: Env) -> None:
    controller = opened(env)
    target = env.root / "native.csv"

    controller.export(target, include_native=True)

    assert "emotion_native_" in env.written[target].splitlines()[0]


def test_a_failed_write_gives_a_fixed_message_and_changes_nothing(env: Env) -> None:
    def failing(path: Path, text: str) -> None:
        raise PermissionError(f"{path} {SENTINEL}")

    controller = ReviewController(env.workflow(), ImmediateRunner(), write_file=failing)
    controller.open(env.project_id)
    controller.set_draft(judge_both("keep me"))
    controller.save()

    controller.export(env.root / "x.csv", include_native=False)

    notice = controller.state.notice
    assert notice is not None and notice.code == "export_failed"
    assert notice.kind is NoticeKind.ERROR
    assert SENTINEL not in notice.body and str(env.root) not in notice.body
    assert snapshot_of(controller.state).review.note == "keep me"  # project intact


def test_a_storage_failure_shows_a_fixed_message_without_content(env: Env) -> None:
    class Broken(ReviewWorkflow):
        def save(self, *args: Any, **kwargs: Any) -> Any:
            raise ProjectStorageError(
                code="storage_failed", message="The project could not be saved."
            )

    controller = env.controller(workflow=Broken(env.repository))
    controller.open(env.project_id)
    controller.set_draft(judge_both(f"note {SENTINEL}"))

    controller.save()

    notice = controller.state.notice
    assert notice is not None and notice.kind is NoticeKind.ERROR
    assert SENTINEL not in notice.title + notice.body
    assert controller.state.has_unsaved_changes  # the human's work is still there


def test_an_unexpected_error_is_generic_and_never_echoes_its_text(env: Env) -> None:
    class Boom(ReviewWorkflow):
        def accept_both(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"/secret/path {SENTINEL}")

    controller = env.controller(workflow=Boom(env.repository))
    controller.open(env.project_id)

    controller.accept_both()

    notice = controller.state.notice
    assert notice is not None and notice.code == "unexpected_error"
    assert SENTINEL not in notice.body and "secret" not in notice.body


def test_a_project_removed_elsewhere_closes_the_review_with_a_notice(
    env: Env,
) -> None:
    controller = opened(env)
    ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(env.root)),
        ScriptedGateway(),
        LIMITS,
    ).delete_project(env.project_id)
    controller.set_draft(ReviewDraft(note=""))

    controller.accept_both()

    state = controller.state
    assert state.is_open is False and state.snapshot is None
    assert state.notice is not None and state.notice.code == "project_not_found"


def test_closing_discards_the_draft_and_is_refused_while_busy(env: Env) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)
    controller.open(env.project_id)
    runner.run_next()
    controller.set_draft(ReviewDraft(note="x"))
    controller.save()  # queued, not yet run

    assert controller.close() is False
    runner.run_next()
    assert controller.close() is True

    assert controller.state.is_open is False
    assert controller.state.draft == ReviewDraft()


def test_the_review_is_durable_across_a_fresh_controller(env: Env) -> None:
    controller = opened(env)
    controller.set_draft(judge_both("durable"))
    controller.save()

    fresh = env.controller()
    fresh.open(env.project_id)

    review = snapshot_of(fresh.state).review
    assert review.is_reviewed and review.note == "durable"
    assert fresh.state.draft == ReviewDraft.from_review(review)


def test_discarding_restores_the_saved_review_and_keeps_the_position(
    env: Env,
) -> None:
    controller = opened(env)
    controller.next()
    controller.set_draft(judge_both("keep?"))
    assert controller.state.has_unsaved_changes

    controller.discard_changes()

    state = controller.state
    assert snapshot_of(state).row_number == 2  # still on the same record
    assert state.draft == ReviewDraft.from_review(snapshot_of(state).review)
    assert state.has_unsaved_changes is False
    assert state.is_open and state.notice is None
    assert not snapshot_of(state).review.is_reviewed  # nothing was saved


def test_discarding_is_refused_while_busy(env: Env) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)
    controller.open(env.project_id)
    runner.run_next()
    controller.set_draft(ReviewDraft(note="x"))
    controller.save()  # queued

    controller.discard_changes()

    assert controller.state.draft.note == "x"
    runner.run_next()
    assert snapshot_of(controller.state).review.note == "x"  # the save went through


def test_opening_at_a_row_starts_there(env: Env) -> None:
    controller = env.controller()

    assert controller.open(env.project_id, row=3)

    assert snapshot_of(controller.state).row_number == 3


def test_go_to_opens_a_queue_row_by_its_identity(env: Env) -> None:
    controller = opened(env)

    assert controller.go_to(3)

    assert snapshot_of(controller.state).row_number == 3
    assert not controller.go_to(99)  # not in the queue: refused, nothing changes
    assert snapshot_of(controller.state).row_number == 3


def test_go_to_respects_the_active_filter_and_refuses_a_hidden_row(env: Env) -> None:
    controller = opened(env)
    controller.accept_both()
    assert controller.set_filters(ReviewFilters(status=ReviewFilter.UNREVIEWED))

    assert not controller.go_to(1)  # row 1 is reviewed, so it is not in this queue
    assert controller.go_to(2)
    assert snapshot_of(controller.state).row_number == 2
