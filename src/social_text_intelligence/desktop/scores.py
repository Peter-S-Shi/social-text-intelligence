"""The score breakdown shown beside a model result (Qt-free view model).

Three views of the same report, always in words and numbers (a bar is only a picture of
the number): the three sentiment scores, the nine compact emotion scores with the
threshold rule that picked the dominant and secondary emotions, and the model-native
emotion scores. A score is a model output, not a probability.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import AnalysisReport, EmotionLabel

NOTE_HIGHEST = "highest"
NOTE_DOMINANT = "dominant"
NOTE_SECONDARY = "secondary"


@dataclass(frozen=True, slots=True)
class ScoreRow:
    label: str
    fraction: float  # 0..1, the score itself, for a bar
    text: str  # the exact score, three decimals
    note: str = ""  # a word, so a highlight never relies on colour alone


@dataclass(frozen=True, slots=True)
class ScoreSetView:
    sentiment: tuple[ScoreRow, ...]
    emotion: tuple[ScoreRow, ...]
    emotion_rule: str
    native: tuple[ScoreRow, ...]


def _name(value: str) -> str:
    return value.replace("_", " ").title()


def _row(label: str, score: float, note: str = "") -> ScoreRow:
    return ScoreRow(_name(label), score, f"{score:.3f}", note)


def build_scores(report: AnalysisReport) -> ScoreSetView:
    sentiment, emotion = report.sentiment, report.emotion
    sentiment_rows = tuple(
        _row(
            item.label.value,
            item.score,
            NOTE_HIGHEST if item.label is sentiment.label else "",
        )
        for item in sentiment.scores
    )
    secondary = set(emotion.secondary_emotions)
    emotion_rows = tuple(
        _row(
            item.label.value,
            item.score,
            NOTE_DOMINANT
            if item.label is emotion.dominant_emotion
            else NOTE_SECONDARY
            if item.label in secondary
            else "",
        )
        for item in emotion.scores
    )
    rule = (
        "A compact emotion is active at or above the threshold "
        f"({emotion.threshold:.2f}). The dominant emotion is the highest active one; "
        "the others active are secondary."
    )
    fell_back = emotion.dominant_emotion is EmotionLabel.NEUTRAL and not any(
        item.label is not EmotionLabel.NEUTRAL and item.score >= emotion.threshold
        for item in emotion.scores
    )
    if fell_back:
        rule += (
            " Threshold fallback: no non-neutral compact emotion reached the "
            "threshold. Neutral here is a fallback state, not a claim that the raw "
            "neutral score is the highest score."
        )
    return ScoreSetView(
        sentiment=sentiment_rows,
        emotion=emotion_rows,
        emotion_rule=rule,
        native=tuple(_row(item.label, item.score) for item in emotion.native_scores),
    )
