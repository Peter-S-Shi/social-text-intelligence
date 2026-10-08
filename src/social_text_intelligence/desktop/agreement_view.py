"""Pure view model for the Agreement page (no Qt).

Agreement is how often the person's judgment matched the AI's label over *definitive*
reviews; it is never presented as accuracy. A figure with no definitive review is a
dash, not 0%. The confusion table, label comparison, correction counts, and confidence
bands are exactly what the review service computed; this module only words them.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.review_workflow import (
    MIN_CONFIDENCE_COMPARISON_REVIEWS,
    ConfidenceBand,
    ReviewSummary,
)
from ..contracts import SentimentLabel
from .review_view import AGREEMENT_NOTE

CONFIDENCE_NOTE = (
    "A descriptive comparison only: the AI's confidence is not claimed to be "
    "calibrated, and a band with few reviews says little."
)
EXPORT_LABEL = "Export reviewed CSV…"
_ORDER = (SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL, SentimentLabel.POSITIVE)
_FIVE = {5: "five"}


@dataclass(frozen=True, slots=True)
class FigureView:
    label: str
    value: str
    caption: str


@dataclass(frozen=True, slots=True)
class ConfusionCellView:
    count: int
    match: bool  # the AI label and the human label are the same
    accessible_name: str


@dataclass(frozen=True, slots=True)
class ConfusionRowView:
    ai_label: str
    cells: tuple[ConfusionCellView, ...]


@dataclass(frozen=True, slots=True)
class ConfusionView:
    columns: tuple[str, ...]
    rows: tuple[ConfusionRowView, ...]


@dataclass(frozen=True, slots=True)
class LabelComparisonView:
    label: str
    ai_only: int
    human_only: int
    shared: int


@dataclass(frozen=True, slots=True)
class BandView:
    label: str
    text: str
    fraction: float


@dataclass(frozen=True, slots=True)
class ConfidencePanelView:
    title: str
    available: bool
    bands: tuple[BandView, ...]
    unavailable_line: str


@dataclass(frozen=True, slots=True)
class AgreementView:
    subtitle: str
    figures: tuple[FigureView, ...]
    empty_line: str
    corrections: tuple[str, ...]
    corrections_empty_line: str
    confusion: ConfusionView
    label_comparison: tuple[LabelComparisonView, ...]
    added_removed_line: str
    confidence: tuple[ConfidencePanelView, ConfidencePanelView]
    confidence_note: str
    note: str
    export_label: str
    export_enabled: bool


def _name(value: str) -> str:
    return value.replace("_", " ").title()


def _percent(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "—"


def _figure(label: str, part: int, whole: int) -> FigureView:
    caption = (
        f"{part} of {whole} definitive reviews"
        if whole
        else "No definitive reviews yet"
    )
    return FigureView(label, _percent(part, whole), caption)


def _confusion(summary: ReviewSummary) -> ConfusionView:
    by_ai = {
        row.ai_label: dict(row.human_counts) for row in summary.sentiment.confusion
    }
    rows = []
    for ai in _ORDER:
        cells = []
        for human in _ORDER:
            count = by_ai.get(ai, {}).get(human, 0)
            relation = "agree" if ai is human else "differ"
            cells.append(
                ConfusionCellView(
                    count=count,
                    match=ai is human,
                    accessible_name=(
                        f"AI {ai.value}, you {human.value}: {count} ({relation})"
                    ),
                )
            )
        rows.append(ConfusionRowView(_name(ai.value), tuple(cells)))
    return ConfusionView(tuple(_name(label.value) for label in _ORDER), tuple(rows))


def _panel(
    title: str, bands: tuple[ConfidenceBand, ...], definitive: int
) -> ConfidencePanelView:
    if not bands:
        word = _FIVE[MIN_CONFIDENCE_COMPARISON_REVIEWS]
        return ConfidencePanelView(
            title,
            False,
            (),
            f"Available after at least {word} definitive reviews "
            f"({definitive} so far).",
        )
    return ConfidencePanelView(
        title,
        True,
        tuple(
            BandView(
                band.label,
                f"{band.disagreement_count} / {band.definitive_count} disagreements"
                f" · {_percent(band.disagreement_count, band.definitive_count)}",
                band.disagreement_rate,
            )
            for band in bands
        ),
        "",
    )


def _added_removed(summary: ReviewSummary) -> str:
    def listed(items: tuple[tuple[object, int], ...]) -> str:
        shown = [
            f"{_name(getattr(label, 'value', str(label)))} ({count})"
            for label, count in items
            if count
        ]
        return ", ".join(shown) or "none"

    emotion = summary.emotion
    return (
        f"Most added by you: {listed(emotion.most_added)}. "
        f"Most removed by you: {listed(emotion.most_removed)}."
    )


def build_agreement_view(summary: ReviewSummary) -> AgreementView:
    progress, sentiment, emotion = summary.progress, summary.sentiment, summary.emotion
    nothing_definitive = (
        sentiment.definitive_count == 0 and emotion.definitive_count == 0
    )
    return AgreementView(
        subtitle=(
            f"{progress.reviewed} of {progress.reviewable_records} reviewed · "
            "a dimension marked uncertain is left out of every denominator"
        ),
        figures=(
            _figure(
                "Sentiment agreement",
                sentiment.agreement_count,
                sentiment.definitive_count,
            ),
            _figure(
                "Dominant emotion agreement",
                emotion.dominant_agreement_count,
                emotion.definitive_count,
            ),
            _figure(
                "Exact emotion set agreement",
                emotion.set_agreement_count,
                emotion.definitive_count,
            ),
        ),
        empty_line=(
            "No definitive reviews yet. Agreement appears as you review records."
            if nothing_definitive
            else ""
        ),
        corrections=tuple(
            f"{count} to {label.value}"
            for label, count in sentiment.correction_distribution
            if count
        ),
        corrections_empty_line="No corrections yet.",
        confusion=_confusion(summary),
        label_comparison=tuple(
            LabelComparisonView(
                _name(item.label.value), item.ai_only, item.human_only, item.shared
            )
            for item in emotion.label_comparisons
        ),
        added_removed_line=_added_removed(summary),
        confidence=(
            _panel(
                "Sentiment",
                summary.confidence.sentiment,
                sentiment.definitive_count,
            ),
            _panel(
                "Dominant emotion",
                summary.confidence.dominant_emotion,
                emotion.definitive_count,
            ),
        ),
        confidence_note=CONFIDENCE_NOTE,
        note=AGREEMENT_NOTE,
        export_label=EXPORT_LABEL,
        export_enabled=progress.reviewable_records > 0,
    )
