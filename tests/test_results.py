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
                scores=(EmotionScore(EmotionLabel.NEUTRAL, 1.0),),
                native_scores=(NativeScore("neutral", 1.0),),
                provider=sentiment_metadata(),
            )

    def test_rejects_dominant_emotion_with_lower_score(self) -> None:
        emotion_metadata = ProviderMetadata(
            provider="test-provider",
            model_name="test-emotion",
            revision="test-v1",
            task=TaskType.EMOTION,
            supported_languages=("en",),
            native_labels=("joy", "neutral"),
        )

        with self.assertRaises(InvalidProviderOutputError):
            EmotionResult(
                record_id="record-1",
                dominant_emotion=EmotionLabel.JOY,
                scores=(
                    EmotionScore(EmotionLabel.JOY, 0.2),
                    EmotionScore(EmotionLabel.NEUTRAL, 0.8),
                ),
                native_scores=(
                    NativeScore("joy", 0.2),
                    NativeScore("neutral", 0.8),
                ),
                provider=emotion_metadata,
            )


if __name__ == "__main__":
    unittest.main()
