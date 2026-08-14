"""Tests for the local command-line diagnostics."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from social_text_intelligence.cli import main
from social_text_intelligence.contracts import (
    EmotionLabel,
    ModelInputTooLongError,
    NormalizedTextInput,
    SentimentLabel,
    SentimentResult,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)


class CliTests(unittest.TestCase):
    def test_about_reports_current_scope_and_release_gate(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["about"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Milestone: 10", output.getvalue())
        self.assertIn("Analysis contracts available: yes", output.getvalue())
        self.assertIn("Local sentiment inference available: yes", output.getvalue())
        self.assertIn("Local emotion inference available: yes", output.getvalue())
        self.assertIn("Combined single-text report available: yes", output.getvalue())
        self.assertIn("Local Flask interface available: yes", output.getvalue())
        self.assertIn("CSV batch preview", output.getvalue())
        self.assertIn("Temporary human review", output.getvalue())
        self.assertIn("Temporary local insights", output.getvalue())
        self.assertIn("Synthetic moderation training", output.getvalue())
        self.assertIn("Local Support Triage", output.getvalue())
        self.assertIn("feature freeze and release review pending", output.getvalue())

    def test_contracts_lists_normalized_taxonomies(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["contracts"])

        self.assertEqual(exit_code, 0)
        self.assertIn("positive, negative, neutral", output.getvalue())
        self.assertIn("joy", output.getvalue())
        self.assertIn("licensed local model available", output.getvalue())
        self.assertIn("licensed local multi-label model", output.getvalue())

    def test_sentiment_reports_normalized_result_without_echoing_text(self) -> None:
        output = io.StringIO()
        provider = DeterministicSentimentProvider(SentimentLabel.POSITIVE)

        with (
            patch(
                "social_text_intelligence.cli.CardiffSentimentProvider",
                return_value=provider,
            ),
            redirect_stdout(output),
        ):
            exit_code = main(["sentiment", "A private synthetic input."])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Sentiment: positive", rendered)
        self.assertIn("Estimate only", rendered)
        self.assertNotIn("A private synthetic input", rendered)

    def test_analyze_reports_combined_result_without_echoing_text(self) -> None:
        output = io.StringIO()
        sentiment_provider = DeterministicSentimentProvider(SentimentLabel.POSITIVE)
        emotion_provider = DeterministicEmotionProvider(EmotionLabel.GRATITUDE)

        with (
            patch(
                "social_text_intelligence.cli.CardiffSentimentProvider",
                return_value=sentiment_provider,
            ),
            patch(
                "social_text_intelligence.cli.SamLoweEmotionProvider",
                return_value=emotion_provider,
            ),
            redirect_stdout(output),
        ):
            exit_code = main(["analyze", "A private combined synthetic input."])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Sentiment: positive", rendered)
        self.assertIn("Dominant emotion: gratitude", rendered)
        self.assertIn("Secondary emotions: joy=", rendered)
        self.assertIn("not psychological diagnoses", rendered)
        self.assertNotIn("A private combined synthetic input", rendered)

    def test_no_command_prints_help(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", output.getvalue())

    def test_sentiment_and_combined_commands_reject_partial_analysis(self) -> None:
        class RejectingSentimentProvider(DeterministicSentimentProvider):
            def analyze(self, record: NormalizedTextInput) -> SentimentResult:
                raise ModelInputTooLongError(
                    provider="synthetic-sentiment",
                    encoded_length=513,
                    max_input_tokens=512,
                )

            def validate_input(self, record: NormalizedTextInput) -> None:
                raise ModelInputTooLongError(
                    provider="synthetic-sentiment",
                    encoded_length=513,
                    max_input_tokens=512,
                )

        for command in ("sentiment", "analyze"):
            with self.subTest(command=command):
                errors = io.StringIO()
                with (
                    patch(
                        "social_text_intelligence.cli.CardiffSentimentProvider",
                        return_value=RejectingSentimentProvider(),
                    ),
                    patch(
                        "social_text_intelligence.cli.SamLoweEmotionProvider",
                        return_value=DeterministicEmotionProvider(),
                    ),
                    redirect_stderr(errors),
                    self.assertRaises(SystemExit) as raised,
                ):
                    main([command, "synthetic input"])

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("No truncation or partial analysis", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
