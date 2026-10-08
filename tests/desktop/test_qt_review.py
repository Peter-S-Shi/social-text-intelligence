"""Headless Qt tests of the review user path over a real SQLite project."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from persistence.workflow_samples import (  # noqa: E402
    SENTINEL,
    ScriptedGateway,
    csv_text,
)
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
)

from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewDraft,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel  # noqa: E402
from social_text_intelligence.contracts.errors import ProviderError  # noqa: E402
from social_text_intelligence.infrastructure.app_data import (  # noqa: E402
    AppDataLocations,
)
from social_text_intelligence.infrastructure.sqlite_projects import (  # noqa: E402
    SqliteProjectRepository,
)

from .fakes import FakeProvisioning, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    """Each record needs its own report, so use the per-record scripted gateway."""

    def factory(
        fake: FakeProvisioning,
        runner: Any = None,
        platform: Any = None,
        gateway: Any = None,
    ) -> Shell:
        return cast(
            Shell, make_shell(fake, runner, platform, gateway or ScriptedGateway())
        )

    return factory


def text_of(widget: Any) -> str:
    return str(widget.text())


def analysed_shell(
    make_shell: Any, tmp_path: Path, rows: int = 4, gateway: Any = None
) -> Shell:
    shell: Shell = make_shell(FakeProvisioning(current=READY), gateway=gateway)
    folder = tmp_path / "csv"
    folder.mkdir(exist_ok=True)
    path = folder / "tickets.csv"
    path.write_bytes(csv_text(rows))
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    return shell


def start_review(shell: Shell) -> Any:
    page = shell.window.projects_page
    shell.window.nav_buttons["Review"].click()
    assert page.stack.currentWidget() is page.review_page
    return page.review_page


def pick(review: Any, judgment: str, dimension: str) -> None:
    radios = (
        review.human.sentiment_radios
        if dimension == "sentiment"
        else review.human.emotion_radios
    )
    radios[ReviewJudgment(judgment)].click()


def choose(combo: QComboBox, value: str) -> None:
    combo.setCurrentIndex(combo.findData(value))


def reload_in_fresh_shell(make_shell: Any, tmp_path: Path) -> Any:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page
    shell.button(page, "Open").click()
    return start_review(shell)


def test_the_review_page_is_offered_only_for_an_analysed_project(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    path = tmp_path / "p.csv"
    path.write_bytes(csv_text(2))
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    nav = shell.window.nav_buttons["Review"]
    assert not nav.isEnabled()  # ready, not analysed yet
    assert "Analyze the project first" in nav.toolTip()

    page.analyze_button.click()

    assert nav.isEnabled() and nav.badge == "2"


def test_the_ai_record_is_read_only_and_apart_from_the_human_judgment(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)

    assert SENTINEL in text_of(review.record_text)
    assert "Record 1 of 4" in text_of(review.position)
    ai, human = review.ai, review.human
    assert "not editable" in text_of(ai.heading)
    assert "Your judgment" in text_of(human.heading)
    # nothing in the AI block can be edited: it holds labels and one disclosure only
    for kind in (QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QRadioButton):
        assert ai.findChildren(kind) == []
    assert human.findChildren(QRadioButton) and human.findChildren(QPlainTextEdit)
    assert "Unreviewed" in text_of(human.status)
    assert "○" in text_of(human.status)  # a word and an icon, not colour alone
    assert text_of(ai.heading) != text_of(human.heading)
    assert ai.property("role") == "ai" and human.property("role") == "human"
    assert not ai.native.isVisibleTo(ai)
    ai.native_toggle.click()
    assert ai.native.isVisibleTo(ai)


def test_accept_both_saves_and_survives_a_restart(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)

    review.human.note.setPlainText("looks right")
    review.accept_button.click()

    assert "Reviewed" in text_of(review.human.status)
    assert "✓" in text_of(review.human.status)
    assert "1 of 4 reviewed" in text_of(review.progress)
    assert review.notice.isVisibleTo(review)
    assert text_of(review.notice.title).endswith("Review saved")
    shell.window.close()

    again = reload_in_fresh_shell(make_shell, tmp_path)  # a new app instance
    assert "Reviewed" in text_of(again.human.status)
    assert again.human.note.toPlainText() == "looks right"
    assert again.human.sentiment_radios[ReviewJudgment.ACCEPT].isChecked()
    assert "1 of 4 reviewed" in text_of(again.progress)


def test_sentiment_and_emotion_are_judged_separately_and_correction_reveals_fields(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    human = review.human
    assert not human.sentiment_combo.isVisibleTo(human)

    pick(review, "accept", "sentiment")
    review.save_button.click()
    assert "Partly reviewed" in text_of(human.status)
    assert "◐" in text_of(human.status)
    assert "0 of 4 reviewed" in text_of(review.progress)  # one dimension is not enough
    assert "both" in text_of(review.notice.body)

    pick(review, "correct", "emotion")
    assert human.dominant_combo.isVisibleTo(human)
    assert human.secondary_box.isVisibleTo(human)
    choose(human.dominant_combo, "joy")
    human.secondary_boxes[EmotionLabel.GRATITUDE].setChecked(True)
    review.save_button.click()

    assert "Reviewed" in text_of(human.status) and "Partly" not in text_of(human.status)
    assert "1 of 4 reviewed" in text_of(review.progress)
    assert "1 corrected" in text_of(review.progress)
    pick(review, "uncertain", "sentiment")
    review.save_button.click()
    assert "1 marked uncertain" in text_of(review.progress)


def test_an_invalid_emotion_correction_shows_the_message_and_keeps_the_draft(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    human = review.human
    pick(review, "accept", "sentiment")
    pick(review, "correct", "emotion")
    choose(human.dominant_combo, "joy")
    human.secondary_boxes[EmotionLabel.JOY].setChecked(True)

    review.save_button.click()

    assert "cannot also be secondary" in text_of(review.notice.body)
    assert review.notice.code.text() == "dominant_repeated"
    assert human.secondary_boxes[EmotionLabel.JOY].isChecked()  # nothing was lost
    assert "Unsaved changes" in text_of(human.unsaved)
    assert "Unreviewed" in text_of(human.status)  # and nothing was stored

    human.secondary_boxes[EmotionLabel.JOY].setChecked(False)
    choose(human.dominant_combo, "neutral")
    human.secondary_boxes[EmotionLabel.FEAR].setChecked(True)
    review.save_button.click()
    assert review.notice.code.text() == "neutral_not_exclusive"


def test_a_note_over_the_limit_is_flagged_and_refused(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "accept", "sentiment")
    pick(review, "accept", "emotion")

    review.human.note.setPlainText("x" * 2001)

    assert "over the 2000-character limit" in text_of(review.human.counter)
    review.save_button.click()
    assert review.notice.code.text() == "too_long"
    review.human.note.setPlainText("x" * 2000)
    assert "0 characters left" in text_of(review.human.counter)
    review.save_button.click()
    assert "Reviewed" in text_of(review.human.status)


def test_navigation_and_filters_follow_the_existing_queue_rules(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    assert not review.previous_button.isEnabled()

    review.next_button.click()
    assert "Row 2" in text_of(review.record_title)
    review.accept_button.click()
    review.next_button.click()
    review.next_button.click()
    assert "Row 4" in text_of(review.record_title)
    assert not review.next_button.isEnabled()
    review.next_unreviewed_button.click()
    assert "Row 1" in text_of(review.record_title)  # wraps past the reviewed row 2

    choose(review.status_filter, "reviewed")
    review.status_filter.activated.emit(review.status_filter.currentIndex())
    assert "Row 2" in text_of(review.record_title)
    assert "1 match the filters" in text_of(review.position)
    choose(review.status_filter, "all")
    review.status_filter.activated.emit(review.status_filter.currentIndex())
    assert "4 match" not in text_of(review.position)


def test_unsaved_changes_are_confirmed_before_they_are_discarded(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "uncertain", "sentiment")

    shell.platform.confirmed = False
    review.next_button.click()
    assert "Row 1" in text_of(review.record_title)  # stayed
    assert review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].isChecked()
    assert "unsaved changes" in shell.platform.confirmations[-1]

    shell.platform.confirmed = True
    review.next_button.click()
    assert "Row 2" in text_of(review.record_title)
    assert not review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].isChecked()


def test_switching_pages_asks_before_dropping_an_unsaved_judgment(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "uncertain", "sentiment")
    window = shell.window

    shell.platform.confirmed = False
    window.nav_buttons["Analyze one text"].click()
    assert window.pages.currentWidget() is window.projects_page  # stayed
    assert window.nav_buttons["Review"].isChecked()
    assert review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].isChecked()

    assert review.human.note.toPlainText() == ""
    assert window.review.state.has_unsaved_changes  # the draft is still there
    assert "leave this page" in shell.platform.confirmations[-1].lower()
    assert "close" not in shell.platform.confirmations[-1].lower()

    shell.platform.confirmed = True
    window.nav_buttons["Analyze one text"].click()
    assert window.pages.currentWidget() is window.analyze_page
    assert not window.review.state.has_unsaved_changes  # really discarded
    assert window.review.state.is_open  # the review itself stays where it was

    window.nav_buttons["Review"].click()
    assert window.pages.currentWidget() is window.projects_page
    assert "Unreviewed" in text_of(review.human.status)
    assert not review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].isChecked()
    assert "Row 1" in text_of(review.record_title)  # same record, saved state only
    assert not review.save_button.isEnabled()  # nothing left to save by accident


def test_closing_the_window_asks_before_dropping_an_unsaved_judgment(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "uncertain", "sentiment")

    shell.platform.confirmed = False
    event = QCloseEvent()
    shell.window.closeEvent(event)
    assert not event.isAccepted()
    assert "close" in shell.platform.confirmations[-1].lower()  # window-close wording

    shell.platform.confirmed = True
    event = QCloseEvent()
    shell.window.closeEvent(event)
    assert event.isAccepted()


def test_a_review_saved_elsewhere_is_kept_and_shown_on_conflict(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    project_id = shell.window.review.state.project_id
    assert project_id is not None
    other = ReviewWorkflow(SqliteProjectRepository(AppDataLocations(tmp_path)))
    seen = other.open_review(project_id)
    assert seen.record is not None
    other.save(
        project_id,
        1,
        ReviewDraft(
            sentiment_judgment=ReviewJudgment.UNCERTAIN,
            emotion_judgment=ReviewJudgment.UNCERTAIN,
            note="theirs",
        ),
        expected=seen.record.review,
    )

    review.human.note.setPlainText("mine")
    review.accept_button.click()

    assert review.notice.code.text() == "review_conflict"
    assert review.human.note.toPlainText() == "theirs"
    assert review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].isChecked()
    stored = other.open_review(project_id)
    assert stored.record is not None and stored.record.review.note == "theirs"


def test_failed_rows_are_explained_and_skipped(make_shell: Any, tmp_path: Path) -> None:
    def fail_second(call: int) -> None:
        if call == 2:
            raise ProviderError(provider="p", code="boom", message="row failed")

    shell = analysed_shell(
        make_shell, tmp_path, rows=3, gateway=ScriptedGateway(fail_second)
    )
    review = start_review(shell)

    assert "1 row could not be analysed" in text_of(review.failed)
    assert "Record 1 of 2" in text_of(review.position)
    review.next_button.click()
    assert "Row 3" in text_of(review.record_title)  # row 2 failed and is skipped


def test_export_writes_only_when_the_user_picks_a_file(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "correct", "sentiment")
    choose(review.human.sentiment_combo, "negative")
    pick(review, "accept", "emotion")
    review.human.note.setPlainText("=SUM(A1)")
    review.save_button.click()
    out = tmp_path / "exports"
    out.mkdir()
    target = out / "reviewed.csv"

    review.export_button.click()  # the dialog is cancelled: nothing is written
    assert shell.platform.save_requests == ["reviewed-results.csv"]
    assert list(out.iterdir()) == []
    assert review.notice.code.text() == "review_saved"  # no export, no error

    shell.platform.save_target = target
    review.native_box.setChecked(True)
    review.export_button.click()

    text = target.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["review_status"] == "reviewed"
    assert rows[0]["review_note"] == "'=SUM(A1)"
    assert "emotion_native_" in text.splitlines()[0]
    assert text_of(review.notice.title).endswith("Reviewed CSV saved")
    assert str(tmp_path) not in text_of(review.notice.body)
    assert [p.name for p in out.iterdir()] == ["reviewed.csv"]  # no temp leftovers


def test_a_failed_export_is_a_fixed_safe_message(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    shell.platform.save_target = tmp_path / "no-such-folder" / "out.csv"

    review.export_button.click()

    assert review.notice.code.text() == "export_failed"
    body = text_of(review.notice.body)
    assert str(tmp_path) not in body and SENTINEL not in body
    assert review.export_button.isEnabled()  # and the review is still usable


def test_leaving_the_review_for_another_page_keeps_the_saved_review_and_reopens_it(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    page = shell.window.projects_page
    review = start_review(shell)
    review.accept_button.click()

    shell.window.nav_buttons["Import & validation"].click()

    assert page.stack.currentWidget() is page.detail_page
    assert "Analysed 4 rows" in text_of(page.facts)
    shell.window.nav_buttons["Review"].click()
    assert "Reviewed" in text_of(page.review_page.human.status)
    assert "1 of 4 reviewed" in text_of(page.review_page.progress)


def test_the_review_form_is_keyboard_operable_and_named(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    review = start_review(shell)
    pick(review, "correct", "sentiment")
    pick(review, "correct", "emotion")

    controls = [
        *review.findChildren(QPushButton),
        *review.findChildren(QRadioButton),
        *review.findChildren(QCheckBox),
        *review.findChildren(QComboBox),
        review.human.note,
    ]
    assert controls
    for control in controls:
        assert control.focusPolicy() != Qt.FocusPolicy.NoFocus, control.objectName()
        assert control.accessibleName() or control.text(), control.objectName()
    # the AI values are announced as one named, read-only record
    assert "AI record" in review.ai.accessibleName()
    assert "Your judgment" in review.human.accessibleName()


def test_provisioning_and_project_analysis_still_work_beside_review(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed_shell(make_shell, tmp_path)
    start_review(shell)
    shell.window.show_page("Analyze one text")
    assert shell.window.analyze_page.analyze_button.isEnabled()
    shell.window.show_page("Projects")
    assert shell.window.projects_page.stack.currentWidget() is (
        shell.window.projects_page.review_page
    )  # the open project's page is where the person left it
