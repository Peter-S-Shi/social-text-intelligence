"""Fast tests for normalized Cardiff sentiment mapping without model downloads."""

import math
import unittest

from social_text_intelligence.contracts import (
    InvalidProviderOutputError,
    NormalizedTextInput,
    SentimentLabel,
    UnsupportedLanguageError,
)
from social_text_intelligence.providers import (
    MODEL_ID,
    MODEL_REVISION,
    CardiffSentimentProvider,
    SentimentProvider,
    preprocess_social_text,
)


class StubRuntime:
    def __init__(self, probabilities: tuple[float, ...]) -> None:
        self.probabilities = probabilities
        self.received_text: str | None = None

    def predict(self, text: str) -> tuple[float, ...]:
        self.received_text = text
        return self.probabilities


class CardiffSentimentProviderTests(unittest.TestCase):
    def test_provider_implements_protocol_and_maps_all_native_labels(self) -> None:
        runtime = StubRuntime((0.05, 0.15, 0.80))
        provider = CardiffSentimentProvider(runtime=runtime)
        record = NormalizedTextInput.from_text(
            "A synthetic success case.",
            record_id="record-1",
            language="en-CA",
        )

        result = provider.analyze(record)

        self.assertIsInstance(provider, SentimentProvider)
        self.assertEqual(result.label, SentimentLabel.POSITIVE)
        self.assertEqual(result.confidence, 0.80)
        self.assertEqual(
            {item.label: item.score for item in result.scores},
            {
                SentimentLabel.NEGATIVE: 0.05,
                SentimentLabel.NEUTRAL: 0.15,
                SentimentLabel.POSITIVE: 0.80,
            },
        )
        self.assertEqual(result.provider.model_name, MODEL_ID)
        self.assertEqual(result.provider.revision, MODEL_REVISION)

    def test_model_specific_preprocessing_replaces_usernames_and_urls(self) -> None:
        runtime = StubRuntime((0.1, 0.8, 0.1))
        provider = CardiffSentimentProvider(runtime=runtime)
        record = NormalizedTextInput.from_text(
            "Thanks @sample for https://example.invalid/path",
            record_id="record-2",
            language="en",
        )

        result = provider.analyze(record)

        self.assertEqual(result.label, SentimentLabel.NEUTRAL)
        self.assertEqual(runtime.received_text, "Thanks @user for http")
        self.assertEqual(
            preprocess_social_text("Contact @one or mail@example.invalid"),
            "Contact @user or mail@example.invalid",
        )

    def test_rejects_unsupported_language_before_runtime_call(self) -> None:
        runtime = StubRuntime((0.1, 0.8, 0.1))
        provider = CardiffSentimentProvider(runtime=runtime)
        record = NormalizedTextInput.from_text(
            "Phrase synthétique.",
            record_id="record-3",
            language="fr",
        )

        with self.assertRaises(UnsupportedLanguageError):
            provider.analyze(record)

        self.assertIsNone(runtime.received_text)

    def test_rejects_missing_or_invalid_probability_output(self) -> None:
        record = NormalizedTextInput.from_text(
            "A synthetic invalid output case.",
            record_id="record-4",
            language="en",
        )
        invalid_outputs = (
            (0.5, 0.5),
            (0.2, 0.2, 0.2),
            (math.nan, 0.5, 0.5),
        )

        for probabilities in invalid_outputs:
            with self.subTest(probabilities=probabilities):
                provider = CardiffSentimentProvider(
                    runtime=StubRuntime(probabilities)
                )
                with self.assertRaises(InvalidProviderOutputError):
                    provider.analyze(record)


if __name__ == "__main__":
    unittest.main()
