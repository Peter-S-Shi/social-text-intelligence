"""End-to-end Flask human-review queue tests with synthetic rows."""

import io
import unittest

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface import create_app
from social_text_intelligence.interface.batch_state import EphemeralBatchStore
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


class ReviewRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text,topic,community\n"
                        b"first,Synthetic first row.,release,group-a\n"
                        b"failed,,release,group-a\n"
                        b"third,Synthetic third row.,support,group-b\n"
                    ),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        self.workspace_url = uploaded.headers["Location"]
        self.token = self.workspace_url.rsplit("/", 1)[-1]
        self.client.post(self.workspace_url + "/analyze")

    def test_review_queue_excludes_failures_and_shows_complete_ai_context(self) -> None:
        response = self.client.get(
            self.workspace_url + "/review", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 / 2", response.data)
        self.assertIn(b"Synthetic first row.", response.data)
        self.assertIn(b"release", response.data)
        self.assertIn(b"group-a", response.data)
        self.assertIn(b"Confidence", response.data)
        self.assertIn(b"Inspect all model-native emotion scores", response.data)
        self.assertNotIn(b"failed</h2>", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_accept_correct_navigation_filters_and_progress(self) -> None:
        first_url = self.workspace_url + "/review/1"
        accepted = self.client.post(
            first_url,
            data={"action": "accept_both", "review_note": "Looks acceptable."},
            follow_redirects=True,
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertIn(b"2 / 2", accepted.data)
        self.assertIn(b"1 reviewed", accepted.data)

        corrected = self.client.post(
            self.workspace_url + "/review/3",
            data={
                "action": "save_next",
                "sentiment_judgment": "correct",
                "human_sentiment": "negative",
                "emotion_judgment": "correct",
                "human_dominant_emotion": "anger",
                "human_secondary_emotions": ["fear", "disgust"],
                "review_note": "Synthetic correction.",
            },
            follow_redirects=True,
        )
        self.assertIn(b"2 reviewed", corrected.data)
        self.assertIn(b"Agreement: 1 / 2 definitive reviews", corrected.data)
        self.assertIn(b"1 definitive corrections", corrected.data)

        filtered = self.client.get(
            self.workspace_url + "/review?review=corrected",
            follow_redirects=True,
        )
        self.assertIn(b"third", filtered.data)
        self.assertIn(b"1 match current filters", filtered.data)

    def test_invalid_neutral_combination_is_rejected_without_ai_mutation(self) -> None:
        store = self.app.extensions["sti_batch_store"]
        self.assertIsInstance(store, EphemeralBatchStore)
        workspace = store.get(self.token)
        assert workspace is not None and workspace.result is not None
        original_report = workspace.result.outcomes[0].report

        response = self.client.post(
            self.workspace_url + "/review/1",
            data={
                "action": "save_next",
                "sentiment_judgment": "accept",
                "emotion_judgment": "correct",
                "human_dominant_emotion": "neutral",
                "human_secondary_emotions": ["joy"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Neutral cannot coexist", response.data)
        after = store.get(self.token)
        assert after is not None and after.result is not None
        self.assertIs(after.result.outcomes[0].report, original_report)

    def test_cleared_review_fails_safely(self) -> None:
        self.client.post(self.workspace_url + "/clear")
        response = self.client.get(self.workspace_url + "/review/1")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"expired or was cleared", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_reviewed_export_is_explicit_complete_and_no_store(self) -> None:
        self.client.post(
            self.workspace_url + "/review/1",
            data={"action": "accept_both", "review_note": "@synthetic note"},
        )
        compact = self.client.get(self.workspace_url + "/review/export.csv")
        native = self.client.get(
            self.workspace_url + "/review/export.csv?native=1"
        )

        self.assertEqual(compact.status_code, 200)
        self.assertEqual(compact.mimetype, "text/csv")
        self.assertIn(b"review_status", compact.data)
        self.assertIn(b"sentiment_agreement", compact.data)
        self.assertIn(b"emotion_set_agreement", compact.data)
        self.assertIn(b"'@synthetic note", compact.data)
        self.assertIn(b"empty_text", compact.data)
        self.assertIn(b"sentiment_revision", compact.data)
        self.assertNotIn(b"emotion_native_joy", compact.data)
        self.assertIn(b"emotion_native_joy", native.data)
        self.assertEqual(compact.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
