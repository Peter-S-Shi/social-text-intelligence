"""Tests for provider-neutral analysis orchestration."""

import unittest

from social_text_intelligence.contracts import (
    ModelInputTooLongError,
    NormalizedTextInput,
    SentimentResult,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, SentimentAnalysisService


class AnalysisServiceTests(unittest.TestCase):
    def test_combines_results_for_the_same_record(self) -> None:
        record = NormalizedTextInput.from_text(
            "A project-authored synthetic sentence.",
            record_id="record-1",
            language="en",
        )
        service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(),
            emotion_provider=DeterministicEmotionProvider(),
        )

        report = service.analyze(record)

        self.assertEqual(report.record, record)
        self.assertEqual(report.sentiment.record_id, record.record_id)
        self.assertEqual(report.emotion.record_id, record.record_id)

    def test_sentiment_service_does_not_require_emotion_provider(self) -> None:
        record = NormalizedTextInput.from_text(
            "A single project-authored text.",
            record_id="record-2",
            language="en",
        )
        service = SentimentAnalysisService(DeterministicSentimentProvider())

        result = service.analyze(record)

        self.assertEqual(result.record_id, record.record_id)

    def test_combined_preflight_rejects_before_either_provider_analyzes(self) -> None:
        sentiment = DeterministicSentimentProvider()

        class RejectingEmotionProvider(DeterministicEmotionProvider):
            def validate_input(self, record: NormalizedTextInput) -> None:
                raise ModelInputTooLongError(
                    provider="synthetic-emotion",
                    encoded_length=513,
                    max_input_tokens=512,
                )

        class RecordingSentimentProvider(DeterministicSentimentProvider):
            analyzed = False

            def analyze(self, record: NormalizedTextInput) -> SentimentResult:
                self.analyzed = True
                return sentiment.analyze(record)

        recording_sentiment = RecordingSentimentProvider()
        service = AnalysisService(recording_sentiment, RejectingEmotionProvider())
        record = NormalizedTextInput.from_text("synthetic " * 300, language="en")

        with self.assertRaises(ModelInputTooLongError):
            service.analyze(record)

        self.assertFalse(recording_sentiment.analyzed)


if __name__ == "__main__":
    unittest.main()
