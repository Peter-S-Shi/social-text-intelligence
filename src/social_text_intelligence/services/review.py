"""Human-review contracts and rules for successful batch predictions."""

from __future__ import annotations

import csv
import io
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from ..contracts import EmotionLabel, SentimentLabel
from ..contracts.errors import ValidationError
from .batch import (
    BatchOutcome,
    BatchResult,
    export_batch_csv,
    safe_spreadsheet_text,
)

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


@dataclass(frozen=True, slots=True)
class ReviewProgress:
    total_records: int
    reviewable_records: int
    reviewed: int
    unreviewed: int
    corrected: int
    uncertain: int


@dataclass(frozen=True, slots=True)
class ConfusionRow:
    ai_label: SentimentLabel
    human_counts: tuple[tuple[SentimentLabel, int], ...]


@dataclass(frozen=True, slots=True)
class SentimentReviewSummary:
    definitive_count: int
    agreement_count: int
    corrected_count: int
    correction_distribution: tuple[tuple[SentimentLabel, int], ...]
    confusion: tuple[ConfusionRow, ...]

    @property
    def agreement_rate(self) -> float:
        return (
            self.agreement_count / self.definitive_count
            if self.definitive_count
            else 0.0
        )


@dataclass(frozen=True, slots=True)
class EmotionLabelComparison:
    label: EmotionLabel
    ai_only: int
    human_only: int
    shared: int


@dataclass(frozen=True, slots=True)
class EmotionReviewSummary:
    definitive_count: int
    dominant_agreement_count: int
    set_agreement_count: int
    label_comparisons: tuple[EmotionLabelComparison, ...]
    most_added: tuple[tuple[EmotionLabel, int], ...]
    most_removed: tuple[tuple[EmotionLabel, int], ...]

    @property
    def dominant_agreement_rate(self) -> float:
        return (
            self.dominant_agreement_count / self.definitive_count
            if self.definitive_count
            else 0.0
        )

    @property
    def set_agreement_rate(self) -> float:
        return (
            self.set_agreement_count / self.definitive_count
            if self.definitive_count
            else 0.0
        )


@dataclass(frozen=True, slots=True)
class ConfidenceBand:
    label: str
    disagreement_count: int
    definitive_count: int

    @property
    def disagreement_rate(self) -> float:
        return (
            self.disagreement_count / self.definitive_count
            if self.definitive_count
            else 0.0
        )


@dataclass(frozen=True, slots=True)
class ConfidenceComparison:
    sentiment: tuple[ConfidenceBand, ...]
    dominant_emotion: tuple[ConfidenceBand, ...]


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    progress: ReviewProgress
    sentiment: SentimentReviewSummary
    emotion: EmotionReviewSummary
    confidence: ConfidenceComparison


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


def sentiment_agreement(case: ReviewCase) -> bool | None:
    report = case.outcome.report
    review = case.review
    assert report is not None
    if (
        not review.is_reviewed
        or review.sentiment_judgment is ReviewJudgment.UNCERTAIN
        or review.human_sentiment is None
    ):
        return None
    return review.human_sentiment is report.sentiment.label


def dominant_emotion_agreement(case: ReviewCase) -> bool | None:
    report = case.outcome.report
    review = case.review
    assert report is not None
    if (
        not review.is_reviewed
        or review.emotion_judgment is ReviewJudgment.UNCERTAIN
        or review.human_dominant_emotion is None
    ):
        return None
    return review.human_dominant_emotion is report.emotion.dominant_emotion


def emotion_set_agreement(case: ReviewCase) -> bool | None:
    report = case.outcome.report
    review = case.review
    assert report is not None
    if (
        not review.is_reviewed
        or review.emotion_judgment is ReviewJudgment.UNCERTAIN
        or review.human_dominant_emotion is None
    ):
        return None
    ai_labels = {
        report.emotion.dominant_emotion,
        *report.emotion.secondary_emotions,
    }
    human_labels = {
        review.human_dominant_emotion,
        *review.human_secondary_emotions,
    }
    return ai_labels == human_labels


_CONFIDENCE_BANDS = (
    ("0.00–0.49", 0.0, 0.5),
    ("0.50–0.74", 0.5, 0.75),
    ("0.75–0.89", 0.75, 0.9),
    ("0.90–1.00", 0.9, 1.01),
)
MIN_CONFIDENCE_COMPARISON_REVIEWS = 5


def _confidence_bands(
    values: Sequence[tuple[float, bool]],
) -> tuple[ConfidenceBand, ...]:
    if len(values) < MIN_CONFIDENCE_COMPARISON_REVIEWS:
        return ()
    return tuple(
        ConfidenceBand(
            label=label,
            disagreement_count=sum(
                disagreement
                for confidence, disagreement in values
                if lower <= confidence < upper
            ),
            definitive_count=sum(
                lower <= confidence < upper for confidence, _ in values
            ),
        )
        for label, lower, upper in _CONFIDENCE_BANDS
        if any(lower <= confidence < upper for confidence, _ in values)
    )


def summarize_reviews(result: BatchResult, state: ReviewState) -> ReviewSummary:
    cases = review_cases(result, state)
    reviewed = tuple(case for case in cases if case.review.is_reviewed)
    sentiment_cases = tuple(
        case for case in reviewed if sentiment_agreement(case) is not None
    )
    emotion_cases = tuple(
        case for case in reviewed if dominant_emotion_agreement(case) is not None
    )

    sentiment_corrections = Counter(
        case.review.human_sentiment
        for case in sentiment_cases
        if case.review.sentiment_judgment is ReviewJudgment.CORRECT
        and case.review.human_sentiment is not None
    )
    confusion = tuple(
        ConfusionRow(
            ai_label=ai_label,
            human_counts=tuple(
                (
                    human_label,
                    sum(
                        case.outcome.report is not None
                        and case.outcome.report.sentiment.label is ai_label
                        and case.review.human_sentiment is human_label
                        for case in sentiment_cases
                    ),
                )
                for human_label in SentimentLabel
            ),
        )
        for ai_label in SentimentLabel
    )

    ai_only = Counter[EmotionLabel]()
    human_only = Counter[EmotionLabel]()
    shared = Counter[EmotionLabel]()
    for case in emotion_cases:
        report = case.outcome.report
        review = case.review
        assert report is not None and review.human_dominant_emotion is not None
        ai_labels = {
            report.emotion.dominant_emotion,
            *report.emotion.secondary_emotions,
        }
        human_labels = {
            review.human_dominant_emotion,
            *review.human_secondary_emotions,
        }
        ai_only.update(ai_labels - human_labels)
        human_only.update(human_labels - ai_labels)
        shared.update(ai_labels & human_labels)

    sentiment_confidence = tuple(
        (
            case.outcome.report.sentiment.confidence,
            not bool(sentiment_agreement(case)),
        )
        for case in sentiment_cases
        if case.outcome.report is not None
    )
    emotion_confidence = tuple(
        (
            case.outcome.report.emotion.confidence,
            not bool(dominant_emotion_agreement(case)),
        )
        for case in emotion_cases
        if case.outcome.report is not None
    )
    return ReviewSummary(
        progress=ReviewProgress(
            total_records=len(result.outcomes),
            reviewable_records=len(cases),
            reviewed=len(reviewed),
            unreviewed=len(cases) - len(reviewed),
            corrected=sum(case.review.is_corrected for case in cases),
            uncertain=sum(case.review.is_uncertain for case in cases),
        ),
        sentiment=SentimentReviewSummary(
            definitive_count=len(sentiment_cases),
            agreement_count=sum(
                sentiment_agreement(case) is True for case in sentiment_cases
            ),
            corrected_count=sum(
                case.review.sentiment_judgment is ReviewJudgment.CORRECT
                for case in sentiment_cases
            ),
            correction_distribution=tuple(
                (label, sentiment_corrections[label]) for label in SentimentLabel
            ),
            confusion=confusion,
        ),
        emotion=EmotionReviewSummary(
            definitive_count=len(emotion_cases),
            dominant_agreement_count=sum(
                dominant_emotion_agreement(case) is True for case in emotion_cases
            ),
            set_agreement_count=sum(
                emotion_set_agreement(case) is True for case in emotion_cases
            ),
            label_comparisons=tuple(
                EmotionLabelComparison(
                    label=label,
                    ai_only=ai_only[label],
                    human_only=human_only[label],
                    shared=shared[label],
                )
                for label in EmotionLabel
            ),
            most_added=tuple(
                sorted(
                    ((label, human_only[label]) for label in EmotionLabel),
                    key=lambda item: (-item[1], item[0].value),
                )[:3]
            ),
            most_removed=tuple(
                sorted(
                    ((label, ai_only[label]) for label in EmotionLabel),
                    key=lambda item: (-item[1], item[0].value),
                )[:3]
            ),
        ),
        confidence=ConfidenceComparison(
            sentiment=_confidence_bands(sentiment_confidence),
            dominant_emotion=_confidence_bands(emotion_confidence),
        ),
    )


def _agreement_cell(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


REVIEW_EXPORT_FIELDS = (
    "review_status",
    "sentiment_judgment",
    "human_sentiment",
    "sentiment_agreement",
    "emotion_judgment",
    "human_dominant_emotion",
    "human_secondary_emotions",
    "dominant_emotion_agreement",
    "emotion_set_agreement",
    "review_note",
    "reviewed_at",
)


def export_reviewed_csv(
    result: BatchResult,
    state: ReviewState,
    *,
    include_native: bool,
) -> str:
    """Extend the normalized batch export without altering any AI fields."""

    base = csv.DictReader(
        io.StringIO(export_batch_csv(result, include_native=include_native))
    )
    base_fields = tuple(base.fieldnames or ())
    rows = list(base)
    if len(rows) != len(result.outcomes):
        raise ValueError("Normalized export rows do not match the batch result.")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(*base_fields, *REVIEW_EXPORT_FIELDS),
        lineterminator="\n",
    )
    writer.writeheader()
    for row, outcome in zip(rows, result.outcomes, strict=True):
        review = (
            state.for_record(outcome.prepared.identity)
            if outcome.report is not None
            else None
        )
        if outcome.report is not None and review is None:
            raise ValueError("Review state does not match the batch result.")
        if review is not None:
            case = ReviewCase(outcome=outcome, review=review)
            row.update(
                {
                    "review_status": (
                        "reviewed" if review.is_reviewed else "unreviewed"
                    ),
                    "sentiment_judgment": review.sentiment_judgment or "",
                    "human_sentiment": review.human_sentiment or "",
                    "sentiment_agreement": _agreement_cell(
                        sentiment_agreement(case)
                    ),
                    "emotion_judgment": review.emotion_judgment or "",
                    "human_dominant_emotion": (
                        review.human_dominant_emotion or ""
                    ),
                    "human_secondary_emotions": "|".join(
                        review.human_secondary_emotions
                    ),
                    "dominant_emotion_agreement": _agreement_cell(
                        dominant_emotion_agreement(case)
                    ),
                    "emotion_set_agreement": _agreement_cell(
                        emotion_set_agreement(case)
                    ),
                    "review_note": safe_spreadsheet_text(review.note or ""),
                    "reviewed_at": (
                        review.reviewed_at.astimezone(UTC).isoformat()
                        if review.reviewed_at is not None
                        else ""
                    ),
                }
            )
        else:
            row.update(dict.fromkeys(REVIEW_EXPORT_FIELDS, ""))
        writer.writerow(row)
    return output.getvalue()
