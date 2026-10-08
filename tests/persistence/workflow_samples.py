"""Synthetic CSV and gateway helpers shared by the project-workflow tests."""

from __future__ import annotations

from collections.abc import Callable

from social_text_intelligence.contracts import AnalysisReport, NormalizedTextInput
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService

SENTINEL = "ZQX-private-sentinel-77"


def csv_text(rows: int = 5, column: str = "text") -> bytes:
    lines = [f"record_id,{column}"]
    lines += [
        f"r{n},{SENTINEL} synthetic message number {n}." for n in range(1, rows + 1)
    ]
    return ("\n".join(lines) + "\n").encode()


class ScriptedGateway:
    """Deterministic analysis with a hook before each row."""

    initialized = True

    def __init__(self, before_row: Callable[[int], None] | None = None) -> None:
        self._service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(),
            emotion_provider=DeterministicEmotionProvider(),
        )
        self.before_row = before_row
        self.calls = 0

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        self.calls += 1
        if self.before_row is not None:
            self.before_row(self.calls)
        return self._service.analyze(record)
