"""Human-review contracts and rules for successful batch predictions."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from ..contracts import EmotionLabel, SentimentLabel
from ..contracts.errors import ValidationError
from .batch import BatchOutcome, BatchResult

MAX_REVIEW_NOTE_LENGTH = 2_000


class ReviewJudgment(StrEnum):
    ACCEPT = "accept"
    CORRECT = "correct"
    UNCERTAIN = "uncertain"


class ReviewFilter(StrEnum):
    ALL = "all"
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    CORRECTED = "corrected"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class HumanReview:
    """Human labels stored separately from the immutable AI report."""

    record_id: str
    sentiment_judgment: ReviewJudgment | None = None
    human_sentiment: SentimentLabel | None = None
    emotion_judgment: ReviewJudgment | None = None
    human_dominant_emotion: EmotionLabel | None = None
    human_secondary_emotions: tuple[EmotionLabel, ...] = ()
    note: str | None = None
    reviewed_at: datetime | None = None

    @property
    def is_reviewed(self) -> bool:
        return (
            self.sentiment_judgment is not None
            and self.emotion_judgment is not None
        )

    @property
    def is_corrected(self) -> bool:
        return ReviewJudgment.CORRECT in (
            self.sentiment_judgment,
            self.emotion_judgment,
        )

    @property
    def is_uncertain(self) -> bool:
        return ReviewJudgment.UNCERTAIN in (
            self.sentiment_judgment,
            self.emotion_judgment,
        )


@dataclass(frozen=True, slots=True)
class ReviewState:
    reviews: tuple[HumanReview, ...]

    def __post_init__(self) -> None:
        identities = tuple(review.record_id for review in self.reviews)
        if len(identities) != len(set(identities)):
            raise ValueError("Review record IDs must be unique.")

    def for_record(self, record_id: str) -> HumanReview | None:
        return next(
            (review for review in self.reviews if review.record_id == record_id),
            None,
        )


@dataclass(frozen=True, slots=True)
class ReviewCase:
    outcome: BatchOutcome
    review: HumanReview


@dataclass(frozen=True, slots=True)
class ReviewNavigation:
    previous_row: int | None
    next_row: int | None
    next_unreviewed_row: int | None


def create_review_state(result: BatchResult) -> ReviewState:
    return ReviewState(
        reviews=tuple(
            HumanReview(record_id=outcome.prepared.identity)
            for outcome in result.outcomes
            if outcome.report is not None
        )
    )


def _parse_judgment(value: str | None, *, field: str) -> ReviewJudgment | None:
    if value is None or not value.strip():
        return None
    try:
        return ReviewJudgment(value.strip())
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_judgment",
            message=f"{field} must be accept, correct, or uncertain.",
        ) from error


def _parse_sentiment(value: str | None) -> SentimentLabel | None:
    if value is None or not value.strip():
        return None
    try:
        return SentimentLabel(value.strip())
    except ValueError as error:
        raise ValidationError(
            field="human_sentiment",
            code="invalid_label",
            message="Select a valid compact sentiment label.",
        ) from error


def _parse_emotion(value: str | None, *, field: str) -> EmotionLabel | None:
    if value is None or not value.strip():
        return None
    try:
        return EmotionLabel(value.strip())
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_label",
            message="Select only labels from the compact emotion taxonomy.",
        ) from error


def _clean_note(value: str) -> str | None:
    normalized = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    ).strip()
    if not normalized:
        return None
    if len(normalized) > MAX_REVIEW_NOTE_LENGTH:
        raise ValidationError(
            field="review_note",
            code="too_long",
            message=(
                f"Review note exceeds {MAX_REVIEW_NOTE_LENGTH} characters."
            ),
        )
    return normalized


def _sentiment_fields(
    judgment: ReviewJudgment | None,
    selected: SentimentLabel | None,
    outcome: BatchOutcome,
) -> tuple[ReviewJudgment | None, SentimentLabel | None]:
    assert outcome.report is not None
    if judgment is ReviewJudgment.ACCEPT:
        return judgment, outcome.report.sentiment.label
    if judgment is ReviewJudgment.CORRECT:
        if selected is None:
            raise ValidationError(
                field="human_sentiment",
                code="required",
                message="Select a human sentiment when correcting the AI label.",
            )
        return judgment, selected
    return judgment, None


def _emotion_fields(
    judgment: ReviewJudgment | None,
    dominant: EmotionLabel | None,
    selected_secondary: Sequence[str],
    outcome: BatchOutcome,
) -> tuple[
    ReviewJudgment | None,
    EmotionLabel | None,
    tuple[EmotionLabel, ...],
]:
    assert outcome.report is not None
    if judgment is ReviewJudgment.ACCEPT:
        return (
            judgment,
            outcome.report.emotion.dominant_emotion,
            outcome.report.emotion.secondary_emotions,
        )
    if judgment is not ReviewJudgment.CORRECT:
        return judgment, None, ()
    if dominant is None:
        raise ValidationError(
            field="human_dominant_emotion",
            code="required",
            message="Select one dominant emotion when correcting the AI labels.",
        )
    parsed_secondary = tuple(
        _parse_emotion(value, field="human_secondary_emotions")
        for value in selected_secondary
    )
    secondary = tuple(label for label in EmotionLabel if label in parsed_secondary)
    if len(parsed_secondary) != len(set(parsed_secondary)):
        raise ValidationError(
            field="human_secondary_emotions",
            code="duplicate_label",
            message="Secondary emotion labels must be unique.",
        )
    if dominant in secondary:
        raise ValidationError(
            field="human_secondary_emotions",
            code="dominant_repeated",
            message="The dominant emotion cannot also be secondary.",
        )
    selected = {dominant, *secondary}
    if EmotionLabel.NEUTRAL in selected and len(selected) > 1:
        raise ValidationError(
            field="human_secondary_emotions",
            code="neutral_not_exclusive",
            message="Neutral cannot coexist with a non-neutral emotion.",
        )
    return judgment, dominant, secondary


def update_review(
    result: BatchResult,
    state: ReviewState,
    *,
    record_id: str,
    sentiment_judgment: str | None,
    human_sentiment: str | None,
    emotion_judgment: str | None,
    human_dominant_emotion: str | None,
    human_secondary_emotions: Sequence[str],
    note: str,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ReviewState:
    """Validate and immutably replace only one record's human-review fields."""

    outcome = next(
        (
            item
            for item in result.outcomes
            if item.report is not None and item.prepared.identity == record_id
        ),
        None,
    )
    current = state.for_record(record_id)
    if outcome is None or current is None:
        raise ValidationError(
            field="record_id",
            code="not_reviewable",
            message="Only successfully analyzed batch rows can be reviewed.",
        )

    parsed_sentiment_judgment = _parse_judgment(
        sentiment_judgment, field="sentiment_judgment"
    )
    parsed_emotion_judgment = _parse_judgment(
        emotion_judgment, field="emotion_judgment"
    )
    parsed_sentiment = _parse_sentiment(human_sentiment)
    parsed_dominant = _parse_emotion(
        human_dominant_emotion, field="human_dominant_emotion"
    )
    saved_sentiment_judgment, saved_sentiment = _sentiment_fields(
        parsed_sentiment_judgment, parsed_sentiment, outcome
    )
    (
        saved_emotion_judgment,
        saved_dominant,
        saved_secondary,
    ) = _emotion_fields(
        parsed_emotion_judgment,
        parsed_dominant,
        human_secondary_emotions,
        outcome,
    )
    is_reviewed = (
        saved_sentiment_judgment is not None
        and saved_emotion_judgment is not None
    )
    timestamp = now() if is_reviewed else None
    if timestamp is not None and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    replacement = HumanReview(
        record_id=record_id,
        sentiment_judgment=saved_sentiment_judgment,
        human_sentiment=saved_sentiment,
        emotion_judgment=saved_emotion_judgment,
        human_dominant_emotion=saved_dominant,
        human_secondary_emotions=saved_secondary,
        note=_clean_note(note),
        reviewed_at=timestamp,
    )
    return ReviewState(
        reviews=tuple(
            replacement if review.record_id == record_id else review
            for review in state.reviews
        )
    )


def accept_both(
    result: BatchResult,
    state: ReviewState,
    *,
    record_id: str,
    note: str,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ReviewState:
    return update_review(
        result,
        state,
        record_id=record_id,
        sentiment_judgment=ReviewJudgment.ACCEPT,
        human_sentiment=None,
        emotion_judgment=ReviewJudgment.ACCEPT,
        human_dominant_emotion=None,
        human_secondary_emotions=(),
        note=note,
        now=now,
    )


def review_cases(result: BatchResult, state: ReviewState) -> tuple[ReviewCase, ...]:
    cases: list[ReviewCase] = []
    for outcome in result.outcomes:
        if outcome.report is None:
            continue
        review = state.for_record(outcome.prepared.identity)
        if review is None:
            raise ValueError("Review state does not match the batch result.")
        cases.append(ReviewCase(outcome=outcome, review=review))
    return tuple(cases)


def filter_review_cases(
    result: BatchResult,
    state: ReviewState,
    *,
    review_filter: str = ReviewFilter.ALL,
    sentiment_filter: str = "all",
    emotion_filter: str = "all",
) -> tuple[ReviewCase, ...]:
    try:
        selected_review_filter = ReviewFilter(review_filter)
    except ValueError:
        selected_review_filter = ReviewFilter.ALL

    def matches(case: ReviewCase) -> bool:
        report = case.outcome.report
        assert report is not None
        review = case.review
        status_matches = {
            ReviewFilter.ALL: True,
            ReviewFilter.UNREVIEWED: not review.is_reviewed,
            ReviewFilter.REVIEWED: review.is_reviewed,
            ReviewFilter.CORRECTED: review.is_corrected,
            ReviewFilter.UNCERTAIN: review.is_uncertain,
        }[selected_review_filter]
        return (
            status_matches
            and (
                sentiment_filter == "all"
                or report.sentiment.label.value == sentiment_filter
            )
            and (
                emotion_filter == "all"
                or report.emotion.dominant_emotion.value == emotion_filter
            )
        )

    return tuple(case for case in review_cases(result, state) if matches(case))


def review_navigation(
    result: BatchResult,
    state: ReviewState,
    *,
    current_record_id: str,
    filtered_cases: Sequence[ReviewCase],
) -> ReviewNavigation:
    filtered_rows = tuple(case.outcome.prepared.row_number for case in filtered_cases)
    current_row = next(
        (
            case.outcome.prepared.row_number
            for case in review_cases(result, state)
            if case.review.record_id == current_record_id
        ),
        None,
    )
    if current_row is None:
        raise ValidationError(
            field="record_id",
            code="not_reviewable",
            message="The selected record is not reviewable.",
        )
    try:
        index = filtered_rows.index(current_row)
    except ValueError:
        previous_row = filtered_rows[-1] if filtered_rows else None
        next_row = filtered_rows[0] if filtered_rows else None
    else:
        previous_row = filtered_rows[index - 1] if index > 0 else None
        next_row = filtered_rows[index + 1] if index + 1 < len(filtered_rows) else None

    all_cases = review_cases(result, state)
    current_index = next(
        index
        for index, case in enumerate(all_cases)
        if case.review.record_id == current_record_id
    )
    following = (*all_cases[current_index + 1 :], *all_cases[: current_index + 1])
    next_unreviewed = next(
        (
            case.outcome.prepared.row_number
            for case in following
            if not case.review.is_reviewed
            and case.review.record_id != current_record_id
        ),
        None,
    )
    return ReviewNavigation(previous_row, next_row, next_unreviewed)
