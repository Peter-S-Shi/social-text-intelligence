"""The Results and Import & validation view models over a real stored project."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from persistence.insight_samples import SENTINEL, VariedGateway, insights_csv

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.results_workflow import (
    ResultsFilters,
    ResultsStatus,
    ResultsWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.desktop.results import (
    ResultsActivity,
    ResultsController,
    ResultsState,
)
from social_text_intelligence.desktop.results_view import (
    build_results_view,
    build_validation_view,
    filters_from,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


def loaded(root: Path, *, analyse: bool = True) -> ResultsController:
    repository = SqliteProjectRepository(AppDataLocations(root))
    flow = ProjectWorkflow(repository, VariedGateway(), LIMITS)
    project_id = flow.import_csv(insights_csv(), name="P").summary.project_id
    if analyse:
        flow.analyze(project_id)
    controller = ResultsController(ResultsWorkflow(repository), ImmediateRunner())
    controller.open(project_id)
    return controller


@pytest.fixture
def controller(tmp_path: Path) -> ResultsController:
    return loaded(tmp_path)


def test_the_subtitle_and_tabs_count_what_was_analysed_and_what_was_not(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    assert view.subtitle == "24 analysed · 1 failed · 1 rejected at import"
    assert [(label, count) for label, _, count in view.status_tabs] == [
        ("All rows", 26),
        ("Analysed", 24),
        ("Not analysed", 2),
    ]
    assert [value for _, value, _ in view.status_tabs] == ["all", "ok", "error"]


def test_sentiment_and_dominant_emotion_are_row_counts_with_their_share(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    sentiment = {bar.label: bar for bar in view.sentiment.bars}
    assert (sentiment["Positive"].value, sentiment["Positive"].fraction) == (7, 7 / 24)
    assert sentiment["Neutral"].text == "10 rows · 41.7%"
    emotions = {bar.label: bar.value for bar in view.dominant.bars}
    assert len(emotions) == 9
    assert (emotions["Joy"], emotions["Anger"], emotions["Neutral"]) == (7, 7, 10)
    assert "mutually exclusive" in view.sentiment.caption.lower()


def test_activation_rates_are_independent_and_say_they_need_not_sum_to_100(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    rates = {bar.label: bar for bar in view.activation.bars}
    assert "Neutral" not in rates and len(rates) == 8
    # joy-dominant rows (7) plus the joy secondary of the anger rows (7), of 24
    assert rates["Joy"].text == "58.3% · 14 of 24"
    assert rates["Gratitude"].text == "29.2% · 7 of 24"
    assert "not sum to 100%" in view.activation.caption


def test_each_row_has_a_status_in_words_and_a_reason_when_it_has_no_result(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    rows = view.rows
    assert len(rows) == 26
    first, failed, rejected = rows[0], rows[24], rows[25]
    assert (first.status_word, first.sentiment, first.dominant) == (
        "✓ Analysed",
        "Positive",
        "Joy",
    )
    assert first.can_review is True
    assert failed.status_word == "✕ Failed"
    assert failed.detail == "synthetic_failure: Row failed."
    assert failed.sentiment == "—" and failed.can_review is False
    assert rejected.status_word == "✕ Rejected at import"
    assert rejected.record_id == "r26" and ": " in rejected.detail
    assert SENTINEL not in repr(view)


def test_an_analysed_row_lists_its_secondary_emotions_or_none(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    joy_row, plain_row = view.rows[0], view.rows[8]  # r1 joy, r9 plain
    assert joy_row.detail == "Gratitude"
    assert plain_row.detail == "none"


def test_filters_narrow_the_rows_and_the_line_says_how_many_matched(
    controller: ResultsController,
) -> None:
    controller.set_filters(ResultsFilters(status=ResultsStatus.ERROR))

    view = build_results_view(controller.state)

    assert view is not None
    assert [row.row for row in view.rows] == [25, 26]
    assert view.shown_line == "2 of 26 rows match the filters"
    assert view.filters_active is True
    assert view.selected == ("error", "all", "all")
    assert view.empty_line == ""


def test_filters_that_match_nothing_say_so_and_offer_to_clear(
    controller: ResultsController,
) -> None:
    controller.set_filters(
        ResultsFilters(sentiment=SentimentLabel.POSITIVE, emotion=EmotionLabel.ANGER)
    )

    view = build_results_view(controller.state)

    assert view is not None and view.rows == ()
    assert view.empty_line == "No rows match these filters."
    assert view.shown_line == "0 of 26 rows match the filters"


def test_unfiltered_the_line_just_counts_the_rows(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    assert view.shown_line == "26 rows" and view.filters_active is False


def test_filters_round_trip_through_the_values_a_widget_reports() -> None:
    assert filters_from("ok", "negative", "joy") == ResultsFilters(
        ResultsStatus.OK, SentimentLabel.NEGATIVE, EmotionLabel.JOY
    )
    assert filters_from("all", "all", "all") == ResultsFilters()


def test_the_language_check_is_summarised_beside_the_table(
    controller: ResultsController,
) -> None:
    view = build_results_view(controller.state)

    assert view is not None
    assert view.language_headline  # the service had no detector: said, not hidden
    assert view.language_warns is True
    assert view.rows[0].language_warns is True


def test_export_is_offered_when_idle_and_not_while_busy(
    controller: ResultsController,
) -> None:
    idle = build_results_view(controller.state)
    busy = build_results_view(
        replace(controller.state, activity=ResultsActivity.EXPORTING)
    )

    assert idle is not None and busy is not None
    assert idle.export_enabled and idle.export_label == "Export normalized CSV…"
    assert "native" in idle.native_label.lower()
    assert not busy.export_enabled


def test_a_project_not_analysed_has_no_results_view_but_says_why(
    tmp_path: Path,
) -> None:
    state = loaded(tmp_path, analyse=False).state

    assert build_results_view(state) is None
    assert build_results_view(ResultsState()) is None


# -- import & validation ------------------------------------------------------


def test_validation_names_each_rejected_row_with_its_code_and_message(
    tmp_path: Path,
) -> None:
    state = loaded(tmp_path, analyse=False).state

    view = build_validation_view(state)

    assert view is not None
    assert view.summary_line == "26 rows · 25 ready · 1 with problems"
    assert view.column_line == "Text column: text"
    assert [(p.row, p.record_id) for p in view.problems] == [(26, "r26")]
    assert view.problems[0].reason.startswith("Rejected at import")
    assert view.failures == ()
    assert view.all_ready_line == ""


def test_after_analysis_failed_rows_are_listed_apart_with_their_reason(
    controller: ResultsController,
) -> None:
    view = build_validation_view(controller.state)

    assert view is not None
    assert [p.row for p in view.problems] == [26]
    assert [(p.row, p.reason) for p in view.failures] == [
        (25, "Failed in analysis · synthetic_failure: Row failed.")
    ]


def test_a_clean_csv_says_every_row_is_ready(tmp_path: Path) -> None:
    repository = SqliteProjectRepository(AppDataLocations(tmp_path))
    flow = ProjectWorkflow(repository, VariedGateway(), LIMITS)
    project_id = flow.import_csv(
        b"record_id,text\nr1,hello there\nr2,another plain one\n", name="Q"
    ).summary.project_id
    controller = ResultsController(ResultsWorkflow(repository), ImmediateRunner())
    controller.open(project_id)

    view = build_validation_view(controller.state)

    assert view is not None
    assert view.problems == () and view.failures == ()
    assert view.all_ready_line == "Every row is ready to analyse."


def test_ignored_columns_are_named_as_untrusted(tmp_path: Path) -> None:
    repository = SqliteProjectRepository(AppDataLocations(tmp_path))
    flow = ProjectWorkflow(repository, VariedGateway(), LIMITS)
    project_id = flow.import_csv(
        b"record_id,text,secret_col\nr1,hello there,x\n", name="Q"
    ).summary.project_id
    controller = ResultsController(ResultsWorkflow(repository), ImmediateRunner())
    controller.open(project_id)

    view = build_validation_view(controller.state)

    assert view is not None
    assert view.ignored_line == "Ignored untrusted columns: secret_col"
