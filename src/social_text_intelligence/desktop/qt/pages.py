"""The Analyze one text page and the shared analysis-block notice."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...application.model_provisioning import ModelsStatus
from ..analysis import AnalysisPageState
from ..gate import AnalysisAvailability
from ..panel import ActionId, ActionView, build_analysis_block
from .components import Card, Page, PageHeader, ScorePanel
from .widgets import ActionRow, LanguageBox, add_all, announce, frame, label


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


class AnalyzePage(Page):
    open_models = Signal()
    verify_requested = Signal()
    analyze_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.header = PageHeader("Analyze one text")
        self.heading = self.header.title
        self.header.set_subtitle(
            "Not saved: nothing is written to disk, and the text stays on this computer."
        )
        self.block = AnalysisBlockBox()
        self.block.triggered.connect(lambda _: self.open_models.emit())
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("text-input")
        self.editor.setAccessibleName("Text to analyse")
        self.editor.setPlaceholderText(
            "Paste one text to analyse. It stays on this computer."
        )
        self.editor.setMinimumHeight(140)
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("analyze-button")
        self.analyze_button.setProperty("primary", True)
        self.analyze_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.analyze_button.clicked.connect(
            lambda: self.analyze_requested.emit(self.editor.toPlainText())
        )
        self.progress_note = label(role="muted")
        self.progress_note.setObjectName("analysis-running")

        self.input_card = Card("TEXT")
        self.input_card.add(self.editor)
        actions = QHBoxLayout()
        actions.addWidget(self.analyze_button, 0)
        actions.addWidget(self.progress_note, 1)
        self.input_card.layout_.addLayout(actions)

        self.result_box = Card("RESULT")
        self.result_box.setObjectName("analysis-result")
        self.result_title = self.result_box.eyebrow
        self.result_text = label(role="title")
        self.result_text.setObjectName("result-text")
        self.result_provenance = label(role="mono")
        # The language check sits beside the labels, never inside them.
        self.language_box = LanguageBox("analysis-language")
        self.language_headline = self.language_box.headline
        self.language_detail = self.language_box.detail
        self.scores = ScorePanel()
        add_all(
            self.result_box.layout_,
            self.result_text,
            self.language_box,
            self.scores,
            self.result_provenance,
        )
        self.error_box = frame("alert")
        self.error_box.setObjectName("analysis-error")
        error_layout = QVBoxLayout(self.error_box)
        self.error_title = label(role="title")
        self.error_body = label()
        self.error_actions = ActionRow()
        self.error_actions.triggered.connect(self._error_action)
        add_all(error_layout, self.error_title, self.error_body, self.error_actions)
        add_all(self.body, self.header, self.block, self.input_card)
        add_all(self.body, self.result_box, self.error_box)
        self.body.addStretch(1)
        self.result_box.setVisible(False)
        self.error_box.setVisible(False)
        self.progress_note.setVisible(False)
        self._availability = AnalysisAvailability.AVAILABLE
        self._running = False
        self._external_busy = False

    def _error_action(self, action: ActionView) -> None:
        if action.action is ActionId.VERIFY:
            self.verify_requested.emit()
        else:
            self.open_models.emit()

    def set_external_busy(self, busy: bool) -> None:
        """A project analysis is running; one analysis at a time."""

        self._external_busy = busy
        self.progress_note.setVisible(self._running or busy)
        if busy and not self._running:
            self.progress_note.setText(
                "A project analysis is running. Analyze one text is available when "
                "it finishes."
            )
        self._refresh_button()

    def render_availability(
        self, status: ModelsStatus, availability: AnalysisAvailability
    ) -> None:
        self._availability = availability
        self.block.show_block(status, availability)
        self._refresh_button()

    def _refresh_button(self) -> None:
        available = self._availability is AnalysisAvailability.AVAILABLE
        self.analyze_button.setEnabled(
            available and not self._running and not self._external_busy
        )
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
            self.language_box.show_language(
                result.language_headline,
                result.language_detail,
                result.language_warns,
            )
            self.scores.show_scores(result.scores)
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
