"""Flask routes for the local Milestone 8 insight workflow."""

import io
import unittest

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface.app import create_app
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


def synthetic_csv() -> bytes:
    rows = ["record_id,text,topic,community,timestamp"]
    for number in range(1, 13):
        topic = "release" if number <= 6 else "support"
        community = "group-a" if number % 2 else "group-b"
        rows.append(
            f"row-{number},Synthetic row {number}.,{topic},{community},"
            f"2026-07-{number:02d}T12:00:00+00:00"
        )
    return ("\n".join(rows) + "\n").encode()


class InsightRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 20_000,
                "MAX_BATCH_ROWS": 20,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()
        uploaded = self.client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(synthetic_csv()), "synthetic.csv")},
            content_type="multipart/form-data",
        )
        self.workspace_url = uploaded.headers["Location"]
        self.client.post(self.workspace_url + "/analyze")
        self.insight_url = self.workspace_url + "/insights"

    def test_group_explorer_shows_definition_provenance_and_disclosures(self) -> None:
        response = self.client.get(
            self.insight_url
            + "?grouping=topic&group=release&perspective=ai&metric=ai_sentiment"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Group Explorer", response.data)
        self.assertIn(b"6 eligible / 6 group rows", response.data)
        self.assertIn(b"Small sample", response.data)
        self.assertIn(b"One AI sentiment label per successful row", response.data)
        self.assertIn(b"deterministic-sentiment@mock-v1", response.data)
        self.assertIn(b"Descriptive, not causal", response.data)
        self.assertIn(b'aria-label="Insight views"', response.data)
        self.assertIn(b"<label", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_comparison_accepts_two_groups_and_rejects_one(self) -> None:
        comparison = self.client.get(
            self.insight_url
            + "?view=comparison&grouping=topic&group=release&group=support"
            + "&perspective=ai&metric=ai_dominant_emotion"
        )
        self.assertEqual(comparison.status_code, 200)
        self.assertIn(b"release", comparison.data)
        self.assertIn(b"support", comparison.data)
        self.assertIn(b"2 displayed groups", comparison.data)

        invalid = self.client.get(
            self.insight_url
            + "?view=comparison&grouping=topic&group=release"
            + "&perspective=ai&metric=ai_sentiment"
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"Select between two and four groups", invalid.data)

    def test_context_note_is_separate_temporary_and_validated(self) -> None:
        created = self.client.post(
            self.insight_url + "/notes",
            data={
                "association": "record",
                "association_value": "row-1",
                "phrase": "=synthetic phrase",
                "explanation": "A synthetic quoted expression.",
                "context_importance": "Quotation changes interpretation.",
                "tags": ["quotation_or_reported_speech", "missing_context"],
            },
            follow_redirects=True,
        )
        self.assertEqual(created.status_code, 200)
        self.assertIn(b"=synthetic phrase", created.data)
        self.assertIn(b"Human annotation", created.data)

        invalid = self.client.post(
            self.insight_url + "/notes",
            data={
                "association": "record",
                "association_value": "row-1",
                "phrase": "Synthetic phrase",
                "explanation": "Synthetic explanation.",
                "context_importance": "Synthetic context.",
                "tags": ["unsupported_tag"],
            },
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn(b"supported tags", invalid.data)

    def test_examples_explain_selection_and_avoid_representative_claims(
        self,
    ) -> None:
        response = self.client.get(
            self.insight_url + "?view=examples&example_mode=lowest_ai_confidence"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lowest displayed AI confidence", response.data)
        self.assertIn(b"not representative of every person", response.data)
        self.assertIn(b"Navigation aid only", response.data)

    def test_export_is_explicit_formula_safe_optional_and_no_store(self) -> None:
        self.client.post(
            self.insight_url + "/notes",
            data={
                "association": "record",
                "association_value": "row-1",
                "phrase": "=synthetic phrase",
                "explanation": "@synthetic explanation",
                "context_importance": "+synthetic context",
                "tags": ["other"],
            },
        )
        compact = self.client.get(
            self.insight_url
            + "/export.csv?grouping=topic&group=release"
            + "&perspective=ai&metric=ai_sentiment&records=1"
        )
        native = self.client.get(
            self.insight_url
            + "/export.csv?grouping=topic&group=release"
            + "&perspective=ai&metric=ai_sentiment&records=1&native=1"
        )
        self.assertEqual(compact.status_code, 200)
        self.assertIn(b"group_summary", compact.data)
        self.assertIn(b"context_note", compact.data)
        self.assertIn(b"'=synthetic phrase", compact.data)
        self.assertIn(b"supporting_record", compact.data)
        self.assertNotIn(b"joy:0.6", compact.data)
        self.assertIn(b"joy:0.6", native.data)
        self.assertEqual(compact.headers["Cache-Control"], "no-store")

    def test_cleared_workspace_fails_safely(self) -> None:
        self.client.post(self.workspace_url + "/clear")
        response = self.client.get(self.insight_url)
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"expired or was cleared", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_invalid_grouping_and_malformed_export_fail_safely(self) -> None:
        page = self.client.get(self.insight_url + "?grouping=arbitrary_identity")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"supported trusted metadata grouping", page.data)
        export = self.client.get(
            self.insight_url
            + "/export.csv?grouping=topic&group=unknown"
            + "&perspective=ai&metric=ai_sentiment"
        )
        self.assertEqual(export.status_code, 400)
        self.assertIn(b"not present", export.data)


if __name__ == "__main__":
    unittest.main()
