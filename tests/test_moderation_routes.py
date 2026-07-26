"""End-to-end Flask tests for the M9 moderation training workflow."""

import io
import unittest

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface import create_app
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, LazyAnalysisService


def gateway() -> LazyAnalysisService:
    return LazyAnalysisService(
        lambda: AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )
    )


class ModerationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 200,
            },
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()

    def create_workspace(self, batch_token: str = "") -> str:
        response = self.client.post(
            "/moderation/start", data={"batch_token": batch_token}
        )
        self.assertEqual(response.status_code, 302)
        return response.headers["Location"].removesuffix("/prepare")

    def test_warning_submission_feedback_comparison_export_and_no_store(
        self,
    ) -> None:
        workspace_url = self.create_workspace()
        started = self.client.post(
            workspace_url + "/sessions",
            data={
                "case_ids": ["synthetic-001"],
                "case_count": "1",
                "mode": "independent",
                "feedback_timing": "immediate_feedback",
                "order_mode": "original_order",
                "content_notice_confirmed": "true",
            },
        )
        self.assertEqual(started.status_code, 302)
        session_url = started.headers["Location"]

        rejected = self.client.post(
            session_url + "/cases/synthetic-001",
            data={
                "action": "submit",
                "disposition": "warn",
                "primary_violation": "harassment_abuse",
                "severity": "high",
                "escalate": "true",
                "reasoning": "Synthetic reason.",
                "reviewer_note": "Synthetic note.",
            },
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn(b"Select an escalation reason", rejected.data)

        submitted = self.client.post(
            session_url + "/cases/synthetic-001",
            data={
                "action": "submit",
                "disposition": "allow",
                "primary_violation": "harassment_abuse",
                "severity": "critical",
                "escalate": "false",
                "reasoning": "=retain synthetic reasoning",
                "reviewer_note": "@retain synthetic note",
            },
        )
        self.assertEqual(submitted.status_code, 302)
        results_url = submitted.headers["Location"]
        results = self.client.get(results_url)
        self.assertIn(b"Retained guidance warnings", results.data)
        self.assertIn(b"allow_with_violation", results.data)
        self.assertIn(b"not a composite score", results.data)
        self.assertIn(b"Category-level reference alignment", results.data)
        self.assertIn(b"Severity-level reference alignment", results.data)
        self.assertIn(b"Reference provenance", results.data)
        self.assertIn(b"Educational disagreement patterns", results.data)

        session_id = session_url.rsplit("/", 1)[-1]
        feedback = self.client.post(
            session_url
            + "/cases/synthetic-001/feedback"
        )
        self.assertEqual(feedback.status_code, 302)
        case_page = self.client.get(feedback.headers["Location"])
        self.assertIn(b"Frozen feedback", case_page.data)
        self.assertIn(b"built_in", case_page.data)
        self.assertIn(b"Your submitted judgment was retained unchanged", case_page.data)

        export = self.client.get(
            workspace_url + f"/sessions/{session_id}/export.csv"
        )
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.headers["Cache-Control"], "no-store")
        self.assertIn(b"summary_metric", export.data)
        self.assertIn(b"'=retain synthetic reasoning", export.data)
        self.assertIn(b"allow_with_violation", export.data)
        self.assertIn(b"built_in_default;user_excluded", export.data)

    def test_successful_batch_record_can_be_snapshotted_explicitly(
        self,
    ) -> None:
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text,topic\n"
                        b"row-1,A synthetic workspace record.,testing\n"
                    ),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        batch_url = uploaded.headers["Location"]
        self.client.post(batch_url + "/analyze")
        batch_token = batch_url.rsplit("/", 1)[-1]
        workspace_url = self.create_workspace(batch_token)
        prepared = self.client.post(
            workspace_url + "/prepare",
            data={
                "record_id": "row-1",
                "excerpt": "synthetic workspace",
                "difficulty": "beginner",
                "learning_objective": "policy_vs_factual_uncertainty",
            },
            follow_redirects=True,
        )
        self.assertEqual(prepared.status_code, 200)
        self.assertIn(b"workspace-", prepared.data)
        self.assertIn(b"synthetic workspace", prepared.data)
        self.assertIn(b"none / unscored", prepared.data)
        token = workspace_url.rsplit("/", 1)[-1]
        store = self.app.extensions["sti_moderation_store"]
        workspace = store.get(token)
        case_id = workspace.prepared_cases[0].case_id
        started = self.client.post(
            workspace_url + "/sessions",
            data={
                "case_ids": [case_id],
                "case_count": "1",
                "mode": "independent",
                "feedback_timing": "immediate_feedback",
                "order_mode": "original_order",
                "content_notice_confirmed": "true",
            },
        )
        session_page = self.client.get(started.headers["Location"])
        self.assertIn(b"Contextual M3", session_page.data)
        self.assertIn(b"not moderation verdicts", session_page.data)
        self.assertIn(b"deterministic-sentiment", session_page.data)
        self.assertIn(b"deterministic-emotion", session_page.data)

    def test_configured_limits_are_visible_and_capacity_does_not_evict(
        self,
    ) -> None:
        app = create_app(
            {
                "TESTING": True,
                "MAX_MODERATION_PREPARED_CASES": 7,
                "MAX_MODERATION_SESSION_CASES": 3,
                "MAX_MODERATION_SESSION_ATTEMPTS": 2,
                "MODERATION_WORKSPACE_CAPACITY": 1,
            },
            analysis_gateway=gateway(),
        )
        client = app.test_client()
        page = client.get("/moderation")
        self.assertIn(b"7", page.data)
        self.assertIn(b"3", page.data)
        self.assertIn(b"2", page.data)
        first = client.post("/moderation/start")
        blocked = client.post("/moderation/start")
        self.assertEqual(first.status_code, 302)
        self.assertEqual(blocked.status_code, 409)
        self.assertIn(b"capacity reached", blocked.data)
        self.assertEqual(client.get(first.headers["Location"]).status_code, 200)


if __name__ == "__main__":
    unittest.main()
