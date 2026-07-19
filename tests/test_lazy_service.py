"""Tests for one-time, reusable analysis-service construction."""

import unittest

from social_text_intelligence.contracts import NormalizedTextInput
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, LazyAnalysisService


class LazyAnalysisServiceTests(unittest.TestCase):
    def test_builds_models_once_and_reuses_service(self) -> None:
        calls = 0

        def factory() -> AnalysisService:
            nonlocal calls
            calls += 1
            return AnalysisService(
                sentiment_provider=DeterministicSentimentProvider(),
                emotion_provider=DeterministicEmotionProvider(),
            )

        gateway = LazyAnalysisService(factory)
        self.assertFalse(gateway.initialized)

        for record_id in ("first", "second"):
            gateway.analyze(
                NormalizedTextInput.from_text(
                    "A project-authored synthetic message.",
                    record_id=record_id,
                    language="en",
                )
            )

        self.assertTrue(gateway.initialized)
        self.assertEqual(calls, 1)
