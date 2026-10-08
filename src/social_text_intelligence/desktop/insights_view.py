"""Pure view models for the Insights surface (no Qt).

Every number shown here is the service's own number: the denominators, the sample-size
assessment, and the review populations are read from ``GroupMetricSummary`` and never
recomputed. The wording is descriptive on purpose: agreement is never accuracy, the
language grouping is always "as supplied", and a human-written note is always labelled
as human context, apart from every AI and review value.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.insights_workflow import (
    INSIGHT_METRICS_BY_PERSPECTIVE,
    ContextAssociation,
    ContextNote,
    ContextTag,
    ExampleMode,
    GroupingDimension,
    GroupMetricSummary,
    InsightMetric,
    InsightPerspective,
    InsightsSnapshot,
    RepresentativeExample,
    SampleSizeLevel,
    outcome_report,
)
from ..application.language import describe_language, describe_summary
from ..application.review_workflow import HumanReview
from ..contracts import EmotionLabel, SentimentLabel
from .insights import InsightsActivity, InsightsNotice, InsightsState

LIMITATIONS = (
    "Descriptive, not causal. These values describe only the data in this project. "
    "Groups come from the fields you supplied, not from inferred identities. AI labels "
    "estimate how a text is expressed; they do not establish feelings, intent, "
    "culture, or traits of a person or a community. Human-reviewed values describe "
    "only the reviewed records that count for that metric, and agreement is not "
    "accuracy."
)
CASES_NOTE = (
    "Cases are picked by the rule shown, to help you find records to read. They are "
    "not representative of every person, record, or community, and a rule does not "
    "diagnose sarcasm, intent, or culture. Confidence figures are the model's own "
    "scores, not calibrated probabilities."
)
NOTES_NOTE = (
    "Notes are written by you. They stay apart from AI predictions, review labels, "
    "scores, and agreement, and they never reclassify a record."
)
EXPORT_NOTE = (
    "The export contains the view last shown (after Show this view), not control "
    "changes you have not applied. Nothing is written until you choose a file. It "
    "can contain record text when you include supporting records, and it always "
    "contains your notes."
)

GROUPING_LABELS = {
    GroupingDimension.SOURCE_TYPE: "Source type",
    GroupingDimension.SOURCE_LABEL: "Source label",
    GroupingDimension.TOPIC: "Topic",
    GroupingDimension.COMMUNITY: "Community",
    GroupingDimension.LANGUAGE: "Language (as supplied in the file)",
    GroupingDimension.TIMESTAMP_MONTH: "Month (from the supplied timestamp)",
}
PERSPECTIVE_LABELS = {
    InsightPerspective.AI: "AI",
    InsightPerspective.HUMAN: "Human-reviewed",
    InsightPerspective.AGREEMENT: "AI and human agreement",
}
METRIC_LABELS = {
    InsightMetric.AI_SENTIMENT: "AI sentiment",
    InsightMetric.AI_DOMINANT_EMOTION: "AI dominant emotion",
    InsightMetric.AI_EMOTION_ACTIVATION: "AI emotion activation",
    InsightMetric.HUMAN_SENTIMENT: "Human sentiment",
    InsightMetric.HUMAN_DOMINANT_EMOTION: "Human dominant emotion",
    InsightMetric.HUMAN_EMOTION_INCLUSION: "Human emotion inclusion",
    InsightMetric.SENTIMENT_DISAGREEMENT: "Sentiment disagreement",
    InsightMetric.DOMINANT_EMOTION_DISAGREEMENT: "Dominant-emotion disagreement",
    InsightMetric.EMOTION_SET_DISAGREEMENT: "Emotion-set disagreement",
    InsightMetric.REVIEW_COVERAGE: "Review coverage",
}
MODE_LABELS = {
    ExampleMode.HIGHEST_AI_SCORE: "Highest AI emotion score",
    ExampleMode.LOWEST_AI_CONFIDENCE: "Lowest AI confidence",
    ExampleMode.AI_HUMAN_DISAGREEMENT: "AI and human disagreement",
    ExampleMode.HUMAN_CORRECTED: "Corrected by a human",
    ExampleMode.UNCERTAIN: "Marked uncertain by a human",
    ExampleMode.CONTEXT_NOTES: "Has a context note",
    ExampleMode.USER_SELECTED: "Records you select",
}
ASSOCIATION_LABELS = {
    ContextAssociation.RECORD: "Record",
    ContextAssociation.TOPIC: "Topic",
    ContextAssociation.COMMUNITY: "Community",
    ContextAssociation.SOURCE_LABEL: "Source label",
    ContextAssociation.COMPARISON: "Current comparison",
}
NOTE_HEADING = "Your context note (human-written, not AI output)"
AI_CASE_HEADING = "AI record (read-only)"
HUMAN_CASE_HEADING = "Human judgment (yours)"


def _words(value: str) -> str:
    text = value.replace("_", " ")
    return text[:1].upper() + text[1:]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


@dataclass(frozen=True, slots=True)
class MetricRowView:
    label: str
    count_text: str
    percent_text: str
    fraction: float = 0.0  # the rate, for a bar; the written text carries the value
    emphasized: bool = True  # False when the sample is too small to stress a rate


@dataclass(frozen=True, slots=True)
class GroupCardView:
    heading: str
    context_line: str
    failed_line: str
    sample_line: str | None
    rows: tuple[MetricRowView, ...]
    review_line: str
    language_line: str = ""
    tone: str = "ai"  # "ai" for the model's labels, "human" for the person's

    @property
    def accessible_name(self) -> str:
        parts = [self.heading, self.context_line]
        if self.sample_line:
            parts.append(self.sample_line)
        return ". ".join(parts)


@dataclass(frozen=True, slots=True)
class NoteView:
    note_id: str
    heading: str
    phrase: str
    subtitle: str
    explanation: str
    importance: str
    tags_line: str
    created_line: str
    delete_label: str


@dataclass(frozen=True, slots=True)
class CaseView:
    row_number: int
    reason: str
    title: str
    text: str
    ai_heading: str
    ai_line: str
    human_heading: str
    human_line: str
    language_headline: str = ""
    language_detail: str = ""
    language_warns: bool = False


@dataclass(frozen=True, slots=True)
class InsightsView:
    grouping_choices: tuple[tuple[str, str], ...]
    perspective_choices: tuple[tuple[str, str], ...]
    metric_choices: tuple[tuple[str, str], ...]
    sentiment_choices: tuple[tuple[str, str], ...]
    emotion_choices: tuple[tuple[str, str], ...]
    group_choices: tuple[tuple[str, bool], ...]
    group_hint: str
    controls_echo: InsightsControlsEcho
    definition_line: str
    filters_line: str
    cards: tuple[GroupCardView, ...]
    comparison_caution: str | None
    error_message: str
    provenance_lines: tuple[str, ...]
    notes: tuple[NoteView, ...]
    association_choices: tuple[tuple[str, str], ...]
    note_value_choices: dict[ContextAssociation, tuple[str, ...]]
    tag_choices: tuple[tuple[str, str], ...]
    example_mode_choices: tuple[tuple[str, str], ...]
    example_emotion_choices: tuple[tuple[str, str], ...]
    example_tag_choices: tuple[tuple[str, str], ...]
    record_choices: tuple[tuple[str, bool], ...]
    cases: tuple[CaseView, ...]
    cases_empty_line: str
    controls_enabled: bool
    apply_enabled: bool
    add_note_enabled: bool
    export_enabled: bool
    unsaved: bool
    notice: InsightsNotice | None
    # The language check over every analysed text in the project, as a caveat on
    # every figure below. It changes no metric and no grouping.
    language_headline: str | None = None
    language_detail: str = ""
    language_warns: bool = False


@dataclass(frozen=True, slots=True)
class InsightsControlsEcho:
    """The control values the widgets should currently show."""

    grouping: str
    perspective: str
    metric: str
    sentiment: str
    emotion: str
    date_from: str
    date_to: str
    comparison: bool
    example_mode: str
    example_emotion: str
    example_tag: str


def _card(summary: GroupMetricSummary, *, ai_view: bool) -> GroupCardView:
    sample = summary.sample
    sample_line = None
    if sample.message:
        sample_line = sample.message
        if sample.level is SampleSizeLevel.INSUFFICIENT:
            sample_line += "; comparative emphasis is suppressed."
    rows = tuple(
        MetricRowView(
            _words(value.label),
            f"{value.count} / {value.denominator}",
            f"{value.rate * 100:.1f}%"
            if sample.emphasize_percentages
            else "Percentage de-emphasized",
            value.rate,
            sample.emphasize_percentages,
        )
        for value in summary.values
    )
    return GroupCardView(
        heading=summary.group,
        context_line=(
            f"{summary.eligible_count} eligible for this metric · group has "
            f"{_plural(summary.total_count, 'row')} "
            f"({summary.successful_count} analysed successfully)"
        ),
        failed_line=(
            f"{_plural(summary.failed_count, 'failed row')} assigned to this group · "
            f"{_plural(summary.unassigned_failed_count, 'failed row')} unassigned "
            "across this grouping. Failed rows are never counted in a metric."
        ),
        sample_line=sample_line,
        rows=rows,
        review_line=(
            ""
            if ai_view
            else f"{summary.unreviewed_count} unreviewed · {summary.uncertain_count} "
            "uncertain. Eligibility is metric-specific."
        ),
        language_line=(
            f"⚠ {summary.language_attention_count} of "
            f"{summary.filtered_successful_count} analysed texts here are not "
            "confirmed as a supported language. They are still counted above."
            if summary.language_attention_count
            else ""
        ),
        tone="ai" if ai_view else "human",
    )


def _comparison_caution(snapshot: InsightsSnapshot) -> str | None:
    if not snapshot.comparison:
        return None
    weak = [s.group for s in snapshot.summaries if not s.sample.allow_comparison]
    if not weak:
        return None
    return (
        "Compare with care: too few eligible rows in "
        + ", ".join(weak)
        + " for a reliable comparison. Differences there may be chance."
    )


def _note_view(note: ContextNote) -> NoteView:
    tags = ", ".join(_words(tag.value).lower() for tag in note.tags) or "none"
    return NoteView(
        note_id=note.note_id,
        heading=NOTE_HEADING,
        phrase=note.phrase,
        subtitle=f"{ASSOCIATION_LABELS[note.association]}: {note.association_value}",
        explanation=note.explanation,
        importance=f"Why context matters: {note.context_importance}",
        tags_line=f"Tags: {tags}",
        created_line=f"Written {note.created_at.strftime('%Y-%m-%d %H:%M')} UTC",
        delete_label=f"Delete note: {note.phrase}",
    )


def _human_line(review: HumanReview | None) -> str:
    if review is None:
        return "No review entry for this record."
    if review.is_reviewed:
        status = "Reviewed"
    elif review.sentiment_judgment or review.emotion_judgment:
        status = "Partly reviewed"
    else:
        status = "Unreviewed"
    sentiment = (
        _words(review.human_sentiment.value) if review.human_sentiment else "not set"
    )
    dominant = (
        _words(review.human_dominant_emotion.value)
        if review.human_dominant_emotion
        else "not set"
    )
    return f"{status} · Sentiment: {sentiment} · Dominant emotion: {dominant}"


def _case(example: RepresentativeExample) -> CaseView:
    report = outcome_report(example.outcome)
    language = describe_language(report.language)
    return CaseView(
        row_number=example.outcome.prepared.row_number,
        reason=f"Why shown: {example.reason}",
        title=f"Row {example.outcome.prepared.row_number} · "
        f"{example.outcome.prepared.identity}",
        text=report.record.text,
        ai_heading=AI_CASE_HEADING,
        ai_line=(
            f"Sentiment {_words(report.sentiment.label.value)} "
            f"(confidence {report.sentiment.confidence * 100:.1f}%) · Emotion "
            f"{_words(report.emotion.dominant_emotion.value)} "
            f"(confidence {report.emotion.confidence * 100:.1f}%)"
        ),
        human_heading=HUMAN_CASE_HEADING,
        human_line=_human_line(example.review),
        language_headline=language.headline,
        language_detail=language.detail,
        language_warns=language.warns,
    )


def _groups_valid(state: InsightsState) -> bool:
    controls = state.controls
    if controls is None:
        return False
    count = len(controls.groups)
    return 2 <= count <= 4 if controls.comparison else count >= 1


def build_insights_view(state: InsightsState) -> InsightsView | None:
    snapshot, controls = state.snapshot, state.controls
    if snapshot is None or controls is None:
        return None
    idle = state.activity is InsightsActivity.IDLE
    selection = snapshot.selection
    ai_view = selection.perspective is InsightPerspective.AI
    filters = selection.filters
    report = snapshot.provenance
    examples = state.examples
    language = describe_summary(snapshot.language)
    return InsightsView(
        grouping_choices=tuple(
            (GROUPING_LABELS[g], g.value) for g in GroupingDimension
        ),
        perspective_choices=tuple(
            (PERSPECTIVE_LABELS[p], p.value) for p in InsightPerspective
        ),
        metric_choices=tuple(
            (METRIC_LABELS[m], m.value)
            for m in INSIGHT_METRICS_BY_PERSPECTIVE[controls.perspective]
        ),
        sentiment_choices=(
            ("Any AI sentiment", ""),
            *((_words(s.value), s.value) for s in SentimentLabel),
        ),
        emotion_choices=(
            ("Any AI dominant emotion", ""),
            *((_words(e.value), e.value) for e in EmotionLabel),
        ),
        group_choices=tuple(
            (group, group in controls.groups)
            for group in snapshot.groups_for(controls.grouping)
        ),
        group_hint=(
            "Choose two to four groups to compare."
            if controls.comparison
            else "Choose one or more groups to show."
        ),
        controls_echo=InsightsControlsEcho(
            grouping=controls.grouping.value,
            perspective=controls.perspective.value,
            metric=controls.metric.value,
            sentiment=controls.sentiment.value if controls.sentiment else "",
            emotion=controls.emotion.value if controls.emotion else "",
            date_from=controls.date_from,
            date_to=controls.date_to,
            comparison=controls.comparison,
            example_mode=examples.mode.value,
            example_emotion=examples.emotion.value,
            example_tag=examples.tag.value if examples.tag else "",
        ),
        definition_line=snapshot.metric_definition,
        filters_line=(
            f"Showing {GROUPING_LABELS[selection.grouping].lower()} · "
            f"{PERSPECTIVE_LABELS[selection.perspective]} · "
            f"{METRIC_LABELS[selection.metric]}. Filters: sentiment "
            f"{filters.sentiment.value if filters.sentiment else 'all'}, dominant "
            f"emotion {filters.emotion.value if filters.emotion else 'all'}, dates "
            f"{filters.date_from or 'unbounded'} to {filters.date_to or 'unbounded'}."
        ),
        cards=tuple(_card(s, ai_view=ai_view) for s in snapshot.summaries),
        comparison_caution=_comparison_caution(snapshot),
        error_message=snapshot.error_message or "",
        provenance_lines=(
            f"Sentiment model: {report.sentiment.provider.model_name}@"
            f"{report.sentiment.provider.revision}",
            f"Emotion model: {report.emotion.provider.model_name}@"
            f"{report.emotion.provider.revision} (activation threshold at least "
            f"{report.emotion.threshold:.2f})",
        ),
        notes=tuple(_note_view(n) for n in snapshot.notes),
        association_choices=tuple(
            (ASSOCIATION_LABELS[a], a.value) for a in ContextAssociation
        ),
        note_value_choices={
            ContextAssociation.RECORD: snapshot.record_ids,
            ContextAssociation.TOPIC: snapshot.association_choices(
                ContextAssociation.TOPIC
            ),
            ContextAssociation.COMMUNITY: snapshot.association_choices(
                ContextAssociation.COMMUNITY
            ),
            ContextAssociation.SOURCE_LABEL: snapshot.association_choices(
                ContextAssociation.SOURCE_LABEL
            ),
            ContextAssociation.COMPARISON: (),
        },
        tag_choices=tuple((_words(t.value), t.value) for t in ContextTag),
        example_mode_choices=tuple((MODE_LABELS[m], m.value) for m in ExampleMode),
        example_emotion_choices=tuple(
            (_words(e.value), e.value)
            for e in EmotionLabel
            if e is not EmotionLabel.NEUTRAL
        ),
        example_tag_choices=(
            ("Any tag", ""),
            *((_words(t.value), t.value) for t in ContextTag),
        ),
        record_choices=tuple(
            (record_id, record_id in examples.record_ids)
            for record_id in snapshot.record_ids
        ),
        cases=tuple(_case(e) for e in snapshot.examples),
        cases_empty_line="No records meet this rule." if not snapshot.examples else "",
        controls_enabled=idle,
        apply_enabled=idle and _groups_valid(state),
        add_note_enabled=idle and state.has_unsaved_changes,
        export_enabled=idle,
        unsaved=state.has_unsaved_changes,
        notice=state.notice,
        language_headline=None if language is None else language.headline,
        language_detail="" if language is None else language.detail,
        language_warns=language is not None and language.warns,
    )
