"""Support triage preparation, lifecycle, summary, limits, and export tests."""

import csv
import io
import unittest
from dataclasses import replace
from datetime import UTC, datetime

from social_text_intelligence.contracts import (
    IssueCategory,
    NextAction,
    RecommendedQueue,
    SupportIntent,
    TicketComplexity,
    TriageFields,
    TriageMode,
    TriageUrgency,
    ValidationError,
)
from social_text_intelligence.contracts.errors import ProviderError
from social_text_intelligence.contracts.inputs import NormalizedTextInput
from social_text_intelligence.contracts.results import AnalysisReport
from social_text_intelligence.services import (
    TriageLimits,
    add_synthetic_tickets,
    analyze_batch,
    export_triage_csv,
    finalize_ticket,
    inspect_csv_upload,
    load_support_tickets,
    load_triage_guide,
    new_triage_workspace,
    prepare_csv_batch,
    prepare_workspace_ticket,
    revise_ticket,
    save_triage_draft,
    summarize_triage,
)


def fields(**overrides: object) -> TriageFields:
    values: dict[str, object] = {
        "primary_intent": SupportIntent.RECOVER_ACCOUNT_ACCESS,
        "issue_category": IssueCategory.ACCOUNT_AND_ACCESS,
        "urgency": TriageUrgency.HIGH,
        "recommended_queue": RecommendedQueue.ACCOUNT_AND_ACCESS,
        "primary_next_action": NextAction.VERIFY_IDENTITY_OR_ACCOUNT_OWNERSHIP,
    }
    values.update(overrides)
    return TriageFields(**values)  # type: ignore[arg-type]


class FailingAnalyzer:
    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        raise ProviderError(
            provider="synthetic-failing-provider",
            code="model_load_failed",
            message="Synthetic failure.",
        )


class SupportTriageServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guide = load_triage_guide()
        self.tickets = load_support_tickets(self.guide)

    def test_limit_blocks_without_silent_eviction(self) -> None:
        workspace = new_triage_workspace(mode=TriageMode.INDEPENDENT)
        one = add_synthetic_tickets(
            workspace,
            self.tickets,
            ticket_ids=(self.tickets[0].ticket_id,),
            limits=TriageLimits(max_tickets=1),
        )
        with self.assertRaisesRegex(ValidationError, "at most 1"):
            add_synthetic_tickets(
                one,
                self.tickets,
                ticket_ids=(self.tickets[1].ticket_id,),
                limits=TriageLimits(max_tickets=1),
            )
        self.assertEqual(one.entries[0].ticket.ticket_id, self.tickets[0].ticket_id)

    def test_parsed_record_remains_eligible_when_nlp_fails(self) -> None:
        pending = inspect_csv_upload(
            b"record_id,text,topic\nfailed,Synthetic parsed record.,testing\n",
            max_bytes=10_000,
        )
        preview = prepare_csv_batch(
            pending, text_column="text", max_rows=10, max_text_length=200
        )
        result = analyze_batch(preview, FailingAnalyzer())
        self.assertIsNone(result.outcomes[0].report)
        workspace = prepare_workspace_ticket(
            new_triage_workspace(mode=TriageMode.INDEPENDENT),
            result,
            None,
            None,
            record_id="failed",
            excerpt="Synthetic parsed",
            complexity=TicketComplexity.INTERMEDIATE,
            guide=self.guide,
            applicable_rule_ids=("TRIAGE-UNCLEAR-001",),
            mock_suggestion=None,
            limits=TriageLimits(),
            ticket_id_factory=lambda: "failed",
            now=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        )
        entry = workspace.entries[0]
        self.assertEqual(entry.ticket.text, "Synthetic parsed")
        assert entry.ticket.source_snapshot is not None
        self.assertEqual(entry.ticket.source_snapshot.sentiment_signal, "")
        self.assertEqual(entry.ticket.source_snapshot.emotion_signal, "")

    def test_draft_finalize_warning_revision_and_summary(self) -> None:
        workspace = add_synthetic_tickets(
            new_triage_workspace(mode=TriageMode.INDEPENDENT),
            self.tickets,
            ticket_ids=("support-001",),
            limits=TriageLimits(),
        )
        drafted = save_triage_draft(
            workspace,
            ticket_id="support-001",
            fields=TriageFields(primary_intent=SupportIntent.RECOVER_ACCOUNT_ACCESS),
        )
        finalized = finalize_ticket(
            drafted, ticket_id="support-001", fields=fields()
        )
        first = finalized.entries[0].first_final
        revised = revise_ticket(
            finalized,
            ticket_id="support-001",
            fields=fields(
                urgency=TriageUrgency.CRITICAL,
                escalation_required=False,
                human_notes="Retain a non-blocking synthetic warning.",
            ),
        )
        entry = revised.entries[0]
        self.assertIs(entry.first_final, first)
        self.assertEqual(entry.revision_count, 1)
        self.assertTrue(entry.final and entry.final.warnings)
        summary = summarize_triage(revised)
        self.assertEqual(summary.finalized_count, 1)
        self.assertEqual(summary.warning_ticket_count, 1)
        self.assertEqual(summary.first_agreement[0].denominator, 1)

    def test_finalized_distribution_sample_uses_finalized_denominator(self) -> None:
        selected = tuple(ticket.ticket_id for ticket in self.tickets[:10])
        workspace = add_synthetic_tickets(
            new_triage_workspace(mode=TriageMode.INDEPENDENT),
            self.tickets,
            ticket_ids=selected,
            limits=TriageLimits(),
        )
        workspace = finalize_ticket(
            workspace,
            ticket_id=selected[0],
            fields=fields(),
        )

        summary = summarize_triage(workspace)
        self.assertEqual(summary.total_eligible, 10)
        self.assertEqual(summary.finalized_count, 1)
        self.assertEqual(summary.sample.level.value, "insufficient")
        self.assertEqual(
            summary.sample.message,
            "Insufficient sample for comparison",
        )

        rows = list(csv.DictReader(io.StringIO(export_triage_csv(workspace))))
        metadata = rows[0]
        self.assertEqual(metadata["numerator"], "1")
        self.assertEqual(metadata["denominator"], "1")
        self.assertEqual(metadata["exclusions"], "9")
        self.assertEqual(metadata["sample_status"], "insufficient")

    def test_mock_agreement_sample_uses_mock_eligible_denominator(self) -> None:
        selected_tickets = tuple(
            ticket if index == 0 else replace(ticket, mock_suggestion=None)
            for index, ticket in enumerate(self.tickets[:10])
        )
        selected = tuple(ticket.ticket_id for ticket in selected_tickets)
        workspace = add_synthetic_tickets(
            new_triage_workspace(mode=TriageMode.INDEPENDENT),
            selected_tickets,
            ticket_ids=selected,
            limits=TriageLimits(),
        )
        for ticket_id in selected:
            workspace = finalize_ticket(
                workspace,
                ticket_id=ticket_id,
                fields=fields(),
            )

        summary = summarize_triage(workspace)
        self.assertEqual(summary.finalized_count, 10)
        self.assertEqual(summary.sample.level.value, "descriptive")
        for metric in (*summary.first_agreement, *summary.final_agreement):
            self.assertEqual(metric.denominator, 1)
            self.assertEqual(metric.excluded, 9)
            self.assertEqual(metric.sample.level.value, "insufficient")

        rows = list(csv.DictReader(io.StringIO(export_triage_csv(workspace))))
        metrics = [row for row in rows if row["row_type"] == "summary_metric"]
        self.assertEqual(len(metrics), 12)
        self.assertTrue(all(row["denominator"] == "1" for row in metrics))
        self.assertTrue(
            all(row["sample_status"] == "insufficient" for row in metrics)
        )

    def test_unavailable_mock_is_neither_visible_nor_hidden(self) -> None:
        unavailable = next(
            ticket for ticket in self.tickets if ticket.mock_suggestion is None
        )
        for mode in (TriageMode.INDEPENDENT, TriageMode.MOCK_ASSISTED):
            with self.subTest(mode=mode):
                workspace = add_synthetic_tickets(
                    new_triage_workspace(mode=mode),
                    self.tickets,
                    ticket_ids=(unavailable.ticket_id,),
                    limits=TriageLimits(),
                )
                workspace = finalize_ticket(
                    workspace,
                    ticket_id=unavailable.ticket_id,
                    fields=fields(),
                )
                first = workspace.entries[0].first_final
                assert first is not None
                self.assertFalse(
                    first.mock_visible_before_first_submission
                )
                summary = summarize_triage(workspace)
                self.assertEqual(summary.mock_visible_before_count, 0)
                self.assertEqual(summary.mock_hidden_before_count, 0)

    def test_export_is_auditable_formula_safe_and_privacy_default(self) -> None:
        workspace = add_synthetic_tickets(
            new_triage_workspace(mode=TriageMode.INDEPENDENT),
            self.tickets,
            ticket_ids=("support-022",),
            limits=TriageLimits(),
        )
        workspace = finalize_ticket(
            workspace,
            ticket_id="support-022",
            fields=fields(
                primary_intent=SupportIntent.OTHER_OR_UNCLEAR,
                issue_category=IssueCategory.OTHER_OR_UNCLEAR,
                urgency=TriageUrgency.UNCLEAR,
                recommended_queue=RecommendedQueue.GENERAL_SUPPORT,
                primary_next_action=NextAction.REQUEST_MORE_INFORMATION,
                unclear_reason="=synthetic unclear reason",
                human_notes="@synthetic note",
            ),
        )
        content = export_triage_csv(
            workspace,
            now=lambda: datetime(2026, 7, 26, 12, tzinfo=UTC),
        )
        rows = list(csv.DictReader(io.StringIO(content)))
        self.assertEqual(rows[0]["row_type"], "export_metadata")
        self.assertRegex(rows[0]["exported_at"], r"\+00:00$")
        self.assertIn("denominator", rows[0]["metric_definition"])
        ticket = next(row for row in rows if row["row_type"] == "ticket")
        self.assertTrue(ticket["source_text"].startswith("'="))
        self.assertIn(
            "unclear_reason==synthetic unclear reason",
            ticket["final_fields"],
        )
        self.assertIn("human_notes=@synthetic note", ticket["final_fields"])


if __name__ == "__main__":
    unittest.main()
