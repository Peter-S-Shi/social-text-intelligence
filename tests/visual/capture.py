"""Render the real desktop app and save what it draws (visual-evidence run).

Not a test: run it by hand with the platform's own Qt plugin (not ``offscreen``), for
example ``python tests/visual/capture.py out_dir`` (Windows, with the ``dev`` extras).
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
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton, QWidget  # noqa: E402

from social_text_intelligence.application.model_provisioning import (  # noqa: E402
    Readiness,
)
from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewDraft,
    ReviewJudgment,
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
from social_text_intelligence.desktop.qt.platform import DesktopPlatform  # noqa: E402
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


class Gateway:
    """The shared analysis service: synthetic providers, the real local detector."""

    initialized = True

    def __init__(self) -> None:
        self._service = AnalysisService(
            sentiment_provider=SyntheticSentiment(),
            emotion_provider=SyntheticEmotion(),
            language_detector=Py3LangidDetector(),
        )

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
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
    for _ in range(8):
        QCoreApplication.processEvents()


class Run:
    def __init__(
        self, out: Path, fake: FakeProvisioning | None = None, *, start: bool = True
    ) -> None:
        self.out = out
        self.root = Path(tempfile.mkdtemp(prefix="sti-visual-"))
        self.platform = Platform()
        self.fake = fake or FakeProvisioning(current=status())
        self.services = build_desktop_services(
            AppDataLocations(self.root),
            provisioning=self.fake,
            analysis=Gateway(),
        )
        self.window = MainWindow(
            self.services,
            ImmediateRunner(),
            DesktopPlatform(
                pick_folder=self.platform.pick_folder,
                pick_csv=self.platform.pick_csv,
                pick_save_csv=self.platform.pick_save_csv,
                open_folder=self.platform.open_folder,
                confirm=self.platform.confirm,
            ),
        )
        self.window.resize(WIDTH, HEIGHT)
        self.window.show()
        if start:
            self.window.start()
        settle()

    def shot(self, name: str, widget: QWidget | None = None) -> None:
        settle()
        target = widget or self.window
        path = self.out / f"{name}.png"
        target.grab().save(str(path))
        print("saved", path.name)

    def full(self, name: str) -> None:
        """The whole shown page, however tall (the window shows only part of it)."""

        settle()
        page = self.window.projects_page.stack.currentWidget()
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

    def import_csv(self, content: bytes, name: str = "Autumn survey") -> None:
        path = self.root / f"{name}.csv"
        path.write_bytes(content)
        self.platform.csv_file = path
        self.window.projects_page.import_button.click()
        settle()

    def analyse(self) -> None:
        self.window.projects_page.analyze_button.click()
        settle()

    def review_rows(self, rows: range, pattern: list[str]) -> None:
        """Save judgments through the workflow, as a person would over time."""

        workflow = self.services.reviews
        project_id = self.window.projects.state.current.summary.project_id  # type: ignore[union-attr]
        for index, row in enumerate(rows):
            snapshot = workflow.open_review(project_id, row=row)
            record = snapshot.record
            if record is None:
                continue
            how = pattern[index % len(pattern)]
            if how == "accept":
                workflow.accept_both(project_id, row, "", expected=record.review)
            elif how == "correct":
                workflow.save(
                    project_id,
                    row,
                    ReviewDraft(
                        sentiment_judgment=ReviewJudgment.CORRECT,
                        human_sentiment=SentimentLabel.NEGATIVE
                        if record.report.sentiment.label is not SentimentLabel.NEGATIVE
                        else SentimentLabel.NEUTRAL,
                        emotion_judgment=ReviewJudgment.CORRECT,
                        human_dominant_emotion=EmotionLabel.ANGER
                        if record.report.emotion.dominant_emotion
                        is not EmotionLabel.ANGER
                        else EmotionLabel.SADNESS,
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


def button(parent: QWidget, text: str) -> QPushButton:
    for item in parent.findChildren(QPushButton):
        if item.text() == text and item.isVisibleTo(parent):
            return item
    raise LookupError(text)


Scene = Callable[[Path], None]


def populated(out: Path) -> Run:
    run = Run(out)
    run.import_csv(feedback_csv())
    run.analyse()
    return run


def scene_projects_empty(out: Path) -> None:
    run = Run(out)
    run.shot("01-projects-empty")


def scene_import_validation(out: Path) -> None:
    run = Run(out)
    run.import_csv(feedback_csv())
    run.shot("02-import-validation-ready")


def scene_results(out: Path) -> None:
    run = populated(out)
    run.shot("03-results")
    run.full("03-results-full")
    page = run.window.projects_page.results_page
    page.status_filter.buttons["error"].click()
    run.shot("04-results-not-analysed")
    page._clear_filters()
    settle()
    page.sentiment_filter.setCurrentIndex(page.sentiment_filter.findData("negative"))
    page._filters_changed()
    run.shot("05-results-negative")


def scene_import_after(out: Path) -> None:
    run = populated(out)
    run.nav(Section.IMPORT)
    run.shot("06-import-validation-after-analysis")


def scene_review(out: Path) -> None:
    run = populated(out)
    run.review_rows(range(1, 13), ["accept", "correct", "accept", "uncertain"])
    run.nav(Section.REVIEW)
    run.shot("07-review")
    run.full("07-review-full")


def scene_agreement(out: Path) -> None:
    run = populated(out)
    run.review_rows(
        range(1, 30), ["accept", "accept", "correct", "accept", "uncertain"]
    )
    run.nav(Section.AGREEMENT)
    run.shot("08-agreement")
    run.full("08-agreement-full")


def scene_agreement_early(out: Path) -> None:
    run = populated(out)
    run.review_rows(range(1, 4), ["accept", "correct"])
    run.nav(Section.AGREEMENT)
    run.shot("09-agreement-early")


def scene_insights(out: Path) -> None:
    run = populated(out)
    run.review_rows(range(1, 20), ["accept", "correct", "accept"])
    run.nav(Section.COMPARE)
    run.shot("10-insights-compare")
    run.full("10-insights-compare-full")
    run.nav(Section.NOTES)
    run.shot("11-insights-notes-cases")
    run.full("11-insights-notes-cases-full")


def scene_analyze(out: Path) -> None:
    run = Run(out)
    run.window.show_page("Analyze one text")
    page = run.window.analyze_page
    page.editor.setPlainText(
        "The new update fixed the login bug, thanks a lot to the team."
    )
    page.analyze_button.click()
    run.shot("12-analyze-result")
    page.editor.setPlainText(
        "Merci beaucoup, la nouvelle version est beaucoup plus rapide."
    )
    page.analyze_button.click()
    run.shot("13-analyze-unsupported-language")


def scene_models(out: Path) -> None:
    fake = FakeProvisioning(
        current=status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
    )
    run = Run(out, fake)
    run.shot("14-setup-first-run", run.window.ui.setup_dialog)
    run.window.ui.show_models()
    settle()
    run.shot("15-models", run.window.ui.models_dialog)
    run.window.show_page("Analyze one text")
    run.shot("16-analyze-models-unavailable")


SCENES: dict[str, Scene] = {
    "projects_empty": scene_projects_empty,
    "import": scene_import_validation,
    "results": scene_results,
    "import_after": scene_import_after,
    "review": scene_review,
    "agreement": scene_agreement,
    "agreement_early": scene_agreement_early,
    "insights": scene_insights,
    "analyze": scene_analyze,
    "models": scene_models,
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
