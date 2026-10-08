"""The review workflow over a real SQLite project (synthetic data)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectNotFoundError,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    Advance,
    ReviewConflictError,
    ReviewDraft,
    ReviewFilters,
    ReviewSnapshot,
    ReviewUnavailableError,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.contracts.errors import ProviderError, ValidationError
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.review import (
    MAX_REVIEW_NOTE_LENGTH,
    HumanReview,
    ReviewFilter,
    ReviewJudgment,
)

from .workflow_samples import SENTINEL, ScriptedGateway, csv_text

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
ACCEPT, CORRECT, UNCERTAIN = (
    ReviewJudgment.ACCEPT,
    ReviewJudgment.CORRECT,
    ReviewJudgment.UNCERTAIN,
)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def reviews(root: Path) -> ReviewWorkflow:
    """A fresh workflow, as after an application restart."""

    return ReviewWorkflow(repository(root))


def analysed(root: Path, rows: int = 3, gateway: ScriptedGateway | None = None) -> str:
    flow = ProjectWorkflow(repository(root), gateway or ScriptedGateway(), LIMITS)
    project_id = flow.import_csv(csv_text(rows), name="P").summary.project_id
    flow.analyze(project_id)
    return project_id


def current(snapshot: ReviewSnapshot) -> HumanReview:
    assert snapshot.record is not None
    return snapshot.record.review


def correct_both(
    sentiment: SentimentLabel = SentimentLabel.NEGATIVE,
    dominant: EmotionLabel = EmotionLabel.ANGER,
    secondary: tuple[EmotionLabel, ...] = (),
    note: str = "",
) -> ReviewDraft:
    return ReviewDraft(
        sentiment_judgment=CORRECT,
        human_sentiment=sentiment,
        emotion_judgment=CORRECT,
        human_dominant_emotion=dominant,
        human_secondary_emotions=secondary,
        note=note,
    )


def test_opening_shows_the_ai_record_apart_from_an_empty_human_review(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, rows=3)

    snapshot = reviews(tmp_path).open_review(project_id)

    assert snapshot.record is not None and snapshot.record.row_number == 1
    assert SENTINEL in snapshot.record.report.record.text
    assert snapshot.record.report.sentiment.label in SentimentLabel
    assert snapshot.record.review.sentiment_judgment is None
    assert snapshot.record.review.is_reviewed is False
    assert (snapshot.position, snapshot.queue_total) == (1, 3)
    assert snapshot.summary.progress.reviewable_records == 3
    assert snapshot.summary.progress.reviewed == 0
    assert (snapshot.previous_row, snapshot.next_row) == (None, 2)
    assert snapshot.next_unreviewed_row == 2


def test_only_an_analysed_project_can_be_reviewed(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    ready = flow.import_csv(csv_text(2), name="P").summary.project_id

    with pytest.raises(ReviewUnavailableError):
        reviews(tmp_path).open_review(ready)
    with pytest.raises(ProjectNotFoundError):
        reviews(tmp_path).open_review("0" * 32)


def test_accept_both_is_a_complete_review_that_survives_a_restart(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    first = reviews(tmp_path).open_review(project_id)
    assert first.record is not None

    saved = reviews(tmp_path).accept_both(
        project_id, 1, "looks right", expected=current(first)
    )

    assert saved.record is not None and saved.record.row_number == 1  # stays put
    assert saved.record.review.is_reviewed
    assert saved.record.review.sentiment_judgment is ACCEPT
    assert saved.record.review.emotion_judgment is ACCEPT
    assert saved.record.review.human_sentiment == first.record.report.sentiment.label
    assert saved.record.review.note == "looks right"
    again = reviews(tmp_path).open_review(project_id, row=1)  # a fresh app instance
    assert again.record is not None and again.record.review == saved.record.review
    assert again.summary.progress.reviewed == 1


def test_sentiment_and_emotion_are_judged_separately(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = reviews(tmp_path)
    seen = current(flow.open_review(project_id))

    partial = flow.save(
        project_id, 1, ReviewDraft(sentiment_judgment=ACCEPT), expected=seen
    )
    assert partial.record is not None
    assert partial.record.review.sentiment_judgment is ACCEPT
    assert partial.record.review.emotion_judgment is None
    assert partial.record.review.is_reviewed is False  # one dimension is not enough
    assert partial.summary.progress.reviewed == 0

    done = flow.save(
        project_id,
        1,
        ReviewDraft(
            sentiment_judgment=ACCEPT,
            emotion_judgment=CORRECT,
            human_dominant_emotion=EmotionLabel.JOY,
            human_secondary_emotions=(EmotionLabel.GRATITUDE, EmotionLabel.AMUSEMENT),
        ),
        expected=current(partial),
    )
    assert done.record is not None and done.record.review.is_reviewed
    assert done.record.review.is_corrected
    assert done.record.review.human_dominant_emotion is EmotionLabel.JOY
    assert done.record.review.human_secondary_emotions == (
        EmotionLabel.AMUSEMENT,  # stored in taxonomy order
        EmotionLabel.GRATITUDE,
    )

    unsure = flow.save(
        project_id,
        2,
        ReviewDraft(sentiment_judgment=UNCERTAIN, emotion_judgment=UNCERTAIN),
        expected=current(flow.open_review(project_id, row=2)),
    )
    assert unsure.record is not None and unsure.record.review.is_uncertain
    assert unsure.record.review.human_sentiment is None
    assert unsure.summary.progress.uncertain == 1


@pytest.mark.parametrize(
    ("draft", "field", "code"),
    [
        (
            ReviewDraft(sentiment_judgment=CORRECT, emotion_judgment=ACCEPT),
            "human_sentiment",
            "required",
        ),
        (
            ReviewDraft(sentiment_judgment=ACCEPT, emotion_judgment=CORRECT),
            "human_dominant_emotion",
            "required",
        ),
        (
            correct_both(dominant=EmotionLabel.JOY, secondary=(EmotionLabel.JOY,)),
            "human_secondary_emotions",
            "dominant_repeated",
        ),
        (
            correct_both(dominant=EmotionLabel.NEUTRAL, secondary=(EmotionLabel.FEAR,)),
            "human_secondary_emotions",
            "neutral_not_exclusive",
        ),
        (
            correct_both(
                dominant=EmotionLabel.FEAR,
                secondary=(EmotionLabel.JOY, EmotionLabel.JOY),
            ),
            "human_secondary_emotions",
            "duplicate_label",
        ),
        (
            correct_both(note="x" * (MAX_REVIEW_NOTE_LENGTH + 1)),
            "review_note",
            "too_long",
        ),
    ],
)
def test_an_invalid_judgment_is_refused_and_nothing_is_stored(
    tmp_path: Path, draft: ReviewDraft, field: str, code: str
) -> None:
    project_id = analysed(tmp_path)
    flow = reviews(tmp_path)
    seen = current(flow.open_review(project_id))

    with pytest.raises(ValidationError) as failure:
        flow.save(project_id, 1, draft, expected=seen)

    assert (failure.value.field, failure.value.code) == (field, code)
    assert current(reviews(tmp_path).open_review(project_id)) == seen


def test_a_note_at_the_limit_is_accepted(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = reviews(tmp_path)
    seen = current(flow.open_review(project_id))

    saved = flow.save(
        project_id,
        1,
        correct_both(note="x" * MAX_REVIEW_NOTE_LENGTH),
        expected=seen,
    )

    assert current(saved).note == "x" * MAX_REVIEW_NOTE_LENGTH


def test_a_second_edit_replaces_the_human_review_and_never_the_ai_record(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = reviews(tmp_path)
    first = flow.open_review(project_id)
    assert first.record is not None
    one = flow.save(project_id, 1, correct_both(note="first"), expected=current(first))
    assert current(one).note == "first" and current(one).is_corrected

    two = flow.accept_both(project_id, 1, "second", expected=current(one))

    assert two.record is not None
    assert current(two).sentiment_judgment is ACCEPT  # replaced, not merged
    assert current(two).human_secondary_emotions == (
        first.record.report.emotion.secondary_emotions
    )
    assert current(two).note == "second"
    assert two.record.report == first.record.report  # the AI record is untouched
    reopened = reviews(tmp_path).open_review(project_id, row=1)
    assert reopened.record is not None
    assert reopened.record.report == first.record.report


def test_advancing_follows_the_filtered_queue(tmp_path: Path) -> None:
    project_id = analysed(tmp_path, rows=4)
    flow = reviews(tmp_path)
    unreviewed = ReviewFilters(status=ReviewFilter.UNREVIEWED)
    one = flow.open_review(project_id, unreviewed)
    assert one.filtered_count == 4

    after = flow.accept_both(
        project_id,
        1,
        "",
        expected=current(one),
        filters=unreviewed,
        advance=Advance.NEXT,
    )

    assert after.record is not None and after.record.row_number == 2
    assert after.filtered_count == 3  # the saved row left the "unreviewed" queue
    assert after.summary.progress.reviewed == 1


def test_save_and_next_under_a_filter_continues_from_the_current_position(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, rows=4)
    flow = reviews(tmp_path)
    unreviewed = ReviewFilters(status=ReviewFilter.UNREVIEWED)

    after = flow.accept_both(
        project_id,
        3,
        "",
        expected=current(flow.open_review(project_id, unreviewed, row=3)),
        filters=unreviewed,
        advance=Advance.NEXT,
    )

    assert after.record is not None and after.record.row_number == 4  # not row 1


def test_staying_on_a_saved_row_keeps_its_place_in_the_filtered_queue(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, rows=4)
    flow = reviews(tmp_path)
    unreviewed = ReviewFilters(status=ReviewFilter.UNREVIEWED)

    stayed = flow.accept_both(
        project_id,
        2,
        "",
        expected=current(flow.open_review(project_id, unreviewed, row=2)),
        filters=unreviewed,
    )

    assert stayed.record is not None and stayed.record.row_number == 2
    assert (stayed.previous_row, stayed.next_row) == (1, 3)  # around row 2, not wrapped
    assert stayed.filtered_count == 3  # the saved row no longer matches the filter


def test_next_unreviewed_wraps_and_skips_reviewed_rows(tmp_path: Path) -> None:
    project_id = analysed(tmp_path, rows=3)
    flow = reviews(tmp_path)
    for row in (2, 3):
        flow.accept_both(
            project_id, row, "", expected=current(flow.open_review(project_id, row=row))
        )

    from_last = flow.open_review(project_id, row=3)

    assert from_last.next_unreviewed_row == 1  # wraps around to the only open one
    assert flow.open_review(project_id, row=1).next_unreviewed_row is None


def test_filters_narrow_the_queue_and_fall_back_when_empty(tmp_path: Path) -> None:
    project_id = analysed(tmp_path, rows=3)
    flow = reviews(tmp_path)
    flow.save(
        project_id,
        2,
        correct_both(),
        expected=current(flow.open_review(project_id, row=2)),
    )

    corrected = flow.open_review(
        project_id, ReviewFilters(status=ReviewFilter.CORRECTED)
    )
    none_match = flow.open_review(
        project_id, ReviewFilters(status=ReviewFilter.UNCERTAIN)
    )

    assert corrected.record is not None and corrected.record.row_number == 2
    assert corrected.filtered_count == 1
    assert none_match.filtered_count == 0
    assert none_match.record is not None  # an empty filter still shows the queue


def test_a_stale_form_is_a_conflict_that_keeps_the_newer_review(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    mine = reviews(tmp_path)
    old = current(mine.open_review(project_id))
    kept = reviews(tmp_path).save(project_id, 1, correct_both(), expected=old)

    with pytest.raises(ReviewConflictError) as failure:
        mine.accept_both(project_id, 1, "", expected=old)

    assert SENTINEL not in failure.value.message
    assert current(reviews(tmp_path).open_review(project_id)) == current(kept)


def test_failed_rows_are_not_reviewable_but_stay_in_the_export(
    tmp_path: Path,
) -> None:
    def fail_second(call: int) -> None:
        if call == 2:
            raise ProviderError(provider="p", code="boom", message="row failed")

    project_id = analysed(tmp_path, rows=3, gateway=ScriptedGateway(fail_second))
    flow = reviews(tmp_path)

    snapshot = flow.open_review(project_id)
    assert snapshot.summary.progress.total_records == 3
    assert snapshot.summary.progress.reviewable_records == 2
    assert snapshot.queue_total == 2
    assert snapshot.next_row == 3  # the failed row 2 is skipped
    with pytest.raises(ReviewUnavailableError):
        flow.open_review(project_id, row=2)
    with pytest.raises(ReviewUnavailableError):
        flow.accept_both(project_id, 2, "", expected=current(snapshot))

    rows = list(csv.DictReader(io.StringIO(flow.export_csv(project_id))))
    assert [r["status"] for r in rows] == ["ok", "error", "ok"]
    assert rows[1]["review_status"] == "" and rows[1]["error_code"] == "boom"


def test_the_reviewed_export_keeps_the_existing_schema_and_protects_formulas(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = reviews(tmp_path)
    seen = flow.open_review(project_id)
    flow.save(project_id, 1, correct_both(note="=HYPERLINK(1)"), expected=current(seen))

    plain = flow.export_csv(project_id)
    native = flow.export_csv(project_id, include_native=True)

    rows = list(csv.DictReader(io.StringIO(plain)))
    assert rows[0]["review_status"] == "reviewed"
    assert rows[0]["review_note"] == "'=HYPERLINK(1)"  # spreadsheet-safe
    assert rows[1]["review_status"] == "unreviewed"
    assert seen.record is not None
    assert rows[0]["sentiment_label"] == seen.record.report.sentiment.label
    assert "emotion_native_" not in plain.splitlines()[0]
    assert "emotion_native_" in native.splitlines()[0]
    assert flow.export_csv(project_id) == plain  # an export changes nothing


def test_the_agreement_summary_is_available_without_opening_a_record(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, rows=3)
    flow = reviews(tmp_path)
    first = flow.open_review(project_id)
    flow.save(project_id, 1, correct_both(), expected=current(first))

    summary = reviews(tmp_path).agreement(project_id)

    assert summary.progress.reviewable_records == 3
    assert summary.progress.reviewed == 1
    assert summary.sentiment.definitive_count == 1
    assert summary == flow.open_review(project_id).summary  # the same summary


def test_agreement_needs_an_analysed_project(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    ready = flow.import_csv(csv_text(2), name="P").summary.project_id

    with pytest.raises(ReviewUnavailableError):
        reviews(tmp_path).agreement(ready)
    with pytest.raises(ProjectNotFoundError):
        reviews(tmp_path).agreement("no-such-project")
