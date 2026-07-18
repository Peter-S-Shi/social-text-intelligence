"""Opt-in smoke test for the immutable sentiment and emotion model revisions."""

import importlib.util
import os
import unittest
from pathlib import Path

from social_text_intelligence.contracts import EmotionLabel, NormalizedTextInput
from social_text_intelligence.providers import (
    NATIVE_EMOTION_LABELS,
    CardiffSentimentProvider,
    SamLoweEmotionProvider,
)
from social_text_intelligence.services import AnalysisService

_MODEL_TESTS_ENABLED = os.environ.get("STI_RUN_MODEL_TESTS") == "1"
_RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(package) is not None
    for package in ("torch", "transformers")
)


@unittest.skipUnless(
    _MODEL_TESTS_ENABLED and _RUNTIME_AVAILABLE,
    "set STI_RUN_MODEL_TESTS=1 and install model extras to run local inference",
)
class CombinedModelIntegrationTests(unittest.TestCase):
    def test_pinned_models_return_one_combined_normalized_report(self) -> None:
        cache_dir = Path(os.environ.get("STI_MODEL_CACHE", "model_cache"))
        offline = os.environ.get("STI_MODEL_OFFLINE") == "1"
        service = AnalysisService(
            sentiment_provider=CardiffSentimentProvider(
                cache_dir=cache_dir,
                offline=offline,
            ),
            emotion_provider=SamLoweEmotionProvider(
                cache_dir=cache_dir,
                offline=offline,
            ),
        )
        record = NormalizedTextInput.from_text(
            "Thank you so much for your wonderful help!",
            record_id="integration-combined-1",
            language="en",
        )

        report = service.analyze(record)

        self.assertEqual(report.record, record)
        self.assertEqual(report.sentiment.record_id, record.record_id)
        self.assertEqual(report.emotion.record_id, record.record_id)
        self.assertEqual(report.emotion.dominant_emotion, EmotionLabel.GRATITUDE)
        self.assertEqual(
            len(report.emotion.native_scores),
            len(NATIVE_EMOTION_LABELS),
        )
        self.assertEqual(len(report.emotion.scores), len(EmotionLabel))


if __name__ == "__main__":
    unittest.main()
