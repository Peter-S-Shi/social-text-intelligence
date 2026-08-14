"""Flask routes for the local Milestone 8 insight workflow."""

import csv
import io
import unittest
from unittest.mock import patch

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.contracts.errors import ProviderError
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


class SelectiveFailureGateway:
    initialized = True

    def __init__(self) -> None:
        self.service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(
                EmotionLabel.GRATITUDE
            ),
        )

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if record.record_id == "provider-fail":
            raise ProviderError(
                provider="synthetic-failing-provider",
                code="model_load_failed",
                message="Synthetic route failure.",
            )
        return self.service.analyze(record)


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
        self.assertIn(b"6 successful analysis rows", response.data)
        self.assertIn(b"0 failed rows assigned reliably", response.data)
        self.assertIn(b"0 failed rows unassigned across this grouping", response.data)
        self.assertIn(b"Small sample", response.data)
        self.assertIn(b"One AI sentiment label per successful row", response.data)
        self.assertIn(b"deterministic-sentiment@mock-v1", response.data)
        self.assertIn(b"Descriptive, not causal", response.data)
        self.assertIn(b'aria-label="Insight views"', response.data)
        self.assertIn(b"<label", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_group_context_explicitly_separates_failed_and_unassigned_rows(
        self,
    ) -> None:
        app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 20_000,
                "MAX_BATCH_ROWS": 20,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=SelectiveFailureGateway(),
        )
        client = app.test_client()
        uploaded = client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text,topic\n"
                        b"ok,Synthetic success.,edge_testing\n"
                        b"provider-fail,Synthetic failure.,edge_testing\n"
                        b"invalid-text,," + (b"x" * 513) + b"\n"
                    ),
                    "synthetic-edge.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        client.post(workspace_url + "/analyze")
        response = client.get(
            workspace_url
            + "/insights?grouping=topic&group=edge_testing"
            + "&perspective=ai&metric=ai_sentiment"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 successful analysis row", response.data)
        self.assertIn(b"1 failed row assigned reliably", response.data)
        self.assertIn(b"1 failed row unassigned across this grouping", response.data)

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
        self.assertIn(b"Created at (UTC):", created.data)
        self.assertRegex(created.data, rb"Created at \(UTC\):.*\+00:00")

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

    def test_interleaved_context_notes_preserve_both_mutations(self) -> None:
        token = self.workspace_url.rsplit("/", 1)[-1]
        store = self.app.extensions["sti_batch_store"]
        original_mutate = store.mutate
        nested_client = self.app.test_client()
        interleaved = False

        def note_data(phrase: str) -> dict[str, object]:
            return {
                "association": "record",
                "association_value": "row-1",
                "phrase": phrase,
                "explanation": f"Explanation for {phrase}",
                "context_importance": f"Context for {phrase}",
                "tags": ["other"],
            }

        def mutate_with_interleaving(
            workspace_token: str, mutation: object
        ) -> object:
            nonlocal interleaved
            if not interleaved:
                interleaved = True
                nested = nested_client.post(
                    self.insight_url + "/notes",
                    data=note_data("Second tab note."),
                )
                self.assertEqual(nested.status_code, 302)
            return original_mutate(workspace_token, mutation)

        with patch.object(store, "mutate", side_effect=mutate_with_interleaving):
            first = self.client.post(
                self.insight_url + "/notes",
                data=note_data("First tab note."),
            )

        self.assertEqual(first.status_code, 302)
        current = store.get(token)
        assert current is not None and current.insights is not None
        self.assertEqual(
            {note.phrase for note in current.insights.notes},
            {"First tab note.", "Second tab note."},
        )

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
        rows = list(csv.DictReader(io.StringIO(compact.data.decode())))
        metadata = rows[0]
        self.assertEqual(metadata["section"], "export_metadata")
        self.assertRegex(metadata["exported_at"], r"\+00:00$")
        self.assertIn("successful row", metadata["metric_definition"])
        self.assertEqual(metadata["insufficient_sample_below"], "5")
        self.assertEqual(metadata["small_sample_below"], "10")
        self.assertEqual(metadata["total_input_count"], "12")
        self.assertEqual(metadata["reviewable_count"], "12")
        note = next(row for row in rows if row["section"] == "context_note")
        self.assertRegex(note["created_at"], r"\+00:00$")

    def test_oversized_context_note_is_413_without_state_change(self) -> None:
        token = self.workspace_url.rsplit("/", 1)[-1]
        store = self.app.extensions["sti_batch_store"]
        before = store.get(token)
        assert before is not None
        self.app.config["MAX_CONTENT_LENGTH"] = 256
        marker = "SYNTHETIC-PRIVATE-NOTE-MARKER"

        response = self.client.post(
            self.insight_url + "/notes",
            data={
                "association": "record",
                "association_value": "row-1",
                "phrase": marker + ("x" * 1024),
                "explanation": "Synthetic explanation.",
                "context_importance": "Synthetic context.",
            },
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn(marker.encode(), response.data)
        self.assertEqual(store.get(token), before)

    def test_cleared_workspace_fails_safely(self) -> None:
        self.client.post(
            self.workspace_url + "/clear", data={"confirm": "clear"}
        )
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
