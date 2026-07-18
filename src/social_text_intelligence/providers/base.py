"""Stable provider interfaces independent of any model library."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts.inputs import NormalizedTextInput
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


@runtime_checkable
class EmotionProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata:
        """Return traceable provider identity and native labels."""
        ...

    def analyze(self, record: NormalizedTextInput) -> EmotionResult:
        """Analyze one normalized record without persistence side effects."""
        ...
