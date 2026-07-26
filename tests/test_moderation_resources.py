"""Versioned synthetic moderation resource tests."""

import unittest

from social_text_intelligence.contracts import (
    ReferenceProvenance,
    ViolationCategory,
)
from social_text_intelligence.services import (
    audit_fixture_coverage,
    load_moderation_cases,
    load_moderation_policy,
)


class ModerationResourceTests(unittest.TestCase):
    def test_policy_and_fixture_provenance_and_coverage_are_complete(
        self,
    ) -> None:
        policy = load_moderation_policy()
        cases = load_moderation_cases(policy)
        coverage = audit_fixture_coverage(cases)

        self.assertEqual(policy.policy_version, "1.0.0")
        self.assertEqual(coverage.case_count, 20)
        self.assertEqual(
            coverage.categories,
            frozenset(ViolationCategory)
            - {ViolationCategory.NO_VIOLATION},
        )
        self.assertGreater(coverage.acceptable_alternative_cases, 0)
        self.assertGreater(coverage.ai_available_cases, 0)
        self.assertGreater(coverage.ai_unavailable_cases, 0)
        self.assertTrue(
            all(
                case.reference is not None
                and case.reference.provenance
                is ReferenceProvenance.BUILT_IN
                for case in cases
            )
        )

    def test_fixture_cases_are_synthetic_and_policy_versioned(self) -> None:
        policy = load_moderation_policy()
        cases = load_moderation_cases(policy)
        self.assertEqual(len({case.case_id for case in cases}), len(cases))
        self.assertTrue(
            all(
                case.policy_id == policy.policy_id
                and case.policy_version == policy.policy_version
                and case.source_snapshot is None
                for case in cases
            )
        )


if __name__ == "__main__":
    unittest.main()
