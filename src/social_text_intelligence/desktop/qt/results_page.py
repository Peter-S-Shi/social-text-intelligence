"""The Results page: aggregates, a filterable table of every row, and the export."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..results import ResultsController, ResultsState
from ..results_view import (
    ResultsView,
    TableRowView,
    build_results_view,
    filters_from,
)
from . import style
from .components import (
    BarGrid,
    Card,
    Combo,
    DataTable,
    EmptyState,
    Figure,
    FlowRow,
    Page,
    PageHeader,
    ReflowRow,
    SegmentedFilter,
    StackedBar,
    relax_width,
)
from .platform import DesktopPlatform
from .widgets import LanguageBox, NoticeBox, add_all, label

EXPORT_FILE_NAME = "normalized-results.csv"
SENTIMENT_COLUMN = 4
COLUMNS = (
    ("Row", 44),
    ("Record ID", 88),
    ("Status", 116),
    ("Text", 232),
    ("Sentiment", 80),
    ("Dominant emotion", 120),
    ("Secondary emotions / reason", 150),
    ("Language check", 120),
)


def _combo(name: str, accessible: str) -> Combo:
    combo = Combo()
    combo.setObjectName(name)
    combo.setAccessibleName(accessible)
    return combo


def _fill(combo: Combo, choices: tuple[tuple[str, str], ...], value: str) -> None:
    combo.blockSignals(True)
    current = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    if current != list(choices):
        combo.clear()
        for text, data in choices:
            combo.addItem(text, data)
    combo.setCurrentIndex(max(combo.findData(value), 0))
    combo.blockSignals(False)


class ResultsPage(Page):
    review_requested = Signal(int)  # a row number to open in Review
    import_requested = Signal()

    def __init__(
        self,
        controller: ResultsController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._platform = platform
        self._rows: tuple[TableRowView, ...] = ()
        self._shown_project_id: str | None = None
        self._syncing = False

        self.header = PageHeader("Results")
        self.header.title.setObjectName("results-title")
        self.header.subtitle.setObjectName("results-subtitle")
        self.export_button = QPushButton("Export normalized CSV…")
        self.export_button.setObjectName("results-export")
        self.export_button.setAccessibleName("Export normalized CSV")
        self.export_button.clicked.connect(self._export)
        self.header.add_action(self.export_button)
        self.native_box = QCheckBox("Include model-native emotion scores in the export")
        self.native_box.setObjectName("export-native")
        relax_width(self.native_box)
        self.notice = NoticeBox()
        self.notice.setVisible(False)
        self.language_box = LanguageBox("results-language")

        self.empty = EmptyState()
        self.empty.setObjectName("results-empty")
        self.import_button = QPushButton("Go to Import & validation")
        self.import_button.setObjectName("results-go-import")
        self.import_button.clicked.connect(self.import_requested.emit)
        self.empty.layout_.addWidget(self.import_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.sentiment_figures: dict[str, Figure] = {}
        figures = QHBoxLayout()
        figures.setSpacing(14)
        for tone in ("negative", "neutral", "positive"):
            figure = Figure(tone, tone)
            figure.setObjectName(f"sentiment-{tone}")
            self.sentiment_figures[tone] = figure
            figures.addWidget(figure, 1)
        self.sentiment_stack = StackedBar()
        self.sentiment_stack.setObjectName("sentiment-stack")
        self.sentiment_card = Card()
        self.sentiment_card.layout_.addLayout(figures)
        self.sentiment_card.add(self.sentiment_stack)
        self.sentiment_caption = label(role="muted")
        self.sentiment_card.add(self.sentiment_caption)
        self.dominant_bars = BarGrid("ai")
        self.dominant_bars.setObjectName("dominant-bars")
        self.dominant_card = Card()
        self.dominant_card.add(self.dominant_bars)
        self.dominant_caption = label(role="muted")
        self.dominant_card.add(self.dominant_caption)
        self.activation_bars = BarGrid("ai")
        self.activation_bars.setObjectName("activation-bars")
        self.activation_card = Card()
        self.activation_card.add(self.activation_bars)
        self.activation_caption = label(role="muted")
        self.activation_card.add(self.activation_caption)
        self.failed_card = Card("NOT ANALYSED")
        self.failed_figure = label(role="figure", wrap=False)
        self.failed_figure.setProperty("polarity", "negative")
        self.failed_figure.setObjectName("failed-figure")
        self.failed_caption = label(
            "Rows that were rejected at import or failed in analysis are kept with "
            "their reason, never dropped.",
            role="muted",
        )
        add_all(self.failed_card.layout_, self.failed_figure, self.failed_caption)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        add_all(left_layout, self.sentiment_card, self.failed_card)
        left_layout.addStretch(1)
        self.cards = ReflowRow(min_width=270)
        for item in (left, self.dominant_card, self.activation_card):
            self.cards.add(item)

        self.status_filter = SegmentedFilter()
        self.status_filter.setObjectName("results-status")
        self.status_filter.selected.connect(self._filters_changed)
        self.sentiment_filter = _combo("filter-sentiment", "AI sentiment filter")
        self.emotion_filter = _combo("filter-emotion", "AI dominant emotion filter")
        self.sentiment_filter.activated.connect(self._filters_changed)
        self.emotion_filter.activated.connect(self._filters_changed)
        self.clear_button = QPushButton("Clear filters")
        self.clear_button.setObjectName("results-clear")
        self.clear_button.clicked.connect(self._clear_filters)
        self.shown_line = label(role="mono")
        self.shown_line.setObjectName("results-shown")
        filters = FlowRow()
        for control in (
            self.status_filter,
            self.sentiment_filter,
            self.emotion_filter,
            self.clear_button,
        ):
            filters.add(control)

        self.table = DataTable()
        self.table.setObjectName("results-table")
        self.table.setAccessibleName("Results, one row per record")
        self.table.set_columns([name for name, _ in COLUMNS], [w for _, w in COLUMNS])
        self.table.setMinimumHeight(430)
        self.table.row_activated.connect(self._activated)
        self.table.itemSelectionChanged.connect(self._sync_buttons)
        self.table_empty = label(role="muted")
        self.table_empty.setObjectName("results-no-match")
        self.review_button = QPushButton("Review this row")
        self.review_button.setObjectName("results-review-row")
        self.review_button.setAccessibleName("Open the selected row in Review")
        self.review_button.clicked.connect(self._review_selected)
        self.review_hint = label(
            "Select an analysed row to open it in Review. Rows without a result "
            "show their reason instead.",
            role="muted",
        )
        footer = QHBoxLayout()
        footer.addWidget(self.shown_line)
        footer.addWidget(self.review_hint, 1)
        footer.addWidget(self.review_button)

        add_all(self.body, self.header, self.notice, self.empty)
        add_all(self.body, self.language_box, self.cards)
        self.body.addWidget(filters)
        add_all(self.body, self.table_empty)
        self.body.addWidget(self.table, 1)
        self.body.addLayout(footer)
        self.body.addWidget(self.native_box)

        controller.subscribe(self.show_state)
        self.show_state(controller.state)

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: ResultsState) -> None:
        had_focus = self._has_focus()
        is_new = self.notice.show_notice(state.notice)
        view = build_results_view(state)
        analysed = view is not None
        for widget in (
            self.cards,
            self.status_filter,
            self.sentiment_filter,
            self.emotion_filter,
            self.clear_button,
            self.shown_line,
            self.table,
            self.review_button,
            self.review_hint,
            self.native_box,
            self.export_button,
        ):
            widget.setVisible(analysed)
        self.empty.setVisible(not analysed)
        if view is None:
            self.table.selectionModel().clear()
            self._rows = ()
            self._shown_project_id = state.project_id
            self._sync_buttons()
            self._show_empty(state)
            return
        self._syncing = True
        try:
            self._show_results(view)
        finally:
            self._syncing = False
        if is_new and had_focus:
            self.notice.setFocus()

    def _show_empty(self, state: ResultsState) -> None:
        self.header.set_subtitle("")
        self.language_box.setVisible(False)
        self.table_empty.setVisible(False)
        if state.busy and not state.loaded:
            self.empty.show_text("Loading results…", "")
            self.import_button.setVisible(False)
        else:
            self.empty.show_text(
                "No results yet",
                "This project has not been analysed. Analyse it from Import & "
                "validation, and its results appear here.",
            )
            self.import_button.setVisible(state.active)

    def _show_results(self, view: ResultsView) -> None:
        self.header.set_subtitle(view.subtitle)
        self.language_box.show_language(
            view.language_headline or None, view.language_detail, view.language_warns
        )
        self.sentiment_card.eyebrow.setText(view.sentiment.title.upper())
        self.sentiment_card.eyebrow.setVisible(True)
        self.dominant_card.eyebrow.setText(view.dominant.title.upper())
        self.dominant_card.eyebrow.setVisible(True)
        self.activation_card.eyebrow.setText(view.activation.title.upper())
        self.activation_card.eyebrow.setVisible(True)
        self.sentiment_caption.setText(view.sentiment.caption)
        for grid, caption, dist in (
            (self.dominant_bars, self.dominant_caption, view.dominant),
            (self.activation_bars, self.activation_caption, view.activation),
        ):
            grid.set_rows([(b.label, b.fraction, b.text, "") for b in dist.bars])
            caption.setText(dist.caption)
            grid.setAccessibleName(dist.title)
        self._show_sentiment_figures(view)
        self.failed_figure.setText(str(view.failed_count))
        self.failed_card.setAccessibleName(
            f"{view.failed_count} rows not analysed, kept with their reason"
        )
        self.status_filter.set_options(view.status_tabs, view.selected[0])
        _fill(self.sentiment_filter, view.sentiment_choices, view.selected[1])
        _fill(self.emotion_filter, view.emotion_choices, view.selected[2])
        self.clear_button.setEnabled(view.filters_active)
        self.shown_line.setText(view.shown_line)
        self.table_empty.setText(view.empty_line)
        self.table_empty.setVisible(bool(view.empty_line))
        selected = self.table.selectionModel().selectedRows()
        selected_record_row = None
        if self._shown_project_id == self._controller.state.project_id and selected:
            index = selected[0].row()
            if 0 <= index < len(self._rows):
                selected_record_row = self._rows[index].row
        self._rows = view.rows
        self._shown_project_id = self._controller.state.project_id
        self.table.set_rows(
            [
                (
                    str(row.row),
                    row.record_id,
                    row.status_word,
                    row.text,
                    row.sentiment,
                    row.dominant,
                    row.detail,
                    row.language,
                )
                for row in view.rows
            ],
            failed=[not row.can_review for row in view.rows],
        )
        self._tone_cells()
        self.table.selectionModel().clear()
        for index, row in enumerate(self._rows):
            if row.row == selected_record_row:
                self.table.selectRow(index)
                break
        self.export_button.setEnabled(view.export_enabled)
        self.native_box.setEnabled(view.export_enabled)
        self.native_box.setText(view.native_label)
        controls = self._controller.state.busy
        for widget in (self.sentiment_filter, self.emotion_filter):
            widget.setEnabled(not controls)
        self._sync_buttons()

    def _show_sentiment_figures(self, view: ResultsView) -> None:
        """Big counts and a proportional bar over the exact rows and percentages."""

        segments: list[tuple[float, str]] = []
        for tone, figure in self.sentiment_figures.items():
            bar = next(
                (b for b in view.sentiment.bars if b.label.lower() == tone), None
            )
            figure.setVisible(bar is not None)
            if bar is not None:
                figure.set_value(str(bar.value))
                percent = bar.text.split("·")[-1].strip()
                figure.caption.setText(f"{tone}\n{percent}")
                figure.setAccessibleName(f"{bar.value} {tone} rows, {percent}")
                segments.append((float(bar.value), tone))
        self.sentiment_stack.set_segments(segments)
        self.sentiment_stack.setAccessibleName(view.sentiment.title)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _tone_cells(self) -> None:
        """Colour the label words (the word is always written too)."""

        tones = {
            "positive": style.POSITIVE,
            "negative": style.VERMILION,
            "neutral": style.NEUTRAL,
        }
        for row in range(self.table.rowCount()):
            item = self.table.item(row, SENTIMENT_COLUMN)
            if item is not None and item.text().lower() in tones:
                item.setForeground(QColor(tones[item.text().lower()]))

    def _sync_buttons(self) -> None:
        row = self.table.currentRow()
        selectable = 0 <= row < len(self._rows) and self._rows[row].can_review
        self.review_button.setEnabled(selectable and not self._controller.state.busy)

    # -- actions ------------------------------------------------------------

    def _filters_changed(self, *_: object) -> None:
        if self._syncing:
            return
        status = next(
            (v for v, b in self.status_filter.buttons.items() if b.isChecked()), "all"
        )
        self._controller.set_filters(
            filters_from(
                status,
                str(self.sentiment_filter.currentData()),
                str(self.emotion_filter.currentData()),
            )
        )

    def _clear_filters(self) -> None:
        self._controller.set_filters(filters_from("all", "all", "all"))

    def _activated(self, index: int) -> None:
        if 0 <= index < len(self._rows) and self._rows[index].can_review:
            self.review_requested.emit(self._rows[index].row)

    def _review_selected(self) -> None:
        self._activated(self.table.currentRow())

    def _export(self) -> None:
        path = self._platform.pick_save_csv(self, EXPORT_FILE_NAME)
        if path is not None:  # cancelling the dialog writes nothing
            self._controller.export(path, include_native=self.native_box.isChecked())
