"""Focused accessibility semantics and keyboard-recovery regressions."""

import io
import re
import unittest
from pathlib import Path

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface import create_app
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, LazyAnalysisService

TEMPLATES = (
    Path(__file__).parents[1]
    / "src"
    / "social_text_intelligence"
    / "interface"
    / "templates"
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


class AccessibilitySemanticsTests(unittest.TestCase):
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

    def test_full_pages_have_skip_target_and_no_keyboard_anti_patterns(self) -> None:
        for template in TEMPLATES.glob("*.html"):
            if template.name.startswith("_"):
                continue
            source = template.read_text(encoding="utf-8")
            with self.subTest(template=template.name):
                self.assertIn('class="skip-link" href="#main-content"', source)
                self.assertIn('<main id="main-content" tabindex="-1">', source)
                self.assertIsNone(re.search(r'tabindex="[1-9][0-9]*"', source))
                self.assertIsNone(
                    re.search(r'<(?:div|span)[^>]+(?:onclick=|role="button")', source)
                )
                self.assertNotIn("<th>", source)

    def test_direct_navigation_help_and_error_recovery_are_programmatic(self) -> None:
        initial = self.client.get("/")
        self.assertIn(b'aria-current="page"', initial.data)
        self.assertIn(b'aria-describedby="text-help"', initial.data)

        invalid = self.client.post("/", data={"text": "   "})
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b'role="alert"', invalid.data)
        self.assertIn(b'aria-invalid="true" autofocus', invalid.data)
        self.assertIn(b'aria-describedby="text-help text-error"', invalid.data)

    def test_batch_upload_and_running_state_have_accessible_contracts(self) -> None:
        invalid = self.client.post(
            "/batch/upload",
            data={},
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b'role="alert" tabindex="-1" autofocus', invalid.data)
        self.assertIn(
            b'aria-describedby="batch-file-help batch-error"', invalid.data
        )

        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(b"record_id,text\nrow-1,Synthetic keyboard row.\n"),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        page = self.client.get(uploaded.headers["Location"])
        self.assertIn(b'aria-current="page"', page.data)
        self.assertIn(b'role="status"', page.data)
        self.assertIn(b'aria-label="Batch analysis in progress"', page.data)
        self.assertIn(b'<th scope="col">Row</th>', page.data)

        script = self.client.get("/static/batch.js")
        self.assertIn(b'form.setAttribute("aria-busy", "true")', script.data)

    def test_workflow_navigation_exposes_current_page_or_step(self) -> None:
        moderation = self.client.get("/moderation")
        triage = self.client.get("/triage")
        self.assertIn(
            b'class="active" aria-current="page"', moderation.data
        )
        self.assertIn(b'class="active" aria-current="page"', triage.data)

        moderation_started = self.client.post(
            "/moderation/start", data={"batch_token": ""}
        )
        moderation_prepare = self.client.get(moderation_started.headers["Location"])
        self.assertIn(b'aria-current="step"', moderation_prepare.data)

        triage_started = self.client.post(
            "/triage/start", data={"mode": "independent", "batch_token": ""}
        )
        triage_guide = self.client.get(triage_started.headers["Location"])
        self.assertIn(b'aria-current="step"', triage_guide.data)

    def test_insight_multiselect_uses_separate_label_and_help(self) -> None:
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(
                        b"record_id,text,topic\n"
                        b"row-1,Synthetic insight row.,support\n"
                    ),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        self.client.post(workspace_url + "/analyze")

        insight = self.client.get(workspace_url + "/insights")
        self.assertIn(b'aria-current="page"', insight.data)
        self.assertIn(
            b'<label for="insight-groups">Displayed groups</label>', insight.data
        )
        self.assertIn(b'aria-describedby="insight-groups-help"', insight.data)


if __name__ == "__main__":
    unittest.main()
