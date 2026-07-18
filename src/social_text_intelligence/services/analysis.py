"""Provider-neutral analysis orchestration without logging or persistence."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.inputs import NormalizedTextInput
from ..contracts.results import AnalysisReport, SentimentResult
from ..providers.base import EmotionProvider, SentimentProvider


@dataclass(frozen=True, slots=True)
class AnalysisService:
    sentiment_provider: SentimentProvider
    emotion_provider: EmotionProvider

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        """Analyze one record while preserving provider and result boundaries."""

        sentiment = self.sentiment_provider.analyze(record)
        emotion = self.emotion_provider.analyze(record)
        return AnalysisReport(record=record, sentiment=sentiment, emotion=emotion)


@dataclass(frozen=True, slots=True)
class SentimentAnalysisService:
    """Orchestrate one sentiment prediction without invoking emotion analysis."""

    sentiment_provider: SentimentProvider

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        return self.sentiment_provider.analyze(record)
