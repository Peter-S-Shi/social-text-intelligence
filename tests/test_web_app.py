"""Flask route tests using deterministic local providers."""

import unittest

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
from social_text_intelligence.services import AnalysisService, LazyAnalysisService


def deterministic_gateway() -> LazyAnalysisService:
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
            provider="synthetic-provider",
            code="model_load_failed",
            message="Synthetic internal detail must not be rendered.",
        )


class WebAppTests(unittest.TestCase):
    def test_get_explains_local_mode_and_first_load(self) -> None:
        app = create_app(
            {"TESTING": True, "OFFLINE": True},
            analysis_gateway=deterministic_gateway(),
        )
        response = app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Offline mode", response.data)
        self.assertIn(b"load on first analysis", response.data)
        self.assertIn(b"Estimate, not diagnosis", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_post_renders_complete_combined_report(self) -> None:
        gateway = deterministic_gateway()
        app = create_app({"TESTING": True}, analysis_gateway=gateway)
        response = app.test_client().post(
            "/", data={"text": "A private synthetic browser input."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(gateway.initialized)
        self.assertIn(b"positive", response.data)
        self.assertIn(b"gratitude", response.data)
        self.assertIn(b"Threshold", response.data)
        self.assertIn(b"deterministic-sentiment@mock-v1", response.data)
        self.assertIn(b"Inspect all model-native emotion scores", response.data)
        self.assertIn(b"Secondary: joy", response.data)

    def test_neutral_result_explains_threshold_fallback(self) -> None:
        app = create_app(
            {"TESTING": True},
            analysis_gateway=LazyAnalysisService(
                lambda: AnalysisService(
                    sentiment_provider=DeterministicSentimentProvider(
                        SentimentLabel.NEUTRAL
                    ),
                    emotion_provider=DeterministicEmotionProvider(
                        EmotionLabel.NEUTRAL
                    ),
                )
            ),
        )
        response = app.test_client().post(
            "/", data={"text": "A synthetic neutral example."}
        )
        self.assertIn(b"Threshold fallback", response.data)
        self.assertIn(
            b"not a claim that the raw neutral score is the highest", response.data
        )

    def test_empty_and_oversized_text_are_safe_user_errors(self) -> None:
        app = create_app(
            {"TESTING": True, "MAX_TEXT_LENGTH": 5},
            analysis_gateway=deterministic_gateway(),
        )
        client = app.test_client()
        empty = client.post("/", data={"text": "   "})
        oversized = client.post("/", data={"text": "123456"})
        self.assertIn(b"at least one non-whitespace", empty.data)
        self.assertIn(b"exceeds 5 characters", oversized.data)
        self.assertNotIn(b"Traceback", empty.data + oversized.data)
        self.assertNotIn(b"positive", oversized.data)
        self.assertNotIn(b"gratitude", oversized.data)

    def test_provider_failure_does_not_expose_internal_detail(self) -> None:
        app = create_app(
            {"TESTING": True, "OFFLINE": True},
            analysis_gateway=FailingGateway(),
        )
        response = app.test_client().post("/", data={"text": "Safe input."})
        self.assertIn(b"could not be loaded", response.data)
        self.assertNotIn(b"Synthetic internal detail", response.data)
        self.assertNotIn(b"Traceback", response.data)
