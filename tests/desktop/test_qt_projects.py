"""Headless Qt tests of the user path: CSV, project, analysis, reopen, delete."""

from __future__ import annotations

import os
import threading
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
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import QPushButton  # noqa: E402

from social_text_intelligence.application.model_provisioning import (  # noqa: E402
    Readiness,
)
from social_text_intelligence.desktop.projects import ProjectsActivity  # noqa: E402
from social_text_intelligence.desktop.qt.runner import QtJobRunner  # noqa: E402

from .conftest import FakePlatform  # noqa: E402
from .fakes import FakeProvisioning, ManualRunner, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()
CORRUPT = status(
    Readiness.READY,
    Readiness.CORRUPT,
    emotion_args={"problems": ("model.safetensors",)},
)


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    """Project tests need a gateway that answers each record with its own report."""

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


def csv_file(tmp_path: Path, name: str, content: bytes) -> Path:
    folder = tmp_path / "csv"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_bytes(content)
    return path


def text_of(widget: Any) -> str:
    return str(widget.text())


def import_csv(shell: Shell, path: Path) -> None:
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()


def test_importing_a_csv_creates_a_project_and_opens_it(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page
    assert page.empty_list.isVisibleTo(page)
    assert "No projects yet" in text_of(page.empty_list.title)

    import_csv(shell, csv_file(tmp_path, "Support tickets.csv", csv_text(4)))

    assert page.stack.currentWidget() is page.detail_page
    assert text_of(page.detail_title_label) == "Support tickets"
    assert text_of(page.state_line) == "Ready to analyse."
    assert page.analyze_button.isEnabled()
    assert text_of(page.analyze_button) == "Analyze 4 rows"
    assert not page.column_box.isVisibleTo(page)

    assert shell.window.nav_buttons["Import & validation"].isChecked()
    assert text_of(shell.window.project_title) == "Support tickets"

    shell.window.nav_buttons["Projects"].click()
    assert page.stack.currentWidget() is page.list_page
    assert "1 project(s)" in text_of(page.summary)
    assert not shell.window.project_area.isVisibleTo(shell.window)


def test_a_csv_without_a_text_column_shows_a_real_selection_step(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page

    import_csv(shell, csv_file(tmp_path, "notes.csv", csv_text(3, column="message")))

    assert page.column_box.isVisibleTo(page)
    items = [page.column_combo.itemText(i) for i in range(page.column_combo.count())]
    assert items == ["Choose a column…", "record_id", "message"]
    assert not page.analyze_button.isVisibleTo(page)  # not before a column is chosen
    assert not page.choose_button.isEnabled()  # no default: the choice is explicit
    page.column_combo.setCurrentText("message")
    assert page.choose_button.isEnabled()

    shell.button(page, "Use this column").click()

    assert not page.column_box.isVisibleTo(page)
    assert text_of(page.state_line) == "Ready to analyse."
    assert page.analyze_button.isEnabled()


def test_an_invalid_csv_shows_a_safe_notice_and_creates_nothing(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page

    import_csv(shell, csv_file(tmp_path, "empty.csv", b""))

    assert page.stack.currentWidget() is page.list_page
    assert page.notice.isVisibleTo(page)
    assert "The CSV file is empty." in text_of(page.notice.body)
    assert page.notice.code.text() == "empty_file"
    assert page.empty_list.isVisibleTo(page)

    import_csv(shell, csv_file(tmp_path, "huge.csv", b"x" * 3_000_000))
    assert page.notice.code.text() == "file_too_large"
    assert str(tmp_path) not in text_of(page.notice.body)


def test_analysis_shows_row_progress_then_the_result(
    make_shell: Any, tmp_path: Path
) -> None:
    runner = ManualRunner()
    shell = make_shell(FakeProvisioning(current=READY), runner)
    while runner.jobs:
        runner.run_next()
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(4)))
    runner.run_next()  # the import
    runner.run_next()  # the validation detail of the new project
    assert page.analyze_button.isEnabled()

    page.analyze_button.click()
    work, deliver = runner.jobs.popleft()
    outcome = work()
    runner.pump_posts()  # the coalesced row-progress update

    assert page.progress.isVisibleTo(page)
    assert text_of(page.progress.text) == "Analyzing row 4 of 4"
    assert page.progress.bar.value() == 1000
    assert not page.analyze_button.isEnabled() and not page.delete_button.isEnabled()
    assert page.progress.cancel_button.isEnabled()

    deliver(outcome)

    assert not page.progress.isVisibleTo(page)
    assert "Analysed 4 rows" in text_of(page.facts)
    assert "Sentiment:" in text_of(page.facts)
    assert not page.analyze_button.isVisibleTo(page)
    assert page.section.value == "results"  # the analysis finished: show the results


def test_cancel_keeps_the_project_unanalysed_and_it_can_run_again(
    make_shell: Any, tmp_path: Path, pump: Any
) -> None:
    started, proceed = threading.Event(), threading.Event()

    def pause_at_row_three(n: int) -> None:
        if n == 3:
            started.set()
            proceed.wait(5)

    gateway = ScriptedGateway(pause_at_row_three)
    runner = QtJobRunner()
    shell = make_shell(FakeProvisioning(current=READY), runner, gateway=gateway)
    page = shell.window.projects_page
    try:
        pump(lambda: shell.window.projects.state.listed)  # the launch listing
        import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(8)))
        pump(lambda: shell.window.projects.state.current is not None)
        page.analyze_button.click()
        pump(started.is_set)
        pump(lambda: page.progress.cancel_button.isEnabled())
        assert shell.window.analyze_page.analyze_button.isEnabled() is False

        page.progress.cancel_button.click()
        assert "Nothing will be saved" in text_of(page.progress.text)
        proceed.set()
        pump(lambda: shell.window.projects.state.activity is ProjectsActivity.IDLE)
    finally:
        proceed.set()
        runner.wait_idle()

    assert gateway.calls == 3
    assert "Analysis cancelled" in text_of(page.notice.title)
    assert text_of(page.state_line) == "Ready to analyse."
    assert page.analyze_button.isEnabled()


def test_a_project_reopens_after_a_restart_with_its_analysis(
    make_shell: Any, tmp_path: Path
) -> None:
    first = make_shell(FakeProvisioning(current=READY))
    import_csv(first, csv_file(tmp_path, "p.csv", csv_text(3)))
    first.window.projects_page.analyze_button.click()
    assert "Analysed 3 rows" in text_of(first.window.projects_page.facts)

    second = make_shell(FakeProvisioning(current=READY))  # a fresh app, same folder
    page = second.window.projects_page
    assert "1 project(s)" in text_of(page.summary)
    second.button(page, "Open").click()

    assert text_of(page.detail_title_label) == "p"
    assert "Analysed 3 rows" in text_of(page.facts)


def test_delete_asks_first_uses_conservative_wording_and_removes_the_files(
    make_shell: Any, tmp_path: Path
) -> None:
    platform = FakePlatform()
    shell = make_shell(FakeProvisioning(current=READY), platform=platform)
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(2)))
    shell.window.nav_buttons["Projects"].click()
    platform.confirmed = False

    shell.button(page, "Delete…").click()
    assert platform.confirmations
    text = platform.confirmations[0]
    assert "removed from this application's data files" in text
    assert "backups are not affected" in text
    assert "securely" not in text.lower() and "erase" not in text.lower()
    assert list((tmp_path / "projects").glob("*"))  # declined: still there

    platform.confirmed = True
    shell.button(page, "Delete…").click()

    assert not list((tmp_path / "projects").glob("*"))
    assert page.empty_list.isVisibleTo(page)
    assert "Project deleted" in text_of(page.notice.title)
    assert "application's data files" in text_of(page.notice.body)


def test_deleting_from_the_open_project_returns_to_the_list(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(2)))

    shell.button(page, "Delete project…").click()

    assert page.stack.currentWidget() is page.list_page
    assert not list((tmp_path / "projects").glob("*"))


def test_unreadable_entries_are_listed_safely_and_can_be_deleted(
    make_shell: Any, tmp_path: Path
) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / f"{'ab' * 16}.sqlite3").write_bytes(b"not a database")
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page

    assert "1 project(s)" in text_of(page.summary)
    names = [b.accessibleName() for b in page.findChildren(QPushButton)]
    assert "Delete Unreadable project" in names
    assert "Open Unreadable project" not in [
        b.accessibleName() for b in page.findChildren(QPushButton) if b.isVisible()
    ]

    shell.button(page, "Delete…").click()
    assert page.empty_list.isVisibleTo(page)


def test_projects_stay_usable_when_models_are_not_ready_but_analysis_is_off(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(
        FakeProvisioning(
            current=status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
        )
    )
    page = shell.window.projects_page
    assert page.block.isVisibleTo(page)  # a quiet notice on the list

    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(2)))  # import still works

    assert page.detail_block.isVisibleTo(page)
    assert "models are not ready" in text_of(page.detail_block.body)
    assert not page.analyze_button.isEnabled()
    assert "not ready" in page.analyze_button.accessibleDescription()
    assert page.delete_button.isEnabled()


def test_h2_latching_mid_batch_fails_the_run_and_commits_nothing(
    make_shell: Any, tmp_path: Path
) -> None:
    holder: list[Shell] = []

    def latch_at_row_three(n: int) -> None:
        if n == 3:  # a Verify finds damage while this batch is running
            holder[0].window.services.gate.note_verify_result(CORRUPT)

    shell = make_shell(
        FakeProvisioning(current=READY), gateway=ScriptedGateway(latch_at_row_three)
    )
    holder.append(shell)
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(6)))

    page.analyze_button.click()

    assert page.notice.code.text() == "analysis_session_blocked"
    assert "restart" in text_of(page.notice.body).lower()
    assert text_of(page.state_line) == "Ready to analyse."  # nothing was committed
    assert not page.analyze_button.isEnabled()
    assert page.detail_block.isVisibleTo(page)
    assert "restart" in text_of(page.detail_block.body).lower()


def test_text_analysis_waits_while_a_project_batch_runs(
    make_shell: Any, tmp_path: Path
) -> None:
    runner = ManualRunner()
    shell = make_shell(FakeProvisioning(current=READY), runner)
    while runner.jobs:
        runner.run_next()
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(3)))
    runner.run_next()  # the import
    runner.run_next()  # the validation detail of the new project
    shell.window.show_page("Analyze one text")
    analyze_page = shell.window.analyze_page
    assert analyze_page.analyze_button.isEnabled()

    shell.window.projects_page.analyze_button.click()

    assert not analyze_page.analyze_button.isEnabled()
    assert "project analysis is running" in text_of(analyze_page.progress_note)
    runner.run_next()
    assert analyze_page.analyze_button.isEnabled()


def test_closing_during_a_project_analysis_cancels_it_and_closes_after(
    make_shell: Any, tmp_path: Path
) -> None:
    runner = ManualRunner()
    shell = make_shell(FakeProvisioning(current=READY), runner)
    while runner.jobs:
        runner.run_next()
    import_csv(shell, csv_file(tmp_path, "p.csv", csv_text(3)))
    runner.run_next()  # the import
    runner.run_next()  # the validation detail of the new project
    shell.window.projects_page.analyze_button.click()

    event = QCloseEvent()
    shell.window.closeEvent(event)

    assert not event.isAccepted()
    assert shell.window.projects.state.cancelling
    runner.run_next()  # the cancelled run finishes
    QCoreApplication.processEvents()
    assert not shell.window.isVisible()
    persisted = shell.window.services.workflow.list_projects()
    assert (
        shell.window.services.workflow.open_project(
            persisted[0].project_id
        ).analyzed_rows
        is None
    )


def test_no_notice_in_the_ui_carries_csv_content(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "x.csv", SENTINEL.encode() + b"\xff"))
    shown = text_of(page.notice.title) + text_of(page.notice.body)
    assert SENTINEL not in shown and "x.csv" not in shown


def test_the_import_card_shows_figures_and_recognised_columns(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page

    import_csv(shell, csv_file(tmp_path, "Support tickets.csv", csv_text(4)))

    assert text_of(page.figure_ready.value) == "4"
    assert text_of(page.figure_rejected.value) == "0"
    assert not page.figure_language.isVisibleTo(page)  # known only after analysis
    names = {
        c.accessibleName() for c in page.metadata_row.findChildren(type(page.heading))
    }
    assert "record_id column, in the file" in names
    assert "notes column, not in the file" in names
    # each chip says its state in words as well as by tint
    texts = {c.text() for c in page.metadata_row.findChildren(type(page.heading))}
    assert "notes — not in file" in texts


def test_the_project_list_is_one_card_with_the_newest_open_as_the_primary_action(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page
    import_csv(shell, csv_file(tmp_path, "First.csv", csv_text(2)))
    shell.window.nav_buttons["Projects"].click()
    import_csv(shell, csv_file(tmp_path, "Second.csv", csv_text(2)))
    shell.window.nav_buttons["Projects"].click()

    opens = [row.open_button for row in page._rows]
    assert len(opens) == 2
    assert [b.property("primary") for b in opens] == [True, False]
    assert page.rows_card.isVisibleTo(page)
    assert all(row.parent() is page.rows_card for row in page._rows)


def test_the_list_offers_a_way_to_analyze_one_text(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    page = shell.window.projects_page

    page.analyze_text_button.click()

    assert shell.window.current_section().value == "analyze"
    assert shell.window.nav_buttons["Analyze one text"].isChecked()


def test_the_sidebar_says_when_no_project_is_open(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = make_shell(FakeProvisioning(current=READY))
    window = shell.window
    assert window.no_project.isVisibleTo(window)
    assert not window.project_area.isVisibleTo(window)

    import_csv(shell, csv_file(tmp_path, "Support tickets.csv", csv_text(2)))

    assert window.project_area.isVisibleTo(window)
    assert not window.no_project.isVisibleTo(window)
