"""The shared provisioning panel: model cards, actions, progress, and the last result.

The setup window and the Models window embed the same panel, as the M5.1 design
requires; only the window-level actions differ (``build_panel(window=...)``).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..panel import ActionId, ActionView, PanelView
from .widgets import (
    ActionRow,
    CardWidget,
    ProgressBlock,
    ReportBox,
    add_all,
    frame,
    label,
)


class ProvisioningPanel(QWidget):
    action_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("panel-scroll")
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        self._layout = QVBoxLayout(body)
        self.headline = label(role="headline")
        self.headline.setObjectName("panel-headline")
        self.subline = label(role="muted")
        self.session_note = frame("alert")
        self.session_note.setObjectName("session-note")
        note_layout = QVBoxLayout(self.session_note)
        self.session_text = label()
        note_layout.addWidget(self.session_text)
        self.busy_note = label(role="muted")
        self.busy_note.setObjectName("busy-note")
        self.folder_note = label(role="muted")
        self.folder_note.setObjectName("folder-note")
        self.cards: dict[str, CardWidget] = {}
        self.cards_box = QVBoxLayout()
        self.action_row = ActionRow()
        self.progress = ProgressBlock()
        self.report = ReportBox()
        add_all(
            self._layout,
            self.headline,
            self.subline,
            self.session_note,
            self.progress,
            self.report,
            self.busy_note,
        )
        self._layout.addLayout(self.cards_box)
        self._layout.addWidget(self.action_row)
        self._layout.addWidget(self.folder_note)
        self._layout.addStretch(1)
        self.action_row.triggered.connect(self.action_requested.emit)
        self.report.triggered.connect(self.action_requested.emit)
        self.progress.stop_requested.connect(self._stop)
        self.progress.setVisible(False)
        self.report.setVisible(False)
        self.session_note.setVisible(False)
        self.busy_note.setVisible(False)
        self.folder_note.setVisible(False)

    def _stop(self) -> None:
        self.action_requested.emit(ActionView(ActionId.STOP, "Stop"))

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def show_view(self, view: PanelView) -> None:
        had_focus = self._has_focus()
        self.headline.setText(view.headline)
        self.subline.setText(view.subline)
        self.session_note.setVisible(view.session_note is not None)
        self.session_text.setText(view.session_note or "")
        for card_view in view.cards:
            card = self.cards.get(card_view.key)
            if card is None:
                card = CardWidget(card_view.key)
                card.triggered.connect(self.action_requested.emit)
                self.cards[card_view.key] = card
                self.cards_box.addWidget(card)
                card.show()
            card.show_card(card_view)
        self.action_row.set_actions(view.actions)
        self.action_row.setVisible(bool(view.actions))
        self.busy_note.setText(view.busy_note or "")
        self.busy_note.setVisible(view.busy_note is not None)
        self.folder_note.setText(view.folder_note or "")
        self.folder_note.setVisible(view.folder_note is not None)

        was_running = self.progress.isVisible()
        if view.progress is not None:
            self.progress.setVisible(True)
            self.progress.show_progress(view.progress)
            if not was_running and had_focus and view.progress.can_stop:
                self.progress.stop_button.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self.progress.setVisible(False)
            self.progress.reset()

        if view.report is not None:
            self.report.setVisible(True)
            if self.report.show_report(view.report) and had_focus:
                self.report.setFocus()  # only when the user is working in here
        else:
            self.report.setVisible(False)
            self.report.clear()
