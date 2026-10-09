"""Render the real desktop app and save what it draws (visual-evidence run).

Not a test: run it by hand with the platform's own Qt plugin (not ``offscreen``), for
example ``python tests/visual/capture.py out_dir [scene ...]`` on Windows with the
``dev`` extras. Set ``QT_SCALE_FACTOR=1.5`` to see the same screens at 150% scaling.

Every picture is ``QWidget.grab()`` of the application's own widgets, driven through
its own controllers on synthetic data in a throwaway data directory, so it can never
capture anything else on the desktop. Nothing here claims a screen-reader,
high-contrast, or any other assistive-technology check.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests/ (desktop.fakes, persistence.*)
sys.path.insert(0, str(HERE.parents[1] / "src"))

from desktop.fakes import (  # noqa: E402
    FakeProvisioning,
    ImmediateRunner,
    status,
)
from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from social_text_intelligence.application.insights_workflow import (  # noqa: E402
    InsightPerspective,
)
from social_text_intelligence.application.model_provisioning import (  # noqa: E402
    Readiness,
)
from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewDraft,
    ReviewJudgment,
    ReviewUnavailableError,
)
from social_text_intelligence.contracts import (  # noqa: E402
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.desktop.composition import (  # noqa: E402
    build_desktop_services,
)
from social_text_intelligence.desktop.navigation import Section  # noqa: E402
from social_text_intelligence.desktop.qt.main_window import MainWindow  # noqa: E402
from social_text_intelligence.desktop.qt.platform import (  # noqa: E402
    DesktopPlatform,
    confirm_box,
)
from social_text_intelligence.desktop.qt.style import STYLESHEET  # noqa: E402
from social_text_intelligence.infrastructure.app_data import (  # noqa: E402
    AppDataLocations,
)
from social_text_intelligence.providers.language_py3langid import (  # noqa: E402
    Py3LangidDetector,
)
from social_text_intelligence.services import AnalysisService  # noqa: E402
from visual.synthetic import (  # noqa: E402
    SyntheticEmotion,
    SyntheticSentiment,
    feedback_csv,
)

WIDTH, HEIGHT = 1280, 860


class LiveRunner(ImmediateRunner):
    """Runs a job at once and lets row progress reach the window while it runs."""

    def post(self, call: Callable[[], None]) -> None:
        call()


class Gateway:
    """The shared analysis service: synthetic providers, the real local detector."""

    initialized = True

    def __init__(self, on_call: Callable[[int], None] | None = None) -> None:
        self._service = AnalysisService(
            sentiment_provider=SyntheticSentiment(),
            emotion_provider=SyntheticEmotion(),
            language_detector=Py3LangidDetector(),
        )
        self.on_call = on_call
        self.calls = 0

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        self.calls += 1
        if self.on_call is not None:
            self.on_call(self.calls)
        return self._service.analyze(record)


class Platform:
    def __init__(self) -> None:
        self.csv_file: Path | None = None
        self.save_target: Path | None = None
        self.confirmed = True

    def pick_folder(self, parent: Any) -> Path | None:
        return None

    def pick_csv(self, parent: Any) -> Path | None:
        return self.csv_file

    def pick_save_csv(self, parent: Any, suggested: str) -> Path | None:
        return self.save_target

    def open_folder(self, path: Path) -> bool:
        return True

    def confirm(self, parent: Any, title: str, text: str) -> bool:
        return self.confirmed


def settle() -> None:
    for _ in range(10):
        QCoreApplication.processEvents()


class Run:
    def __init__(
        self,
        out: Path,
        fake: FakeProvisioning | None = None,
        *,
        size: tuple[int, int] = (WIDTH, HEIGHT),
        gateway: Gateway | None = None,
        live: bool = False,
        unmapped: bool = False,
    ) -> None:
        self.out = out
        self.root = Path(tempfile.mkdtemp(prefix="sti-visual-"))
        self.platform = Platform()
        self.fake = fake or FakeProvisioning(current=status())
        self.gateway = gateway or Gateway()
        self.services = build_desktop_services(
            AppDataLocations(self.root),
            provisioning=self.fake,
            analysis=self.gateway,
        )
        self.window = MainWindow(
            self.services,
            LiveRunner() if live else ImmediateRunner(),
            DesktopPlatform(
                pick_folder=self.platform.pick_folder,
                pick_csv=self.platform.pick_csv,
                pick_save_csv=self.platform.pick_save_csv,
                open_folder=self.platform.open_folder,
                confirm=self.platform.confirm,
            ),
        )
        if unmapped:
            # Real platform plugin, real layout and painting, but never mapped to the
            # desktop: the size is exact (a mapped window is clamped to the screen)
            self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.window.resize(*size)
        self.window.show()
        self.window.start()
        settle()

    @property
    def page(self) -> Any:
        return self.window.projects_page

    def shot(self, name: str, widget: QWidget | None = None) -> None:
        settle()
        target = widget or self.window
        path = self.out / f"{name}.png"
        target.grab().save(str(path))
        print("saved", path.name)

    def full(self, name: str) -> None:
        """The whole shown page, however tall (the window shows only part of it)."""

        settle()
        page = self.page.stack.currentWidget()
        assert page is not None
        scroller = getattr(page, "scroller", None)
        target: QWidget = page
        if scroller is not None:
            inner = scroller.widget()
            assert isinstance(inner, QWidget)
            target = inner
        path = self.out / f"{name}.png"
        target.grab().save(str(path))
        print("saved", path.name)

    def nav(self, section: Section) -> None:
        self.window._open_section(section)
        settle()

    def clear_focus(self) -> None:
        focused = self.window.focusWidget()
        if focused is not None:
            focused.clearFocus()
        settle()

    def import_csv(self, content: bytes, name: str = "Autumn survey") -> None:
        path = self.root / f"{name}.csv"
        path.write_bytes(content)
        self.platform.csv_file = path
        self.page.import_button.click()
        settle()

    def analyse(self) -> None:
        self.page.analyze_button.click()
        settle()

    def review_rows(self, rows: range, pattern: list[str]) -> None:
        """Save judgments through the workflow, as a person would over time."""

        workflow = self.services.reviews
        current = self.window.projects.state.current
        assert current is not None
        project_id = current.summary.project_id
        for index, row in enumerate(rows):
            try:
                record = workflow.open_review(project_id, row=row).record
            except ReviewUnavailableError:
                continue  # a rejected or failed row has nothing to review
            if record is None:
                continue
            how = pattern[index % len(pattern)]
            if how == "accept":
                workflow.accept_both(project_id, row, "", expected=record.review)
            elif how == "correct":
                negative = record.report.sentiment.label is SentimentLabel.NEGATIVE
                angry = record.report.emotion.dominant_emotion is EmotionLabel.ANGER
                workflow.save(
                    project_id,
                    row,
                    ReviewDraft(
                        sentiment_judgment=ReviewJudgment.CORRECT,
                        human_sentiment=SentimentLabel.NEUTRAL
                        if negative
                        else SentimentLabel.NEGATIVE,
                        emotion_judgment=ReviewJudgment.CORRECT,
                        human_dominant_emotion=EmotionLabel.SADNESS
                        if angry
                        else EmotionLabel.ANGER,
                        note="Synthetic reviewer note.",
                    ),
                    expected=record.review,
                )
            elif how == "uncertain":
                workflow.save(
                    project_id,
                    row,
                    ReviewDraft(
                        sentiment_judgment=ReviewJudgment.UNCERTAIN,
                        emotion_judgment=ReviewJudgment.ACCEPT,
                    ),
                    expected=record.review,
                )


Scene = Callable[[Path], None]


def populated(out: Path, **kwargs: Any) -> Run:
    run = Run(out, **kwargs)
    run.import_csv(feedback_csv())
    run.analyse()
    return run


# -- scenes -------------------------------------------------------------------------


def scene_projects(out: Path) -> None:
    run = Run(out)
    run.clear_focus()
    run.shot("01-projects-empty")
    run.import_csv(feedback_csv())
    run.analyse()
    run.nav(Section.PROJECTS)
    run.import_csv(
        b"record_id,text\nr1,hello there friend\nr2,another plain row\n", "Pilot notes"
    )
    run.nav(Section.PROJECTS)
    run.clear_focus()
    run.shot("02-projects-list")


def scene_import(out: Path) -> None:
    run = Run(out)
    run.import_csv(feedback_csv())
    run.clear_focus()
    run.shot("03-import-validation-ready")
    run.full("03-import-validation-ready-full")


def scene_running(out: Path) -> None:
    holder: list[Run] = []

    def at_row(n: int) -> None:
        if n == 21:
            holder[0].clear_focus()
            holder[0].shot("04-import-analysis-running")
        if n == 30:
            holder[0].window.projects.cancel()
            holder[0].shot("04b-import-cancelling")

    run = Run(out, gateway=Gateway(at_row), live=True)
    holder.append(run)
    run.import_csv(feedback_csv())
    run.analyse()
    run.clear_focus()
    run.shot("04c-import-after-cancel")


def scene_results(out: Path) -> None:
    run = populated(out)
    run.clear_focus()
    run.shot("05-results")
    run.full("05-results-full")
    page = run.page.results_page
    page.status_filter.buttons["error"].click()
    run.shot("06-results-not-analysed")
    page.clear_button.click()
    for sentiment in ("negative", "positive", "neutral"):
        page.sentiment_filter.setCurrentIndex(page.sentiment_filter.findData(sentiment))
        for emotion in ("joy", "anger", "gratitude", "fear", "disgust"):
            page.emotion_filter.setCurrentIndex(page.emotion_filter.findData(emotion))
            page._filters_changed()
            if page.table.rowCount() == 0:
                break
        if page.table.rowCount() == 0:
            break
    assert page.table.rowCount() == 0
    run.shot("07-results-no-match")


def scene_import_after(out: Path) -> None:
    run = populated(out)
    run.nav(Section.IMPORT)
    run.clear_focus()
    run.shot("08-import-validation-after-analysis")
    run.full("08-import-validation-after-analysis-full")


def scene_review(out: Path) -> None:
    run = populated(out)
    run.review_rows(range(1, 13), ["accept", "correct", "accept", "uncertain"])
    run.nav(Section.REVIEW)
    run.clear_focus()
    run.shot("09-review-partial")
    run.full("09-review-partial-full")
    review = run.page.review_page
    review.human.sentiment_radios[ReviewJudgment.UNCERTAIN].click()
    run.shot("10-review-unsaved-draft")
    box = confirm_box(
        run.window,
        "Unsaved changes",
        "You have unsaved changes to a review. Leave this page and discard them?",
    )
    box.show()
    run.shot("11-unsaved-changes-confirmation", box)
    box.close()


def scene_agreement(out: Path) -> None:
    run = populated(out)
    run.nav(Section.AGREEMENT)
    run.clear_focus()
    run.shot("12-agreement-none-reviewed")
    run.review_rows(range(1, 4), ["accept", "correct"])
    run.nav(Section.RESULTS)
    run.nav(Section.AGREEMENT)
    run.clear_focus()
    run.shot("13-agreement-below-thresholds")
    run.review_rows(
        range(4, 31), ["accept", "accept", "correct", "accept", "uncertain"]
    )
    run.nav(Section.RESULTS)
    run.nav(Section.AGREEMENT)
    run.clear_focus()
    run.shot("14-agreement")
    run.full("14-agreement-full")


def scene_insights(out: Path) -> None:
    run = populated(out)
    run.review_rows(range(1, 24), ["accept", "correct", "accept"])
    run.nav(Section.COMPARE)
    run.clear_focus()
    run.shot("15-insights-compare-ai")
    page = run.page.insights_page
    for perspective, name in (
        (InsightPerspective.HUMAN, "16-insights-compare-human"),
        (InsightPerspective.AGREEMENT, "17-insights-compare-agreement"),
    ):
        combo = page.perspective_combo
        combo.setCurrentIndex(combo.findData(perspective.value))
        combo.activated.emit(combo.currentIndex())
        page.apply_button.click()
        run.full(name)
    run.nav(Section.NOTES)
    run.clear_focus()
    run.shot("18-insights-notes-cases")
    page.select_button.click()
    run.full("18-insights-notes-cases-full")


def scene_analyze(out: Path) -> None:
    run = Run(out)
    run.window.show_page("Analyze one text")
    page = run.window.analyze_page
    page.editor.setPlainText(
        "The new update fixed the login bug, thanks a lot to the team."
    )
    page.analyze_button.click()
    run.clear_focus()
    run.shot("19-analyze-result")
    page.scores.native_toggle.click()
    page.scroller.verticalScrollBar().setValue(10_000)
    run.shot("19b-analyze-native-scores")
    page.editor.setPlainText(
        "Merci beaucoup, la nouvelle version est beaucoup plus rapide."
    )
    page.analyze_button.click()
    page.scroller.verticalScrollBar().setValue(0)
    run.shot("20-analyze-unsupported-language")


def scene_models(out: Path) -> None:
    run = Run(
        out,
        FakeProvisioning(
            current=status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
        ),
    )
    run.shot("21-setup-first-run", run.window.ui.setup_dialog)
    run.window.show_page("Analyze one text")
    run.clear_focus()
    run.shot("22-analyze-models-unavailable")
    run.nav(Section.PROJECTS)
    run.shot("23-projects-models-unavailable")
    problems = Run(
        out,
        FakeProvisioning(
            current=status(
                Readiness.CORRUPT,
                Readiness.INCOMPLETE,
                sentiment_args={"problems": ("model.safetensors",)},
                emotion_args={"resumable": 40 * 1024 * 1024},
            )
        ),
    )
    problems.window.ui.show_models()
    settle()
    problems.shot("24-models-needs-attention", problems.window.ui.models_dialog)
    ready = Run(out)
    ready.window.ui.show_models()
    settle()
    ready.shot("25-models-ready", ready.window.ui.models_dialog)


def scene_export(out: Path) -> None:
    run = populated(out)
    page = run.page.results_page
    run.platform.save_target = run.root / "normalized.csv"
    page.export_button.click()
    run.clear_focus()
    run.shot("26-results-export-saved")
    run.platform.save_target = run.root / "missing-folder" / "x.csv"
    page.export_button.click()
    run.shot("27-results-export-failed")


def scene_focus(out: Path) -> None:
    run = populated(out)
    page = run.page.results_page
    page.table.selectRow(3)
    page.table.setFocus()
    run.shot("28-focus-results-table")
    run.window.nav_buttons["Review"].setFocus()
    run.shot("29-focus-sidebar")
    page.status_filter.buttons["ok"].setFocus()
    run.shot("30-focus-filter-button")


def scene_small(out: Path) -> None:
    run = populated(out, size=(900, 620))
    run.clear_focus()
    run.shot("31-min-size-results")
    run.review_rows(range(1, 8), ["accept", "correct"])
    run.nav(Section.REVIEW)
    run.clear_focus()
    run.shot("32-min-size-review")
    run.nav(Section.AGREEMENT)
    run.shot("33-min-size-agreement")
    run.nav(Section.COMPARE)
    run.shot("34-min-size-insights")


def scene_unreadable(out: Path) -> None:
    run = Run(out)
    projects = run.root / "projects"
    projects.mkdir(exist_ok=True)
    (projects / f"{'ab' * 16}.sqlite3").write_bytes(b"not a database")
    run.window.projects.refresh()
    run.nav(Section.PROJECTS)
    run.clear_focus()
    run.shot("35-projects-unreadable-entry")


SCENES: dict[str, Scene] = {
    "projects": scene_projects,
    "import": scene_import,
    "running": scene_running,
    "results": scene_results,
    "import_after": scene_import_after,
    "review": scene_review,
    "agreement": scene_agreement,
    "insights": scene_insights,
    "analyze": scene_analyze,
    "models": scene_models,
    "export": scene_export,
    "focus": scene_focus,
    "small": scene_small,
    "unreadable": scene_unreadable,
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
