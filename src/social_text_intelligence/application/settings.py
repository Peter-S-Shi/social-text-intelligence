"""Typed settings and composition for the shared analysis application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..contracts import AnalysisReport, NormalizedTextInput
from ..providers import CardiffSentimentProvider, SamLoweEmotionProvider
from ..providers.language_py3langid import Py3LangidDetector
from ..providers.samlowe_emotion import DEFAULT_EMOTION_THRESHOLD
from ..services import AnalysisService, LazyAnalysisService
from ..services.batch import DEFAULT_MAX_BATCH_BYTES, DEFAULT_MAX_BATCH_ROWS


class AnalysisGateway(Protocol):
    @property
    def initialized(self) -> bool: ...

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport: ...


@dataclass(frozen=True, slots=True)
class AppSettings:
    cache_dir: Path = Path("model_cache")
    offline: bool = False
    emotion_threshold: float = DEFAULT_EMOTION_THRESHOLD
    max_text_length: int = 20_000
    max_request_bytes: int = 3 * 1024 * 1024
    max_batch_bytes: int = DEFAULT_MAX_BATCH_BYTES
    max_batch_rows: int = DEFAULT_MAX_BATCH_ROWS
    workspace_ttl_seconds: int = 30 * 60
    workspace_capacity: int = 8

    def __post_init__(self) -> None:
        if self.max_request_bytes < 1:
            raise ValueError("MAX_CONTENT_LENGTH must be positive")
        if self.max_request_bytes <= self.max_batch_bytes:
            raise ValueError(
                "MAX_CONTENT_LENGTH must be greater than MAX_BATCH_BYTES so "
                "multipart encoding has separate request-level capacity."
            )
        if self.max_text_length < 1 or self.max_batch_rows < 1:
            raise ValueError("Text and batch row limits must be positive")


def build_analysis_service(settings: AppSettings) -> AnalysisGateway:
    """Construct models lazily; importing this module never loads model weights."""

    return LazyAnalysisService(lambda: pinned_analysis_service(settings))


def pinned_analysis_service(settings: AppSettings) -> AnalysisService:
    return AnalysisService(
        sentiment_provider=CardiffSentimentProvider(
            cache_dir=settings.cache_dir, offline=settings.offline
        ),
        emotion_provider=SamLoweEmotionProvider(
            cache_dir=settings.cache_dir,
            offline=settings.offline,
            threshold=settings.emotion_threshold,
        ),
        # Local and offline; reports itself unavailable if its package is missing.
        language_detector=Py3LangidDetector(),
    )
