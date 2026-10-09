"""Headless Qt tests of the Import & validation and Results pages (real SQLite)."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from persistence.insight_samples import (  # noqa: E402
    SENTINEL,
    VariedGateway,
    insights_csv,
)
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QCheckBox, QPushButton  # noqa: E402

from .fakes import FakeProvisioning, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    """The 26-row synthetic project: 24 analyse, one fails, one is rejected."""

    def factory(fake: FakeProvisioning, runner: Any = None) -> Shell:
        return cast(Shell, make_shell(fake, runner, None, VariedGateway()))

    return factory


def text_of(widget: Any) -> str:
    return str(widget.text())


def cell(table: Any, row: int, column: int) -> str:
    return str(table.item(row, column).text())


def opened(make_shell: Any, tmp_path: Path, *, analyse: bool = True) -> Shell:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    path = tmp_path / "tickets.csv"
    path.write_bytes(insights_csv())
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    if analyse:
        page.analyze_button.click()
    return shell


# -- import and validation ----------------------------------------------------------


def test_the_import_page_lists_each_rejected_row_with_its_code_and_reason(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path, analyse=False)
    page = shell.window.projects_page

    table = page.problems_table
    assert page.stack.currentWidget() is page.detail_page
    assert page.problems_card.isVisibleTo(page)
    assert table.rowCount() == 1
    assert [cell(table, 0, c) for c in (0, 1)] == ["26", "r26"]
    assert cell(table, 0, 2).startswith("Rejected at import · ")
    assert ": " in cell(table, 0, 2)  # code, then the fixed message
    assert not page.failures_card.isVisibleTo(page)  # nothing analysed yet
    assert SENTINEL not in cell(table, 0, 2)


def test_after_analysis_the_failed_row_is_listed_apart_with_its_reason(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page

    shell.window.nav_buttons["Import & validation"].click()

    assert page.stack.currentWidget() is page.detail_page
    assert page.failures_card.isVisibleTo(page)
    table = page.failures_table
    assert table.rowCount() == 1
    assert [cell(table, 0, c) for c in (0, 1)] == ["25", "r25"]
    assert cell(table, 0, 2) == "Failed in analysis · synthetic_failure: Row failed."
    assert page.problems_table.rowCount() == 1  # the rejected row is still listed


def test_a_clean_csv_says_every_row_is_ready(make_shell: Any, tmp_path: Path) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    path = tmp_path / "clean.csv"
    path.write_bytes(b"record_id,text\nr1,hello there\nr2,plain words\n")
    shell.platform.csv_file = path
    page = shell.window.projects_page

    shell.button(page, "Import CSV…").click()

    assert page.all_ready.isVisibleTo(page)
    assert text_of(page.all_ready) == "Every row is ready to analyse."
    assert not page.problems_table.isVisibleTo(page)


# -- results ------------------------------------------------------------------------


def test_analysis_finishing_shows_the_results_page(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page

    assert page.stack.currentWidget() is page.results_page
    assert shell.window.nav_buttons["Results"].isChecked()
    results = page.results_page
    assert text_of(results.header.subtitle) == (
        "24 analysed · 1 failed · 1 rejected at import"
    )


def test_the_aggregates_are_written_beside_their_bars(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page

    figures = {
        tone: figure.accessibleName()
        for tone, figure in results.sentiment_figures.items()
    }  # "count tone rows, share"
    assert figures["positive"] == "7 positive rows, 29.2%"
    assert figures["neutral"] == "10 neutral rows, 41.7%"
    assert {
        tone: text_of(f.value) for tone, f in results.sentiment_figures.items()
    } == {
        "negative": "7",
        "neutral": "10",
        "positive": "7",
    }
    assert len(results.dominant_bars.meters) == 9
    assert len(results.activation_bars.meters) == 8
    assert text_of(results.failed_figure) == "2"
    # a bar is only a picture: its segments are the counts the figures state
    assert dict(
        (tone, weight) for weight, tone in results.sentiment_stack.segments
    ) == {
        "negative": 7.0,
        "neutral": 10.0,
        "positive": 7.0,
    }


def test_every_row_is_in_the_table_with_a_status_word_and_a_reason(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    table = shell.window.projects_page.results_page.table

    assert table.rowCount() == 26
    assert [cell(table, 0, c) for c in range(5)] == [
        "1",
        "r1",
        "✓ Analysed",
        "Positive",
        "Joy",
    ]
    assert cell(table, 24, 2) == "✕ Failed"
    assert cell(table, 24, 5) == "synthetic_failure: Row failed."
    assert cell(table, 25, 2) == "✕ Rejected at import"
    assert SENTINEL not in " ".join(
        cell(table, r, c) for r in range(26) for c in range(7)
    )


def test_the_status_tabs_filter_the_rows_and_the_count_says_how_many(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page
    assert [b.text() for b in results.status_filter.buttons.values()] == [
        "All rows  26",
        "Analysed  24",
        "Not analysed  2",
    ]

    results.status_filter.buttons["error"].click()

    table = results.table
    assert table.rowCount() == 2
    assert [cell(table, r, 0) for r in range(2)] == ["25", "26"]
    assert text_of(results.shown_line) == "2 of 26 rows match the filters"
    assert results.status_filter.buttons["error"].isChecked()
    assert results.clear_button.isEnabled()

    results.clear_button.click()
    assert table.rowCount() == 26
    assert not results.clear_button.isEnabled()
    assert results.status_filter.buttons["all"].isChecked()


def test_the_sentiment_and_emotion_filters_combine_and_can_match_nothing(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page

    results.sentiment_filter.setCurrentIndex(
        results.sentiment_filter.findData("negative")
    )
    results.sentiment_filter.activated.emit(results.sentiment_filter.currentIndex())
    assert results.table.rowCount() == 7

    results.emotion_filter.setCurrentIndex(results.emotion_filter.findData("joy"))
    results.emotion_filter.activated.emit(results.emotion_filter.currentIndex())
    assert results.table.rowCount() == 0
    assert results.table_empty.isVisibleTo(results)
    assert text_of(results.table_empty) == "No rows match these filters."


def test_a_row_opens_in_review_by_button_or_enter_and_a_failed_row_does_not(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page
    results = page.results_page

    results.table.selectRow(24)  # the failed row
    assert not results.review_button.isEnabled()
    results._activated(24)
    assert page.stack.currentWidget() is page.results_page

    results.table.selectRow(4)  # row 5, an analysed row
    assert results.review_button.isEnabled()
    results.review_button.click()

    assert page.stack.currentWidget() is page.review_page
    assert "Row 5" in text_of(page.review_page.record_title)
    assert shell.window.nav_buttons["Review"].isChecked()


def test_filter_keeps_the_same_selected_record_after_its_position_changes(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page
    results = page.results_page
    results.table.selectRow(4)  # r5 is the first negative record

    results.sentiment_filter.setCurrentIndex(
        results.sentiment_filter.findData("negative")
    )
    results.sentiment_filter.activated.emit(results.sentiment_filter.currentIndex())

    assert results.table.currentRow() == 0
    assert cell(results.table, results.table.currentRow(), 1) == "r5"
    assert results.review_button.isEnabled()
    results.review_button.click()
    assert page.stack.currentWidget() is page.review_page
    assert "Row 5" in text_of(page.review_page.record_title)


def test_filter_keeps_a_selected_record_when_its_position_is_unchanged(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page
    results = page.results_page
    results.table.selectRow(1)  # r2 remains the second analysed row

    results.status_filter.buttons["ok"].click()

    assert results.table.currentRow() == 1
    assert cell(results.table, 1, 1) == "r2"
    results.review_button.click()
    assert "Row 2" in text_of(page.review_page.record_title)


def test_filter_clears_selection_when_the_record_is_no_longer_shown(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page
    results = page.results_page
    results.table.selectRow(0)  # r1 is positive

    results.sentiment_filter.setCurrentIndex(
        results.sentiment_filter.findData("negative")
    )
    results.sentiment_filter.activated.emit(results.sentiment_filter.currentIndex())

    assert results.table.rowCount() == 7
    assert not results.table.selectionModel().selectedRows()
    assert results.table.currentRow() == -1
    assert not results.review_button.isEnabled()
    results.review_button.click()
    assert page.stack.currentWidget() is page.results_page


def test_selection_does_not_carry_into_another_project(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    page = shell.window.projects_page
    results = page.results_page
    results.table.selectRow(4)
    assert results.review_button.isEnabled()

    shell.window.nav_buttons["Projects"].click()
    other_csv = tmp_path / "other.csv"
    other_csv.write_bytes(insights_csv())
    shell.platform.csv_file = other_csv
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()

    assert page.stack.currentWidget() is results
    assert results.table.rowCount() == 26
    assert not results.table.selectionModel().selectedRows()
    assert results.table.currentRow() == -1
    assert not results.review_button.isEnabled()
    results.table.selectRow(5)
    results.review_button.click()
    assert "Row 6" in text_of(page.review_page.record_title)


def test_export_asks_where_and_writes_nothing_when_cancelled(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page
    shell.platform.save_target = None

    results.export_button.click()

    assert shell.platform.save_requests == ["normalized-results.csv"]
    assert not results.notice.isVisibleTo(results)  # cancelling is not an error
    assert not list(tmp_path.glob("*.tmp"))


def test_export_writes_every_row_with_the_supplied_and_detected_language_apart(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page
    out = tmp_path / "out"
    out.mkdir()
    shell.platform.save_target = out / "normalized.csv"

    results.export_button.click()

    rows = list(
        csv.DictReader(io.StringIO((out / "normalized.csv").read_text("utf-8")))
    )
    assert len(rows) == 26
    assert "language" in rows[0] and "detected_language" in rows[0]
    assert (
        "native_emotion_scores" not in rows[0] or not rows[0]["native_emotion_scores"]
    )
    assert text_of(results.notice.title).endswith("Normalized CSV saved")
    assert str(tmp_path) not in text_of(results.notice.body)
    assert [p.name for p in out.iterdir()] == ["normalized.csv"]


def test_native_scores_are_included_only_when_the_box_is_ticked(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page
    shell.platform.save_target = tmp_path / "n.csv"
    results.native_box.setChecked(True)

    results.export_button.click()

    header = (tmp_path / "n.csv").read_text("utf-8").splitlines()[0]
    assert "emotion_native_" in header


def test_a_failed_export_is_a_fixed_message_without_the_path(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page
    shell.platform.save_target = tmp_path / "no-such-folder" / "out.csv"

    results.export_button.click()

    assert results.notice.code.text() == "export_failed"
    assert str(tmp_path) not in text_of(results.notice.body)
    assert results.export_button.isEnabled()  # and the page is still usable


def test_a_project_not_analysed_shows_why_there_are_no_results(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path, analyse=False)
    page = shell.window.projects_page
    nav = shell.window.nav_buttons["Results"]

    assert not nav.isEnabled()
    page.show_section(page.section.RESULTS)  # even if asked for directly
    results = page.results_page
    assert results.empty.isVisibleTo(results)
    assert "not been analysed" in text_of(results.empty.body)
    assert not results.table.isVisibleTo(results)


def test_the_results_controls_are_keyboard_operable_and_named(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = opened(make_shell, tmp_path)
    results = shell.window.projects_page.results_page

    controls = [
        *results.findChildren(QPushButton),
        *results.findChildren(QCheckBox),
        results.table,
        results.sentiment_filter,
        results.emotion_filter,
    ]
    for control in controls:
        assert control.focusPolicy() != Qt.FocusPolicy.NoFocus, control.objectName()
        label = getattr(control, "text", lambda: "")()
        assert control.accessibleName() or label, control.objectName()
    # the table is named, and each status button carries its count in its name
    assert results.table.accessibleName() == "Results, one row per record"
    assert results.status_filter.buttons["error"].accessibleName() == (
        "Not analysed, 2 rows"
    )
