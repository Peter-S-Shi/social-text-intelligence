"""The two pages the provisioning experience needs as context: Projects and Analyze."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...application.model_provisioning import ModelsStatus
from ...application.projects import ProjectStatus, ProjectSummary
from ..analysis import AnalysisPageState
from ..controller import JobRunner
from ..gate import AnalysisAvailability
from ..panel import ActionId, ActionView, build_analysis_block
from .widgets import ActionRow, add_all, announce, frame, label


class AnalysisBlockBox(QWidget):
    """The always-visible, non-modal reason analysis is off, plus one way to fix it."""

    triggered = Signal(object)

    def __init__(self, parent: QWidget | None = None, *, quiet: bool = False) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Projects stay fully usable, so there the reason is a quiet notice
        self.box = frame("notice" if quiet else "alert")
        self.box.setObjectName("analysis-block")
        inner = QVBoxLayout(self.box)
        self.title = label(role="title")
        self.body = label()
        self.detail = label(role="muted")
        self.action_row = ActionRow()
        self.action_row.triggered.connect(self.triggered.emit)
        add_all(inner, self.title, self.body, self.detail, self.action_row)
        layout.addWidget(self.box)
        self.setVisible(False)
        self.description = ""

    def show_block(
        self, status: ModelsStatus, availability: AnalysisAvailability
    ) -> None:
        block = build_analysis_block(status, availability)
        if block is None:
            self.setVisible(False)
            self.description = ""
            return
        self.setVisible(True)
        self.title.setText(f"✕ {block.title}")
        self.body.setText(block.body)
        self.detail.setText("\n".join(block.detail))
        self.detail.setVisible(bool(block.detail))
        self.action_row.set_actions((block.action,))
        self.description = f"{block.title}. {block.body}"
        self.box.setAccessibleName(self.description)


class AnalyzePage(QWidget):
    open_models = Signal()
    verify_requested = Signal()
    analyze_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.heading = label("Analyze one text", role="headline")
        self.block = AnalysisBlockBox()
        self.block.triggered.connect(lambda _: self.open_models.emit())
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("text-input")
        self.editor.setAccessibleName("Text to analyse")
        self.editor.setPlaceholderText(
            "Paste one text to analyse. It stays on this computer."
        )
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("analyze-button")
        self.analyze_button.setProperty("primary", True)
        self.analyze_button.clicked.connect(
            lambda: self.analyze_requested.emit(self.editor.toPlainText())
        )
        self.progress_note = label(role="muted")
        self.progress_note.setObjectName("analysis-running")
        self.result_box = frame("panel")
        self.result_box.setObjectName("analysis-result")
        result_layout = QVBoxLayout(self.result_box)
        self.result_title = label("Result", role="title")
        self.result_text = label()
        self.result_provenance = label(role="mono")
        add_all(
            result_layout, self.result_title, self.result_text, self.result_provenance
        )
        self.error_box = frame("alert")
        self.error_box.setObjectName("analysis-error")
        error_layout = QVBoxLayout(self.error_box)
        self.error_title = label(role="title")
        self.error_body = label()
        self.error_actions = ActionRow()
        self.error_actions.triggered.connect(self._error_action)
        add_all(error_layout, self.error_title, self.error_body, self.error_actions)
        add_all(
            layout,
            self.heading,
            self.block,
            self.editor,
            self.progress_note,
            self.result_box,
            self.error_box,
        )
        layout.addWidget(self.analyze_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        self.result_box.setVisible(False)
        self.error_box.setVisible(False)
        self.progress_note.setVisible(False)
        self._availability = AnalysisAvailability.AVAILABLE
        self._running = False

    def _error_action(self, action: ActionView) -> None:
        if action.action is ActionId.VERIFY:
            self.verify_requested.emit()
        else:
            self.open_models.emit()

    def render_availability(
        self, status: ModelsStatus, availability: AnalysisAvailability
    ) -> None:
        self._availability = availability
        self.block.show_block(status, availability)
        self._refresh_button()

    def _refresh_button(self) -> None:
        available = self._availability is AnalysisAvailability.AVAILABLE
        self.analyze_button.setEnabled(available and not self._running)
        # the reason is always visible; this links it for assistive technology
        self.analyze_button.setAccessibleDescription(
            "" if available else self.block.description
        )

    def render_analysis(self, state: AnalysisPageState) -> None:
        self._running = state.running
        self.progress_note.setVisible(state.running)
        if state.running:
            text = (
                "Analyzing… the first analysis loads both models and can take a while."
            )
            self.progress_note.setText(text)
            announce(self.progress_note, text)
        result = state.result
        self.result_box.setVisible(result is not None)
        if result is not None:
            others = (
                f" · also {', '.join(result.secondary_emotions)}"
                if result.secondary_emotions
                else ""
            )
            self.result_text.setText(
                f"Sentiment: {result.sentiment} ({result.sentiment_confidence})\n"
                f"Emotion: {result.emotion} ({result.emotion_confidence}){others}"
            )
            self.result_provenance.setText("\n".join(result.provenance))
        error = state.error
        self.error_box.setVisible(error is not None)
        if error is not None:
            self.error_title.setText(f"✕ {error.title}")
            self.error_body.setText(error.body)
            actions: list[ActionView] = []
            if error.offers_verify:
                actions.append(ActionView(ActionId.VERIFY, "Verify files"))
            if error.offers_models:
                actions.append(ActionView(ActionId.OPEN_MODELS, "Open models…"))
            self.error_actions.set_actions(tuple(actions))
            announce(self.error_box, f"{error.title}. {error.body}", assertive=True)
        self._refresh_button()


def _when(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else "unknown"


class ProjectsPage(QWidget):
    open_models = Signal()

    def __init__(
        self,
        list_projects: Callable[[], tuple[ProjectSummary, ...]],
        runner: JobRunner,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._list = list_projects
        self._runner = runner
        layout = QVBoxLayout(self)
        self.heading = label("Projects", role="headline")
        self.block = AnalysisBlockBox(quiet=True)
        self.block.triggered.connect(lambda _: self.open_models.emit())
        self.summary = label()
        self.summary.setObjectName("projects-summary")
        self.items = QVBoxLayout()
        self.note = label(
            "Importing a CSV and analysing a project arrive in a later milestone. "
            "Existing projects stay on this computer until you delete them.",
            role="muted",
        )
        add_all(layout, self.heading, self.block, self.summary)
        layout.addLayout(self.items)
        layout.addWidget(self.note)
        layout.addStretch(1)
        self._item_widgets: list[QWidget] = []

    def render_availability(
        self, status: ModelsStatus, availability: AnalysisAvailability
    ) -> None:
        self.block.show_block(status, availability)

    def show_projects(self, projects: tuple[ProjectSummary, ...]) -> None:
        for widget in self._item_widgets:
            self.items.removeWidget(widget)
            widget.deleteLater()
        self._item_widgets = []
        if not projects:
            self.summary.setText("No projects yet.")
            return
        self.summary.setText(f"{len(projects)} project(s) on this computer.")
        for project in projects:
            box = frame("card")
            inner = QVBoxLayout(box)
            if project.status is ProjectStatus.OK:
                name = project.name or "Untitled project"
                text = f"Updated {_when(project.updated_at)}"
            elif project.status is ProjectStatus.UNSUPPORTED_VERSION:
                name = "Project from a newer version"
                text = "This version of the app cannot open it."
            else:
                name = "Unreadable project"
                text = "This project file cannot be read."
            inner.addWidget(label(name, role="title"))
            inner.addWidget(label(text, role="muted"))
            box.setAccessibleName(f"{name}. {text}")
            self.items.addWidget(box)
            box.show()
            self._item_widgets.append(box)

    def refresh(self) -> None:
        """List projects off the UI thread; a failure shows a fixed line."""

        self._runner.run(self._list, self._listed)

    def _listed(self, outcome: object) -> None:
        if isinstance(outcome, BaseException):
            self.show_projects(())
            self.summary.setText("The project list could not be read.")
        else:
            self.show_projects(outcome)  # type: ignore[arg-type]
