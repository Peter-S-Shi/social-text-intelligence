"""Every page keeps working at the 900 px minimum width: no sideways scrolling.

The test fonts of the headless platform are wider than Windows' own, so passing here
is a stricter check than the real window needs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from persistence.workflow_samples import ScriptedGateway, csv_text  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QScrollArea  # noqa: E402

from social_text_intelligence.desktop.navigation import Section  # noqa: E402

from .fakes import FakeProvisioning, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    def factory(fake: FakeProvisioning) -> Shell:
        return cast(Shell, make_shell(fake, None, None, ScriptedGateway()))

    return factory


def settle() -> None:
    for _ in range(5):
        QCoreApplication.processEvents()


def test_every_page_fits_the_minimum_width_with_real_content(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    window = shell.window
    window.resize(900, 620)
    settle()
    folder = tmp_path / "csv"
    folder.mkdir()
    path = folder / "tickets.csv"
    path.write_bytes(csv_text(6))
    shell.platform.csv_file = path
    page = window.projects_page
    shell.button(page, "Import CSV…").click()  # the import page, ready to analyse
    settle()
    scrollers = {"import": page.detail_page.scroller}
    page.analyze_button.click()  # analysed: the page moves on to the results
    settle()
    window.nav_buttons["Review"].click()
    page.review_page.accept_button.click()  # one reviewed record
    settle()
    scrollers.update(
        {
            "results": page.results_page.scroller,
            "review": page.review_page.scroller,
            "agreement": page.agreement_page.scroller,
            "insights": page.insights_page.scroller,
        }
    )

    for section, key in (
        (Section.IMPORT, "import"),
        (Section.RESULTS, "results"),
        (Section.REVIEW, "review"),
        (Section.AGREEMENT, "agreement"),
        (Section.COMPARE, "insights"),
        (Section.NOTES, "insights"),
    ):
        window._open_section(section)
        settle()
        bar = scrollers[key].horizontalScrollBar()
        assert bar.maximum() == 0, f"{section.value} scrolls sideways at 900 px"

    window._open_section(Section.ANALYZE)
    analyze = window.analyze_page
    analyze.editor.setPlainText("A synthetic joyful sentence.")
    analyze.analyze_button.click()
    settle()
    assert analyze.scroller.horizontalScrollBar().maximum() == 0

    window._open_section(Section.PROJECTS)
    settle()
    assert page.list_page.scroller.horizontalScrollBar().maximum() == 0


def test_the_first_run_window_and_the_models_window_fit_their_minimum_size(
    make_shell: Any,
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    for dialog in (shell.setup, shell.models):
        dialog.resize(dialog.minimumSize())
        dialog.show()
        settle()
        scroll = dialog.panel.findChild(QScrollArea, "panel-scroll")
        assert scroll is not None
        assert scroll.horizontalScrollBar().maximum() == 0, dialog.windowTitle()


def test_review_never_scrolls_sideways_across_a_sweep_of_widths(
    make_shell: Any, tmp_path: Path
) -> None:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    window = shell.window
    folder = tmp_path / "csv"
    folder.mkdir()
    (folder / "tickets.csv").write_bytes(csv_text(6))
    shell.platform.csv_file = folder / "tickets.csv"
    page = window.projects_page
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    window.nav_buttons["Review"].click()
    settle()

    for width in range(900, 1500, 37):  # across every layout flip point
        window.resize(width, 700)
        settle()
        bar = page.review_page.scroller.horizontalScrollBar()
        assert bar.maximum() == 0, f"sideways scroll at {width} px"
