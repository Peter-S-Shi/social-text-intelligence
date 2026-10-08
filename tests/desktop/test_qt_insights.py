"""Headless Qt tests of the insights user path over a real SQLite project."""

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
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QCheckBox,
    QComboBox,
    QFrame,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
)

from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel  # noqa: E402
from social_text_intelligence.infrastructure.app_data import (  # noqa: E402
    AppDataLocations,
)
from social_text_intelligence.infrastructure.sqlite_projects import (  # noqa: E402
    SqliteProjectRepository,
)
from social_text_intelligence.services.insights import ContextTag  # noqa: E402

from .fakes import FakeProvisioning, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    """Each record needs its own labels, so use the keyword-driven gateway."""

    def factory(
        fake: FakeProvisioning,
        runner: Any = None,
        platform: Any = None,
        gateway: Any = None,
    ) -> Shell:
        return cast(
            Shell, make_shell(fake, runner, platform, gateway or VariedGateway())
        )

    return factory


def text_of(widget: Any) -> str:
    return str(widget.text())


def analysed_shell(make_shell: Any, tmp_path: Path) -> Shell:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    folder = tmp_path / "csv"
    folder.mkdir(exist_ok=True)
    path = folder / "tickets.csv"
    path.write_bytes(insights_csv())
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    return shell


def start_insights(shell: Shell) -> Any:
    page = shell.window.projects_page
    page.insights_button.click()
    assert page.stack.currentWidget() is page.insights_page
    return page.insights_page


def choose(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    assert index >= 0, value
    combo.setCurrentIndex(index)
    combo.activated.emit(index)


def check_only(widget: QListWidget, *wanted: str) -> None:
    for i in range(widget.count()):
        item = widget.item(i)
        item.setCheckState(
            Qt.CheckState.Checked if item.text() in wanted else Qt.CheckState.Unchecked
        )


def cards(page: Any) -> list[str]:
    return [
        page.cards_box.itemAt(i).widget().accessibleName()
        for i in range(page.cards_box.count())
    ]


def stored(tmp_path: Path, project_id: str) -> Any:
    workspace = SqliteProjectRepository(AppDataLocations(tmp_path)).get(project_id)
    assert workspace is not None
    return workspace


def fill_note(page: Any, **fields: str) -> None:
    values = {
        "value": "shipping",
        "phrase": "running late",
        "explanation": "A common phrase here.",
        "importance": "It may mean delay, not anger.",
        **fields,
    }
    page.value_combo.setEditText(values["value"])
    page.phrase_edit.setText(values["phrase"])
    page.explanation_edit.setPlainText(values["explanation"])
    page.importance_edit.setPlainText(values["importance"])


def test_the_insights_button_appears_only_for_an_analysed_project(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    path = tmp_path / "p.csv"
    path.write_bytes(insights_csv())
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    assert not page.insights_button.isVisibleTo(page)  # ready, not analysed yet

    page.analyze_button.click()

    assert page.insights_button.isVisibleTo(page) and page.insights_button.isEnabled()


def test_opening_shows_the_default_view_with_denominators_and_warnings(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)

    assert text_of(insights.title) == "Insights"
    assert insights.tabs.tabText(0) == "Group insights"
    assert insights.tabs.tabText(1) == "Notes and cases"
    (card,) = cards(insights)
    assert card.startswith("billing")
    assert "7 eligible of 8 group rows" in card
    assert "Small sample" in card
    assert "denominator is successful rows" in text_of(insights.definition)
    assert "Agreement is not accuracy".lower() in text_of(insights.limitations).lower()
    assert "Sentiment model:" in text_of(insights.provenance)


def test_applying_a_view_shows_it_and_it_survives_a_restart(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)

    choose(insights.grouping_combo, "community")
    check_only(insights.group_list, "south")
    assert insights.apply_button.isEnabled()
    insights.apply_button.click()

    (card,) = cards(insights)
    assert card.startswith("south")
    shell.window.close()
    again = make_shell(FakeProvisioning(current=READY))
    again.button(again.window.projects_page, "Open").click()
    reopened = start_insights(again)
    assert reopened.grouping_combo.currentData() == "community"
    (card,) = cards(reopened)
    assert card.startswith("south")


def test_a_comparison_needs_two_to_four_groups_and_shows_the_caution(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)

    insights.compare_box.setChecked(True)
    check_only(insights.group_list, "shipping")
    assert not insights.apply_button.isEnabled()  # one group cannot be compared
    assert "two to four" in text_of(insights.group_hint).lower()
    check_only(insights.group_list, "shipping", "returns")
    assert insights.apply_button.isEnabled()
    insights.apply_button.click()

    assert [c.split(".")[0] for c in cards(insights)] == ["returns", "shipping"]
    assert insights.caution.isVisibleTo(insights)
    assert "returns" in text_of(insights.caution)
    assert "shipping" not in text_of(insights.caution)
    assert "Insufficient sample for comparison" in " ".join(cards(insights))


def test_the_metric_choices_follow_the_perspective(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    before = [insights.metric_combo.itemData(i) for i in range(3)]

    choose(insights.perspective_combo, "human")

    after = [insights.metric_combo.itemData(i) for i in range(3)]
    assert before[0] == "ai_sentiment" and after[0] == "human_sentiment"
    insights.apply_button.click()
    (card,) = cards(insights)
    assert "0 eligible of 8 group rows" in card  # nothing reviewed yet
    assert "Insufficient sample" in card


def test_a_bad_date_shows_an_inline_message_and_keeps_the_saved_view(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)

    insights.date_from_edit.setText("01/02/2026")
    insights.date_from_edit.textEdited.emit("01/02/2026")
    insights.apply_button.click()

    assert insights.field_error.isVisibleTo(insights)
    assert "YYYY-MM-DD" in text_of(insights.field_error)
    assert insights.notice.code.text() == "invalid_date"
    assert card_heading(insights) == "billing"  # the shown view did not change


def card_heading(page: Any) -> str:
    return cards(page)[0].split(".")[0]


def test_a_context_note_is_added_listed_as_human_text_and_deleted(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    assert insights.no_notes.isVisibleTo(insights)

    fill_note(insights)
    insights.tag_boxes[ContextTag.IDIOM_OR_SLANG].setChecked(True)
    assert "Unsaved note" in text_of(insights.unsaved_note)
    insights.add_note_button.click()

    assert text_of(insights.notice.title).endswith("Note added")
    assert not insights.no_notes.isVisibleTo(insights)
    note = insights.notes_box.itemAt(0).widget()
    assert "not AI output" in note.accessibleName()
    assert insights.phrase_edit.text() == ""  # the draft was cleared
    assert not insights.tag_boxes[ContextTag.IDIOM_OR_SLANG].isChecked()
    workspace = stored(tmp_path, workspace_id(shell))
    assert [n.phrase for n in workspace.insights.notes] == ["running late"]

    delete = note.findChildren(QPushButton)[0]
    shell.platform.confirmed = False
    delete.click()
    assert len(stored(tmp_path, workspace_id(shell)).insights.notes) == 1
    shell.platform.confirmed = True
    delete.click()
    assert stored(tmp_path, workspace_id(shell)).insights.notes == ()
    assert insights.no_notes.isVisibleTo(insights)


def workspace_id(shell: Shell) -> str:
    project_id = shell.window.insights.state.project_id
    assert project_id is not None
    return project_id


def test_an_invalid_note_shows_the_field_message_and_keeps_the_draft(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    fill_note(insights, value="not a topic")

    insights.add_note_button.click()

    assert insights.note_error.isVisibleTo(insights)
    assert "not present in this workspace" in text_of(insights.note_error)
    assert insights.phrase_edit.text() == "running late"  # nothing was lost
    assert stored(tmp_path, workspace_id(shell)).insights.notes == ()


def test_cases_show_why_they_were_chosen_with_ai_and_human_apart(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)

    choose(insights.mode_combo, "highest_ai_score")
    choose(insights.example_emotion_combo, EmotionLabel.ANGER.value)
    insights.select_button.click()

    assert insights.cases_box.count() == 5
    first = insights.cases_box.itemAt(0).widget()
    labels = " ".join(
        label.text() for label in first.findChildren(type(insights.title))
    )
    assert "Why shown: Highest AI compact anger score" in labels
    assert "AI record (read-only)" in labels and "Human judgment (yours)" in labels
    ai, human = (
        [f for f in first.findChildren(QFrame) if f.property("role") == role]
        for role in ("ai", "human")
    )
    assert ai and human
    for kind in (QLineEdit, QPlainTextEdit, QComboBox, QCheckBox):
        assert ai[0].findChildren(kind) == []  # the AI side holds labels only


def test_a_case_opens_in_review_at_its_row(make_shell: Any, tmp_path: Path) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    choose(insights.mode_combo, "highest_ai_score")
    insights.select_button.click()
    page = shell.window.projects_page

    first = insights.cases_box.itemAt(0).widget()
    first.findChildren(QPushButton)[0].click()

    assert page.stack.currentWidget() is page.review_page
    assert not shell.window.insights.state.active
    assert "Row 5" in text_of(page.review_page.record_title)  # the first angry row


def test_opening_a_case_in_review_asks_before_dropping_an_unsaved_note(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    choose(insights.mode_combo, "highest_ai_score")
    insights.select_button.click()
    fill_note(insights)
    page = shell.window.projects_page
    open_button = insights.cases_box.itemAt(0).widget().findChildren(QPushButton)[0]

    shell.platform.confirmed = False
    open_button.click()
    assert page.stack.currentWidget() is page.insights_page  # stayed
    assert insights.phrase_edit.text() == "running late"
    assert "note" in shell.platform.confirmations[-1].lower()

    shell.platform.confirmed = True
    open_button.click()
    assert page.stack.currentWidget() is page.review_page
    assert not shell.window.insights.state.has_unsaved_changes


def test_review_changes_show_up_in_the_human_view(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    page = shell.window.projects_page
    page.review_button.click()
    page.review_page.accept_button.click()  # r1 reviewed
    page.review_page.back_button.click()

    insights = start_insights(shell)
    choose(insights.grouping_combo, "topic")
    check_only(insights.group_list, "shipping")
    choose(insights.perspective_combo, "human")
    insights.apply_button.click()

    assert "1 eligible of 13 group rows" in cards(insights)[0]
    assert "11 unreviewed" in " ".join(
        label.text()
        for label in insights.cards_box.itemAt(0)
        .widget()
        .findChildren(type(insights.title))
    )


def test_export_writes_only_when_the_user_picks_a_file(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    out = tmp_path / "exports"
    out.mkdir()
    target = out / "insights.csv"

    insights.export_button.click()  # the dialog is cancelled
    assert shell.platform.save_requests == ["insights.csv"]
    assert list(out.iterdir()) == []
    assert not insights.notice.isVisibleTo(insights)  # no error either

    shell.platform.save_target = target
    insights.records_box.setChecked(True)
    insights.native_box.setChecked(True)
    insights.export_button.click()

    rows = list(csv.DictReader(io.StringIO(target.read_text(encoding="utf-8"))))
    sections = {r["section"] for r in rows}
    assert {"export_metadata", "group_summary", "supporting_record"} <= sections
    assert any(r["native_emotion_scores"] for r in rows)
    assert text_of(insights.notice.title).endswith("Insights CSV saved")
    assert str(tmp_path) not in text_of(insights.notice.body)
    assert [p.name for p in out.iterdir()] == ["insights.csv"]


def test_a_failed_export_is_a_fixed_safe_message(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    shell.platform.save_target = tmp_path / "no-such-folder" / "out.csv"

    insights.export_button.click()

    assert insights.notice.code.text() == "export_failed"
    body = text_of(insights.notice.body)
    assert str(tmp_path) not in body and SENTINEL not in body
    assert insights.export_button.isEnabled()


def test_an_unsaved_note_is_confirmed_before_leaving_and_really_discarded(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    fill_note(insights)
    window = shell.window

    shell.platform.confirmed = False
    window.nav_buttons["Analyze one text"].click()
    assert window.pages.currentWidget() is window.projects_page  # stayed
    assert insights.phrase_edit.text() == "running late"
    assert "note" in shell.platform.confirmations[-1].lower()
    assert "leave this page" in shell.platform.confirmations[-1].lower()

    shell.platform.confirmed = True
    window.nav_buttons["Analyze one text"].click()
    assert window.pages.currentWidget() is window.analyze_page
    assert not window.insights.state.has_unsaved_changes  # really discarded
    window.nav_buttons["Projects"].click()
    assert insights.phrase_edit.text() == ""


def test_closing_the_window_asks_before_dropping_an_unsaved_note(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    fill_note(insights)

    shell.platform.confirmed = False
    event = QCloseEvent()
    shell.window.closeEvent(event)

    assert not event.isAccepted()
    assert "close" in shell.platform.confirmations[-1].lower()
    shell.platform.confirmed = True
    event = QCloseEvent()
    shell.window.closeEvent(event)
    assert event.isAccepted()


def test_viewing_noting_and_exporting_never_change_results_or_reviews(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    page = shell.window.projects_page
    page.review_button.click()
    page.review_page.accept_button.click()
    page.review_page.back_button.click()
    before = stored(tmp_path, shell.window.projects.state.current.summary.project_id)  # type: ignore[union-attr]
    insights = start_insights(shell)

    insights.compare_box.setChecked(True)
    check_only(insights.group_list, "shipping", "billing")
    insights.apply_button.click()
    insights.tabs.setCurrentIndex(1)
    fill_note(insights)
    insights.add_note_button.click()
    shell.platform.save_target = tmp_path / "i.csv"
    insights.export_button.click()

    after = stored(tmp_path, workspace_id(shell))
    assert (after.preview, after.result, after.reviews) == (
        before.preview,
        before.result,
        before.reviews,
    )
    flow = ReviewWorkflow(SqliteProjectRepository(AppDataLocations(tmp_path)))
    kept = flow.open_review(workspace_id(shell), row=1)
    assert kept.record is not None and kept.record.review.is_reviewed


def test_the_insights_controls_are_keyboard_operable_and_named(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    insights = start_insights(shell)
    insights.tabs.setCurrentIndex(1)
    controls: list[Any] = [
        *insights.findChildren(QPushButton),
        *insights.findChildren(QCheckBox),
        *insights.findChildren(QComboBox),
        *insights.findChildren(QLineEdit),
        *insights.findChildren(QPlainTextEdit),
        *insights.findChildren(QListWidget),
    ]
    assert controls
    for control in controls:
        if control.objectName() == "qt_scrollarea_viewport":
            continue
        assert control.focusPolicy() != Qt.FocusPolicy.NoFocus, control.objectName()
        named = control.accessibleName() or getattr(control, "text", lambda: "")()
        assert named, (type(control).__name__, control.objectName())
    assert insights.tabs.accessibleName() == "Insight views"
