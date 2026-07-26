"""Structural validation and non-blocking moderation guidance tests."""

import unittest

from social_text_intelligence.contracts import (
    EscalationReason,
    GuidanceWarning,
    ModerationDisposition,
    ModerationJudgment,
    ModerationSeverity,
    TraineeDecision,
    UnclearReason,
    ValidationError,
    ViolationCategory,
    guidance_warnings,
)
from social_text_intelligence.services import parse_moderation_judgment


def judgment(**overrides: object) -> ModerationJudgment:
    values: dict[str, object] = {
        "disposition": ModerationDisposition.ALLOW,
        "primary_violation": ViolationCategory.NO_VIOLATION,
        "secondary_violations": (),
        "severity": ModerationSeverity.NONE,
        "escalate": False,
    }
    values.update(overrides)
    return ModerationJudgment(**values)  # type: ignore[arg-type]


class ModerationContractTests(unittest.TestCase):
    def test_structural_conflicts_are_rejected(self) -> None:
        invalid = (
            {
                "escalate": True,
            },
            {
                "disposition": ModerationDisposition.UNCLEAR_NEEDS_REVIEW,
            },
            {
                "disposition": ModerationDisposition.WARN,
            },
            {
                "primary_violation": ViolationCategory.HARASSMENT_ABUSE,
                "secondary_violations": (
                    ViolationCategory.NO_VIOLATION,
                ),
                "severity": ModerationSeverity.LOW,
            },
            {
                "primary_violation": ViolationCategory.HARASSMENT_ABUSE,
                "secondary_violations": (
                    ViolationCategory.HARASSMENT_ABUSE,
                ),
                "severity": ModerationSeverity.LOW,
            },
            {
                "escalation_reason": EscalationReason.POLICY_AMBIGUITY,
            },
            {
                "unclear_reasons": (
                    UnclearReason.INSUFFICIENT_CONTEXT,
                ),
            },
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(
                ValidationError
            ):
                judgment(**values)

    def test_guidance_departures_are_retained_without_rewriting(self) -> None:
        submitted = judgment(
            disposition=ModerationDisposition.ALLOW,
            primary_violation=ViolationCategory.HARASSMENT_ABUSE,
            severity=ModerationSeverity.CRITICAL,
        )
        warnings = guidance_warnings(submitted)
        self.assertEqual(
            warnings,
            (
                GuidanceWarning.ALLOW_WITH_VIOLATION,
                GuidanceWarning.CRITICAL_WITHOUT_ESCALATION,
                GuidanceWarning.HIGH_SEVERITY_LIGHT_DISPOSITION,
            ),
        )
        decision = TraineeDecision.create(
            submitted,
            reasoning="Context may justify a non-default disposition.",
            reviewer_note="Retain and review the policy-guidance warning.",
        )
        self.assertIs(decision.judgment, submitted)
        self.assertEqual(decision.guidance_warnings, warnings)

    def test_reasoning_and_reviewer_note_are_structurally_required(self) -> None:
        for reasoning, note in (("", "note"), ("reason", "")):
            with self.subTest(
                reasoning=reasoning, note=note
            ), self.assertRaises(ValidationError):
                TraineeDecision.create(
                    judgment(),
                    reasoning=reasoning,
                    reviewer_note=note,
                )

    def test_illegal_enumeration_is_rejected_at_parse_boundary(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            parse_moderation_judgment(
                disposition="unsupported",
                primary_violation="no_violation",
                secondary_violations=(),
                severity="none",
                escalate=False,
                escalation_reason="",
                unclear_reasons=(),
            )
        self.assertEqual(raised.exception.code, "invalid_choice")


if __name__ == "__main__":
    unittest.main()
