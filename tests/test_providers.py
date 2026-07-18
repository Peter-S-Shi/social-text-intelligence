"""Tests for stable provider interfaces and deterministic mock providers."""

import unittest

from social_text_intelligence.contracts import (
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
    UnsupportedLanguageError,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
    EmotionProvider,
    SentimentProvider,
)


class ProviderContractTests(unittest.TestCase):
    def test_mocks_implement_runtime_provider_protocols(self) -> None:
        self.assertIsInstance(DeterministicSentimentProvider(), SentimentProvider)
        self.assertIsInstance(DeterministicEmotionProvider(), EmotionProvider)

    def test_sentiment_mock_is_configurable_and_deterministic(self) -> None:
        record = NormalizedTextInput.from_text(
            "A synthetic example.",
            record_id="record-1",
            language="en",
        )
        provider = DeterministicSentimentProvider(SentimentLabel.POSITIVE)

        first = provider.analyze(record)
        second = provider.analyze(record)

        self.assertEqual(first, second)
        self.assertEqual(first.label, SentimentLabel.POSITIVE)

    def test_emotion_mock_preserves_multiple_scores(self) -> None:
        record = NormalizedTextInput.from_text(
            "Another synthetic example.",
            record_id="record-2",
        )
        result = DeterministicEmotionProvider(EmotionLabel.GRATITUDE).analyze(record)

        self.assertEqual(result.dominant_emotion, EmotionLabel.GRATITUDE)
        self.assertEqual(len(result.scores), len(EmotionLabel))
        self.assertEqual(result.secondary_emotions, (EmotionLabel.JOY,))

    def test_mock_rejects_unsupported_language(self) -> None:
        record = NormalizedTextInput.from_text(
            "Texte synthétique.",
            record_id="record-3",
            language="fr",
        )

        with self.assertRaises(UnsupportedLanguageError):
            DeterministicSentimentProvider().analyze(record)


if __name__ == "__main__":
    unittest.main()
