"""Deterministic providers for fast tests; these are not NLP models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.errors import UnsupportedLanguageError
from ..contracts.inputs import NormalizedTextInput
from ..contracts.results import (
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    NativeScore,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    TaskType,
)


def _supports_language(metadata: ProviderMetadata, language: str | None) -> bool:
    if language is None:
        return True
    primary = language.split("-", maxsplit=1)[0].lower()
    return primary in {item.lower() for item in metadata.supported_languages}


@dataclass(frozen=True, slots=True)
class DeterministicSentimentProvider:
    """Return configured, repeatable sentiment output for orchestration tests."""

    selected_label: SentimentLabel = SentimentLabel.NEUTRAL
    metadata: ProviderMetadata = field(
        default_factory=lambda: ProviderMetadata(
            provider="built-in-mock",
            model_name="deterministic-sentiment",
            revision="mock-v1",
            task=TaskType.SENTIMENT,
            supported_languages=("en",),
            native_labels=("positive", "negative", "neutral"),
        )
    )

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        if not _supports_language(self.metadata, record.language):
            raise UnsupportedLanguageError(
                provider=self.metadata.provider,
                language=record.language or "unknown",
            )
        scores = tuple(
            SentimentScore(
                label=label,
                score=0.8 if label is self.selected_label else 0.1,
            )
            for label in SentimentLabel
        )
        return SentimentResult(
            record_id=record.record_id,
            label=self.selected_label,
            confidence=0.8,
            scores=scores,
            native_scores=tuple(
                NativeScore(label=item.label.value, score=item.score) for item in scores
            ),
            provider=self.metadata,
        )


@dataclass(frozen=True, slots=True)
class DeterministicEmotionProvider:
    """Return configured, repeatable multi-label output for orchestration tests."""

    dominant_emotion: EmotionLabel = EmotionLabel.NEUTRAL
    metadata: ProviderMetadata = field(
        default_factory=lambda: ProviderMetadata(
            provider="built-in-mock",
            model_name="deterministic-emotion",
            revision="mock-v1",
            task=TaskType.EMOTION,
            supported_languages=("en",),
            native_labels=tuple(label.value for label in EmotionLabel),
        )
    )

    def analyze(self, record: NormalizedTextInput) -> EmotionResult:
        if not _supports_language(self.metadata, record.language):
            raise UnsupportedLanguageError(
                provider=self.metadata.provider,
                language=record.language or "unknown",
            )
        secondary = (
            EmotionLabel.JOY
            if self.dominant_emotion is not EmotionLabel.JOY
            else EmotionLabel.GRATITUDE
        )
        threshold = 0.5
        scores = tuple(
            EmotionScore(
                label,
                0.8
                if label is self.dominant_emotion
                else 0.6
                if self.dominant_emotion is not EmotionLabel.NEUTRAL
                and label is secondary
                else 0.1,
            )
            for label in EmotionLabel
        )
        secondary_emotions = (
            (secondary,) if self.dominant_emotion is not EmotionLabel.NEUTRAL else ()
        )
        return EmotionResult(
            record_id=record.record_id,
            dominant_emotion=self.dominant_emotion,
            confidence=0.8,
            threshold=threshold,
            secondary_emotions=secondary_emotions,
            scores=scores,
            native_scores=tuple(
                NativeScore(label=item.label.value, score=item.score) for item in scores
            ),
            provider=self.metadata,
        )
