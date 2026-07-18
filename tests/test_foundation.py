"""Tests for the dependency-free project status."""

import unittest

from social_text_intelligence.foundation import PROJECT_STATUS, ProjectStatus


class ProjectStatusTests(unittest.TestCase):
    def test_status_is_immutable_and_marks_milestone_four(self) -> None:
        self.assertIsInstance(PROJECT_STATUS, ProjectStatus)
        self.assertEqual(PROJECT_STATUS.milestone, 4)
        self.assertTrue(PROJECT_STATUS.local_first)
        self.assertTrue(PROJECT_STATUS.analysis_contracts_available)
        self.assertTrue(PROJECT_STATUS.model_inference_available)


if __name__ == "__main__":
    unittest.main()
