"""Focused browser-boundary regressions for the loopback Flask interface."""

import io
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from werkzeug.test import TestResponse

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface import create_app
from social_text_intelligence.interface.app import CONTENT_SECURITY_POLICY
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


class BrowserSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = gateway()
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 10_000,
                "MAX_BATCH_ROWS": 10,
                "MAX_TEXT_LENGTH": 200,
            },
            analysis_gateway=self.gateway,
        )
        self.client = self.app.test_client()

    def assert_security_headers(self, response: TestResponse) -> None:
        headers = response.headers
        self.assertEqual(headers["Content-Security-Policy"], CONTENT_SECURITY_POLICY)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "same-origin")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("Strict-Transport-Security", headers)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def create_analyzed_batch(self) -> tuple[str, str]:
        content = (
            b"record_id,text,language,topic\n"
            b"row-1,A synthetic browser boundary sample.,en,launch\n"
        )
        uploaded = self.client.post(
            "/batch/upload",
            data={"file": (io.BytesIO(content), "synthetic.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 302)
        workspace_path = urlsplit(uploaded.headers["Location"]).path
        analyzed = self.client.post(f"{workspace_path}/analyze")
        self.assertEqual(analyzed.status_code, 302)
        return workspace_path, workspace_path.rsplit("/", 1)[-1]

    def test_approved_loopback_hosts_and_same_origin_posts_work(self) -> None:
        for base_url in (
            "http://localhost",
            "http://localhost:8765",
            "http://127.0.0.1",
            "http://127.0.0.1:8765",
        ):
            with self.subTest(base_url=base_url):
                response = self.client.get("/", base_url=base_url)
                self.assertEqual(response.status_code, 200)

        same_origin = self.client.post(
            "/",
            base_url="http://127.0.0.1:8765",
            headers={"Origin": "http://127.0.0.1:8765"},
            data={"text": "A same-origin synthetic input."},
        )
        same_referer = self.client.post(
            "/",
            headers={"Referer": "http://localhost/local/form"},
            data={"text": "A same-origin Referer fallback input."},
        )
        no_browser_headers = self.client.post(
            "/", data={"text": "A local non-browser synthetic input."}
        )

        self.assertEqual(same_origin.status_code, 200)
        self.assertEqual(same_referer.status_code, 200)
        self.assertEqual(no_browser_headers.status_code, 200)

    def test_untrusted_host_is_private_400_before_direct_analysis(self) -> None:
        marker = "SYNTHETIC-UNTRUSTED-HOST-MARKER"
        response = self.client.post(
            "/",
            base_url="http://untrusted.invalid",
            data={"text": marker},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.gateway.initialized)
        self.assertNotIn(marker.encode(), response.data)
        self.assertNotIn(b"untrusted.invalid", response.data)
        self.assertNotIn(b"Traceback", response.data)
        self.assertNotIn(b"site-packages", response.data)
        self.assert_security_headers(response)

    def test_explicit_cross_origin_and_null_origin_are_private_403(self) -> None:
        marker = "SYNTHETIC-CROSS-ORIGIN-MARKER"
        for headers in (
            {"Origin": "https://external.invalid"},
            {"Origin": "http://localhost:9999"},
            {"Origin": "not-an-origin"},
            {"Origin": "null"},
            {"Referer": "https://external.invalid/form"},
        ):
            with self.subTest(headers=headers):
                local_gateway = gateway()
                app = create_app(
                    {"TESTING": True}, analysis_gateway=local_gateway
                )
                response = app.test_client().post(
                    "/", headers=headers, data={"text": marker}
                )
                self.assertEqual(response.status_code, 403)
                self.assertFalse(local_gateway.initialized)
                self.assertNotIn(marker.encode(), response.data)
                self.assertNotIn(b"external.invalid", response.data)
                self.assert_security_headers(response)

    def test_cross_origin_mutations_preserve_every_ephemeral_workspace(self) -> None:
        workspace_path, batch_token = self.create_analyzed_batch()
        batch_store = self.app.extensions["sti_batch_store"]
        batch_before = batch_store.get(batch_token)
        self.assertIsNotNone(batch_before)

        rejected_batch_requests = (
            (f"{workspace_path}/clear", {"confirm": "clear"}),
            (f"{workspace_path}/review/1", {"action": "accept_both"}),
            (f"{workspace_path}/insights/notes", {"phrase": "blocked"}),
        )
        for path, data in rejected_batch_requests:
            response = self.client.post(
                path,
                headers={"Origin": "https://external.invalid"},
                data=data,
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(batch_store.get(batch_token), batch_before)

        moderation_created = self.client.post("/moderation/start")
        moderation_path = urlsplit(moderation_created.headers["Location"]).path
        moderation_token = moderation_path.split("/")[2]
        moderation_store = self.app.extensions["sti_moderation_store"]
        moderation_before = moderation_store.get(moderation_token)
        moderation_rejected = self.client.post(
            f"/moderation/{moderation_token}/clear",
            headers={"Origin": "https://external.invalid"},
        )
        self.assertEqual(moderation_rejected.status_code, 403)
        self.assertEqual(moderation_store.get(moderation_token), moderation_before)

        triage_created = self.client.post(
            "/triage/start", data={"mode": "independent", "batch_token": ""}
        )
        triage_path = urlsplit(triage_created.headers["Location"]).path
        triage_token = triage_path.split("/")[2]
        triage_store = self.app.extensions["sti_triage_store"]
        triage_before = triage_store.get(triage_token)
        triage_rejected = self.client.post(
            f"/triage/{triage_token}/clear",
            headers={"Origin": "https://external.invalid"},
        )
        self.assertEqual(triage_rejected.status_code, 403)
        self.assertEqual(triage_store.get(triage_token), triage_before)

    def test_representative_responses_have_security_headers(self) -> None:
        html = self.client.get("/")
        missing = self.client.get("/missing")
        redirect = self.client.post(
            "/moderation/start", headers={"Origin": "http://localhost"}
        )
        css = self.client.get("/static/app.css")
        javascript = self.client.get("/static/batch.js")
        workspace_path, _token = self.create_analyzed_batch()
        csv_download = self.client.get(f"{workspace_path}/export.csv")

        limited_app = create_app(
            {
                "TESTING": True,
                "MAX_CONTENT_LENGTH": 128,
                "MAX_BATCH_BYTES": 64,
            },
            analysis_gateway=gateway(),
        )
        too_large = limited_app.test_client().post(
            "/", data={"text": "x" * 256}
        )

        for response in (
            html,
            missing,
            redirect,
            css,
            javascript,
            csv_download,
            too_large,
        ):
            self.assert_security_headers(response)
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(csv_download.mimetype, "text/csv")
        self.assertEqual(css.mimetype, "text/css")
        self.assertIn("javascript", javascript.mimetype or "")

    def test_templates_need_no_unsafe_inline_or_external_resources(self) -> None:
        template_dir = (
            Path(__file__).parents[1]
            / "src"
            / "social_text_intelligence"
            / "interface"
            / "templates"
        )
        for path in template_dir.glob("*.html"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(template=path.name):
                self.assertNotRegex(text, r"(?i)<style\b")
                self.assertNotRegex(text, r"(?i)\sstyle\s*=")
                self.assertNotRegex(text, r"(?i)\son[a-z]+\s*=")
                self.assertNotIn("http://", text)
                self.assertNotIn("https://", text)
                for attributes in re.findall(
                    r"(?is)<script\b([^>]*)>", text
                ):
                    self.assertRegex(attributes, r"(?i)\bsrc\s*=")


if __name__ == "__main__":
    unittest.main()
