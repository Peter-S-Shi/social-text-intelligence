"""The Agreement page view model, from literal summaries (no code under test used)."""

from __future__ import annotations

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.desktop.agreement_view import build_agreement_view
from social_text_intelligence.services.review import (
    ConfidenceBand,
    ConfidenceComparison,
    ConfusionRow,
    EmotionLabelComparison,
    EmotionReviewSummary,
    ReviewProgress,
    ReviewSummary,
    SentimentReviewSummary,
)

NEG, NEU, POS = SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL, SentimentLabel.POSITIVE


def confusion(
    counts: dict[tuple[SentimentLabel, SentimentLabel], int],
) -> tuple[ConfusionRow, ...]:
    return tuple(
        ConfusionRow(
            ai,
            tuple((human, counts.get((ai, human), 0)) for human in (POS, NEG, NEU)),
        )
        for ai in (POS, NEG, NEU)
    )


def summary(
    *,
    reviewed: int = 29,
    sentiment_definitive: int = 28,
    sentiment_agree: int = 23,
    emotion_definitive: int = 28,
    bands_sentiment: tuple[ConfidenceBand, ...] = (),
    bands_emotion: tuple[ConfidenceBand, ...] = (),
) -> ReviewSummary:
    return ReviewSummary(
        progress=ReviewProgress(
            total_records=48,
            reviewable_records=46,
            reviewed=reviewed,
            unreviewed=46 - reviewed,
            corrected=5,
            uncertain=2,
        ),
        sentiment=SentimentReviewSummary(
            definitive_count=sentiment_definitive,
            agreement_count=sentiment_agree,
            corrected_count=sentiment_definitive - sentiment_agree,
            correction_distribution=((POS, 2), (NEG, 2), (NEU, 1)),
            confusion=confusion(
                {
                    (NEG, NEG): 12,
                    (NEG, POS): 2,
                    (NEU, NEU): 5,
                    (POS, POS): 6,
                    (POS, NEG): 1,
                    (POS, NEU): 2,
                }
            ),
        ),
        emotion=EmotionReviewSummary(
            definitive_count=emotion_definitive,
            dominant_agreement_count=20,
            set_agreement_count=18,
            label_comparisons=(
                EmotionLabelComparison(EmotionLabel.JOY, 3, 1, 9),
                EmotionLabelComparison(EmotionLabel.ANGER, 0, 2, 4),
            ),
            most_added=((EmotionLabel.SADNESS, 3), (EmotionLabel.FEAR, 0)),
            most_removed=((EmotionLabel.JOY, 3),),
        ),
        confidence=ConfidenceComparison(
            sentiment=bands_sentiment, dominant_emotion=bands_emotion
        ),
    )


def test_the_three_agreement_figures_show_their_denominators() -> None:
    view = build_agreement_view(summary())

    figures = {f.label: f for f in view.figures}
    assert figures["Sentiment agreement"].value == "82.1%"
    assert figures["Sentiment agreement"].caption == "23 of 28 definitive reviews"
    assert figures["Dominant emotion agreement"].value == "71.4%"
    assert (
        figures["Dominant emotion agreement"].caption == "20 of 28 definitive reviews"
    )
    assert figures["Exact emotion set agreement"].value == "64.3%"
    assert "18 of 28" in figures["Exact emotion set agreement"].caption


def test_with_no_definitive_review_a_figure_is_a_dash_not_zero_percent() -> None:
    view = build_agreement_view(
        summary(
            reviewed=0, sentiment_definitive=0, sentiment_agree=0, emotion_definitive=0
        )
    )

    assert all(f.value == "—" for f in view.figures)
    assert all("No definitive reviews" in f.caption for f in view.figures)
    assert "No definitive reviews yet" in view.empty_line


def test_the_subtitle_says_how_much_is_reviewed_and_what_is_left_out() -> None:
    view = build_agreement_view(summary())

    assert view.subtitle.startswith("29 of 46 reviewed")
    assert "uncertain" in view.subtitle.lower()


def test_the_confusion_table_puts_ai_rows_against_human_columns() -> None:
    view = build_agreement_view(summary())

    assert view.confusion.columns == ("Negative", "Neutral", "Positive")
    rows = {row.ai_label: row for row in view.confusion.rows}
    negative = rows["Negative"]
    assert [cell.count for cell in negative.cells] == [12, 0, 2]
    assert [cell.match for cell in negative.cells] == [True, False, False]
    assert "AI negative, you positive: 2" in negative.cells[2].accessible_name
    assert [cell.count for cell in rows["Positive"].cells] == [1, 2, 6]


def test_corrections_are_listed_as_the_human_label_after_correcting() -> None:
    view = build_agreement_view(summary())

    assert view.corrections == ("2 to positive", "2 to negative", "1 to neutral")


def test_emotion_labels_are_compared_as_ai_only_human_only_and_shared() -> None:
    view = build_agreement_view(summary())

    joy = view.label_comparison[0]
    assert (joy.label, joy.ai_only, joy.human_only, joy.shared) == ("Joy", 3, 1, 9)
    assert "Most added by you: Sadness (3)" in view.added_removed_line
    assert "Most removed by you: Joy (3)" in view.added_removed_line


def test_with_nothing_added_or_removed_it_says_none() -> None:
    quiet = summary()
    view = build_agreement_view(quiet)

    assert "Fear" not in view.added_removed_line  # a zero count is not listed
    from dataclasses import replace

    empty = replace(
        quiet, emotion=replace(quiet.emotion, most_added=(), most_removed=())
    )
    assert "none" in build_agreement_view(empty).added_removed_line


def test_confidence_bands_appear_only_with_five_definitive_reviews() -> None:
    bands = (ConfidenceBand("0.50–0.74", 4, 13), ConfidenceBand("0.90–1.00", 0, 8))
    view = build_agreement_view(summary(bands_sentiment=bands))

    sentiment, emotion = view.confidence
    assert sentiment.available is True
    assert [(b.label, b.text) for b in sentiment.bands] == [
        ("0.50–0.74", "4 / 13 disagreements · 30.8%"),
        ("0.90–1.00", "0 / 8 disagreements · 0.0%"),
    ]
    assert sentiment.bands[0].fraction == 4 / 13
    assert emotion.available is False
    assert "at least five definitive reviews" in emotion.unavailable_line
    assert "(28 so far)" in emotion.unavailable_line


def test_the_page_never_calls_agreement_accuracy() -> None:
    view = build_agreement_view(summary())

    assert "not accuracy" in view.note.lower()
    assert "descriptive" in view.confidence_note.lower()
    assert (
        "calibrated" in view.confidence_note.lower()
    )  # "not claimed to be calibrated"


def test_with_no_correction_the_page_says_so() -> None:
    from dataclasses import replace

    base = summary()
    quiet = replace(
        base,
        sentiment=replace(
            base.sentiment, correction_distribution=((POS, 0), (NEG, 0), (NEU, 0))
        ),
    )

    view = build_agreement_view(quiet)

    assert view.corrections == ()
    assert view.corrections_empty_line == "No corrections yet."
