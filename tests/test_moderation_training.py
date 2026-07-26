"""Moderation session, comparison, limit, and export service tests."""

import csv
import io
import unittest
from datetime import UTC, datetime

from social_text_intelligence.contracts import (
    CaseOrderMode,
    ComparisonState,
    EscalationReason,
    FeedbackTiming,
    ModerationDisposition,
    ModerationJudgment,
    ModerationSeverity,
    TraineeDecision,
    TrainingMode,
    ValidationError,
    ViolationCategory,
)
from social_text_intelligence.services import (
    ModerationLimits,
    ModerationWorkspace,
    cancel_session,
    compare_attempt,
    export_moderation_session_csv,
    load_moderation_cases,
    mark_feedback_viewed,
    restart_session,
    revise_final_decision,
    start_training_session,
    submit_first_decision,
)


def decision(
    judgment: ModerationJudgment,
    *,
    reasoning: str = "A synthetic reason.",
    note: str = "A synthetic reviewer note.",
) -> TraineeDecision:
    return TraineeDecision.create(
        judgment, reasoning=reasoning, reviewer_note=note
    )


class ModerationTrainingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = load_moderation_cases()
        self.limits = ModerationLimits()

    def start(
        self,
        *,
        case_id: str | None = None,
        feedback: FeedbackTiming = FeedbackTiming.IMMEDIATE,
        limits: ModerationLimits | None = None,
    ) -> ModerationWorkspace:
        selected = case_id or self.cases[0].case_id
        return start_training_session(
            ModerationWorkspace(),
            self.cases,
            case_ids=(selected,),
            case_count=1,
            mode=TrainingMode.INDEPENDENT,
            feedback_timing=feedback,
            order_mode=CaseOrderMode.ORIGINAL_ORDER,
            content_notice_confirmed=True,
            limits=limits or self.limits,
            session_id_factory=lambda: "session-1",
            now=lambda: datetime(2026, 7, 25, tzinfo=UTC),
        )

    def test_first_decision_is_immutable_and_revision_is_separate(self) -> None:
        workspace = self.start()
        session = workspace.sessions[0]
        case = session.cases[0]
        first = decision(case.frozen_reference.preferred)  # type: ignore[union-attr]
        submitted = submit_first_decision(
            workspace,
            session_id=session.session_id,
            case_id=case.case.case_id,
            decision=first,
        )
        with self.assertRaisesRegex(ValidationError, "already submitted"):
            submit_first_decision(
                submitted,
                session_id=session.session_id,
                case_id=case.case.case_id,
                decision=first,
            )
        viewed = mark_feedback_viewed(
            submitted,
            session_id=session.session_id,
            case_id=case.case.case_id,
        )
        revised_judgment = ModerationJudgment(
            disposition=ModerationDisposition.ALLOW,
            primary_violation=ViolationCategory.HARASSMENT_ABUSE,
            secondary_violations=(),
            severity=ModerationSeverity.CRITICAL,
            escalate=False,
        )
        revised = revise_final_decision(
            viewed,
            session_id=session.session_id,
            case_id=case.case.case_id,
            decision=decision(revised_judgment),
        )
        attempt = revised.sessions[0].attempts[0]
        self.assertEqual(attempt.first_decision, first)
        self.assertEqual(attempt.final_decision.judgment, revised_judgment)
        self.assertEqual(attempt.revision_count, 1)
        comparison = compare_attempt(case, attempt)
        self.assertTrue(comparison.final_guidance_warnings)

    def test_complete_acceptable_alternative_is_scored_separately(self) -> None:
        source_case = next(
            case
            for case in self.cases
            if case.reference
            and case.reference.acceptable_alternatives
        )
        workspace = self.start(case_id=source_case.case_id)
        session = workspace.sessions[0]
        alternative = source_case.reference.acceptable_alternatives[0]  # type: ignore[union-attr]
        submitted = submit_first_decision(
            workspace,
            session_id=session.session_id,
            case_id=source_case.case_id,
            decision=decision(alternative),
        )
        comparison = compare_attempt(
            session.cases[0], submitted.sessions[0].attempts[0]
        )
        self.assertIs(
            comparison.first_overall,
            ComparisonState.ACCEPTABLE_ALTERNATIVE,
        )

    def test_sensitive_notice_and_retained_attempt_limit_block_creation(
        self,
    ) -> None:
        sensitive = next(case for case in self.cases if case.safety_sensitive)
        with self.assertRaisesRegex(ValidationError, "Confirm"):
            start_training_session(
                ModerationWorkspace(),
                self.cases,
                case_ids=(sensitive.case_id,),
                case_count=1,
                mode=TrainingMode.INDEPENDENT,
                feedback_timing=FeedbackTiming.IMMEDIATE,
                order_mode=CaseOrderMode.ORIGINAL_ORDER,
                content_notice_confirmed=False,
                limits=self.limits,
            )
        one_attempt = ModerationLimits(max_session_attempts=1)
        workspace = self.start(limits=one_attempt)
        cancelled = cancel_session(
            workspace, session_id=workspace.sessions[0].session_id
        )
        with self.assertRaisesRegex(
            ValidationError, "retains at most 1"
        ):
            restart_session(
                cancelled,
                session_id=cancelled.sessions[0].session_id,
                limits=one_attempt,
            )
        self.assertEqual(len(cancelled.sessions), 1)

    def test_csv_is_auditable_formula_safe_and_privacy_explicit(self) -> None:
        workspace = self.start()
        session = workspace.sessions[0]
        frozen = session.cases[0]
        judgment = ModerationJudgment(
            disposition=ModerationDisposition.ALLOW,
            primary_violation=ViolationCategory.HARASSMENT_ABUSE,
            secondary_violations=(),
            severity=ModerationSeverity.CRITICAL,
            escalate=True,
            escalation_reason=EscalationReason.CREDIBLE_THREAT,
        )
        submitted = submit_first_decision(
            workspace,
            session_id=session.session_id,
            case_id=frozen.case.case_id,
            decision=decision(
                judgment,
                reasoning="=synthetic formula",
                note="@synthetic note",
            ),
            now=lambda: datetime(2026, 7, 25, 13, tzinfo=UTC),
        )
        content = export_moderation_session_csv(
            submitted.sessions[0],
            include_user_source_text=False,
            include_signals=False,
            include_context_notes=False,
            include_trusted_metadata=False,
            now=lambda: datetime(2026, 7, 25, 14, tzinfo=UTC),
        )
        rows = list(csv.DictReader(io.StringIO(content)))
        metadata = rows[0]
        self.assertEqual(metadata["section"], "export_metadata")
        self.assertRegex(metadata["exported_at"], r"\+00:00$")
        self.assertEqual(metadata["insufficient_sample_below"], "5")
        self.assertEqual(metadata["small_sample_below"], "10")
        self.assertEqual(metadata["case_count"], "1")
        self.assertEqual(metadata["completed_count"], "1")
        self.assertIn(
            "exact preferred or complete acceptable alternative",
            metadata["metric_definitions"],
        )
        self.assertTrue(
            any(row["section"] == "summary_metric" for row in rows)
        )
        self.assertTrue(
            any(row["section"] == "severity_metric" for row in rows)
        )
        case_row = next(
            row for row in rows if row["section"] == "case_result"
        )
        self.assertEqual(
            case_row["trainee_first_reasoning"], "'=synthetic formula"
        )
        self.assertEqual(
            case_row["trainee_first_reviewer_note"], "'@synthetic note"
        )
        self.assertIn(
            "allow_with_violation",
            case_row["trainee_first_guidance_warnings"],
        )
        self.assertTrue(case_row["reference_rationale"])
        self.assertTrue(case_row["mock_ai_rationale"])


if __name__ == "__main__":
    unittest.main()
