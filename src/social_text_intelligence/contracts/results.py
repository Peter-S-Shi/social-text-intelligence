"""Normalized sentiment, emotion, and combined analysis result contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidProviderOutputError, ValidationError
from .inputs import NormalizedTextInput


class TaskType(StrEnum):
    SENTIMENT = "sentiment"
    EMOTION = "emotion"


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EmotionLabel(StrEnum):
    JOY = "joy"
    AMUSEMENT = "amusement"
    ADMIRATION = "admiration"
    GRATITUDE = "gratitude"
    ANGER = "anger"
    SADNESS = "sadness"
    FEAR = "fear"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


def _validate_score(score: float, *, field: str) -> None:
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValidationError(
            field=field,
            code="invalid_score",
            message=f"{field} must be a finite value between 0 and 1.",
        )


def _validate_required_text(value: str, *, field: str) -> None:
    if not value.strip():
        raise ValidationError(
            field=field,
            code="required",
            message=f"{field} must not be empty.",
        )


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Traceable provider identity recorded with every normalized result."""

    provider: str
    model_name: str
    revision: str
    task: TaskType
    supported_languages: tuple[str, ...]
    native_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_required_text(self.provider, field="provider")
        _validate_required_text(self.model_name, field="model_name")
        _validate_required_text(self.revision, field="revision")
        if not self.supported_languages:
            raise ValidationError(
                field="supported_languages",
                code="required",
                message="At least one supported language is required.",
            )
        if not self.native_labels:
            raise ValidationError(
                field="native_labels",
                code="required",
                message="At least one native label is required.",
            )
        languages = tuple(item.strip().lower() for item in self.supported_languages)
        labels = tuple(item.strip() for item in self.native_labels)
        if any(not item for item in languages) or len(languages) != len(set(languages)):
            raise ValidationError(
                field="supported_languages",
                code="invalid_values",
                message="Supported languages must be non-empty and unique.",
            )
        if any(not item for item in labels) or len(labels) != len(set(labels)):
            raise ValidationError(
                field="native_labels",
                code="invalid_values",
                message="Native labels must be non-empty and unique.",
            )


@dataclass(frozen=True, slots=True)
class NativeScore:
    label: str
    score: float

    def __post_init__(self) -> None:
        _validate_required_text(self.label, field="native_label")
        _validate_score(self.score, field="native_score")


@dataclass(frozen=True, slots=True)
class SentimentScore:
    label: SentimentLabel
    score: float

    def __post_init__(self) -> None:
        _validate_score(self.score, field="sentiment_score")


@dataclass(frozen=True, slots=True)
class SentimentResult:
    record_id: str
    label: SentimentLabel
    confidence: float
    scores: tuple[SentimentScore, ...]
    native_scores: tuple[NativeScore, ...]
    provider: ProviderMetadata

    def __post_init__(self) -> None:
        _validate_required_text(self.record_id, field="record_id")
        _validate_score(self.confidence, field="confidence")
        if self.provider.task is not TaskType.SENTIMENT:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message="Sentiment results require sentiment provider metadata.",
            )
        labels = tuple(item.label for item in self.scores)
        if not labels or len(labels) != len(set(labels)) or self.label not in labels:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message=(
                    "Sentiment scores must be unique and include the selected label."
                ),
            )
        selected_score = next(
            item.score for item in self.scores if item.label is self.label
        )
        if selected_score != max(item.score for item in self.scores):
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message="The selected sentiment label must have a highest score.",
            )


@dataclass(frozen=True, slots=True)
class EmotionScore:
    label: EmotionLabel
    score: float

    def __post_init__(self) -> None:
        _validate_score(self.score, field="emotion_score")


@dataclass(frozen=True, slots=True)
class EmotionResult:
    record_id: str
    dominant_emotion: EmotionLabel
    confidence: float
    threshold: float
    secondary_emotions: tuple[EmotionLabel, ...]
    scores: tuple[EmotionScore, ...]
    native_scores: tuple[NativeScore, ...]
    provider: ProviderMetadata

    def __post_init__(self) -> None:
        _validate_required_text(self.record_id, field="record_id")
        _validate_score(self.confidence, field="emotion_confidence")
        if not math.isfinite(self.threshold) or not 0.0 < self.threshold <= 1.0:
            raise ValidationError(
                field="emotion_threshold",
                code="invalid_threshold",
                message="emotion_threshold must be greater than 0 and at most 1.",
            )
        if self.provider.task is not TaskType.EMOTION:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message="Emotion results require emotion provider metadata.",
            )
        labels = tuple(item.label for item in self.scores)
        if len(labels) != len(set(labels)) or set(labels) != set(EmotionLabel):
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message=(
                    "Emotion scores must contain each compact emotion exactly once."
                ),
            )
        native_labels = tuple(item.label for item in self.native_scores)
        if native_labels != self.provider.native_labels:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message="Native emotion scores must match provider metadata order.",
            )

        score_by_label = {item.label: item.score for item in self.scores}
        if self.confidence != score_by_label[self.dominant_emotion]:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message="Emotion confidence must equal the dominant emotion score.",
            )

        activated = tuple(
            sorted(
                (
                    label
                    for label in EmotionLabel
                    if label is not EmotionLabel.NEUTRAL
                    and score_by_label[label] >= self.threshold
                ),
                key=lambda label: (-score_by_label[label], label.value),
            )
        )
        expected_dominant = activated[0] if activated else EmotionLabel.NEUTRAL
        expected_secondary = activated[1:] if activated else ()
        if self.dominant_emotion is not expected_dominant:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message=(
                    "The dominant emotion must be the highest compact emotion at "
                    "or above threshold, or neutral when none qualifies."
                ),
            )
        if self.secondary_emotions != expected_secondary:
            raise InvalidProviderOutputError(
                provider=self.provider.provider,
                message=(
                    "Secondary emotions must contain the remaining above-threshold "
                    "compact emotions in descending score order."
                ),
            )


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """Normalized provider outputs tied to one normalized input record."""

    record: NormalizedTextInput
    sentiment: SentimentResult
    emotion: EmotionResult

    def __post_init__(self) -> None:
        expected = self.record.record_id
        if self.sentiment.record_id != expected or self.emotion.record_id != expected:
            raise InvalidProviderOutputError(
                provider="analysis-service",
                message="All analysis outputs must reference the input record ID.",
            )
