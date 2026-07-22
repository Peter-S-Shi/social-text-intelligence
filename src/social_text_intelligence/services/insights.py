"""Dataset-bounded insight metrics, context notes, examples, and export."""

from __future__ import annotations

import csv
import io
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from secrets import token_urlsafe

from ..contracts import EmotionLabel, SentimentLabel
from ..contracts.errors import ValidationError
from .batch import BatchOutcome, BatchResult, safe_spreadsheet_text
from .review import (
    HumanReview,
    ReviewCase,
    ReviewJudgment,
    ReviewState,
    dominant_emotion_agreement,
    emotion_set_agreement,
    review_cases,
    sentiment_agreement,
)

MAX_CONTEXT_FIELD_LENGTH = 2_000
MAX_CONTEXT_PHRASE_LENGTH = 500
MAX_CONTEXT_TAGS = 8
MAX_EXAMPLES = 10
MISSING_GROUP = "(not supplied)"


class GroupingDimension(StrEnum):
    SOURCE_TYPE = "source_type"
    SOURCE_LABEL = "source_label"
    TOPIC = "topic"
    COMMUNITY = "community"
    LANGUAGE = "language"
    TIMESTAMP_MONTH = "timestamp_month"


class InsightPerspective(StrEnum):
    AI = "ai"
    HUMAN = "human"
    AGREEMENT = "agreement"


class InsightMetric(StrEnum):
    AI_SENTIMENT = "ai_sentiment"
    AI_DOMINANT_EMOTION = "ai_dominant_emotion"
    AI_EMOTION_ACTIVATION = "ai_emotion_activation"
    HUMAN_SENTIMENT = "human_sentiment"
    HUMAN_DOMINANT_EMOTION = "human_dominant_emotion"
    HUMAN_EMOTION_INCLUSION = "human_emotion_inclusion"
    SENTIMENT_DISAGREEMENT = "sentiment_disagreement"
    DOMINANT_EMOTION_DISAGREEMENT = "dominant_emotion_disagreement"
    EMOTION_SET_DISAGREEMENT = "emotion_set_disagreement"
    REVIEW_COVERAGE = "review_coverage"


class SampleSizeLevel(StrEnum):
    INSUFFICIENT = "insufficient"
    SMALL = "small"
    DESCRIPTIVE = "descriptive"


class ContextAssociation(StrEnum):
    RECORD = "record"
    TOPIC = "topic"
    COMMUNITY = "community"
    SOURCE_LABEL = "source_label"
    COMPARISON = "comparison"


class ContextTag(StrEnum):
    SARCASM_POSSIBLE = "sarcasm_possible"
    QUOTATION_OR_REPORTED_SPEECH = "quotation_or_reported_speech"
    MISSING_CONTEXT = "missing_context"
    MIXED_STANCE = "mixed_stance"
    IN_GROUP_EXPRESSION = "in_group_expression"
    IDIOM_OR_SLANG = "idiom_or_slang"
    ANNOTATION_UNCERTAIN = "annotation_uncertain"
    TRANSLATION_OR_LANGUAGE_ISSUE = "translation_or_language_issue"
    OTHER = "other"


class ExampleMode(StrEnum):
    HIGHEST_AI_SCORE = "highest_ai_score"
    LOWEST_AI_CONFIDENCE = "lowest_ai_confidence"
    AI_HUMAN_DISAGREEMENT = "ai_human_disagreement"
    HUMAN_CORRECTED = "human_corrected"
    UNCERTAIN = "uncertain"
    CONTEXT_NOTES = "context_notes"
    USER_SELECTED = "user_selected"


_METRIC_PERSPECTIVE = {
    InsightMetric.AI_SENTIMENT: InsightPerspective.AI,
    InsightMetric.AI_DOMINANT_EMOTION: InsightPerspective.AI,
    InsightMetric.AI_EMOTION_ACTIVATION: InsightPerspective.AI,
    InsightMetric.HUMAN_SENTIMENT: InsightPerspective.HUMAN,
    InsightMetric.HUMAN_DOMINANT_EMOTION: InsightPerspective.HUMAN,
    InsightMetric.HUMAN_EMOTION_INCLUSION: InsightPerspective.HUMAN,
    InsightMetric.SENTIMENT_DISAGREEMENT: InsightPerspective.AGREEMENT,
    InsightMetric.DOMINANT_EMOTION_DISAGREEMENT: InsightPerspective.AGREEMENT,
    InsightMetric.EMOTION_SET_DISAGREEMENT: InsightPerspective.AGREEMENT,
    InsightMetric.REVIEW_COVERAGE: InsightPerspective.AGREEMENT,
}

METRIC_DEFINITIONS = {
    InsightMetric.AI_SENTIMENT: (
        "One AI sentiment label per successful row; denominator is successful rows."
    ),
    InsightMetric.AI_DOMINANT_EMOTION: (
        "One compact AI dominant emotion per successful row; denominator is "
        "successful rows."
    ),
    InsightMetric.AI_EMOTION_ACTIVATION: (
        "A compact non-neutral emotion is active when its score is greater than "
        "or equal to that row's threshold. Rates are independent and need not sum "
        "to 100%."
    ),
    InsightMetric.HUMAN_SENTIMENT: (
        "Definitive whole-record human sentiment reviews only; denominator is "
        "definitive human sentiment reviews."
    ),
    InsightMetric.HUMAN_DOMINANT_EMOTION: (
        "One human dominant label per definitive whole-record emotion review; "
        "denominator is definitive human emotion reviews."
    ),
    InsightMetric.HUMAN_EMOTION_INCLUSION: (
        "Each compact human label is counted once per definitive reviewed record "
        "across dominant and secondary labels. Rates are independent."
    ),
    InsightMetric.SENTIMENT_DISAGREEMENT: (
        "AI-human sentiment disagreement among definitive whole-record sentiment "
        "reviews only. Agreement is descriptive, not model accuracy."
    ),
    InsightMetric.DOMINANT_EMOTION_DISAGREEMENT: (
        "AI-human dominant-emotion disagreement among definitive whole-record "
        "emotion reviews only. Agreement is descriptive, not model accuracy."
    ),
    InsightMetric.EMOTION_SET_DISAGREEMENT: (
        "AI-human exact compact emotion-set disagreement among definitive "
        "whole-record emotion reviews only."
    ),
    InsightMetric.REVIEW_COVERAGE: (
        "Review coverage counts reviewable successful rows, whole-record reviewed "
        "rows, definitive dimensions, uncertain rows, and unreviewed rows."
    ),
}


@dataclass(frozen=True, slots=True)
class InsightFilters:
    sentiment: SentimentLabel | None = None
    emotion: EmotionLabel | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True, slots=True)
class InsightSelection:
    grouping: GroupingDimension
    groups: tuple[str, ...]
    perspective: InsightPerspective
    metric: InsightMetric
    filters: InsightFilters = InsightFilters()

    def __post_init__(self) -> None:
        if not self.groups or any(not group.strip() for group in self.groups):
            raise ValidationError(
                field="groups",
                code="missing_group",
                message="Select at least one non-blank group.",
            )
        if len(self.groups) != len(set(self.groups)):
            raise ValidationError(
                field="groups",
                code="duplicate_group",
                message="Selected groups must be unique.",
            )
        if _METRIC_PERSPECTIVE[self.metric] is not self.perspective:
            raise ValidationError(
                field="metric",
                code="incompatible_metric",
                message="The selected metric does not belong to this perspective.",
            )


@dataclass(frozen=True, slots=True)
class SampleSizeAssessment:
    level: SampleSizeLevel
    message: str | None
    emphasize_percentages: bool
    allow_comparison: bool


@dataclass(frozen=True, slots=True)
class MetricValue:
    label: str
    count: int
    denominator: int

    @property
    def rate(self) -> float:
        return self.count / self.denominator if self.denominator else 0.0


@dataclass(frozen=True, slots=True)
class GroupMetricSummary:
    group: str
    total_count: int
    eligible_count: int
    values: tuple[MetricValue, ...]
    sample: SampleSizeAssessment
    unreviewed_count: int = 0
    uncertain_count: int = 0


@dataclass(frozen=True, slots=True)
class ContextNote:
    note_id: str
    association: ContextAssociation
    association_value: str
    phrase: str
    explanation: str
    context_importance: str
    tags: tuple[ContextTag, ...]


@dataclass(frozen=True, slots=True)
class InsightState:
    notes: tuple[ContextNote, ...] = ()


@dataclass(frozen=True, slots=True)
class RepresentativeExample:
    outcome: BatchOutcome
    review: HumanReview | None
    reason: str


def sample_size_assessment(eligible_count: int) -> SampleSizeAssessment:
    if eligible_count < 5:
        return SampleSizeAssessment(
            SampleSizeLevel.INSUFFICIENT,
            "Insufficient sample for comparison",
            False,
            False,
        )
    if eligible_count < 10:
        return SampleSizeAssessment(
            SampleSizeLevel.SMALL,
            "Small sample",
            True,
            False,
        )
    return SampleSizeAssessment(SampleSizeLevel.DESCRIPTIVE, None, True, True)


def parse_insight_filters(
    *, sentiment: str = "", emotion: str = "", date_from: str = "", date_to: str = ""
) -> InsightFilters:
    try:
        parsed_sentiment = SentimentLabel(sentiment) if sentiment else None
    except ValueError as error:
        raise ValidationError(
            field="sentiment",
            code="invalid_filter",
            message="Invalid sentiment filter.",
        ) from error
    try:
        parsed_emotion = EmotionLabel(emotion) if emotion else None
    except ValueError as error:
        raise ValidationError(
            field="emotion", code="invalid_filter", message="Invalid emotion filter."
        ) from error

    def parsed_date(value: str, field: str) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValidationError(
                field=field,
                code="invalid_date",
                message=f"{field} must use YYYY-MM-DD format.",
            ) from error

    start = parsed_date(date_from, "date_from")
    end = parsed_date(date_to, "date_to")
    if start is not None and end is not None and start > end:
        raise ValidationError(
            field="date_range",
            code="invalid_date_range",
            message="The start date must not be after the end date.",
        )
    return InsightFilters(parsed_sentiment, parsed_emotion, start, end)


def _group_value(outcome: BatchOutcome, grouping: GroupingDimension) -> str:
    report = outcome.report
    if report is None:
        return MISSING_GROUP
    record = report.record
    if grouping is GroupingDimension.TIMESTAMP_MONTH:
        return record.timestamp.strftime("%Y-%m") if record.timestamp else MISSING_GROUP
    value = getattr(record, grouping.value)
    return str(value.value if hasattr(value, "value") else value or MISSING_GROUP)


def available_group_values(
    result: BatchResult, grouping: GroupingDimension
) -> tuple[str, ...]:
    values = {
        _group_value(outcome, grouping)
        for outcome in result.outcomes
        if outcome.report is not None
    }
    return tuple(
        sorted(values, key=lambda value: (value == MISSING_GROUP, value.casefold()))
    )


def _filtered_outcomes(
    result: BatchResult, filters: InsightFilters
) -> tuple[BatchOutcome, ...]:
    selected: list[BatchOutcome] = []
    for outcome in result.outcomes:
        report = outcome.report
        if report is None:
            continue
        timestamp = report.record.timestamp
        if (
            filters.sentiment is not None
            and report.sentiment.label is not filters.sentiment
        ):
            continue
        if (
            filters.emotion is not None
            and report.emotion.dominant_emotion is not filters.emotion
        ):
            continue
        if filters.date_from is not None and (
            timestamp is None or timestamp.date() < filters.date_from
        ):
            continue
        if filters.date_to is not None and (
            timestamp is None or timestamp.date() > filters.date_to
        ):
            continue
        selected.append(outcome)
    return tuple(selected)


def _case_map(result: BatchResult, state: ReviewState) -> dict[str, ReviewCase]:
    return {case.review.record_id: case for case in review_cases(result, state)}


def _review_counts(cases: Sequence[ReviewCase]) -> tuple[int, int]:
    return (
        sum(not case.review.is_reviewed for case in cases),
        sum(case.review.is_uncertain for case in cases),
    )


def _distribution(
    labels: Sequence[StrEnum], ordered_labels: Sequence[StrEnum]
) -> tuple[MetricValue, ...]:
    counts = Counter(labels)
    denominator = len(labels)
    return tuple(
        MetricValue(label.value, counts[label], denominator) for label in ordered_labels
    )


def _summarize_group(
    outcomes: Sequence[BatchOutcome],
    cases: Sequence[ReviewCase],
    metric: InsightMetric,
    group: str,
) -> GroupMetricSummary:
    total = len(outcomes)
    unreviewed, uncertain = _review_counts(cases)
    values: tuple[MetricValue, ...]
    eligible: int
    if metric is InsightMetric.AI_SENTIMENT:
        sentiment_labels: list[StrEnum] = [
            outcome.report.sentiment.label
            for outcome in outcomes
            if outcome.report
        ]
        values = _distribution(sentiment_labels, tuple(SentimentLabel))
        eligible = len(sentiment_labels)
    elif metric is InsightMetric.AI_DOMINANT_EMOTION:
        emotion_labels: list[StrEnum] = [
            outcome.report.emotion.dominant_emotion
            for outcome in outcomes
            if outcome.report
        ]
        values = _distribution(emotion_labels, tuple(EmotionLabel))
        eligible = len(emotion_labels)
    elif metric is InsightMetric.AI_EMOTION_ACTIVATION:
        eligible = total
        values = tuple(
            MetricValue(
                label.value,
                sum(
                    any(
                        score.label is label
                        and score.score >= outcome.report.emotion.threshold
                        for score in outcome.report.emotion.scores
                    )
                    for outcome in outcomes
                    if outcome.report
                ),
                eligible,
            )
            for label in EmotionLabel
            if label is not EmotionLabel.NEUTRAL
        )
    elif metric is InsightMetric.HUMAN_SENTIMENT:
        human_sentiment_labels: list[StrEnum] = [
            case.review.human_sentiment
            for case in cases
            if case.review.is_reviewed
            and case.review.sentiment_judgment is not ReviewJudgment.UNCERTAIN
            and case.review.human_sentiment is not None
        ]
        values = _distribution(human_sentiment_labels, tuple(SentimentLabel))
        eligible = len(human_sentiment_labels)
    elif metric in (
        InsightMetric.HUMAN_DOMINANT_EMOTION,
        InsightMetric.HUMAN_EMOTION_INCLUSION,
    ):
        definitive = [
            case
            for case in cases
            if case.review.is_reviewed
            and case.review.emotion_judgment is not ReviewJudgment.UNCERTAIN
            and case.review.human_dominant_emotion is not None
        ]
        eligible = len(definitive)
        if metric is InsightMetric.HUMAN_DOMINANT_EMOTION:
            human_emotion_labels: list[StrEnum] = []
            for case in definitive:
                human_label = case.review.human_dominant_emotion
                assert human_label is not None
                human_emotion_labels.append(human_label)
            values = _distribution(
                human_emotion_labels,
                tuple(EmotionLabel),
            )
        else:
            counts = Counter[EmotionLabel]()
            for case in definitive:
                dominant = case.review.human_dominant_emotion
                assert dominant is not None
                counts.update({dominant, *case.review.human_secondary_emotions})
            values = tuple(
                MetricValue(label.value, counts[label], eligible)
                for label in EmotionLabel
            )
    elif metric is InsightMetric.REVIEW_COVERAGE:
        eligible = len(cases)
        definitive_sentiment = sum(
            case.review.is_reviewed
            and case.review.sentiment_judgment is not ReviewJudgment.UNCERTAIN
            for case in cases
        )
        definitive_emotion = sum(
            case.review.is_reviewed
            and case.review.emotion_judgment is not ReviewJudgment.UNCERTAIN
            for case in cases
        )
        values = tuple(
            MetricValue(label, count, eligible)
            for label, count in (
                (
                    "whole-record reviewed",
                    sum(case.review.is_reviewed for case in cases),
                ),
                ("definitive sentiment", definitive_sentiment),
                ("definitive emotion", definitive_emotion),
                ("uncertain", uncertain),
                ("unreviewed", unreviewed),
            )
        )
    else:
        agreement_function = {
            InsightMetric.SENTIMENT_DISAGREEMENT: sentiment_agreement,
            InsightMetric.DOMINANT_EMOTION_DISAGREEMENT: dominant_emotion_agreement,
            InsightMetric.EMOTION_SET_DISAGREEMENT: emotion_set_agreement,
        }[metric]
        agreements = [agreement_function(case) for case in cases]
        definitive_values = [value for value in agreements if value is not None]
        eligible = len(definitive_values)
        disagreement = sum(value is False for value in definitive_values)
        values = (
            MetricValue("disagreement", disagreement, eligible),
            MetricValue("agreement", eligible - disagreement, eligible),
        )
    return GroupMetricSummary(
        group=group,
        total_count=total,
        eligible_count=eligible,
        values=values,
        sample=sample_size_assessment(eligible),
        unreviewed_count=unreviewed,
        uncertain_count=uncertain,
    )


def build_group_metrics(
    result: BatchResult,
    state: ReviewState,
    selection: InsightSelection,
    *,
    comparison: bool = False,
) -> tuple[GroupMetricSummary, ...]:
    if comparison and not 2 <= len(selection.groups) <= 4:
        raise ValidationError(
            field="groups",
            code="comparison_group_count",
            message="Select between two and four groups for comparison.",
        )
    available = set(available_group_values(result, selection.grouping))
    unknown = tuple(group for group in selection.groups if group not in available)
    if unknown:
        raise ValidationError(
            field="groups",
            code="unknown_group",
            message="A selected group is not present in this workspace.",
        )
    outcomes = _filtered_outcomes(result, selection.filters)
    cases_by_id = _case_map(result, state)
    summaries: list[GroupMetricSummary] = []
    for group in selection.groups:
        grouped = tuple(
            outcome
            for outcome in outcomes
            if _group_value(outcome, selection.grouping) == group
        )
        cases = tuple(
            cases_by_id[outcome.prepared.identity]
            for outcome in grouped
            if outcome.prepared.identity in cases_by_id
        )
        summaries.append(_summarize_group(grouped, cases, selection.metric, group))
    return tuple(summaries)


def _clean_context_text(value: str, *, field: str, limit: int) -> str:
    cleaned = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    ).strip()
    if not cleaned:
        raise ValidationError(
            field=field, code="required", message=f"{field} must not be blank."
        )
    if len(cleaned) > limit:
        raise ValidationError(
            field=field,
            code="too_long",
            message=f"{field} exceeds {limit} characters.",
        )
    return cleaned


def _valid_association_values(
    result: BatchResult, association: ContextAssociation
) -> set[str]:
    if association is ContextAssociation.RECORD:
        return {
            outcome.prepared.identity
            for outcome in result.outcomes
            if outcome.report is not None
        }
    dimension = {
        ContextAssociation.TOPIC: GroupingDimension.TOPIC,
        ContextAssociation.COMMUNITY: GroupingDimension.COMMUNITY,
        ContextAssociation.SOURCE_LABEL: GroupingDimension.SOURCE_LABEL,
    }.get(association)
    return set(available_group_values(result, dimension)) if dimension else set()


def add_context_note(
    state: InsightState,
    result: BatchResult,
    *,
    association: str,
    association_value: str,
    phrase: str,
    explanation: str,
    context_importance: str,
    tags: Sequence[str],
) -> InsightState:
    try:
        parsed_association = ContextAssociation(association)
    except ValueError as error:
        raise ValidationError(
            field="association",
            code="invalid_association",
            message="Select a supported note association.",
        ) from error
    value = _clean_context_text(
        association_value, field="association_value", limit=MAX_CONTEXT_PHRASE_LENGTH
    )
    if parsed_association is not ContextAssociation.COMPARISON and value not in (
        _valid_association_values(result, parsed_association)
    ):
        raise ValidationError(
            field="association_value",
            code="unknown_association",
            message="The note association is not present in this workspace.",
        )
    try:
        parsed_tags = tuple(ContextTag(tag) for tag in tags)
    except ValueError as error:
        raise ValidationError(
            field="tags", code="invalid_tag", message="Select only supported tags."
        ) from error
    if len(parsed_tags) != len(set(parsed_tags)) or len(parsed_tags) > MAX_CONTEXT_TAGS:
        raise ValidationError(
            field="tags",
            code="invalid_tags",
            message=f"Select no more than {MAX_CONTEXT_TAGS} unique tags.",
        )
    note = ContextNote(
        note_id=token_urlsafe(12),
        association=parsed_association,
        association_value=value,
        phrase=_clean_context_text(
            phrase, field="phrase", limit=MAX_CONTEXT_PHRASE_LENGTH
        ),
        explanation=_clean_context_text(
            explanation, field="explanation", limit=MAX_CONTEXT_FIELD_LENGTH
        ),
        context_importance=_clean_context_text(
            context_importance,
            field="context_importance",
            limit=MAX_CONTEXT_FIELD_LENGTH,
        ),
        tags=parsed_tags,
    )
    return InsightState(notes=(*state.notes, note))


def delete_context_note(state: InsightState, *, note_id: str) -> InsightState:
    notes = tuple(note for note in state.notes if note.note_id != note_id)
    if len(notes) == len(state.notes):
        raise ValidationError(
            field="note_id", code="note_not_found", message="Context note not found."
        )
    return InsightState(notes=notes)


def select_representative_examples(
    result: BatchResult,
    state: ReviewState,
    insight_state: InsightState,
    *,
    mode: ExampleMode,
    emotion_label: EmotionLabel = EmotionLabel.ANGER,
    record_ids: Sequence[str] = (),
    limit: int = 5,
) -> tuple[RepresentativeExample, ...]:
    bounded_limit = min(max(limit, 1), MAX_EXAMPLES)
    cases = _case_map(result, state)
    outcomes = tuple(item for item in result.outcomes if item.report is not None)
    reason = ""
    if mode is ExampleMode.HIGHEST_AI_SCORE:
        def emotion_score(outcome: BatchOutcome) -> float:
            assert outcome.report is not None
            return next(
                score.score
                for score in outcome.report.emotion.scores
                if score.label is emotion_label
            )

        selected = sorted(
            outcomes,
            key=lambda item: (-emotion_score(item), item.prepared.row_number),
        )
        reason = f"Highest AI compact {emotion_label.value} score"
    elif mode is ExampleMode.LOWEST_AI_CONFIDENCE:
        selected = sorted(
            outcomes,
            key=lambda item: (
                min(
                    item.report.sentiment.confidence,
                    item.report.emotion.confidence,
                )
                if item.report
                else 1.0,
                item.prepared.row_number,
            ),
        )
        reason = "Lowest displayed AI confidence"
    elif mode is ExampleMode.AI_HUMAN_DISAGREEMENT:
        selected = sorted(
            (
                outcome
                for outcome in outcomes
                if outcome.prepared.identity in cases
                and any(
                    comparison(cases[outcome.prepared.identity]) is False
                    for comparison in (
                        sentiment_agreement,
                        dominant_emotion_agreement,
                        emotion_set_agreement,
                    )
                )
            ),
            key=lambda item: item.prepared.row_number,
        )
        reason = "Definitive AI-human disagreement"
    elif mode is ExampleMode.HUMAN_CORRECTED:
        selected = [
            outcome
            for outcome in outcomes
            if outcome.prepared.identity in cases
            and cases[outcome.prepared.identity].review.is_corrected
        ]
        reason = "Human-corrected review"
    elif mode is ExampleMode.UNCERTAIN:
        selected = [
            outcome
            for outcome in outcomes
            if outcome.prepared.identity in cases
            and cases[outcome.prepared.identity].review.is_uncertain
        ]
        reason = "Human review marked uncertain"
    elif mode is ExampleMode.CONTEXT_NOTES:
        noted_ids = {
            note.association_value
            for note in insight_state.notes
            if note.association is ContextAssociation.RECORD
        }
        selected = [
            outcome
            for outcome in outcomes
            if outcome.prepared.identity in noted_ids
        ]
        reason = "Record has a user-authored context note"
    else:
        selected_ids = set(record_ids)
        selected = [
            outcome
            for outcome in outcomes
            if outcome.prepared.identity in selected_ids
        ]
        reason = "Explicitly selected by the user"
    return tuple(
        RepresentativeExample(
            outcome=outcome,
            review=(
                cases[outcome.prepared.identity].review
                if outcome.prepared.identity in cases
                else None
            ),
            reason=reason,
        )
        for outcome in selected[:bounded_limit]
    )


INSIGHT_EXPORT_FIELDS = (
    "section",
    "grouping",
    "group",
    "perspective",
    "metric",
    "label",
    "count",
    "denominator",
    "rate",
    "sample_warning",
    "total_group_rows",
    "unreviewed_count",
    "uncertain_count",
    "association",
    "association_value",
    "phrase",
    "explanation",
    "context_importance",
    "tags",
    "record_id",
    "text",
    "source_type",
    "source_label",
    "language",
    "timestamp",
    "topic",
    "community",
    "ai_sentiment",
    "ai_dominant_emotion",
    "human_sentiment",
    "human_dominant_emotion",
    "sentiment_model",
    "sentiment_revision",
    "emotion_model",
    "emotion_revision",
    "emotion_threshold",
    "native_emotion_scores",
)


def export_insights_csv(
    result: BatchResult,
    reviews: ReviewState,
    insight_state: InsightState,
    selection: InsightSelection,
    *,
    include_records: bool,
    include_native: bool,
) -> str:
    summaries = build_group_metrics(result, reviews, selection)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=INSIGHT_EXPORT_FIELDS, lineterminator="\n"
    )
    writer.writeheader()
    for summary in summaries:
        for value in summary.values:
            writer.writerow(
                {
                    "section": "group_summary",
                    "grouping": selection.grouping,
                    "group": safe_spreadsheet_text(summary.group),
                    "perspective": selection.perspective,
                    "metric": selection.metric,
                    "label": value.label,
                    "count": value.count,
                    "denominator": value.denominator,
                    "rate": value.rate,
                    "sample_warning": summary.sample.message or "",
                    "total_group_rows": summary.total_count,
                    "unreviewed_count": summary.unreviewed_count,
                    "uncertain_count": summary.uncertain_count,
                }
            )
    for note in insight_state.notes:
        writer.writerow(
            {
                "section": "context_note",
                "association": note.association,
                "association_value": safe_spreadsheet_text(note.association_value),
                "phrase": safe_spreadsheet_text(note.phrase),
                "explanation": safe_spreadsheet_text(note.explanation),
                "context_importance": safe_spreadsheet_text(note.context_importance),
                "tags": safe_spreadsheet_text("|".join(note.tags)),
            }
        )
    if include_records:
        cases = _case_map(result, reviews)
        selected_groups = set(selection.groups)
        for outcome in _filtered_outcomes(result, selection.filters):
            report = outcome.report
            assert report is not None
            if _group_value(outcome, selection.grouping) not in selected_groups:
                continue
            review = cases.get(outcome.prepared.identity)
            writer.writerow(
                {
                    "section": "supporting_record",
                    "record_id": safe_spreadsheet_text(report.record.record_id),
                    "text": safe_spreadsheet_text(report.record.text),
                    "source_type": report.record.source_type,
                    "source_label": safe_spreadsheet_text(
                        report.record.source_label or ""
                    ),
                    "language": safe_spreadsheet_text(report.record.language or ""),
                    "timestamp": (
                        report.record.timestamp.isoformat()
                        if report.record.timestamp
                        else ""
                    ),
                    "topic": safe_spreadsheet_text(report.record.topic or ""),
                    "community": safe_spreadsheet_text(report.record.community or ""),
                    "ai_sentiment": report.sentiment.label,
                    "ai_dominant_emotion": report.emotion.dominant_emotion,
                    "human_sentiment": review.review.human_sentiment if review else "",
                    "human_dominant_emotion": (
                        review.review.human_dominant_emotion if review else ""
                    ),
                    "sentiment_model": report.sentiment.provider.model_name,
                    "sentiment_revision": report.sentiment.provider.revision,
                    "emotion_model": report.emotion.provider.model_name,
                    "emotion_revision": report.emotion.provider.revision,
                    "emotion_threshold": report.emotion.threshold,
                    "native_emotion_scores": (
                        "|".join(
                            f"{score.label}:{score.score}"
                            for score in report.emotion.native_scores
                        )
                        if include_native
                        else ""
                    ),
                }
            )
    return output.getvalue()
