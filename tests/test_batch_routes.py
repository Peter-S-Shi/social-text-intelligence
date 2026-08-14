"""End-to-end Flask batch workflow tests with synthetic CSV data."""

import csv
import io
import unittest
from unittest.mock import patch

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    ModelInputTooLongError,
    NormalizedTextInput,
    SentimentLabel,
)
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


class MixedInputBudgetGateway:
    initialized = True

    def __init__(self) -> None:
        self._service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if "encoded-over-limit" in record.text:
            raise ModelInputTooLongError(
                provider="synthetic-emotion",
                encoded_length=513,
                max_input_tokens=512,
            )
        return self._service.analyze(record)


class BatchRouteTests(unittest.TestCase):
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

    def test_preview_analyze_filter_export_and_clear(self) -> None:
        content = (
            b"record_id,text,language,topic\n"
            b"row-1,A synthetic success.,en,launch\n"
            b"row-2,,en,launch\n"
            b"row-3,Texte synthetique.,fr,launch\n"
        )
        uploaded = self.client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "synthetic.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 302)
        workspace_url = uploaded.headers["Location"]

        preview = self.client.get(workspace_url)
        self.assertIn(b"<strong>3</strong> rows", preview.data)
        self.assertIn(b"<strong>2</strong> valid", preview.data)
        self.assertIn(b"<strong>1</strong> invalid", preview.data)

        analyzed = self.client.post(workspace_url + "/analyze")
        self.assertEqual(analyzed.status_code, 302)
        results = self.client.get(workspace_url)
        self.assertIn(b"Sentiment distribution", results.data)
        self.assertIn(b"Compact activation rate", results.data)
        self.assertIn(b"rates do not sum to 100%", results.data)
        self.assertIn(b"1 analyzed", results.data)
        self.assertIn(b"2 failed", results.data)
        self.assertIn(b"Prepare Support Triage", results.data)
        batch_token = workspace_url.rsplit("/", 1)[-1]
        self.assertIn(
            f'/triage?batch_token={batch_token}'.encode(), results.data
        )
        self.assertIn(b'This action cannot be undone.', results.data)
        self.assertIn(b'name="confirm" value="clear" required', results.data)

        filtered = self.client.get(workspace_url + "?status=error")
        self.assertNotIn(b"<td>positive</td>", filtered.data)
        self.assertIn(b"empty_text", filtered.data)

        compact = self.client.get(workspace_url + "/export.csv")
        native = self.client.get(workspace_url + "/export.csv?native=1")
        self.assertEqual(compact.mimetype, "text/csv")
        self.assertIn(b"sentiment_revision", compact.data)
        self.assertNotIn(b"emotion_native_joy", compact.data)
        self.assertIn(b"emotion_native_joy", native.data)
        self.assertIn(b"empty_text", compact.data)
        self.assertIn(b"unsupported_language", compact.data)

        triage_home = self.client.get(f"/triage?batch_token={batch_token}")
        self.assertIn(
            f'name="batch_token" value="{batch_token}"'.encode(),
            triage_home.data,
        )
        triage_started = self.client.post(
            "/triage/start",
            data={"mode": "independent", "batch_token": batch_token},
        )
        self.assertEqual(triage_started.status_code, 302)
        triage_guide = self.client.get(triage_started.headers["Location"])
        self.assertIn(b"row-1", triage_guide.data)
        self.assertIn(b"row-3", triage_guide.data)

        unconfirmed = self.client.post(workspace_url + "/clear")
        self.assertEqual(unconfirmed.status_code, 400)
        self.assertEqual(self.client.get(workspace_url).status_code, 200)

        cleared = self.client.post(
            workspace_url + "/clear", data={"confirm": "clear"}
        )
        self.assertEqual(cleared.status_code, 302)
        self.assertEqual(self.client.get(workspace_url).status_code, 404)

    def test_mixed_batch_rejects_only_over_budget_row_and_exports_no_scores(
        self,
    ) -> None:
        app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=MixedInputBudgetGateway(),
        )
        client = app.test_client()
        uploaded = client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text\n"
                        b"within,A synthetic success.\n"
                        b"over,encoded-over-limit synthetic text.\n"
                    ),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]

        self.assertEqual(client.post(workspace_url + "/analyze").status_code, 302)
        rendered = client.get(workspace_url)
        self.assertIn(b"1 analyzed", rendered.data)
        self.assertIn(b"1 failed", rendered.data)
        self.assertIn(b"model_input_too_long", rendered.data)
        self.assertIn(b"No truncation or partial analysis", rendered.data)

        exported = client.get(workspace_url + "/export.csv")
        rows = {
            row["record_id"]: row
            for row in csv.DictReader(io.StringIO(exported.get_data(as_text=True)))
        }
        self.assertEqual(rows["within"]["status"], "ok")
        self.assertEqual(rows["within"]["sentiment_label"], "positive")
        self.assertEqual(rows["over"]["status"], "error")
        self.assertEqual(rows["over"]["error_code"], "model_input_too_long")
        for field in (
            "sentiment_label",
            "sentiment_confidence",
            "sentiment_positive",
            "dominant_emotion",
            "emotion_confidence",
            "emotion_joy",
            "sentiment_model",
            "emotion_model",
        ):
            self.assertEqual(rows["over"][field], "")

    def test_nonstandard_text_column_requires_selection(self) -> None:
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(b"message,topic\nSynthetic message.,test\n"),
                    "columns.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        select_page = self.client.get(workspace_url)
        self.assertIn(b"Select the text column", select_page.data)
        selected = self.client.post(
            workspace_url + "/select", data={"text_column": "message"}
        )
        self.assertEqual(selected.status_code, 302)
        self.assertIn(b"<strong>1</strong> rows", self.client.get(workspace_url).data)

    def test_interleaved_column_selection_returns_conflict_without_overwrite(
        self,
    ) -> None:
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"message,alternate\nSynthetic message.,Alternate text.\n"
                    ),
                    "columns.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        token = workspace_url.rsplit("/", 1)[-1]
        store = self.app.extensions["sti_batch_store"]
        original_mutate = store.mutate
        nested_client = self.app.test_client()
        interleaved = False

        def mutate_with_interleaving(
            workspace_token: str, mutation: object
        ) -> object:
            nonlocal interleaved
            if not interleaved:
                interleaved = True
                nested = nested_client.post(
                    workspace_url + "/select",
                    data={"text_column": "alternate"},
                )
                self.assertEqual(nested.status_code, 302)
            return original_mutate(workspace_token, mutation)

        with patch.object(store, "mutate", side_effect=mutate_with_interleaving):
            stale = self.client.post(
                workspace_url + "/select",
                data={"text_column": "message"},
            )

        self.assertEqual(stale.status_code, 409)
        self.assertIn(b"changed in another request", stale.data)
        current = store.get(token)
        assert current is not None and current.preview is not None
        self.assertEqual(current.preview.text_column, "alternate")

    def test_oversized_upload_is_rejected_without_traceback(self) -> None:
        app = create_app(
            {"TESTING": True, "MAX_BATCH_BYTES": 5},
            analysis_gateway=gateway(),
        )
        response = app.test_client().post(
            "/batch/upload",
            data={"file": (io.BytesIO(b"text\nlonger\n"), "large.csv")},
            content_type="multipart/form-data",
        )
        self.assertIn(b"exceeds the 5-byte limit", response.data)
        self.assertNotIn(b"Traceback", response.data)

    def test_oversized_multipart_is_413_without_creating_workspace(self) -> None:
        marker = b"SYNTHETIC-PRIVATE-BATCH-MARKER"
        app = create_app(
            {
                "TESTING": True,
                "MAX_CONTENT_LENGTH": 512,
                "MAX_BATCH_BYTES": 128,
            },
            analysis_gateway=gateway(),
        )
        client = app.test_client()
        store = app.extensions["sti_batch_store"]

        with patch.object(store, "create", wraps=store.create) as create:
            response = client.post(
                "/batch/upload",
                data={
                    "file": (
                        io.BytesIO(marker + (b"x" * 1024)),
                        "oversized.csv",
                    )
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn(marker, response.data)
        self.assertNotIn(b"Traceback", response.data)
        create.assert_not_called()

    def test_csv_payload_limit_remains_distinct_below_request_ceiling(self) -> None:
        app = create_app(
            {
                "TESTING": True,
                "MAX_CONTENT_LENGTH": 4096,
                "MAX_BATCH_BYTES": 5,
            },
            analysis_gateway=gateway(),
        )
        response = app.test_client().post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(b"text\nlonger\n"),
                    "payload-limit.csv",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"exceeds the 5-byte limit", response.data)
        self.assertNotIn(b"request-body limit", response.data)

    def test_oversized_unparsed_post_is_413_without_analyzing_batch(self) -> None:
        app = create_app(
            {
                "TESTING": True,
                "MAX_CONTENT_LENGTH": 512,
                "MAX_BATCH_BYTES": 128,
                "MAX_BATCH_ROWS": 5,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=gateway(),
        )
        client = app.test_client()
        uploaded = client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(b"record_id,text\nrow-1,Synthetic text.\n"),
                    "small.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        token = workspace_url.rsplit("/", 1)[-1]
        store = app.extensions["sti_batch_store"]
        before = store.get(token)
        assert before is not None and before.result is None

        response = client.post(
            workspace_url + "/analyze",
            data=b"x" * 1024,
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        after = store.get(token)
        assert after is not None
        self.assertIsNone(after.result)
        self.assertEqual(after, before)

    def test_missing_upload_keeps_workspace_capacity_limit_visible(self) -> None:
        app = create_app(
            {"TESTING": True, "BATCH_WORKSPACE_CAPACITY": 3},
            analysis_gateway=gateway(),
        )
        response = app.test_client().post(
            "/batch/upload",
            data={},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose a UTF-8 CSV file", response.data)
        self.assertIn(b"3 concurrent temporary batch workspaces", response.data)

    def test_capacity_blocks_new_upload_without_destroying_linked_state(
        self,
    ) -> None:
        app = create_app(
            {
                "TESTING": True,
                "BATCH_WORKSPACE_CAPACITY": 1,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=gateway(),
        )
        client = app.test_client()
        content = b"record_id,text\nrow-1,A synthetic success.\n"
        first = client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "first.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(first.status_code, 302)
        workspace_url = first.headers["Location"]
        self.assertEqual(client.post(workspace_url + "/analyze").status_code, 302)
        batch_token = workspace_url.rsplit("/", 1)[-1]
        linked = client.post(
            "/triage/start",
            data={"mode": "independent", "batch_token": batch_token},
        )
        self.assertEqual(linked.status_code, 302)
        linked_url = linked.headers["Location"]

        blocked = client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "second.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertIn(b"capacity reached", blocked.data)
        self.assertIn(b"Existing work was not removed", blocked.data)
        self.assertIn(b"Sentiment distribution", client.get(workspace_url).data)
        self.assertEqual(
            client.get(workspace_url + "/review", follow_redirects=True).status_code,
            200,
        )
        self.assertEqual(client.get(workspace_url + "/insights").status_code, 200)
        self.assertEqual(client.get(linked_url).status_code, 200)

        cleared = client.post(
            workspace_url + "/clear", data={"confirm": "clear"}
        )
        self.assertEqual(cleared.status_code, 302)
        recovered = client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "third.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(recovered.status_code, 302)
        self.assertEqual(client.get(linked_url).status_code, 200)

    def test_analysis_write_back_failure_is_explicit_and_recoverable(self) -> None:
        content = b"record_id,text\nrow-1,A synthetic success.\n"
        uploaded = self.client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "synthetic.csv")},
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        store = self.app.extensions["sti_batch_store"]

        with patch.object(store, "complete_analysis", return_value=False):
            failed = self.client.post(workspace_url + "/analyze")

        self.assertEqual(failed.status_code, 409)
        self.assertIn(b"result could not be saved", failed.data)
        self.assertIn(b"No success was recorded", failed.data)
        workspace = store.get(workspace_url.rsplit("/", 1)[-1])
        self.assertIsNotNone(workspace)
        assert workspace is not None
        self.assertIsNone(workspace.result)
        self.assertEqual(
            self.client.post(workspace_url + "/analyze").status_code,
            302,
        )
