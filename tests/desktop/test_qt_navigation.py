"""Headless Qt tests of the project-centred sidebar and the Analyze score panel."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from persistence.insight_samples import (  # noqa: E402
    VariedGateway,
    insights_csv,
)
from PySide6.QtCore import Qt  # noqa: E402

from social_text_intelligence.desktop.navigation import Section  # noqa: E402

from .fakes import FakeProvisioning, ManualRunner, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()
PROJECT_PAGES = (
    "Import & validation",
    "Results",
    "Review",
    "Agreement",
    "Insights · compare",
    "Insights · notes & cases",
)


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    def factory(fake: FakeProvisioning, runner: Any = None) -> Shell:
        return cast(Shell, make_shell(fake, runner, None, VariedGateway()))

    return factory


def text_of(widget: Any) -> str:
    return str(widget.text())


def import_project(shell: Shell, tmp_path: Path) -> None:
    path = tmp_path / "tickets.csv"
    path.write_bytes(insights_csv())
    shell.platform.csv_file = path
    shell.button(shell.window.projects_page, "Import CSV…").click()


def checked(shell: Shell) -> list[str]:
    return [n for n, b in shell.window.nav_buttons.items() if b.isChecked()]


def test_without_a_project_the_sidebar_offers_only_the_start_area(
    make_shell: Any,
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    window = shell.window

    assert not window.project_area.isVisibleTo(window)
    assert window.nav_buttons["Projects"].isEnabled()
    assert window.nav_buttons["Analyze one text"].isEnabled()
    assert checked(shell) == ["Projects"]


def test_an_open_project_shows_its_name_and_the_six_pages_in_order(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    window = shell.window

    assert window.project_area.isVisibleTo(window)
    assert text_of(window.project_title) == "tickets"
    assert text_of(window.project_facts) == "26 rows"
    names = list(window.nav_buttons)
    assert names[names.index("Import & validation") :][:6] == list(PROJECT_PAGES)
    assert checked(shell) == ["Import & validation"]  # not analysed yet


def test_pages_that_need_analysis_are_disabled_with_the_reason(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    buttons = shell.window.nav_buttons

    for name in PROJECT_PAGES[1:]:
        assert not buttons[name].isEnabled(), name
        assert buttons[name].toolTip() == "Analyze the project first."
        assert buttons[name].accessibleDescription() == "Analyze the project first."
    assert buttons["Import & validation"].isEnabled()


def test_a_disabled_page_does_nothing_when_asked_for(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    page = shell.window.projects_page

    shell.window._open_section(Section.REVIEW)

    assert page.section is Section.IMPORT
    assert page.stack.currentWidget() is page.detail_page


def test_after_analysis_each_page_opens_its_own_view_and_one_item_is_checked(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    page = shell.window.projects_page
    page.analyze_button.click()
    expected = {
        "Import & validation": page.detail_page,
        "Results": page.results_page,
        "Review": page.review_page,
        "Agreement": page.agreement_page,
        "Insights · compare": page.insights_page,
        "Insights · notes & cases": page.insights_page,
    }

    for name, widget in expected.items():
        assert shell.window.nav_buttons[name].isEnabled(), name
        shell.window.nav_buttons[name].click()
        assert page.stack.currentWidget() is widget, name
        assert checked(shell) == [name], name


def test_the_counts_beside_the_pages_are_rows_and_reviewable_records(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    shell.window.projects_page.analyze_button.click()
    buttons = shell.window.nav_buttons

    assert buttons["Results"].badge == "26"
    assert buttons["Review"].badge == "24"
    assert buttons["Results"].accessibleName() == "Results, 26"


def test_the_two_insight_pages_share_one_view_and_do_not_reload(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    shell.window.projects_page.analyze_button.click()
    buttons = shell.window.nav_buttons
    insights = shell.window.projects_page.insights_page

    buttons["Insights · compare"].click()
    assert text_of(insights.title) == "Insights · compare"
    insights.compare_box.setChecked(True)
    buttons["Insights · notes & cases"].click()

    assert text_of(insights.title) == "Insights · notes & cases"
    assert shell.window.insights.state.active
    buttons["Insights · compare"].click()
    assert insights.compare_box.isChecked()  # the same, still-open view


def test_projects_leaves_the_project_and_closes_its_pages(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    window = shell.window
    window.projects_page.analyze_button.click()
    window.nav_buttons["Review"].click()
    assert window.review.state.active

    window.nav_buttons["Projects"].click()

    page = window.projects_page
    assert page.stack.currentWidget() is page.list_page
    assert not window.project_area.isVisibleTo(window)
    assert window.projects.state.current is None
    for controller in (window.review, window.results, window.agreement, window.insights):
        assert not controller.state.active
    assert checked(shell) == ["Projects"]
    assert "1 project(s)" in text_of(page.summary)


def test_the_analyze_page_keeps_the_open_project_where_it_was(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    window = shell.window
    window.projects_page.analyze_button.click()
    window.nav_buttons["Agreement"].click()

    window.nav_buttons["Analyze one text"].click()
    assert window.pages.currentWidget() is window.analyze_page
    assert checked(shell) == ["Analyze one text"]
    assert window.project_area.isVisibleTo(window)  # the project is still open

    window.nav_buttons["Agreement"].click()
    assert window.pages.currentWidget() is window.projects_page
    assert window.projects_page.section is Section.AGREEMENT


def test_while_an_analysis_runs_the_project_cannot_be_left_and_the_reason_is_given(
    make_shell: Any, tmp_path: Path
) -> None:
    runner = ManualRunner()
    shell: Shell = make_shell(FakeProvisioning(current=READY), runner)
    while runner.jobs:
        runner.run_next()
    import_project(shell, tmp_path)
    runner.run_next()  # the import
    runner.run_next()  # its validation detail
    shell.window.projects_page.analyze_button.click()

    projects = shell.window.nav_buttons["Projects"]
    assert not projects.isEnabled()
    assert "Cancel" in projects.toolTip()
    assert shell.window.nav_buttons["Import & validation"].isEnabled()
    runner.run_next()  # the run finishes
    assert projects.isEnabled()


def test_the_navigation_is_keyboard_reachable_named_and_has_no_stray_mnemonic(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    import_project(shell, tmp_path)
    shell.window.projects_page.analyze_button.click()

    for name, button in shell.window.nav_buttons.items():
        assert button.focusPolicy() != Qt.FocusPolicy.NoFocus, name
        assert button.accessibleName().startswith(name), name
        assert button.shortcut().isEmpty(), name  # "&" is a letter here, not a key
    assert shell.window.nav_buttons["Import & validation"].text() == "Import && validation"
    assert shell.window.models_button.focusPolicy() != Qt.FocusPolicy.NoFocus


# -- the Analyze page's score breakdown ---------------------------------------------


def test_analyze_shows_the_three_sentiment_scores_and_nine_compact_emotion_scores(
    make_shell: Any,
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    shell.window.nav_buttons["Analyze one text"].click()
    page = shell.window.analyze_page
    page.editor.setPlainText("A synthetic joyful sentence.")

    page.analyze_button.click()

    scores = page.scores
    assert len(scores.sentiment.meters) == 3
    assert len(scores.emotion.meters) == 9
    names = [m.accessibleName() for m in scores.sentiment.meters]
    assert all(": 0." in n for n in names)  # each is written with its score
    assert "highest" in " ".join(names)
    assert "threshold" in text_of(scores.rule).lower()


def test_the_model_native_scores_are_one_click_away_and_listed_when_opened(
    make_shell: Any,
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    shell.window.nav_buttons["Analyze one text"].click()
    page = shell.window.analyze_page
    page.editor.setPlainText("A synthetic joyful sentence.")
    page.analyze_button.click()
    scores = page.scores

    assert not scores.native.isVisibleTo(page)
    assert "model-native emotion scores" in scores.native_toggle.text()

    scores.native_toggle.click()

    assert scores.native.isVisibleTo(page)
    assert len(scores.native.meters) > 0
