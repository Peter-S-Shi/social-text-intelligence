"""Pure review view models: AI record and human judgment stay separate (no Qt)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from persistence.workflow_samples import ScriptedGateway, csv_text

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    ReviewDraft,
    ReviewFilters,
    ReviewJudgment,
    ReviewSnapshot,
    ReviewWorkflow,
)
from social_text_intelligence.desktop.review import ReviewActivity, ReviewState
from social_text_intelligence.desktop.review_view import (
    AGREEMENT_NOTE,
    build_review_view,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
CORRECT, ACCEPT, UNCERTAIN = (
    ReviewJudgment.CORRECT,
    ReviewJudgment.ACCEPT,
    ReviewJudgment.UNCERTAIN,
)


def snapshot_of(root: Path, rows: int = 4) -> tuple[ReviewWorkflow, str]:
    repository = SqliteProjectRepository(AppDataLocations(root))
    flow = ProjectWorkflow(repository, ScriptedGateway(), LIMITS)
    project_id = flow.import_csv(csv_text(rows), name="P").summary.project_id
    flow.analyze(project_id)
    return ReviewWorkflow(repository), project_id


def state_for(
    snapshot: ReviewSnapshot,
    *,
    draft: ReviewDraft | None = None,
    activity: ReviewActivity = ReviewActivity.IDLE,
) -> ReviewState:
    base = ReviewState(
        project_id=snapshot.project_id, snapshot=snapshot, activity=activity
    )
    return base if draft is None else replace(base, draft=draft)


def test_the_ai_record_and_the_human_judgment_are_separate_labelled_blocks(
    tmp_path: Path,
) -> None:
    flow, project_id = snapshot_of(tmp_path)
    snapshot = flow.open_review(project_id)
    assert snapshot.record is not None

    view = build_review_view(state_for(snapshot))

    assert view is not None and view.record is not None
    ai = view.record.ai
    human = view.record.human
    assert ai.heading != human.heading
    assert "not editable" in ai.heading.lower()
    assert "your judgment" in human.heading.lower()
    report = snapshot.record.report
    assert ai.sentiment_line.startswith(report.sentiment.label.value.capitalize())
    assert f"{report.sentiment.confidence * 100:.1f}%" in ai.sentiment_line
    assert any(report.sentiment.provider.model_name in line for line in ai.provenance)
    assert human.status_word == "Unreviewed"
    assert human.status_icon != ""
    assert view.record.text == snapshot.record.report.record.text


def test_status_is_a_word_and_an_icon_for_unreviewed_partial_and_reviewed(
    tmp_path: Path,
) -> None:
    flow, project_id = snapshot_of(tmp_path)
    snapshot = flow.open_review(project_id)
    assert snapshot.record is not None
    saved = flow.save(
        project_id,
        1,
        ReviewDraft(sentiment_judgment=ACCEPT),
        expected=snapshot.record.review,
    )
    done = flow.accept_both(
        project_id,
        1,
        "",
        expected=saved.record.review,  # type: ignore[union-attr]
    )

    partial = build_review_view(state_for(saved))
    full = build_review_view(state_for(done))

    assert partial is not None and partial.record is not None
    assert partial.record.human.status_word == "Partly reviewed"
    assert full is not None and full.record is not None
    assert full.record.human.status_word == "Reviewed"
    words = {
        partial.record.human.status_icon,
        full.record.human.status_icon,
    }
    assert len(words) == 2  # distinct icons, never colour alone


def test_correction_fields_appear_only_for_a_correct_judgment(tmp_path: Path) -> None:
    flow, project_id = snapshot_of(tmp_path)
    snapshot = flow.open_review(project_id)

    plain = build_review_view(state_for(snapshot))
    correcting = build_review_view(
        state_for(
            snapshot,
            draft=ReviewDraft(sentiment_judgment=CORRECT, emotion_judgment=CORRECT),
        )
    )

    assert plain is not None and plain.record is not None
    assert not plain.record.human.sentiment_label_visible
    assert not plain.record.human.emotion_labels_visible
    assert correcting is not None and correcting.record is not None
    assert correcting.record.human.sentiment_label_visible
    assert correcting.record.human.emotion_labels_visible


def test_progress_uses_honest_wording(tmp_path: Path) -> None:
    flow, project_id = snapshot_of(tmp_path, rows=4)
    snapshot = flow.open_review(project_id)
    assert snapshot.record is not None
    done = flow.accept_both(project_id, 1, "", expected=snapshot.record.review)

    view = build_review_view(state_for(done))

    assert view is not None
    assert "1 of 4 reviewed" in view.progress_line
    assert "3 unreviewed" in view.progress_line
    assert "Record 1 of 4" in view.position_line
    # agreement itself lives on its own page (see test_agreement_view)
    assert "not accuracy" in AGREEMENT_NOTE.lower()
    assert not hasattr(view, "agreement_lines")


def test_buttons_follow_the_queue_and_the_busy_state(tmp_path: Path) -> None:
    flow, project_id = snapshot_of(tmp_path)
    snapshot = flow.open_review(project_id)

    idle = build_review_view(state_for(snapshot))
    busy = build_review_view(state_for(snapshot, activity=ReviewActivity.SAVING))

    assert idle is not None
    assert not idle.previous_enabled and idle.next_enabled
    assert idle.next_unreviewed_enabled
    assert idle.accept_both_enabled
    assert not idle.save_enabled  # nothing to save yet
    assert busy is not None
    assert not (busy.next_enabled or busy.accept_both_enabled or busy.controls_enabled)


def test_save_needs_a_change_and_the_note_counter_warns_before_the_limit(
    tmp_path: Path,
) -> None:
    flow, project_id = snapshot_of(tmp_path)
    snapshot = flow.open_review(project_id)

    edited = build_review_view(state_for(snapshot, draft=ReviewDraft(note="x" * 1990)))
    over = build_review_view(state_for(snapshot, draft=ReviewDraft(note="x" * 2001)))

    assert edited is not None and edited.save_enabled and edited.unsaved
    assert "10 characters left" in edited.record.human.note_counter  # type: ignore[union-attr]
    assert over is not None and over.record is not None
    assert "over the 2000-character limit" in over.record.human.note_counter


def test_failed_rows_are_explained_not_listed_as_reviewable(tmp_path: Path) -> None:
    from social_text_intelligence.contracts.errors import ProviderError

    def fail_second(call: int) -> None:
        if call == 2:
            raise ProviderError(provider="p", code="boom", message="row failed")

    repository = SqliteProjectRepository(AppDataLocations(tmp_path))
    flow = ProjectWorkflow(repository, ScriptedGateway(fail_second), LIMITS)
    project_id = flow.import_csv(csv_text(3), name="P").summary.project_id
    flow.analyze(project_id)

    view = build_review_view(
        state_for(ReviewWorkflow(repository).open_review(project_id))
    )

    assert view is not None
    assert "1 row could not be analysed" in view.failed_line
    assert "Record 1 of 2" in view.position_line


@pytest.mark.parametrize("status", ["all", "unreviewed"])
def test_filter_choices_expose_the_existing_review_filters(
    tmp_path: Path, status: str
) -> None:
    flow, project_id = snapshot_of(tmp_path)
    view = build_review_view(state_for(flow.open_review(project_id, ReviewFilters())))

    assert view is not None
    values = [value for _, value in view.status_filter_choices]
    assert status in values
    assert values == ["all", "unreviewed", "reviewed", "corrected", "uncertain"]


def test_the_view_carries_the_queue_the_tabs_and_the_progress_meter(
    tmp_path: Path,
) -> None:
    flow, project_id = snapshot_of(tmp_path)
    second = flow.open_review(project_id, row=2).record
    assert second is not None
    flow.accept_both(project_id, 2, "", expected=second.review)

    view = build_review_view(state_for(flow.open_review(project_id, ReviewFilters())))

    assert view is not None
    tabs = {value: count for _, value, count in view.status_tabs}
    assert tabs["all"] == len(view.queue)
    assert tabs["reviewed"] == 1 and tabs["unreviewed"] == len(view.queue) - 1
    assert view.selected_row == 1
    assert [item.reviewed for item in view.queue][:2] == [False, True]
    assert view.queue_heading == "Queue · All"
    assert view.queue_position == f"1 / {len(view.queue)}"
    assert 0.0 < view.progress_fraction < 1.0
    assert "1 / " in view.progress_text and "to go" in view.progress_text
    assert "reviewed" in view.queue[1].accessible_name
