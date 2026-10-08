"""Pure view models for the Results and Import & validation pages (no Qt).

Counts are row counts over the analysed rows, written out so a bar is only a picture of
a number. A row that has no result says why in words (rejected at import, or failed in
analysis) and never as colour alone. No record text is held here.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.language import (
    describe_language,
    describe_summary,
    language_short,
)
from ..application.results_workflow import (
    ResultRow,
    ResultsFilters,
    ResultsStatus,
    RowProblem,
)
from ..contracts import EmotionLabel, SentimentLabel
from .results import ResultsActivity, ResultsState
from .review_view import NATIVE_LABEL

EXPORT_LABEL = "Export normalized CSV…"
NO_MATCH_LINE = "No rows match these filters."
ALL_READY_LINE = "Every row is ready to analyse."
ACTIVATION_NOTE = (
    "Independent multi-label threshold activations; the rates do not sum to 100%."
)
SENTIMENT_NOTE = "Mutually exclusive dominant labels, shown as row counts."
DOMINANT_NOTE = "One selected dominant compact label per analysed row."
REJECTED = "✕ Rejected at import"
FAILED = "✕ Failed"
ANALYSED = "✓ Analysed"
NO_VALUE = "—"

STATUS_CHOICES = (
    ("All rows", ResultsStatus.ALL),
    ("Analysed", ResultsStatus.OK),
    ("Not analysed", ResultsStatus.ERROR),
)


@dataclass(frozen=True, slots=True)
class BarView:
    label: str
    value: int
    fraction: float
    text: str


@dataclass(frozen=True, slots=True)
class DistributionView:
    title: str
    caption: str
    bars: tuple[BarView, ...]


@dataclass(frozen=True, slots=True)
class TableRowView:
    row: int
    record_id: str
    status_word: str
    sentiment: str
    dominant: str
    detail: str  # secondary emotions, or the reason the row has no result
    language: str
    language_warns: bool
    can_review: bool

    @property
    def accessible_name(self) -> str:
        return (
            f"Row {self.row}, {self.record_id}. {self.status_word.lstrip('✓✕ ')}. "
            f"Sentiment {self.sentiment}. Dominant emotion {self.dominant}. "
            f"{self.detail}."
        )


@dataclass(frozen=True, slots=True)
class ResultsView:
    subtitle: str
    status_tabs: tuple[tuple[str, str, int], ...]  # label, filter value, row count
    sentiment: DistributionView
    dominant: DistributionView
    activation: DistributionView
    failed_count: int
    rows: tuple[TableRowView, ...]
    shown_line: str
    filters_active: bool
    selected: tuple[str, str, str]  # status, sentiment, emotion filter values
    sentiment_choices: tuple[tuple[str, str], ...]
    emotion_choices: tuple[tuple[str, str], ...]
    empty_line: str
    language_headline: str
    language_detail: str
    language_warns: bool
    export_label: str
    native_label: str
    export_enabled: bool


@dataclass(frozen=True, slots=True)
class ProblemView:
    row: int
    record_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ValidationView:
    summary_line: str
    column_line: str
    ignored_line: str
    problems: tuple[ProblemView, ...]  # rejected when the CSV was prepared
    failures: tuple[ProblemView, ...]  # valid rows whose analysis failed
    all_ready_line: str


def _name(value: str) -> str:
    return value.replace("_", " ").title()


def _percent(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "—"


def _rows_word(count: int) -> str:
    return f"{count} row" if count == 1 else f"{count} rows"


def filters_from(status: str, sentiment: str, emotion: str) -> ResultsFilters:
    """Rebuild typed filters from the choice values a widget reports."""

    return ResultsFilters(
        status=ResultsStatus(status),
        sentiment=None if sentiment == "all" else SentimentLabel(sentiment),
        emotion=None if emotion == "all" else EmotionLabel(emotion),
    )


def _table_row(row: ResultRow) -> TableRowView:
    notice = describe_language(row.language) if row.language is not None else None
    short = language_short(row.language) if row.language is not None else NO_VALUE
    if row.status == "ok":
        status = ANALYSED
        detail = ", ".join(_name(label.value) for label in row.secondary_emotions)
        detail = detail or "none"
    else:
        status = REJECTED if row.rejected_at_import else FAILED
        detail = f"{row.error_code or 'error'}: {row.error_message or ''}".rstrip(": ")
    return TableRowView(
        row=row.row_number,
        record_id=row.record_id,
        status_word=status,
        sentiment=_name(row.sentiment.value) if row.sentiment else NO_VALUE,
        dominant=_name(row.dominant_emotion.value)
        if row.dominant_emotion
        else NO_VALUE,
        detail=detail,
        language=short,
        language_warns=bool(notice and notice.warns),
        can_review=row.status == "ok",
    )


def build_results_view(state: ResultsState) -> ResultsView | None:
    results = state.results
    if results is None:
        return None
    aggregates = results.aggregates
    analysed = aggregates.analyzed_count
    rejected = len(state.validation.invalid_rows) if state.validation else 0
    failed = aggregates.failed_count - rejected
    parts = [f"{analysed} analysed", f"{failed} failed"]
    if rejected:
        parts.append(f"{rejected} rejected at import")
    filters = results.filters
    active = filters != ResultsFilters()
    rows = tuple(_table_row(row) for row in results.rows)
    notice = describe_summary(results.language)
    return ResultsView(
        subtitle=" · ".join(parts),
        status_tabs=(
            ("All rows", ResultsStatus.ALL.value, results.total_rows),
            ("Analysed", ResultsStatus.OK.value, analysed),
            ("Not analysed", ResultsStatus.ERROR.value, aggregates.failed_count),
        ),
        sentiment=DistributionView(
            "AI sentiment · rows",
            SENTIMENT_NOTE,
            tuple(
                BarView(
                    _name(label.value),
                    count,
                    count / analysed if analysed else 0.0,
                    f"{_rows_word(count)} · {_percent(count, analysed)}",
                )
                for label, count in aggregates.sentiment_counts
            ),
        ),
        dominant=DistributionView(
            "AI dominant emotion · rows",
            DOMINANT_NOTE,
            tuple(
                BarView(
                    _name(label.value),
                    count,
                    count / analysed if analysed else 0.0,
                    f"{_rows_word(count)} · {_percent(count, analysed)}",
                )
                for label, count in aggregates.dominant_emotion_counts
            ),
        ),
        activation=DistributionView(
            "Compact activation rate",
            ACTIVATION_NOTE,
            tuple(
                BarView(
                    _name(item.label.value),
                    item.active_count,
                    item.rate,
                    f"{item.rate * 100:.1f}% · {item.active_count} of "
                    f"{item.analyzed_count}",
                )
                for item in aggregates.activation_rates
            ),
        ),
        failed_count=aggregates.failed_count,
        rows=rows,
        shown_line=(
            f"{len(rows)} of {results.total_rows} rows match the filters"
            if active
            else _rows_word(results.total_rows)
        ),
        filters_active=active,
        selected=(
            filters.status.value,
            filters.sentiment.value if filters.sentiment else "all",
            filters.emotion.value if filters.emotion else "all",
        ),
        sentiment_choices=(
            ("Any sentiment", "all"),
            *((_name(label.value), label.value) for label in SentimentLabel),
        ),
        emotion_choices=(
            ("Any dominant emotion", "all"),
            *((_name(label.value), label.value) for label in EmotionLabel),
        ),
        empty_line=NO_MATCH_LINE if not rows else "",
        language_headline=notice.headline if notice else "",
        language_detail=notice.detail if notice else "",
        language_warns=bool(notice and notice.warns),
        export_label=EXPORT_LABEL,
        native_label=NATIVE_LABEL,
        export_enabled=state.activity is ResultsActivity.IDLE,
    )


def _problem(problem: RowProblem, prefix: str) -> ProblemView:
    return ProblemView(
        problem.row_number,
        problem.record_id,
        f"{prefix} · {problem.code}: {problem.message}",
    )


def build_validation_view(state: ResultsState) -> ValidationView | None:
    validation = state.validation
    if validation is None:
        return None
    problems = tuple(
        _problem(item, "Rejected at import") for item in validation.invalid_rows
    )
    failures = tuple(
        _problem(item, "Failed in analysis") for item in validation.failed_rows
    )
    line = (
        f"{validation.total_rows} rows · {validation.valid_rows} ready · "
        f"{len(validation.invalid_rows)} with problems"
    )
    return ValidationView(
        summary_line=line,
        column_line=f"Text column: {validation.text_column}",
        ignored_line=(
            "Ignored untrusted columns: " + ", ".join(validation.ignored_columns)
            if validation.ignored_columns
            else ""
        ),
        problems=problems,
        failures=failures,
        all_ready_line=ALL_READY_LINE if not problems and not failures else "",
    )
