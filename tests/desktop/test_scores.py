"""The score breakdown shown beside a model result (Qt-free view model)."""

from __future__ import annotations

from desktop.fakes import synthetic_report
from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.desktop.scores import build_scores
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService


def report(
    sentiment: SentimentLabel = SentimentLabel.POSITIVE,
    emotion: EmotionLabel = EmotionLabel.JOY,
) -> AnalysisReport:
    return AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(sentiment),
        emotion_provider=DeterministicEmotionProvider(emotion),
    ).analyze(NormalizedTextInput.from_text("A synthetic note.", max_text_length=100))


def test_the_three_sentiment_scores_are_listed_with_the_chosen_label_marked() -> None:
    scores = build_scores(report(SentimentLabel.NEGATIVE, EmotionLabel.ANGER))

    by_label = {row.label: row for row in scores.sentiment}
    assert set(by_label) == {"Positive", "Negative", "Neutral"}
    assert (by_label["Negative"].text, by_label["Negative"].note) == (
        "0.800",
        "highest",
    )
    assert (by_label["Positive"].text, by_label["Positive"].note) == ("0.100", "")
    assert by_label["Negative"].fraction == 0.8  # the bar is the score itself


def test_all_nine_compact_emotions_are_listed_with_dominant_and_secondary_named() -> (
    None
):
    scores = build_scores(report(emotion=EmotionLabel.JOY))

    assert len(scores.emotion) == 9
    notes = {row.label: row.note for row in scores.emotion}
    assert notes["Joy"] == "dominant"
    assert notes["Amusement"] == ""
    # the deterministic provider's secondary emotion for joy is gratitude (0.60 >= 0.50)
    assert notes["Gratitude"] == "secondary"
    assert sum(1 for note in notes.values() if note) == 2


def test_the_threshold_rule_is_stated_with_the_threshold_in_use() -> None:
    scores = build_scores(report(emotion=EmotionLabel.JOY))

    assert "0.50" in scores.emotion_rule
    assert "fallback" not in scores.emotion_rule.lower()


def test_neutral_with_nothing_above_the_threshold_is_explained_as_a_fallback() -> None:
    scores = build_scores(report(SentimentLabel.NEUTRAL, EmotionLabel.NEUTRAL))

    assert "fallback" in scores.emotion_rule.lower()
    assert "no non-neutral" in scores.emotion_rule.lower()


def test_the_model_native_scores_follow_the_provider_label_order() -> None:
    value = synthetic_report()

    scores = build_scores(value)

    assert [row.label for row in scores.native] == [
        item.label.replace("_", " ").title() for item in value.emotion.native_scores
    ]
    assert all(0.0 <= row.fraction <= 1.0 for row in scores.native)


def test_no_score_is_called_a_probability_or_a_confidence_in_the_note() -> None:
    scores = build_scores(report())

    words = " ".join(
        [scores.emotion_rule, *(row.note for row in scores.emotion)]
    ).lower()
    assert "probab" not in words and "calibrat" not in words


def test_the_scores_carry_the_activation_threshold_for_the_chart() -> None:
    scores = build_scores(report(emotion=EmotionLabel.JOY))

    assert scores.threshold == 0.5
