"""A synthetic 26-row project for insight tests; no real or private data.

Counts (all derived from the rows below, not from the code under test):

* topic ``shipping``: 12 analysed rows (4 positive/joy, 4 negative/anger, 4 neutral)
  plus 1 row the gateway fails on, so 13 rows in the group;
* topic ``billing``: 7 analysed rows (3 negative/anger, 4 neutral) plus 1 row that
  fails validation (a bad timestamp), so 8 rows in the group;
* topic ``returns``: 3 analysed rows (all positive/joy);
* no topic (``(not supplied)``): 2 analysed neutral rows.
"""

from __future__ import annotations

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.contracts.errors import ProviderError
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService

SENTINEL = "ZQX-insight-sentinel-91"
FAIL_TEXT = "FAILME"


def _row(
    n: int,
    kind: str,
    topic: str,
    community: str,
    timestamp: str,
) -> str:
    text = {"joy": "joyful", "anger": "angry", "plain": "plain", "fail": FAIL_TEXT}[
        kind
    ]
    return f"r{n},{SENTINEL} {text} message {n},{topic},{community},{timestamp},en"


def insights_csv() -> bytes:
    rows = ["record_id,text,topic,community,timestamp,language"]
    n = 0

    def add(kind: str, topic: str, community: str, timestamp: str) -> None:
        nonlocal n
        n += 1
        rows.append(_row(n, kind, topic, community, timestamp))

    for _ in range(4):  # r1-r4 shipping joy, north, January
        add("joy", "shipping", "north", "2026-01-05T10:00:00Z")
    for _ in range(2):  # r5-r6 shipping anger, north, January
        add("anger", "shipping", "north", "2026-01-06T10:00:00Z")
    for _ in range(2):  # r7-r8 shipping anger, south, February
        add("anger", "shipping", "south", "2026-02-10T10:00:00Z")
    for _ in range(4):  # r9-r12 shipping plain, south, February
        add("plain", "shipping", "south", "2026-02-11T10:00:00Z")
    for _ in range(3):  # r13-r15 billing anger, south
        add("anger", "billing", "south", "2026-02-12T10:00:00Z")
    for _ in range(4):  # r16-r19 billing plain, south
        add("plain", "billing", "south", "2026-02-13T10:00:00Z")
    for _ in range(3):  # r20-r22 returns joy, north
        add("joy", "returns", "north", "2026-01-15T10:00:00Z")
    for _ in range(2):  # r23-r24 no topic, plain
        add("plain", "", "north", "2026-01-16T10:00:00Z")
    add("fail", "shipping", "north", "2026-01-20T10:00:00Z")  # r25 gateway fails
    add("plain", "billing", "south", "not-a-date")  # r26 fails validation
    return ("\n".join(rows) + "\n").encode()


class VariedGateway:
    """Deterministic analysis whose labels follow a keyword in the text."""

    initialized = True

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if FAIL_TEXT in record.text:
            raise ProviderError(
                provider="synthetic", code="synthetic_failure", message="Row failed."
            )
        sentiment, emotion = SentimentLabel.NEUTRAL, EmotionLabel.NEUTRAL
        if "joyful" in record.text:
            sentiment, emotion = SentimentLabel.POSITIVE, EmotionLabel.JOY
        elif "angry" in record.text:
            sentiment, emotion = SentimentLabel.NEGATIVE, EmotionLabel.ANGER
        return AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(sentiment),
            emotion_provider=DeterministicEmotionProvider(emotion),
        ).analyze(record)
