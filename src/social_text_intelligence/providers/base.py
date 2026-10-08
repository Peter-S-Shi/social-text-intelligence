"""Stable provider interfaces independent of any model library."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts.inputs import NormalizedTextInput
from ..contracts.language import Detection, DetectorInfo
from ..contracts.results import EmotionResult, ProviderMetadata, SentimentResult


@runtime_checkable
class SentimentProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata:
        """Return traceable provider identity and native labels."""
        ...

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        """Analyze one normalized record without persistence side effects."""
        ...

    def validate_input(self, record: NormalizedTextInput) -> None:
        """Confirm the provider can consume the complete normalized record."""
        ...


@runtime_checkable
class EmotionProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata:
        """Return traceable provider identity and native labels."""
        ...

    def analyze(self, record: NormalizedTextInput) -> EmotionResult:
        """Analyze one normalized record without persistence side effects."""
        ...

    def validate_input(self, record: NormalizedTextInput) -> None:
        """Confirm the provider can consume the complete normalized record."""
        ...


@runtime_checkable
class LanguageDetector(Protocol):
    """Identify the language of text, locally and without side effects.

    A detector sees only the text: never supplied metadata, never a model label.
    """

    @property
    def info(self) -> DetectorInfo:
        """Return the identity needed to audit a result."""
        ...

    def detect(self, text: str) -> Detection:
        """Detect the language, or abstain; raise ``LanguageDetectorUnavailable``."""
        ...
