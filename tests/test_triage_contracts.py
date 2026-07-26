"""Support triage enum, structural, warning, and lifecycle contracts."""

import unittest
from datetime import UTC, datetime

from social_text_intelligence.contracts import (
    FinalizedTriageDecision,
    IssueCategory,
    NextAction,
    RecommendedQueue,
    SupportIntent,
    TriageFields,
    TriageGuidanceWarning,
    TriageUrgency,
    ValidationError,
    triage_guidance_warnings,
    validate_final_fields,
)


def complete_fields(**overrides: object) -> TriageFields:
    values: dict[str, object] = {
        "primary_intent": SupportIntent.REQUEST_INFORMATION,
        "issue_category": IssueCategory.POLICY_OR_ELIGIBILITY_QUESTION,
        "urgency": TriageUrgency.NORMAL,
        "recommended_queue": RecommendedQueue.GENERAL_SUPPORT,
        "primary_next_action": NextAction.PROVIDE_POLICY_OR_ELIGIBILITY_INFORMATION,
    }
    values.update(overrides)
    return TriageFields(**values)  # type: ignore[arg-type]


class TriageContractTests(unittest.TestCase):
    def test_frozen_taxonomies_have_expected_sizes(self) -> None:
        self.assertEqual(len(SupportIntent), 15)
        self.assertEqual(len(IssueCategory), 11)
        self.assertEqual(len(TriageUrgency), 5)
        self.assertEqual(len(RecommendedQueue), 10)
        self.assertEqual(len(NextAction), 10)

    def test_incomplete_draft_is_legal_but_illegal_collections_are_not(
        self,
    ) -> None:
        self.assertIsNone(TriageFields().primary_intent)
        with self.assertRaisesRegex(ValidationError, "at most two"):
            TriageFields(
                secondary_intents=(
                    SupportIntent.REQUEST_INFORMATION,
                    SupportIntent.PROVIDE_FEEDBACK,
                    SupportIntent.REQUEST_FEATURE,
                )
            )
        with self.assertRaisesRegex(ValidationError, "cannot also be secondary"):
            TriageFields(
                primary_intent=SupportIntent.REQUEST_INFORMATION,
                secondary_intents=(SupportIntent.REQUEST_INFORMATION,),
            )

    def test_final_structural_requirements_and_warning_notes_are_separate(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValidationError, "primary_intent"):
            validate_final_fields(TriageFields())
        unusual = complete_fields(
            urgency=TriageUrgency.CRITICAL,
            escalation_required=False,
        )
        self.assertEqual(
            triage_guidance_warnings(unusual),
            (TriageGuidanceWarning.CRITICAL_WITHOUT_ESCALATION,),
        )
        with self.assertRaisesRegex(ValidationError, "Human notes"):
            validate_final_fields(unusual)
        retained = complete_fields(
            urgency=TriageUrgency.CRITICAL,
            escalation_required=False,
            human_notes="Human retains this unusual synthetic decision.",
        )
        self.assertEqual(
            validate_final_fields(retained),
            (TriageGuidanceWarning.CRITICAL_WITHOUT_ESCALATION,),
        )

    def test_finalized_decision_requires_matching_warnings_and_utc(self) -> None:
        fields = complete_fields()
        decision = FinalizedTriageDecision(
            fields=fields,
            warnings=(),
            guide_id="synthetic-guide",
            guide_version="1.0.0",
            applicable_rule_ids=("RULE-001",),
            finalized_at=datetime(2026, 7, 26, tzinfo=UTC),
            mock_visible_before_first_submission=False,
        )
        self.assertEqual(decision.finalized_at.utcoffset(), UTC.utcoffset(None))
        with self.assertRaisesRegex(ValidationError, "timezone-aware UTC"):
            FinalizedTriageDecision(
                fields=fields,
                warnings=(),
                guide_id="synthetic-guide",
                guide_version="1.0.0",
                applicable_rule_ids=("RULE-001",),
                finalized_at=datetime(2026, 7, 26),
                mock_visible_before_first_submission=False,
            )


if __name__ == "__main__":
    unittest.main()
