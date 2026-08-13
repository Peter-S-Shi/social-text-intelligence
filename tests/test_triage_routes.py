"""End-to-end Support Triage route and privacy regression tests."""

import csv
import io
import unittest
from dataclasses import replace
from datetime import UTC, datetime

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.contracts.errors import ProviderError
from social_text_intelligence.interface import create_app
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import (
    AnalysisService,
    ContextAssociation,
    ContextNote,
    ContextTag,
    HumanReview,
    InsightState,
    LazyAnalysisService,
    ReviewJudgment,
    ReviewState,
)


def gateway() -> LazyAnalysisService:
    return LazyAnalysisService(
        lambda: AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )
    )


class FailingGateway:
    initialized = True

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        raise ProviderError(
            provider="synthetic-failing-provider",
            code="model_load_failed",
            message="Synthetic route failure.",
        )


def valid_form() -> dict[str, object]:
    return {
        "primary_intent": "recover_account_access",
        "secondary_intents": [],
        "issue_category": "account_and_access",
        "urgency": "high",
        "recommended_queue": "account_and_access",
        "escalation_required": "false",
        "escalation_reason": "",
        "primary_next_action": "verify_identity_or_account_ownership",
        "secondary_next_actions": [],
        "unclear_reason": "",
        "human_notes": "",
    }


class TriageRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 500,
            },
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()

    def create_triage(
        self, *, mode: str = "independent", batch_token: str = ""
    ) -> str:
        response = self.client.post(
            "/triage/start",
            data={"mode": mode, "batch_token": batch_token},
        )
        self.assertEqual(response.status_code, 302)
        return response.headers["Location"].removesuffix("/guide")

    def add_ticket(self, base: str, ticket_id: str = "support-001") -> None:
        response = self.client.post(
            base + "/synthetic", data={"ticket_ids": [ticket_id]}
        )
        self.assertEqual(response.status_code, 302)

    def test_every_workspace_view_has_an_explicit_application_home_link(
        self,
    ) -> None:
        base = self.create_triage()
        self.add_ticket(base)
        for path in (
            "/guide",
            "/workspace",
            "/tickets/support-001",
            "/summary",
        ):
            with self.subTest(path=path):
                page = self.client.get(base + path)
                self.assertEqual(page.status_code, 200)
                self.assertIn(b'href="/"', page.data)
                self.assertIn(b"Social Text Intelligence home", page.data)
                self.assertIn(b'aria-label="Application navigation"', page.data)

    def test_independent_draft_atomic_finalize_reveal_revision_and_no_store(
        self,
    ) -> None:
        base = self.create_triage()
        self.add_ticket(base)
        ticket_url = base + "/tickets/support-001"
        hidden = self.client.get(ticket_url)
        self.assertEqual(hidden.status_code, 200)
        self.assertNotIn(b"Account access requires ownership verification", hidden.data)
        self.assertEqual(hidden.headers["Cache-Control"], "no-store")

        drafted = self.client.post(
            ticket_url + "/draft",
            data={"primary_intent": "recover_account_access"},
        )
        self.assertEqual(drafted.status_code, 302)
        token = base.split("/")[-1]
        store = self.app.extensions["sti_triage_store"]
        self.assertEqual(store.get(token).entries[0].status.value, "draft")

        invalid = valid_form()
        invalid["primary_next_action"] = ""
        rejected = self.client.post(ticket_url + "/finalize", data=invalid)
        self.assertEqual(rejected.status_code, 400)
        self.assertIn(b"primary_next_action is required", rejected.data)
        self.assertEqual(store.get(token).entries[0].status.value, "draft")

        finalized = self.client.post(ticket_url + "/finalize", data=valid_form())
        self.assertEqual(finalized.status_code, 302)
        first = store.get(token).entries[0].first_final
        before_reveal = self.client.get(ticket_url)
        self.assertNotIn(
            b"Account access requires ownership verification",
            before_reveal.data,
        )
        revealed = self.client.post(ticket_url + "/reveal")
        self.assertEqual(revealed.status_code, 302)
        shown = self.client.get(ticket_url)
        self.assertIn(
            b"Account access requires ownership verification", shown.data
        )

        revision = valid_form()
        revision.update(
            {
                "urgency": "critical",
                "human_notes": "Retain a synthetic non-blocking warning.",
            }
        )
        revised = self.client.post(ticket_url + "/revise", data=revision)
        self.assertEqual(revised.status_code, 302)
        entry = store.get(token).entries[0]
        self.assertIs(entry.first_final, first)
        self.assertEqual(entry.revision_count, 1)
        self.assertTrue(entry.final.warnings)
        summary = self.client.get(base + "/summary")
        self.assertIn(b"Coverage", summary.data)
        self.assertIn(b"Mock comparison", summary.data)

    def test_assisted_mock_is_visible_but_human_form_is_not_prefilled(
        self,
    ) -> None:
        base = self.create_triage(mode="mock_assisted")
        self.add_ticket(base)
        page = self.client.get(base + "/tickets/support-001")
        self.assertIn(b"AI-assisted simulation", page.data)
        self.assertIn(
            b"Account access requires ownership verification", page.data
        )
        self.assertNotIn(
            b'value="recover_account_access" selected', page.data
        )

    def test_no_mock_is_explicit_and_never_claimed_visible(self) -> None:
        for mode in ("independent", "mock_assisted"):
            with self.subTest(mode=mode):
                base = self.create_triage(mode=mode)
                self.add_ticket(base, "support-015")
                page = self.client.get(base + "/tickets/support-015")
                self.assertEqual(page.status_code, 200)
                self.assertIn(b"Mock unavailable", page.data)
                self.assertIn(b"Nothing has been fabricated or inferred", page.data)
                self.assertNotIn(b"the visible suggestion is", page.data)

    def test_summary_separates_finalized_and_mock_sample_notices(self) -> None:
        base = self.create_triage()
        for ticket_id in (
            "support-001",
            "support-002",
            "support-003",
            "support-004",
            "support-005",
            "support-006",
            "support-007",
            "support-008",
            "support-009",
            "support-010",
        ):
            self.add_ticket(base, ticket_id)
        self.client.post(
            base + "/tickets/support-001/finalize", data=valid_form()
        )

        summary = self.client.get(base + "/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertIn(b"Finalized-distribution sample:", summary.data)
        self.assertIn(b"1 eligible finalized ticket", summary.data)
        self.assertIn(b"First sample notice", summary.data)
        self.assertIn(b"Final sample notice", summary.data)
        self.assertGreaterEqual(
            summary.data.count(b"Insufficient sample for comparison"),
            3,
        )

    def test_summary_warns_when_only_one_finalized_ticket_has_a_mock(self) -> None:
        base = self.create_triage()
        ticket_ids = tuple(f"support-{index:03d}" for index in range(1, 11))
        for ticket_id in ticket_ids:
            self.add_ticket(base, ticket_id)
        token = base.split("/")[-1]
        store = self.app.extensions["sti_triage_store"]
        workspace = store.get(token)
        store.replace(
            token,
            replace(
                workspace,
                entries=tuple(
                    entry
                    if index == 0
                    else replace(
                        entry,
                        ticket=replace(
                            entry.ticket,
                            mock_suggestion=None,
                        ),
                    )
                    for index, entry in enumerate(workspace.entries)
                ),
            ),
        )
        for ticket_id in ticket_ids:
            response = self.client.post(
                base + f"/tickets/{ticket_id}/finalize",
                data=valid_form(),
            )
            self.assertEqual(response.status_code, 302)

        summary = self.client.get(base + "/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertNotIn(b"Finalized-distribution sample:", summary.data)
        self.assertEqual(
            summary.data.count(b"Insufficient sample for comparison"),
            12,
        )

    def test_failed_nlp_record_is_eligible_for_explicit_snapshot(self) -> None:
        failing_app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 500,
            },
            analysis_gateway=FailingGateway(),
        )
        client = failing_app.test_client()
        upload = client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(b"record_id,text\nfailed,Synthetic parsed text.\n"),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        batch_url = upload.headers["Location"]
        client.post(batch_url + "/analyze")
        batch_token = batch_url.rsplit("/", 1)[-1]
        started = client.post(
            "/triage/start",
            data={"mode": "independent", "batch_token": batch_token},
        )
        base = started.headers["Location"].removesuffix("/guide")
        prepared = client.post(
            base + "/workspace-ticket",
            data={
                "record_id": "failed",
                "excerpt": "Synthetic parsed",
                "complexity": "intermediate",
                "rule_ids": ["TRIAGE-UNCLEAR-001"],
            },
        )
        self.assertEqual(prepared.status_code, 302)
        token = base.split("/")[-1]
        entry = failing_app.extensions["sti_triage_store"].get(token).entries[0]
        self.assertEqual(entry.ticket.text, "Synthetic parsed")
        self.assertEqual(entry.ticket.source_snapshot.sentiment_signal, "")

    def test_workspace_export_privacy_categories_are_independent_and_no_store(
        self,
    ) -> None:
        upload = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text,topic,community\n"
                        b"row-1,=synthetic workspace record,testing,community-a\n"
                    ),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        batch_url = upload.headers["Location"]
        self.client.post(batch_url + "/analyze")
        batch_token = batch_url.rsplit("/", 1)[-1]
        batch_store = self.app.extensions["sti_batch_store"]
        batch = batch_store.get(batch_token)
        assert batch is not None
        batch_store.replace(
            batch_token,
            replace(
                batch,
                reviews=ReviewState(
                    reviews=(
                        HumanReview(
                            record_id="row-1",
                            sentiment_judgment=ReviewJudgment.ACCEPT,
                            human_sentiment=SentimentLabel.POSITIVE,
                            emotion_judgment=ReviewJudgment.ACCEPT,
                            human_dominant_emotion=EmotionLabel.GRATITUDE,
                            note="Synthetic human review.",
                            reviewed_at=datetime(2026, 7, 26, tzinfo=UTC),
                        ),
                    )
                ),
                insights=InsightState(
                    notes=(
                        ContextNote(
                            note_id="note-1",
                            association=ContextAssociation.RECORD,
                            association_value="row-1",
                            phrase="synthetic workspace",
                            explanation="Synthetic context note.",
                            context_importance="Useful synthetic context.",
                            tags=(ContextTag.MISSING_CONTEXT,),
                            created_at=datetime(2026, 7, 26, tzinfo=UTC),
                        ),
                    )
                ),
            ),
        )
        base = self.create_triage(batch_token=batch_token)
        prepared = self.client.post(
            base + "/workspace-ticket",
            data={
                "record_id": "row-1",
                "excerpt": "=synthetic workspace",
                "complexity": "intermediate",
                "rule_ids": ["TRIAGE-UNCLEAR-001"],
            },
        )
        self.assertEqual(prepared.status_code, 302)
        token = base.split("/")[-1]
        triage_store = self.app.extensions["sti_triage_store"]
        entry = triage_store.get(token).entries[0]
        ticket_id = entry.ticket.ticket_id
        self.client.post(
            base + f"/tickets/{ticket_id}/finalize", data=valid_form()
        )

        def ticket_row(query: str) -> tuple[dict[str, str], object]:
            response = self.client.get(base + "/export.csv" + query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            rows = list(
                csv.DictReader(io.StringIO(response.data.decode("utf-8")))
            )
            return next(row for row in rows if row["row_type"] == "ticket"), response

        default, _ = ticket_row("")
        for field in (
            "source_text",
            "sentiment_signal",
            "emotion_signal",
            "human_review",
            "context_notes",
            "trusted_metadata",
        ):
            self.assertEqual(default[field], "")

        source, _ = ticket_row("?source_text=1")
        self.assertTrue(source["source_text"].startswith("'="))
        self.assertEqual(source["sentiment_signal"], "")
        signals, _ = ticket_row("?signals=1")
        self.assertIn("deterministic-sentiment", signals["sentiment_signal"])
        self.assertEqual(signals["human_review"], "")
        review, _ = ticket_row("?human_review=1")
        self.assertIn("Synthetic human review", review["human_review"])
        notes, _ = ticket_row("?context_notes=1")
        self.assertIn("Synthetic context note", notes["context_notes"])
        metadata, _ = ticket_row("?metadata=1")
        self.assertIn("topic=testing", metadata["trusted_metadata"])
        self.assertEqual(metadata["source_text"], "")


if __name__ == "__main__":
    unittest.main()
