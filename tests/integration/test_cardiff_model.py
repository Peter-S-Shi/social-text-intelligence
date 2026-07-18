"""Opt-in smoke test for the immutable Cardiff model revision."""

import importlib.util
import os
import unittest
from pathlib import Path

from social_text_intelligence.contracts import NormalizedTextInput, SentimentLabel
from social_text_intelligence.providers import CardiffSentimentProvider

_MODEL_TESTS_ENABLED = os.environ.get("STI_RUN_MODEL_TESTS") == "1"
_RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(package) is not None
    for package in ("torch", "transformers")
)


@unittest.skipUnless(
    _MODEL_TESTS_ENABLED and _RUNTIME_AVAILABLE,
    "set STI_RUN_MODEL_TESTS=1 and install .[sentiment] to run model inference",
)
class CardiffModelIntegrationTests(unittest.TestCase):
    def test_pinned_model_returns_normalized_positive_prediction(self) -> None:
        record = NormalizedTextInput.from_text(
            "I am delighted that this synthetic test works so reliably!",
            record_id="integration-record-1",
            language="en",
        )
        provider = CardiffSentimentProvider(
            cache_dir=Path(os.environ.get("STI_MODEL_CACHE", "model_cache")),
            offline=os.environ.get("STI_MODEL_OFFLINE") == "1",
        )

        result = provider.analyze(record)

        self.assertEqual(result.label, SentimentLabel.POSITIVE)
        self.assertEqual(len(result.scores), 3)
        self.assertAlmostEqual(sum(item.score for item in result.scores), 1.0, places=4)
        self.assertEqual(result.confidence, max(item.score for item in result.scores))


if __name__ == "__main__":
    unittest.main()
