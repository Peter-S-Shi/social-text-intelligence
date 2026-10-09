"""Capture the nine Round 3 reference screens from the real native app.

Not a test. Run it by hand with the platform's own Qt plugin (never ``offscreen``)::

    python tests/visual/fidelity.py <output-directory> [scene ...]

Every picture is ``QWidget.grab()`` of the application's own window, driven through
its own controllers on synthetic data in a throwaway data directory. The window is
created *unmapped* (``WA_DontShowOnScreen``): the real Windows plugin lays it out and
paints it, but it never appears on the desktop, so the size is exact (a mapped window
is clamped to the screen) and nothing else on the desktop can be captured. The
reference frame is 1358 x 803 content pixels at 100% scale; set ``QT_SCALE_FACTOR=1.5``
for the 150% set. File names follow the reference screenshots (``demo_*.png``) so the
nine screens line up one to one. The datasets are invented and differ in detail from
the prototype's scripted numbers; see ``docs/V2_M8_TRACK_B_FIDELITY.md``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests/ (desktop.fakes, visual.*)
sys.path.insert(0, str(HERE.parents[1] / "src"))

from desktop.fakes import FakeProvisioning, status  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from social_text_intelligence.application.insights_workflow import (  # noqa: E402
    InsightPerspective,
)
from social_text_intelligence.application.model_provisioning import (  # noqa: E402
    Readiness,
)
from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewFilters,
)
from social_text_intelligence.desktop.navigation import Section  # noqa: E402
from social_text_intelligence.desktop.qt.style import STYLESHEET  # noqa: E402
from social_text_intelligence.services.review import ReviewFilter  # noqa: E402
from visual.capture import Run, settle  # noqa: E402
from visual.synthetic import checkout_csv, support_inbox_csv  # noqa: E402

SIZE = (1358, 803)
REVIEW_PATTERN = ["accept", "accept", "correct", "accept", "uncertain"]
EXAMPLE_TEXT = (
    "The new update finally fixed the login bug, but the app still crashes "
    "whenever I try to export a large file."
)

Scene = Callable[[Path], None]


def new_run(out: Path, **kwargs: object) -> Run:
    return Run(out, size=SIZE, unmapped=True, **kwargs)  # type: ignore[arg-type]


def build_three_projects(out: Path) -> Run:
    """The projects list of the reference: three projects, different review progress."""

    run = new_run(out)
    run.import_csv(support_inbox_csv(), "Community forum - onboarding thread")
    _choose_column(run, "message_body")
    run.analyse()
    run.review_rows(range(1, 15), ["accept", "correct", "accept"])
    run.nav(Section.PROJECTS)
    run.import_csv(
        b"record_id,text\nr1,hello there friend\nr2,another plain row\n"
        b"r3,this is fine\nr4,works for me\nr5,thanks a lot\n",
        "Support inbox pilot",
    )
    run.analyse()
    run.review_rows(range(1, 4), ["accept"])
    run.nav(Section.PROJECTS)
    run.import_csv(checkout_csv(), "Checkout feedback - autumn sample")
    run.analyse()
    run.review_rows(range(1, 30), REVIEW_PATTERN)
    return run


def _choose_column(run: Run, name: str) -> None:
    page = run.page
    if page.column_box.isVisibleTo(page):
        page.column_combo.setCurrentIndex(page.column_combo.findText(name))
        page.choose_button.click()
        settle()


def scene_setup(out: Path) -> None:
    first = new_run(
        out,
        fake=FakeProvisioning(
            current=status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
        ),
    )
    first.shot("demo_setup", first.window.ui.setup_dialog)
    ready = new_run(out)
    ready.window.ui.show_models()
    settle()
    ready.shot("demo_setup-ready", ready.window.ui.models_dialog)


def scene_projects(out: Path) -> None:
    run = build_three_projects(out)
    run.nav(Section.PROJECTS)
    run.clear_focus()
    run.shot("demo_projects")


def scene_direct(out: Path) -> None:
    run = new_run(out)
    run.window.show_page("Analyze one text")
    page = run.window.analyze_page
    page.editor.setPlainText(EXAMPLE_TEXT)
    page.analyze_button.click()
    run.clear_focus()
    run.shot("demo_direct")


def scene_import(out: Path) -> None:
    run = new_run(out)
    run.import_csv(support_inbox_csv(), "Support inbox - October")
    _choose_column(run, "message_body")
    run.clear_focus()
    run.shot("demo_import")


def scene_results(out: Path) -> None:
    run = new_run(out)
    run.import_csv(checkout_csv(), "Checkout feedback - autumn sample")
    run.analyse()
    run.review_rows(range(1, 30), REVIEW_PATTERN)
    run.nav(Section.RESULTS)
    run.clear_focus()
    run.shot("demo_results")


def _reviewed(out: Path) -> Run:
    run = new_run(out)
    run.import_csv(checkout_csv(), "Checkout feedback - autumn sample")
    run.analyse()
    run.review_rows(range(1, 30), REVIEW_PATTERN)
    return run


def scene_review(out: Path) -> None:
    run = _reviewed(out)
    run.nav(Section.REVIEW)
    run.window.review.set_filters(ReviewFilters(status=ReviewFilter.UNREVIEWED))
    settle()
    run.clear_focus()
    run.shot("demo_review")


def scene_agreement(out: Path) -> None:
    run = _reviewed(out)
    run.nav(Section.AGREEMENT)
    run.clear_focus()
    run.shot("demo_agreement")


def scene_compare(out: Path) -> None:
    run = _reviewed(out)
    run.nav(Section.COMPARE)
    page = run.page.insights_page
    combo = page.perspective_combo
    combo.setCurrentIndex(combo.findData(InsightPerspective.AGREEMENT.value))
    combo.activated.emit(combo.currentIndex())
    page.apply_button.click()
    run.clear_focus()
    run.shot("demo_compare")


def scene_notes(out: Path) -> None:
    run = _reviewed(out)
    run.nav(Section.NOTES)
    run.page.insights_page.select_button.click()
    run.clear_focus()
    run.shot("demo_notes")


SCENES: dict[str, Scene] = {
    "setup": scene_setup,
    "projects": scene_projects,
    "direct": scene_direct,
    "import": scene_import,
    "results": scene_results,
    "review": scene_review,
    "agreement": scene_agreement,
    "compare": scene_compare,
    "notes": scene_notes,
}


def main(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    app.setStyleSheet(STYLESHEET)
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    names = argv[2:] or list(SCENES)
    print("platform:", app.platformName())
    for name in names:
        SCENES[name](out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
