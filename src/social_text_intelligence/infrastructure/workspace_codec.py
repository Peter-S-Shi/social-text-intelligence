"""Lossless mapping between workspace dataclasses and stored column values.

Decoding rebuilds values through the original constructors, so every contract
invariant is re-checked on load. Floats use JSON's shortest round-trip form, which
restores the exact original value. Failures raise ordinary exceptions; the
repository converts them into content-free storage errors.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, TypeAlias

from ..contracts import (
    AnalysisReport,
    DetectorInfo,
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    LanguageAssessment,
    LanguageReason,
    LanguageStatus,
    NativeScore,
    NormalizedTextInput,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    SourceType,
    TaskType,
)
from ..services.batch import (
    ActivationRate,
    BatchAggregates,
    BatchOutcome,
    BatchPreview,
    PendingBatchUpload,
    PreparedBatchRow,
)
from ..services.insights import (
    ContextAssociation,
    ContextNote,
    ContextTag,
    GroupingDimension,
    InsightFilters,
    InsightMetric,
    InsightPerspective,
    InsightSelection,
)
from ..services.review import HumanReview, ReviewJudgment

Json: TypeAlias = Any


def dumps(value: Json) -> str:
    """Compact, strict JSON; ASCII-escaped so any Unicode text survives storage."""

    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def loads(text: str) -> Json:
    return json.loads(text)


def encode_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def decode_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


# --- imported input -------------------------------------------------------------


def encode_pending(pending: PendingBatchUpload) -> tuple[bytes, str]:
    return pending.content, dumps(list(pending.headers))


def decode_pending(content: bytes, headers_json: str) -> PendingBatchUpload:
    return PendingBatchUpload(
        content=bytes(content), headers=tuple(loads(headers_json))
    )


def encode_record(record: NormalizedTextInput) -> str:
    return dumps(
        {
            "record_id": record.record_id,
            "text": record.text,
            "source_type": record.source_type.value,
            "source_label": record.source_label,
            "language": record.language,
            "timestamp": encode_datetime(record.timestamp),
            "topic": record.topic,
            "community": record.community,
            "parent_record_id": record.parent_record_id,
            "notes": record.notes,
            "max_text_length": record.max_text_length,
        }
    )


def decode_record(payload: str) -> NormalizedTextInput:
    data = loads(payload)
    return NormalizedTextInput(
        record_id=data["record_id"],
        text=data["text"],
        source_type=SourceType(data["source_type"]),
        source_label=data["source_label"],
        language=data["language"],
        timestamp=decode_datetime(data["timestamp"]),
        topic=data["topic"],
        community=data["community"],
        parent_record_id=data["parent_record_id"],
        notes=data["notes"],
        max_text_length=data["max_text_length"],
    )


def encode_preview(preview: BatchPreview) -> tuple[str, str, str]:
    return (
        preview.text_column,
        dumps(list(preview.headers)),
        dumps(list(preview.ignored_columns)),
    )


def encode_row(
    row: PreparedBatchRow,
) -> tuple[int, str, str, str | None, str | None, str | None]:
    return (
        row.row_number,
        row.identity,
        dumps([list(item) for item in row.input_values]),
        None if row.record is None else encode_record(row.record),
        row.error_code,
        row.error_message,
    )


def decode_row(
    row_number: int,
    identity: str,
    input_values_json: str,
    record_json: str | None,
    error_code: str | None,
    error_message: str | None,
) -> PreparedBatchRow:
    return PreparedBatchRow(
        row_number=row_number,
        identity=identity,
        input_values=tuple((str(k), str(v)) for k, v in loads(input_values_json)),
        record=None if record_json is None else decode_record(record_json),
        error_code=error_code,
        error_message=error_message,
    )


def decode_preview(
    text_column: str,
    headers_json: str,
    ignored_json: str,
    rows: tuple[PreparedBatchRow, ...],
) -> BatchPreview:
    return BatchPreview(
        text_column=text_column,
        headers=tuple(loads(headers_json)),
        ignored_columns=tuple(loads(ignored_json)),
        rows=rows,
    )


# --- immutable AI records -------------------------------------------------------


def _encode_provider(provider: ProviderMetadata) -> Json:
    return {
        "provider": provider.provider,
        "model_name": provider.model_name,
        "revision": provider.revision,
        "task": provider.task.value,
        "supported_languages": list(provider.supported_languages),
        "native_labels": list(provider.native_labels),
    }


def _decode_provider(data: Json) -> ProviderMetadata:
    return ProviderMetadata(
        provider=data["provider"],
        model_name=data["model_name"],
        revision=data["revision"],
        task=TaskType(data["task"]),
        supported_languages=tuple(data["supported_languages"]),
        native_labels=tuple(data["native_labels"]),
    )


def _encode_language(language: LanguageAssessment) -> Json:
    detector = language.detector
    return {
        "status": language.status.value,
        "detected_language": language.detected_language,
        "score": language.score,
        "supported_languages": list(language.supported_languages),
        "reason": None if language.reason is None else language.reason.value,
        "detector": None
        if detector is None
        else {
            "name": detector.name,
            "version": detector.version,
            "model": detector.model,
            "min_score": detector.min_score,
        },
    }


def _decode_language(data: Json) -> LanguageAssessment:
    """A report stored before language checks existed has no entry: not assessed."""

    if data is None:
        return LanguageAssessment.not_assessed()
    detector = data["detector"]
    return LanguageAssessment(
        status=LanguageStatus(data["status"]),
        detected_language=data["detected_language"],
        score=data["score"],
        supported_languages=tuple(data["supported_languages"]),
        detector=None if detector is None else DetectorInfo(**detector),
        reason=None if data["reason"] is None else LanguageReason(data["reason"]),
    )


def encode_report(report: AnalysisReport) -> str:
    sentiment = report.sentiment
    emotion = report.emotion
    return dumps(
        {
            "language": _encode_language(report.language),
            "sentiment": {
                "record_id": sentiment.record_id,
                "label": sentiment.label.value,
                "confidence": sentiment.confidence,
                "scores": [[item.label.value, item.score] for item in sentiment.scores],
                "native_scores": [
                    [item.label, item.score] for item in sentiment.native_scores
                ],
                "provider": _encode_provider(sentiment.provider),
            },
            "emotion": {
                "record_id": emotion.record_id,
                "dominant_emotion": emotion.dominant_emotion.value,
                "confidence": emotion.confidence,
                "threshold": emotion.threshold,
                "secondary_emotions": [
                    label.value for label in emotion.secondary_emotions
                ],
                "scores": [[item.label.value, item.score] for item in emotion.scores],
                "native_scores": [
                    [item.label, item.score] for item in emotion.native_scores
                ],
                "provider": _encode_provider(emotion.provider),
            },
        }
    )


def decode_report(payload: str, record: NormalizedTextInput) -> AnalysisReport:
    data = loads(payload)
    sentiment = data["sentiment"]
    emotion = data["emotion"]
    return AnalysisReport(
        record=record,
        language=_decode_language(data.get("language")),
        sentiment=SentimentResult(
            record_id=sentiment["record_id"],
            label=SentimentLabel(sentiment["label"]),
            confidence=sentiment["confidence"],
            scores=tuple(
                SentimentScore(SentimentLabel(label), score)
                for label, score in sentiment["scores"]
            ),
            native_scores=tuple(
                NativeScore(label, score) for label, score in sentiment["native_scores"]
            ),
            provider=_decode_provider(sentiment["provider"]),
        ),
        emotion=EmotionResult(
            record_id=emotion["record_id"],
            dominant_emotion=EmotionLabel(emotion["dominant_emotion"]),
            confidence=emotion["confidence"],
            threshold=emotion["threshold"],
            secondary_emotions=tuple(
                EmotionLabel(label) for label in emotion["secondary_emotions"]
            ),
            scores=tuple(
                EmotionScore(EmotionLabel(label), score)
                for label, score in emotion["scores"]
            ),
            native_scores=tuple(
                NativeScore(label, score) for label, score in emotion["native_scores"]
            ),
            provider=_decode_provider(emotion["provider"]),
        ),
    )


def encode_outcome(
    outcome: BatchOutcome,
) -> tuple[int, str, str | None, str | None, str | None]:
    return (
        outcome.prepared.row_number,
        outcome.status,
        outcome.error_code,
        outcome.error_message,
        None if outcome.report is None else encode_report(outcome.report),
    )


def decode_outcome(
    prepared: PreparedBatchRow,
    status: str,
    error_code: str | None,
    error_message: str | None,
    report_json: str | None,
) -> BatchOutcome:
    report = None
    if report_json is not None:
        if prepared.record is None:
            raise ValueError("A report requires a valid input record.")
        report = decode_report(report_json, prepared.record)
    return BatchOutcome(
        prepared=prepared,
        status=status,
        report=report,
        error_code=error_code,
        error_message=error_message,
    )


def encode_aggregates(aggregates: BatchAggregates) -> str:
    return dumps(
        {
            "sentiment_counts": [
                [label.value, count] for label, count in aggregates.sentiment_counts
            ],
            "dominant_emotion_counts": [
                [label.value, count]
                for label, count in aggregates.dominant_emotion_counts
            ],
            "activation_rates": [
                [item.label.value, item.active_count, item.analyzed_count]
                for item in aggregates.activation_rates
            ],
            "analyzed_count": aggregates.analyzed_count,
            "failed_count": aggregates.failed_count,
        }
    )


def decode_aggregates(payload: str) -> BatchAggregates:
    data = loads(payload)
    return BatchAggregates(
        sentiment_counts=tuple(
            (SentimentLabel(label), count) for label, count in data["sentiment_counts"]
        ),
        dominant_emotion_counts=tuple(
            (EmotionLabel(label), count)
            for label, count in data["dominant_emotion_counts"]
        ),
        activation_rates=tuple(
            ActivationRate(EmotionLabel(label), active, analyzed)
            for label, active, analyzed in data["activation_rates"]
        ),
        analyzed_count=data["analyzed_count"],
        failed_count=data["failed_count"],
    )


# --- human judgments and insight state -----------------------------------------


def encode_review(
    review: HumanReview,
) -> tuple[
    str, str | None, str | None, str | None, str | None, str, str | None, str | None
]:
    return (
        review.record_id,
        None if review.sentiment_judgment is None else review.sentiment_judgment.value,
        None if review.human_sentiment is None else review.human_sentiment.value,
        None if review.emotion_judgment is None else review.emotion_judgment.value,
        None
        if review.human_dominant_emotion is None
        else review.human_dominant_emotion.value,
        dumps([label.value for label in review.human_secondary_emotions]),
        review.note,
        encode_datetime(review.reviewed_at),
    )


def decode_review(
    record_id: str,
    sentiment_judgment: str | None,
    human_sentiment: str | None,
    emotion_judgment: str | None,
    human_dominant_emotion: str | None,
    secondary_json: str,
    note: str | None,
    reviewed_at: str | None,
) -> HumanReview:
    return HumanReview(
        record_id=record_id,
        sentiment_judgment=(
            None if sentiment_judgment is None else ReviewJudgment(sentiment_judgment)
        ),
        human_sentiment=(
            None if human_sentiment is None else SentimentLabel(human_sentiment)
        ),
        emotion_judgment=(
            None if emotion_judgment is None else ReviewJudgment(emotion_judgment)
        ),
        human_dominant_emotion=(
            None
            if human_dominant_emotion is None
            else EmotionLabel(human_dominant_emotion)
        ),
        human_secondary_emotions=tuple(EmotionLabel(v) for v in loads(secondary_json)),
        note=note,
        reviewed_at=decode_datetime(reviewed_at),
    )


def encode_selection(selection: InsightSelection) -> str:
    filters = selection.filters
    return dumps(
        {
            "grouping": selection.grouping.value,
            "groups": list(selection.groups),
            "perspective": selection.perspective.value,
            "metric": selection.metric.value,
            "filters": {
                "sentiment": None
                if filters.sentiment is None
                else filters.sentiment.value,
                "emotion": None if filters.emotion is None else filters.emotion.value,
                "date_from": None
                if filters.date_from is None
                else filters.date_from.isoformat(),
                "date_to": None
                if filters.date_to is None
                else filters.date_to.isoformat(),
            },
        }
    )


def decode_selection(payload: str) -> InsightSelection:
    data = loads(payload)
    filters = data["filters"]
    return InsightSelection(
        grouping=GroupingDimension(data["grouping"]),
        groups=tuple(data["groups"]),
        perspective=InsightPerspective(data["perspective"]),
        metric=InsightMetric(data["metric"]),
        filters=InsightFilters(
            sentiment=(
                None
                if filters["sentiment"] is None
                else SentimentLabel(filters["sentiment"])
            ),
            emotion=None
            if filters["emotion"] is None
            else EmotionLabel(filters["emotion"]),
            date_from=None
            if filters["date_from"] is None
            else date.fromisoformat(filters["date_from"]),
            date_to=None
            if filters["date_to"] is None
            else date.fromisoformat(filters["date_to"]),
        ),
    )


def encode_note(note: ContextNote) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        note.note_id,
        note.association.value,
        note.association_value,
        note.phrase,
        note.explanation,
        note.context_importance,
        dumps([tag.value for tag in note.tags]),
        note.created_at.isoformat(),
    )


def decode_note(
    note_id: str,
    association: str,
    association_value: str,
    phrase: str,
    explanation: str,
    context_importance: str,
    tags_json: str,
    created_at: str,
) -> ContextNote:
    return ContextNote(
        note_id=note_id,
        association=ContextAssociation(association),
        association_value=association_value,
        phrase=phrase,
        explanation=explanation,
        context_importance=context_importance,
        tags=tuple(ContextTag(value) for value in loads(tags_json)),
        created_at=datetime.fromisoformat(created_at),
    )
