"""Tests for the local command-line diagnostics."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from social_text_intelligence.cli import main
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)


class CliTests(unittest.TestCase):
    def test_about_reports_scope_without_claiming_analysis(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["about"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Milestone: 5", output.getvalue())
        self.assertIn("Analysis contracts available: yes", output.getvalue())
        self.assertIn("Local sentiment inference available: yes", output.getvalue())
        self.assertIn("Local emotion inference available: yes", output.getvalue())
        self.assertIn("Combined single-text report available: yes", output.getvalue())

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


if __name__ == "__main__":
    unittest.main()
