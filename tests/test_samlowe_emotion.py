"""Fast tests for compact emotion mapping without model downloads."""

import math
import unittest

from social_text_intelligence.contracts import (
    EmotionLabel,
    InvalidProviderOutputError,
    ModelInputTooLongError,
    NormalizedTextInput,
    UnsupportedLanguageError,
    ValidationError,
)
from social_text_intelligence.providers import (
    EMOTION_MODEL_ID,
    EMOTION_MODEL_REVISION,
    NATIVE_EMOTION_LABELS,
    EmotionProvider,
    SamLoweEmotionProvider,
)


class StubEmotionRuntime:
    def __init__(self, probabilities: tuple[float, ...]) -> None:
        self.probabilities = probabilities
        self.received_text: str | None = None

    def predict(self, text: str) -> tuple[float, ...]:
        self.received_text = text
        return self.probabilities

    def validate_input(self, text: str) -> None:
        self.received_text = text


class RejectingEmotionRuntime(StubEmotionRuntime):
    def validate_input(self, text: str) -> None:
        raise ModelInputTooLongError(
            provider="samlowe-transformers",
            encoded_length=513,
            max_input_tokens=512,
        )

    def predict(self, text: str) -> tuple[float, ...]:
        self.validate_input(text)
        return super().predict(text)


def probabilities(**overrides: float) -> tuple[float, ...]:
    return tuple(overrides.get(label, 0.01) for label in NATIVE_EMOTION_LABELS)


class SamLoweEmotionProviderTests(unittest.TestCase):
    def test_maps_multi_label_output_and_preserves_all_native_scores(self) -> None:
        runtime = StubEmotionRuntime(
            probabilities(love=0.82, gratitude=0.75, amusement=0.60, neutral=0.40)
        )
        provider = SamLoweEmotionProvider(runtime=runtime)
        record = NormalizedTextInput.from_text(
            "A synthetic mixed-emotion example.",
            record_id="record-1",
            language="en-CA",
        )

        result = provider.analyze(record)

        self.assertIsInstance(provider, EmotionProvider)
        self.assertEqual(result.dominant_emotion, EmotionLabel.JOY)
        self.assertEqual(
            result.secondary_emotions,
            (EmotionLabel.GRATITUDE, EmotionLabel.AMUSEMENT),
        )
        self.assertEqual(len(result.native_scores), len(NATIVE_EMOTION_LABELS))
        self.assertEqual(result.provider.model_name, EMOTION_MODEL_ID)
        self.assertEqual(result.provider.revision, EMOTION_MODEL_REVISION)
        self.assertEqual(runtime.received_text, record.text)

    def test_uses_max_native_score_when_labels_share_compact_category(self) -> None:
        provider = SamLoweEmotionProvider(
            runtime=StubEmotionRuntime(probabilities(anger=0.60, annoyance=0.81))
        )
        record = NormalizedTextInput.from_text(
            "A synthetic mapping example.",
            record_id="record-2",
            language="en",
        )

        result = provider.analyze(record)
        score_by_label = {item.label: item.score for item in result.scores}

        self.assertEqual(result.dominant_emotion, EmotionLabel.ANGER)
        self.assertEqual(score_by_label[EmotionLabel.ANGER], 0.81)

    def test_unmapped_cognitive_label_does_not_become_neutral_score(self) -> None:
        provider = SamLoweEmotionProvider(
            runtime=StubEmotionRuntime(probabilities(curiosity=0.90, neutral=0.20))
        )
        record = NormalizedTextInput.from_text(
            "A synthetic curiosity example.",
            record_id="record-3",
            language="en",
        )

        result = provider.analyze(record)
        native_by_label = {item.label: item.score for item in result.native_scores}

        self.assertEqual(result.dominant_emotion, EmotionLabel.NEUTRAL)
        self.assertEqual(result.confidence, 0.20)
        self.assertEqual(native_by_label["curiosity"], 0.90)

    def test_rejects_unsupported_language_before_runtime_call(self) -> None:
        runtime = StubEmotionRuntime(probabilities(neutral=0.9))
        provider = SamLoweEmotionProvider(runtime=runtime)
        record = NormalizedTextInput.from_text(
            "Phrase synthétique.",
            record_id="record-4",
            language="fr",
        )

        with self.assertRaises(UnsupportedLanguageError):
            provider.analyze(record)

        self.assertIsNone(runtime.received_text)

    def test_rejects_invalid_threshold_or_runtime_output(self) -> None:
        with self.assertRaises(ValidationError):
            SamLoweEmotionProvider(threshold=0.0)

        record = NormalizedTextInput.from_text(
            "A synthetic invalid-output example.",
            record_id="record-5",
            language="en",
        )
        invalid_outputs = (
            (0.1, 0.2),
            tuple(math.nan if index == 0 else 0.1 for index in range(28)),
        )
        for output in invalid_outputs:
            with self.subTest(output_length=len(output)):
                provider = SamLoweEmotionProvider(runtime=StubEmotionRuntime(output))
                with self.assertRaises(InvalidProviderOutputError):
                    provider.analyze(record)

    def test_standalone_provider_rejects_incomplete_model_input(self) -> None:
        provider = SamLoweEmotionProvider(
            runtime=RejectingEmotionRuntime(probabilities(neutral=0.9))
        )
        record = NormalizedTextInput.from_text("synthetic " * 300, language="en")

        with self.assertRaisesRegex(
            ModelInputTooLongError, "No truncation or partial analysis"
        ):
            provider.analyze(record)


if __name__ == "__main__":
    unittest.main()
