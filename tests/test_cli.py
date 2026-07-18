"""Tests for the local command-line diagnostics."""

import io
import unittest
from contextlib import redirect_stdout

from social_text_intelligence.cli import main


class CliTests(unittest.TestCase):
    def test_about_reports_scope_without_claiming_analysis(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["about"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Milestone: 2", output.getvalue())
        self.assertIn("Analysis contracts available: yes", output.getvalue())
        self.assertIn("Model inference available: no", output.getvalue())

    def test_contracts_lists_normalized_taxonomies(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["contracts"])

        self.assertEqual(exit_code, 0)
        self.assertIn("positive, negative, neutral", output.getvalue())
        self.assertIn("joy", output.getvalue())
        self.assertIn("deterministic mocks only", output.getvalue())

    def test_no_command_prints_help(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
