"""Typed application contracts for normalized text analysis."""

from .errors import (
    InvalidProviderOutputError,
    ProviderError,
    SocialTextIntelligenceError,
    UnsupportedLanguageError,
    ValidationError,
)
from .inputs import NormalizedTextInput, SourceType
from .results import (
    AnalysisReport,
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    NativeScore,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    TaskType,
)

__all__ = [
    "AnalysisReport",
    "EmotionLabel",
    "EmotionResult",
    "EmotionScore",
    "InvalidProviderOutputError",
    "NativeScore",
    "NormalizedTextInput",
    "ProviderError",
    "ProviderMetadata",
    "SentimentLabel",
    "SentimentResult",
    "SentimentScore",
    "SocialTextIntelligenceError",
    "SourceType",
    "TaskType",
    "UnsupportedLanguageError",
    "ValidationError",
]
