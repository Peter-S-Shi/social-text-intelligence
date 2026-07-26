"""Provider abstractions and deterministic testing implementations."""

from .base import EmotionProvider, SentimentProvider
from .cardiff_sentiment import (
    MODEL_ID,
    MODEL_REVISION,
    CardiffSentimentProvider,
    SentimentRuntime,
    TransformersSentimentRuntime,
    preprocess_social_text,
)
from .mock import DeterministicEmotionProvider, DeterministicSentimentProvider
from .moderation_mock import (
    FixtureModerationRecommendationProvider,
    ModerationRecommendationProvider,
)
from .samlowe_emotion import (
    COMPACT_EMOTION_MAPPING,
    DEFAULT_EMOTION_THRESHOLD,
    EMOTION_MODEL_ID,
    EMOTION_MODEL_REVISION,
    NATIVE_EMOTION_LABELS,
    UNMAPPED_NATIVE_LABELS,
    EmotionRuntime,
    SamLoweEmotionProvider,
    TransformersEmotionRuntime,
)
from .triage_mock import (
    FixtureTriageSuggestionProvider,
    TriageSuggestionProvider,
)

__all__ = [
    "COMPACT_EMOTION_MAPPING",
    "CardiffSentimentProvider",
    "DEFAULT_EMOTION_THRESHOLD",
    "DeterministicEmotionProvider",
    "DeterministicSentimentProvider",
    "FixtureModerationRecommendationProvider",
    "ModerationRecommendationProvider",
    "EMOTION_MODEL_ID",
    "EMOTION_MODEL_REVISION",
    "EmotionProvider",
    "EmotionRuntime",
    "MODEL_ID",
    "MODEL_REVISION",
    "NATIVE_EMOTION_LABELS",
    "SamLoweEmotionProvider",
    "SentimentRuntime",
    "SentimentProvider",
    "TransformersEmotionRuntime",
    "TransformersSentimentRuntime",
    "UNMAPPED_NATIVE_LABELS",
    "preprocess_social_text",
    "FixtureTriageSuggestionProvider",
    "TriageSuggestionProvider",
]
