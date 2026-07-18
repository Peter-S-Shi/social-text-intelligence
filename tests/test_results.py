"""Tests for normalized sentiment and emotion result contracts."""

import unittest

from social_text_intelligence.contracts import (
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    InvalidProviderOutputError,
    NativeScore,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    TaskType,
    ValidationError,
)


def sentiment_metadata() -> ProviderMetadata:
    return ProviderMetadata(
        provider="test-provider",
        model_name="test-sentiment",
        revision="test-v1",
        task=TaskType.SENTIMENT,
        supported_languages=("en",),
        native_labels=("POS", "NEG", "NEU"),
    )


def emotion_metadata() -> ProviderMetadata:
    return ProviderMetadata(
        provider="test-provider",
        model_name="test-emotion",
        revision="test-v1",
        task=TaskType.EMOTION,
        supported_languages=("en",),
        native_labels=tuple(label.value for label in EmotionLabel),
    )


def emotion_scores(**overrides: float) -> tuple[EmotionScore, ...]:
    return tuple(
        EmotionScore(label, overrides.get(label.value, 0.1))
        for label in EmotionLabel
    )


class ResultContractTests(unittest.TestCase):
    def test_sentiment_preserves_native_and_normalized_scores(self) -> None:
        result = SentimentResult(
            record_id="record-1",
            label=SentimentLabel.POSITIVE,
            confidence=0.9,
            scores=(
                SentimentScore(SentimentLabel.POSITIVE, 0.9),
                SentimentScore(SentimentLabel.NEUTRAL, 0.1),
            ),
            native_scores=(NativeScore("POS", 0.9), NativeScore("NEU", 0.1)),
            provider=sentiment_metadata(),
        )

        self.assertEqual(result.label, SentimentLabel.POSITIVE)
        self.assertEqual(result.native_scores[0].label, "POS")

    def test_rejects_non_finite_scores(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            EmotionScore(EmotionLabel.JOY, float("nan"))

        self.assertEqual(caught.exception.code, "invalid_score")

    def test_rejects_result_with_wrong_provider_task(self) -> None:
        with self.assertRaises(InvalidProviderOutputError):
            EmotionResult(
                record_id="record-1",
                dominant_emotion=EmotionLabel.NEUTRAL,
                confidence=1.0,
                threshold=0.5,
                secondary_emotions=(),
                scores=(EmotionScore(EmotionLabel.NEUTRAL, 1.0),),
                native_scores=(NativeScore("neutral", 1.0),),
                provider=sentiment_metadata(),
            )

    def test_rejects_dominant_emotion_with_lower_score(self) -> None:
        with self.assertRaises(InvalidProviderOutputError):
            EmotionResult(
                record_id="record-1",
                dominant_emotion=EmotionLabel.JOY,
                confidence=0.2,
                threshold=0.5,
                secondary_emotions=(),
                scores=emotion_scores(joy=0.2, neutral=0.8),
                native_scores=tuple(
                    NativeScore(label.value, 0.2 if label is EmotionLabel.JOY else 0.1)
                    for label in EmotionLabel
                ),
                provider=emotion_metadata(),
            )

    def test_preserves_ordered_secondary_emotions_above_threshold(self) -> None:
        scores = emotion_scores(joy=0.9, gratitude=0.8, amusement=0.6, neutral=0.7)
        result = EmotionResult(
            record_id="record-2",
            dominant_emotion=EmotionLabel.JOY,
            confidence=0.9,
            threshold=0.5,
            secondary_emotions=(EmotionLabel.GRATITUDE, EmotionLabel.AMUSEMENT),
            scores=scores,
            native_scores=tuple(
                NativeScore(item.label.value, item.score) for item in scores
            ),
            provider=emotion_metadata(),
        )

        self.assertEqual(
            result.secondary_emotions,
            (EmotionLabel.GRATITUDE, EmotionLabel.AMUSEMENT),
        )

    def test_neutral_means_no_compact_non_neutral_score_reached_threshold(self) -> None:
        scores = emotion_scores(neutral=0.3)
        result = EmotionResult(
            record_id="record-3",
            dominant_emotion=EmotionLabel.NEUTRAL,
            confidence=0.3,
            threshold=0.5,
            secondary_emotions=(),
            scores=scores,
            native_scores=tuple(
                NativeScore(item.label.value, item.score) for item in scores
            ),
            provider=emotion_metadata(),
        )

        self.assertEqual(result.dominant_emotion, EmotionLabel.NEUTRAL)


if __name__ == "__main__":
    unittest.main()
