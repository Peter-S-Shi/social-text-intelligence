"""Provider-neutral analysis orchestration without logging or persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..contracts.inputs import NormalizedTextInput
from ..contracts.results import AnalysisReport, SentimentResult
from ..providers.base import EmotionProvider, LanguageDetector, SentimentProvider
from .language import assess_language


@dataclass(frozen=True, slots=True)
class AnalysisService:
    sentiment_provider: SentimentProvider
    emotion_provider: EmotionProvider
    language_detector: LanguageDetector | None = None

    @property
    def supported_languages(self) -> tuple[str, ...]:
        """Languages every approved model covers, from the models' own metadata."""

        sentiment = self.sentiment_provider.metadata.supported_languages
        emotion = self.emotion_provider.metadata.supported_languages
        shared = {item.lower() for item in sentiment}
        shared &= {item.lower() for item in emotion}
        return tuple(sorted(shared))

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        """Analyze one record while preserving provider and result boundaries."""

        # The models never see a supplied language tag: whether a text is in a
        # language they support is decided from the text itself, below.
        model_input = replace(record, language=None)
        # Preflight every required provider before either model performs inference.
        self.sentiment_provider.validate_input(model_input)
        self.emotion_provider.validate_input(model_input)
        sentiment = self.sentiment_provider.analyze(model_input)
        emotion = self.emotion_provider.analyze(model_input)
        language = assess_language(
            self.language_detector, record.text, self.supported_languages
        )
        return AnalysisReport(
            record=record, sentiment=sentiment, emotion=emotion, language=language
        )


@dataclass(frozen=True, slots=True)
class SentimentAnalysisService:
    """Orchestrate one sentiment prediction without invoking emotion analysis."""

    sentiment_provider: SentimentProvider

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        return self.sentiment_provider.analyze(record)
