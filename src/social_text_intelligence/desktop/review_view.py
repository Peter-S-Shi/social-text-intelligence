"""Pure view models for the Review surface (no Qt).

The immutable AI record and the human judgment are built as two separate blocks with
their own headings, so the widgets can never present a prediction as editable or the
human's choice as the model's. Status is always a word plus an icon, never colour
alone, and agreement is always worded as agreement, never as accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.language import describe_language
from ..application.review_workflow import (
    MAX_REVIEW_NOTE_LENGTH,
    ReviewFilter,
    ReviewFilters,
    ReviewJudgment,
    ReviewRecord,
    ReviewSnapshot,
)
from ..contracts import AnalysisReport, EmotionLabel, SentimentLabel
from .review import ReviewActivity, ReviewNotice, ReviewState
from .scores import ScoreSetView, build_scores

AGREEMENT_NOTE = (
    "Agreement shows how often your judgment matched the AI's label. It is not "
    "accuracy: accepting means acceptable in context, not objectively true, and "
    "records you marked uncertain are left out."
)
AI_HEADING = "AI record (read-only, not editable)"
HUMAN_HEADING = "Your judgment"
EXPORT_LABEL = "Export reviewed CSV…"
NATIVE_LABEL = "Include model-native emotion scores in the export"
NO_ROWS_LINE = (
    "No rows were analysed successfully, so there is nothing to review in this project."
)

STATUS_FILTERS = (
    ("All records", ReviewFilter.ALL),
    ("Unreviewed", ReviewFilter.UNREVIEWED),
    ("Reviewed", ReviewFilter.REVIEWED),
    ("Corrected", ReviewFilter.CORRECTED),
    ("Marked uncertain", ReviewFilter.UNCERTAIN),
)
JUDGMENT_WORDS = (
    (ReviewJudgment.ACCEPT, "Accept"),
    (ReviewJudgment.CORRECT, "Correct"),
    (ReviewJudgment.UNCERTAIN, "Uncertain"),
)


@dataclass(frozen=True, slots=True)
class AiRecordView:
    heading: str
    sentiment_line: str
    emotion_line: str
    secondary_line: str
    scores: ScoreSetView
    provenance: tuple[str, ...]

    @property
    def accessible_name(self) -> str:
        return f"{self.heading}. {self.sentiment_line}. {self.emotion_line}."


@dataclass(frozen=True, slots=True)
class HumanJudgmentView:
    heading: str
    status_word: str
    status_icon: str
    sentiment_judgment: ReviewJudgment | None
    human_sentiment: SentimentLabel | None
    emotion_judgment: ReviewJudgment | None
    human_dominant_emotion: EmotionLabel | None
    human_secondary_emotions: tuple[EmotionLabel, ...]
    note: str
    sentiment_label_visible: bool
    emotion_labels_visible: bool
    note_counter: str

    @property
    def status(self) -> str:
        return f"{self.status_icon} {self.status_word}"


@dataclass(frozen=True, slots=True)
class RecordView:
    row_number: int
    title: str
    text: str
    context: tuple[str, ...]
    ai: AiRecordView
    human: HumanJudgmentView
    # The language check: evidence about the text, shown beside (not inside) the AI
    # labels and apart from the language the file supplied.
    language_headline: str
    language_detail: str
    language_warns: bool


@dataclass(frozen=True, slots=True)
class ReviewView:
    position_line: str
    progress_line: str
    failed_line: str
    record: RecordView | None
    empty_line: str
    previous_enabled: bool
    next_enabled: bool
    next_unreviewed_enabled: bool
    accept_both_enabled: bool
    save_enabled: bool
    controls_enabled: bool  # false while an operation runs
    unsaved: bool
    status_filter_choices: tuple[tuple[str, str], ...]
    sentiment_filter_choices: tuple[tuple[str, str], ...]
    emotion_filter_choices: tuple[tuple[str, str], ...]
    filters: ReviewFilters
    notice: ReviewNotice | None


def filters_from(status: str, sentiment: str, emotion: str) -> ReviewFilters:
    """Rebuild typed filters from the choice values a widget reports."""

    return ReviewFilters(
        status=ReviewFilter(status),
        sentiment=None if sentiment == "all" else SentimentLabel(sentiment),
        emotion=None if emotion == "all" else EmotionLabel(emotion),
    )


def _ai_view(report: AnalysisReport) -> AiRecordView:
    sentiment, emotion = report.sentiment, report.emotion
    secondary = ", ".join(label.value for label in emotion.secondary_emotions)
    return AiRecordView(
        heading=AI_HEADING,
        sentiment_line=(
            f"{sentiment.label.value.capitalize()} · confidence "
            f"{sentiment.confidence * 100:.1f}%"
        ),
        emotion_line=(
            f"{emotion.dominant_emotion.value.capitalize()} · confidence "
            f"{emotion.confidence * 100:.1f}% · threshold ≥ {emotion.threshold:.2f}"
        ),
        secondary_line=f"Secondary emotions: {secondary or 'none'}",
        scores=build_scores(report),
        provenance=(
            f"Sentiment model: {sentiment.provider.model_name}@"
            f"{sentiment.provider.revision}",
            f"Emotion model: {emotion.provider.model_name}@{emotion.provider.revision}",
        ),
    )


def _status(record: ReviewRecord) -> tuple[str, str]:
    review = record.review
    if review.is_reviewed:
        return "✓", "Reviewed"
    if review.sentiment_judgment is not None or review.emotion_judgment is not None:
        return "◐", "Partly reviewed"
    return "○", "Unreviewed"


def _counter(note: str) -> str:
    remaining = MAX_REVIEW_NOTE_LENGTH - len(note)
    if remaining < 0:
        return (
            f"{-remaining} characters over the {MAX_REVIEW_NOTE_LENGTH}-character limit"
        )
    return f"{remaining} character{'' if remaining == 1 else 's'} left"


def _human_view(state: ReviewState, record: ReviewRecord) -> HumanJudgmentView:
    draft = state.draft
    icon, word = _status(record)
    return HumanJudgmentView(
        heading=HUMAN_HEADING,
        status_word=word,
        status_icon=icon,
        sentiment_judgment=draft.sentiment_judgment,
        human_sentiment=draft.human_sentiment,
        emotion_judgment=draft.emotion_judgment,
        human_dominant_emotion=draft.human_dominant_emotion,
        human_secondary_emotions=draft.human_secondary_emotions,
        note=draft.note,
        sentiment_label_visible=draft.sentiment_judgment is ReviewJudgment.CORRECT,
        emotion_labels_visible=draft.emotion_judgment is ReviewJudgment.CORRECT,
        note_counter=_counter(draft.note),
    )


def _context(record: ReviewRecord) -> tuple[str, ...]:
    source = record.report.record
    return (
        f"Language supplied in the file: {record.supplied_language or 'not supplied'}",
        f"Source: {source.source_label or source.source_type.value}",
        f"Topic: {source.topic or 'not supplied'}",
        f"Community: {source.community or 'not supplied'}",
        "Timestamp: "
        + (source.timestamp.isoformat() if source.timestamp else "not supplied"),
    )


def _record_view(state: ReviewState, record: ReviewRecord) -> RecordView:
    language = describe_language(record.report.language)
    return RecordView(
        row_number=record.row_number,
        title=f"Row {record.row_number} · {record.report.record.record_id}",
        text=record.report.record.text,
        context=_context(record),
        ai=_ai_view(record.report),
        human=_human_view(state, record),
        language_headline=language.headline,
        language_detail=language.detail,
        language_warns=language.warns,
    )


def _progress(snapshot: ReviewSnapshot) -> tuple[str, str]:
    progress = snapshot.summary.progress
    line = (
        f"{progress.reviewed} of {progress.reviewable_records} reviewed · "
        f"{progress.corrected} corrected · {progress.uncertain} marked uncertain · "
        f"{progress.unreviewed} unreviewed"
    )
    failed = progress.total_records - progress.reviewable_records
    if failed <= 0:
        return line, ""
    noun = "row" if failed == 1 else "rows"
    return line, (
        f"{failed} {noun} could not be analysed and "
        f"{'is' if failed == 1 else 'are'} not reviewable. They stay in the "
        "exported file."
    )


def _position(snapshot: ReviewSnapshot) -> str:
    if snapshot.record is None:
        return "No records to review"
    line = f"Record {snapshot.position} of {snapshot.queue_total}"
    if snapshot.filtered_count != snapshot.queue_total:
        line += f" · {snapshot.filtered_count} match the filters"
    return line


def _choices(labels: tuple[str, ...], any_label: str) -> tuple[tuple[str, str], ...]:
    return (
        (any_label, "all"),
        *((label.capitalize(), label) for label in labels),
    )


def build_review_view(state: ReviewState) -> ReviewView | None:
    snapshot = state.snapshot
    if snapshot is None:
        return None
    idle = state.activity is ReviewActivity.IDLE
    record = snapshot.record
    progress_line, failed_line = _progress(snapshot)
    changed = state.has_unsaved_changes
    return ReviewView(
        position_line=_position(snapshot),
        progress_line=progress_line,
        failed_line=failed_line,
        record=None if record is None else _record_view(state, record),
        empty_line=NO_ROWS_LINE if record is None else "",
        previous_enabled=idle and snapshot.previous_row is not None,
        next_enabled=idle and snapshot.next_row is not None,
        next_unreviewed_enabled=idle and snapshot.next_unreviewed_row is not None,
        accept_both_enabled=idle and record is not None,
        save_enabled=idle and record is not None and changed,
        controls_enabled=idle,
        unsaved=changed,
        status_filter_choices=tuple((label, f.value) for label, f in STATUS_FILTERS),
        sentiment_filter_choices=_choices(
            tuple(label.value for label in SentimentLabel), "Any AI sentiment"
        ),
        emotion_filter_choices=_choices(
            tuple(label.value for label in EmotionLabel), "Any AI dominant emotion"
        ),
        filters=state.filters,
        notice=state.notice,
    )
