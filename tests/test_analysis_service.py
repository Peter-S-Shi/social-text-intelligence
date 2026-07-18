"""Tests for provider-neutral analysis orchestration."""

import unittest

from social_text_intelligence.contracts import NormalizedTextInput
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService


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


if __name__ == "__main__":
    unittest.main()
