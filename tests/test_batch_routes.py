"""End-to-end Flask batch workflow tests with synthetic CSV data."""

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

        cleared = self.client.post(workspace_url + "/clear")
        self.assertEqual(cleared.status_code, 302)
        self.assertEqual(self.client.get(workspace_url).status_code, 404)

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
