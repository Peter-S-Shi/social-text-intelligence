"""Synthetic language-aware analysis helpers (deterministic, no real detector)."""

from __future__ import annotations

from collections.abc import Callable

from social_text_intelligence.contracts import (
    AnalysisReport,
    Detection,
    DetectorInfo,
    LanguageReason,
    NormalizedTextInput,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService

INFO = DetectorInfo(name="fake", version="1.0", model="fake-model", min_score=0.5)
FRENCH, SHORT = "bonjour", "ok"


class KeywordDetector:
    """English unless the text says otherwise: ``bonjour`` is French, ``ok`` unclear."""

    info = INFO

    def detect(self, text: str) -> Detection:
        if FRENCH in text:
            return Detection(language="fr", score=0.97)
        if SHORT in text.split():
            return Detection(language=None, reason=LanguageReason.LOW_SCORE)
        return Detection(language="en", score=0.99)


class LanguageGateway:
    """The shared analysis service with a fake detector, plus a hook per row."""

    initialized = True

    def __init__(self, before_row: Callable[[int], None] | None = None) -> None:
        self._service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(),
            emotion_provider=DeterministicEmotionProvider(),
            language_detector=KeywordDetector(),
        )
        self.before_row = before_row
        self.calls = 0

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        self.calls += 1
        if self.before_row is not None:
            self.before_row(self.calls)
        return self._service.analyze(record)


def mixed_language_csv() -> bytes:
    """Supplied and detected language disagree on purpose.

    r1 supplied en, English text          -> supported
    r2 supplied en, French text           -> unsupported (supplied stays en)
    r3 supplied fr, English text          -> supported (supplied stays fr)
    r4 no supplied language, French text  -> unsupported
    r5 supplied en, a very short text     -> undetermined
    """

    return (
        b"record_id,text,language\n"
        b"r1,Everything arrived on time.,en\n"
        b"r2,bonjour tout le monde merci,en\n"
        b"r3,Everything arrived on time.,fr\n"
        b"r4,bonjour encore une fois,\n"
        b"r5,ok,en\n"
    )
