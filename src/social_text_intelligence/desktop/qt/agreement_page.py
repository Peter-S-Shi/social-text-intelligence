"""The Agreement page: how often the person's judgment matched the AI's label.

Agreement, not accuracy. Every figure is written with its denominator, the confusion
table and label comparison are the review service's own counts, and confidence bands
appear only when the service says there are enough definitive reviews.
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QPushButton, QWidget

from ..agreement import AgreementController, AgreementState
from ..agreement_view import (
    AgreementView,
    ConfidencePanelView,
    FigureView,
    build_agreement_view,
)
from ..review_view import NATIVE_LABEL
from .components import (
    BarGrid,
    Card,
    ConfusionGrid,
    DataTable,
    EmptyState,
    Page,
    PageHeader,
    ReflowRow,
    relax_width,
)
from .platform import DesktopPlatform
from .widgets import NoticeBox, add_all, label

EXPORT_FILE_NAME = "reviewed-results.csv"
LEGEND = (
    "Dark cells: you and the AI chose the same label. Tinted cells: you chose "
    "a different one. Each cell shows its count."
)


class FigureCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.value = label(role="display", wrap=False)
        self.caption = label(role="muted")
        add_all(self.layout_, self.value, self.caption)

    def show_figure(self, figure: FigureView) -> None:
        self.eyebrow.setText(figure.label.upper())
        self.eyebrow.setVisible(True)
        self.value.setText(figure.value)
        self.caption.setText(figure.caption)
        self.setAccessibleName(f"{figure.label}: {figure.value}, {figure.caption}")


class ConfidenceCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.bars = BarGrid("failure")
        self.unavailable = label(role="muted")
        add_all(self.layout_, self.bars, self.unavailable)

    def show_panel(self, panel: ConfidencePanelView) -> None:
        self.eyebrow.setText(f"DISAGREEMENT BY CONFIDENCE · {panel.title.upper()}")
        self.eyebrow.setVisible(True)
        self.bars.setVisible(panel.available)
        self.bars.set_rows([(b.label, b.fraction, b.text, "") for b in panel.bands])
        self.unavailable.setText(panel.unavailable_line)
        self.unavailable.setVisible(not panel.available)
        self.setAccessibleName(
            f"{panel.title} confidence bands. "
            + (
                "; ".join(f"{b.label}: {b.text}" for b in panel.bands)
                if panel.available
                else panel.unavailable_line
            )
        )


class AgreementPage(Page):
    def __init__(
        self,
        controller: AgreementController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._platform = platform

        self.header = PageHeader("Agreement, not accuracy")
        self.header.title.setObjectName("agreement-title")
        self.header.subtitle.setObjectName("agreement-subtitle")
        self.export_button = QPushButton("Export reviewed CSV…")
        self.export_button.setObjectName("agreement-export")
        self.export_button.setAccessibleName("Export reviewed CSV")
        self.export_button.setProperty("primary", True)
        self.export_button.clicked.connect(self._export)
        self.header.add_action(self.export_button)
        self.native_box = QCheckBox(NATIVE_LABEL)
        self.native_box.setObjectName("export-native")
        relax_width(self.native_box)
        self.notice = NoticeBox()
        self.notice.setVisible(False)
        self.empty = EmptyState()
        self.empty.setObjectName("agreement-empty")
        self.waiting = label(role="muted")
        self.waiting.setObjectName("agreement-waiting")

        self.figure_cards = tuple(FigureCard() for _ in range(3))
        self.figures = ReflowRow(min_width=310)
        for card in self.figure_cards:
            self.figures.add(card)

        self.confusion = ConfusionGrid()
        self.confusion.setObjectName("confusion")
        self.legend = label(LEGEND, role="muted")
        self.corrections = label()
        self.corrections.setObjectName("corrections")
        self.confusion_card = Card("SENTIMENT CONFUSION · AI ROWS × YOUR COLUMNS")
        add_all(self.confusion_card.layout_, self.confusion, self.legend)
        add_all(self.confusion_card.layout_, label("Your corrections", role="title"))
        self.confusion_card.layout_.addWidget(self.corrections)

        self.comparison = DataTable()
        self.comparison.setObjectName("label-comparison")
        self.comparison.setAccessibleName("Emotion label comparison")
        self.comparison.set_columns(
            ["Label", "AI only", "You only", "Shared"], [140, 80, 80, 80]
        )
        self.comparison.fit_rows(9)
        self.added_removed = label(role="muted")
        self.added_removed.setObjectName("added-removed")
        self.comparison_card = Card("EMOTION LABEL COMPARISON")
        add_all(self.comparison_card.layout_, self.comparison, self.added_removed)
        self.matrix_row = ReflowRow(min_width=420)
        self.matrix_row.add(self.confusion_card)
        self.matrix_row.add(self.comparison_card)

        self.confidence_cards = (ConfidenceCard(), ConfidenceCard())
        self.confidence_row = ReflowRow(min_width=360)
        for panel_card in self.confidence_cards:
            self.confidence_row.add(panel_card)
        self.confidence_note = label(role="muted")
        self.note = label(role="muted")
        self.note.setObjectName("agreement-note")

        add_all(self.body, self.header, self.notice, self.empty, self.waiting)
        add_all(self.body, self.figures, self.matrix_row, self.confidence_row)
        add_all(self.body, self.confidence_note, self.note, self.native_box)

        controller.subscribe(self.show_state)
        self.show_state(controller.state)

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: AgreementState) -> None:
        had_focus = self._has_focus()
        is_new = self.notice.show_notice(state.notice)
        summary = state.summary
        shown = summary is not None
        for widget in (
            self.figures,
            self.matrix_row,
            self.confidence_row,
            self.confidence_note,
            self.note,
            self.native_box,
            self.export_button,
        ):
            widget.setVisible(shown)
        self.waiting.setVisible(False)
        if summary is None:
            self.header.set_subtitle("")
            loading = state.busy and state.active
            self.empty.setVisible(not loading)
            self.waiting.setVisible(loading)
            self.waiting.setText("Loading agreement…")
            self.empty.show_text(
                "Nothing to compare yet",
                "Agreement is computed from the records you review. Analyse the "
                "project, then review records to see it here.",
            )
            return
        self.empty.setVisible(False)
        self._show_view(build_agreement_view(summary), state)
        if is_new and had_focus:
            self.notice.setFocus()

    def _show_view(self, view: AgreementView, state: AgreementState) -> None:
        self.header.set_subtitle(view.subtitle)
        for card, figure in zip(self.figure_cards, view.figures, strict=True):
            card.show_figure(figure)
        self.confusion.set_view(view.confusion)
        self.corrections.setText(
            "  ·  ".join(view.corrections) or view.corrections_empty_line
        )
        self.comparison.set_rows(
            [
                (item.label, str(item.ai_only), str(item.human_only), str(item.shared))
                for item in view.label_comparison
            ]
        )
        self.added_removed.setText(view.added_removed_line)
        for panel_card, panel in zip(
            self.confidence_cards, view.confidence, strict=True
        ):
            panel_card.show_panel(panel)
        self.confidence_note.setText(view.confidence_note)
        self.note.setText(view.note)
        self.export_button.setText(view.export_label)
        self.export_button.setEnabled(view.export_enabled and not state.busy)
        self.native_box.setEnabled(not state.busy)
        self.native_box.setText(NATIVE_LABEL)
        self.empty.setVisible(bool(view.empty_line))
        if view.empty_line:
            self.empty.show_text("No definitive reviews yet", view.empty_line)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    # -- actions ------------------------------------------------------------

    def _export(self) -> None:
        path = self._platform.pick_save_csv(self, EXPORT_FILE_NAME)
        if path is not None:  # cancelling the dialog writes nothing
            self._controller.export(path, include_native=self.native_box.isChecked())
