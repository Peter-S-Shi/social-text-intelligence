"""Shared page scaffolding and display widgets for the native pages.

These render the pure view models and hold no rules of their own. Every figure is also
written as text next to its picture, and no state is carried by colour alone.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..agreement_view import ConfusionView
from ..scores import ScoreRow, ScoreSetView
from . import style
from .widgets import FlowLayout, add_all, frame, label

MAX_CONTENT_WIDTH = 1180
TONES = {
    "ai": style.GRAPHITE,
    "human": style.ULTRAMARINE,
    "failure": style.VERMILION,
    "quiet": style.LINE_STRONG,
}


def rule() -> QFrame:
    line = QFrame()
    line.setProperty("role", "rule")
    line.setFixedHeight(1)
    return line


def chip(text: str, tone: str = "ok") -> QLabel:
    """A status chip: always a word (and an icon where the caller put one)."""

    widget = QLabel(text)
    widget.setProperty("chip", True)
    widget.setProperty("tone", tone)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class Page(QWidget):
    """A scrolling page with a centred content column that grows to a sensible width."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroller = QScrollArea()
        self.scroller.setWidgetResizable(True)
        self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.setObjectName("page-scroll")
        outer.addWidget(self.scroller)
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        content.setMaximumWidth(MAX_CONTENT_WIDTH)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(
            style.PAGE_MARGIN_X,
            style.PAGE_MARGIN_TOP,
            style.PAGE_MARGIN_X,
            style.PAGE_MARGIN_X,
        )
        self.body.setSpacing(style.SPACE_L)
        shell_layout.addStretch(1)
        shell_layout.addWidget(content, 100)
        shell_layout.addStretch(1)
        self.scroller.setWidget(shell)


class PageHeader(QWidget):
    """The page title, a one-line mono subtitle, and actions aligned to the right."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = label(title, role="headline")
        self.title.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.subtitle = label(role="subtitle")
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(style.SPACE_S)
        layout.addLayout(text, 1)
        layout.addLayout(self.action_row)

    def set_subtitle(self, text: str) -> None:
        self.subtitle.setText(text)
        self.subtitle.setVisible(bool(text))

    def add_action(self, widget: QWidget) -> None:
        self.action_row.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)


class Card(QFrame):
    """A raised card with a small eyebrow title and a body layout."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            style.SPACE_L, style.SPACE_M, style.SPACE_L, style.SPACE_L
        )
        outer.setSpacing(style.SPACE_S)
        self.eyebrow = label(title, role="eyebrow")
        self.eyebrow.setVisible(bool(title))
        outer.addWidget(self.eyebrow)
        # content goes in the nested layout; the stretch below keeps it at the top
        self.layout_ = QVBoxLayout()
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(style.SPACE_S)
        outer.addLayout(self.layout_)
        outer.addStretch(1)

    def add(self, widget: QWidget) -> None:
        self.layout_.addWidget(widget)


class EmptyState(QFrame):
    """What a page shows instead of data: a title and what to do next."""

    def __init__(
        self, title: str = "", body: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "empty")
        self.layout_ = QVBoxLayout(self)
        pad = style.SPACE_XL
        self.layout_.setContentsMargins(pad, pad, pad, pad)
        self.title = label(title, role="title")
        self.body = label(body, role="muted")
        add_all(self.layout_, self.title, self.body)

    def show_text(self, title: str, body: str) -> None:
        self.title.setText(title)
        self.body.setText(body)
        self.setAccessibleName(f"{title}. {body}")


class FlowRow(QWidget):
    """Wrap controls onto more lines instead of forcing the page wider."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.flow = FlowLayout(self, spacing=style.SPACE_S)
        self.flow.setContentsMargins(0, 0, 0, 0)

    def add(self, widget: QWidget) -> None:
        self.flow.addWidget(widget)


class LabeledControl(QWidget):
    """A caption beside its control, kept together when a row wraps."""

    def __init__(self, caption: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(style.SPACE_S)
        layout.addWidget(label(caption, role="muted", wrap=False))
        layout.addWidget(control)


class ReflowRow(QWidget):
    """Equal-width children in as many columns as fit; cards wrap when narrow."""

    def __init__(
        self,
        min_width: int = 300,
        spacing: int = style.SPACE_L,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min_width = min_width
        self._spacing = spacing
        self._items: list[QWidget] = []
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(spacing)

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def items(self) -> tuple[QWidget, ...]:
        return tuple(self._items)

    def clear(self) -> None:
        for widget in self._items:
            self._grid.removeWidget(widget)
            widget.hide()  # a deleted widget is still painted until the loop runs
            widget.setParent(None)
            widget.deleteLater()
        self._items = []
        self._arrange(force=True)

    def add(self, widget: QWidget) -> None:
        self._items.append(widget)
        self._arrange(force=True)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._arrange()

    def _wanted(self) -> int:
        fit = (self.width() + self._spacing) // (self._min_width + self._spacing)
        return max(1, min(len(self._items), int(fit)))

    def _arrange(self, *, force: bool = False) -> None:
        columns = self._wanted() if self.width() > 1 else max(1, len(self._items))
        if columns == self._columns and not force:
            return
        self._columns = columns
        for widget in self._items:
            self._grid.removeWidget(widget)
        for index, widget in enumerate(self._items):
            self._grid.addWidget(widget, index // columns, index % columns)
        for column in range(len(self._items)):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
        self.updateGeometry()


POLARITY_COLOURS = {
    "negative": style.VERMILION,
    "neutral": style.NEUTRAL,
    "positive": style.POSITIVE,
}


class StackedBar(QWidget):
    """One thin bar split into proportional segments (a picture of written counts)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: tuple[tuple[float, str], ...] = ()
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @property
    def segments(self) -> tuple[tuple[float, str], ...]:
        return self._segments

    def set_segments(self, segments: Sequence[tuple[float, str]]) -> None:
        """Each segment: its weight and a tone name (negative, neutral, positive)."""

        self._segments = tuple(segments)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        total = sum(weight for weight, _ in self._segments)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(style.PAPER_SUNK))
        track = QRectF(0.0, 2.0, float(self.width()), 6.0)
        painter.drawRoundedRect(track, 3, 3)
        if total <= 0:
            return
        x = 0.0
        for weight, tone in self._segments:
            width = track.width() * weight / total
            if width <= 0:
                continue
            painter.setBrush(QColor(POLARITY_COLOURS.get(tone, style.GRAPHITE)))
            painter.drawRect(
                QRectF(x, track.y(), max(width - 1.0, 1.0), track.height())
            )
            x += width


class Figure(QWidget):
    """A large serif number over a small caption, in a tone (never colour alone: the
    caption always says what the number counts)."""

    def __init__(
        self,
        caption: str,
        tone: str | None = None,
        parent: QWidget | None = None,
        *,
        size: str = "figure",
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "plain")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.value = label(role=size, wrap=False)
        if tone:
            self.value.setProperty("polarity", tone)
        self.caption = label(caption, role="muted")
        layout.addWidget(self.value)
        layout.addWidget(self.caption)

    def set_value(self, text: str) -> None:
        self.value.setText(text)
        self.setAccessibleName(f"{text} {self.caption.text()}")


class Combo(QComboBox):
    """A combo box that draws its own chevron, so it looks the same everywhere."""

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colour = QColor(style.INK if self.isEnabled() else "#7A7366")
        painter.setPen(QPen(colour, 1.6))
        cx, cy = self.width() - 15.0, self.height() / 2.0
        painter.drawPolyline(
            [QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2), QPointF(cx + 4, cy - 2)]
        )


class SplitRow(QWidget):
    """A fixed-width side panel beside a flexible main area; stacked when narrow."""

    def __init__(
        self,
        side: QWidget,
        main: QWidget,
        *,
        side_width: int = 340,
        stack_below: int = 780,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._side, self._main = side, main
        self._side_width = side_width
        self._stack_below = stack_below
        self._wide: bool | None = None
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(style.SPACE_L)
        self._arrange(force=True)

    @property
    def wide(self) -> bool:
        return bool(self._wide)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._arrange()

    def _arrange(self, *, force: bool = False) -> None:
        wide = self.width() <= 1 or self.width() >= self._stack_below
        if wide == self._wide and not force:
            return
        self._wide = wide
        for widget in (self._side, self._main):
            self._grid.removeWidget(widget)
        if wide:
            self._side.setFixedWidth(self._side_width)
            self._grid.addWidget(self._side, 0, 0, Qt.AlignmentFlag.AlignTop)
            self._grid.addWidget(self._main, 0, 1)
            self._grid.setColumnStretch(0, 0)
            self._grid.setColumnStretch(1, 1)
        else:
            self._side.setMinimumWidth(0)
            self._side.setMaximumWidth(16_777_215)
            self._grid.addWidget(self._side, 0, 0)
            self._grid.addWidget(self._main, 1, 0)
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 0)
        self.updateGeometry()


class BarMeter(QWidget):
    """A thin horizontal bar: only a picture of a number written beside it."""

    def __init__(
        self, fraction: float = 0.0, tone: str = "ai", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._fraction = max(0.0, min(1.0, fraction))
        self._tone = tone
        self.setMinimumHeight(14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("")

    @property
    def fraction(self) -> float:
        return self._fraction

    def set_value(self, fraction: float, tone: str | None = None) -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        if tone is not None:
            self._tone = tone
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(120, 14)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = 8.0
        top = (self.height() - height) / 2
        track = QRectF(0.5, top, self.width() - 1.0, height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(style.PAPER_SUNK))
        painter.drawRoundedRect(track, 4, 4)
        if self._fraction > 0:
            fill = QRectF(
                track.x(), top, max(6.0, track.width() * self._fraction), height
            )
            painter.setBrush(QColor(TONES.get(self._tone, style.GRAPHITE)))
            painter.drawRoundedRect(fill, 4, 4)


class BarGrid(QWidget):
    """Rows of ``label | bar | text | note``; the text carries every value."""

    def __init__(self, tone: str = "ai", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tone = tone
        self._signature: object = None
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(style.SPACE_M)
        self._grid.setVerticalSpacing(6)
        self._grid.setColumnStretch(1, 1)
        self.meters: list[BarMeter] = []

    def set_rows(self, rows: Sequence[tuple[str, float, str, str]]) -> None:
        """Each row: label, bar fraction, written value, optional word."""

        signature = tuple(rows)
        if signature == self._signature:
            return
        self._signature = signature
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.meters = []
        for index, (name, fraction, text, note) in enumerate(rows):
            meter = BarMeter(fraction, self._tone)
            spoken = f"{name}: {text}" + (f", {note}" if note else "")
            meter.setAccessibleName(spoken)
            self.meters.append(meter)
            written = f"{text}  {note}" if note else text
            value = label(written, role="mono", wrap=False)
            value.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._grid.addWidget(label(name, wrap=False), index, 0)
            self._grid.addWidget(meter, index, 1)
            self._grid.addWidget(value, index, 2)
            for column in range(3):
                item = self._grid.itemAtPosition(index, column)
                shown = item.widget() if item is not None else None
                if shown is not None:
                    shown.show()


def score_rows(rows: Sequence[ScoreRow]) -> list[tuple[str, float, str, str]]:
    return [(row.label, row.fraction, row.text, row.note) for row in rows]


class ScorePanel(QWidget):
    """The score breakdown of one model result: sentiment, compact emotions, native.

    The bars are only a picture of the written scores. The 28 model-native emotion
    scores are one deliberate click away, as in V1, so they never crowd the page.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(style.SPACE_S)
        self.sentiment_heading = label("Sentiment scores", role="eyebrow")
        self.sentiment = BarGrid("ai")
        self.sentiment.setObjectName("sentiment-scores")
        self.emotion_heading = label("Compact emotion scores", role="eyebrow")
        self.emotion = BarGrid("ai")
        self.emotion.setObjectName("emotion-scores")
        self.rule = label(role="muted")
        self.rule.setObjectName("emotion-rule")
        # the threshold rule; a caution box when the fallback chose Neutral
        self.rule_box = frame("quiet")
        self.rule_box.setObjectName("emotion-rule-box")
        rule_layout = QVBoxLayout(self.rule_box)
        rule_layout.setContentsMargins(0, 0, 0, 0)
        rule_layout.addWidget(self.rule)
        self.native_toggle = QToolButton()
        self.native_toggle.setText("Show model-native emotion scores")
        self.native_toggle.setCheckable(True)
        self.native_toggle.setObjectName("native-toggle")
        # a long caption must never widen a narrow card: it may clip instead
        self.native_toggle.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.native = BarGrid("quiet")
        self.native.setObjectName("native-scores")
        self.native.setVisible(False)
        self.native_toggle.toggled.connect(self.native.setVisible)
        add_all(layout, self.sentiment_heading, self.sentiment)
        add_all(layout, self.emotion_heading, self.emotion, self.rule_box)
        layout.addWidget(self.native_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.native)

    def show_scores(self, scores: ScoreSetView) -> None:
        self.sentiment.set_rows(score_rows(scores.sentiment))
        self.emotion.set_rows(score_rows(scores.emotion))
        self.rule.setText(scores.emotion_rule)
        self.rule_box.setProperty("role", "caution" if scores.fallback else "quiet")
        margin = 12 if scores.fallback else 0
        self.rule_box.layout().setContentsMargins(margin, 8, margin, 8)  # type: ignore[union-attr]
        self.rule_box.style().unpolish(self.rule_box)
        self.rule_box.style().polish(self.rule_box)
        self.native.set_rows(score_rows(scores.native))
        self.native_toggle.setText(
            f"Show {len(scores.native)} model-native emotion scores"
        )
        self.native_toggle.setAccessibleName(
            f"Show all {len(scores.native)} model-native emotion scores"
        )
        self.sentiment.setAccessibleName("Sentiment scores")
        self.emotion.setAccessibleName("Compact emotion scores")
        self.native.setAccessibleName("Model-native emotion scores")


class SegmentedFilter(QWidget):
    """A row of exclusive buttons (label and count); the selected one is also bold."""

    selected = Signal(str)

    def __init__(self, parent: QWidget | None = None, *, noun: str = "rows") -> None:
        super().__init__(parent)
        self._noun = noun
        self.setProperty("role", "segtrack")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # wraps onto a second line when the page is narrow, instead of widening it
        self._layout = FlowLayout(self, spacing=2, one_line_hint=True)
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._signature: object = None
        self._syncing = False

    @property
    def buttons(self) -> dict[str, QPushButton]:
        return self._buttons

    def preferred_width(self) -> int:
        """The width of all the buttons on one line (what it takes not to wrap)."""

        widths = [button.sizeHint().width() for button in self._buttons.values()]
        return sum(widths) + 2 * max(len(widths) - 1, 0) + 6

    def set_options(
        self, options: Sequence[tuple[str, str, int]], selected: str
    ) -> None:
        signature = tuple(options)
        if signature != self._signature:
            self._signature = signature
            for button in self._buttons.values():
                self._group.removeButton(button)
                self._layout.removeWidget(button)
                button.hide()
                button.setParent(None)
                button.deleteLater()
            self._buttons = {}
            for index, (text, value, count) in enumerate(options):
                button = QPushButton(f"{text}  {count}")
                button.setCheckable(True)
                button.setProperty("seg", True)
                button.setProperty(
                    "pos",
                    "first"
                    if index == 0
                    else "last"
                    if index == len(options) - 1
                    else "mid",
                )
                button.setAccessibleName(f"{text}, {count} {self._noun}")
                button.setObjectName(f"seg-{value}")
                button.clicked.connect(lambda _=False, v=value: self._chosen(v))
                self._group.addButton(button)
                self._layout.addWidget(button)
                button.show()
                self._buttons[value] = button
        self._syncing = True
        try:
            for value, button in self._buttons.items():
                button.setChecked(value == selected)
        finally:
            self._syncing = False

    def _chosen(self, value: str) -> None:
        if not self._syncing:
            self.selected.emit(value)


class DataTable(QTableWidget):
    """A read-only, keyboard-navigable table; Enter or double click activates."""

    row_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        vertical = self.verticalHeader()
        vertical.setVisible(False)
        vertical.setDefaultSectionSize(30)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.itemDoubleClicked.connect(lambda item: self.row_activated.emit(item.row()))

    def fit_rows(self, count: int, *, cap: int = 12) -> None:
        """Be tall enough for ``count`` rows (at most ``cap`` before scrolling)."""

        shown = max(1, min(count, cap))
        height = (
            (self.horizontalHeader().height() or 30)
            + shown * self.verticalHeader().defaultSectionSize()
            + 6
        )
        self.setMinimumHeight(height)
        self.setMaximumHeight(height if count <= cap else height + 4)

    def set_columns(self, headers: Sequence[str], widths: Sequence[int]) -> None:
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(list(headers))
        for column, width in enumerate(widths):
            self.setColumnWidth(column, width)

    def set_rows(
        self,
        rows: Sequence[Sequence[str]],
        *,
        failed: Sequence[bool] = (),
        names: Sequence[str] = (),
    ) -> None:
        self.setUpdatesEnabled(False)
        try:
            self.clearContents()
            self.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    item = QTableWidgetItem(text)
                    item.setToolTip(text)
                    if failed and failed[r] and c == 2:
                        item.setForeground(QColor(style.VERMILION))
                    if c == 0 and names:
                        item.setData(Qt.ItemDataRole.AccessibleTextRole, names[r])
                    self.setItem(r, c, item)
        finally:
            self.setUpdatesEnabled(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt override)
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and self.currentRow() >= 0
        ):
            self.row_activated.emit(self.currentRow())
            return
        super().keyPressEvent(event)


class ConfusionGrid(QWidget):
    """AI labels down, human labels across; each count is written in its cell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(4)
        self._grid.setVerticalSpacing(4)
        self._signature: object = None

    def set_view(self, view: ConfusionView) -> None:
        if view == self._signature:
            return
        self._signature = view
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        for column, name in enumerate(view.columns, start=1):
            header = label(f"you · {name}", role="eyebrow", wrap=False)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(header, 0, column)
        peak = max((cell.count for row in view.rows for cell in row.cells), default=0)
        for r, row in enumerate(view.rows, start=1):
            self._grid.addWidget(label(f"AI · {row.ai_label}", wrap=False), r, 0)
            for c, cell in enumerate(row.cells, start=1):
                widget = QLabel(str(cell.count))
                widget.setProperty("cell", True)
                widget.setProperty("match", cell.match)
                widget.setProperty("level", _level(cell.count, peak))
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                widget.setAccessibleName(cell.accessible_name)
                self._grid.addWidget(widget, r, c)
        for column in range(1, len(view.columns) + 1):
            self._grid.setColumnStretch(column, 1)


def _level(count: int, peak: int) -> int:
    if count <= 0 or peak <= 0:
        return 0
    return min(4, 1 + int(3 * count / peak))


class NavButton(QPushButton):
    """A sidebar entry with an optional count at the right edge."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text.replace("&", "&&"), parent)  # no accidental mnemonic
        self._badge = ""
        self.setCheckable(True)
        self.setProperty("nav", True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_badge(self, badge: str) -> None:
        self._badge = badge
        self.update()

    @property
    def badge(self) -> str:
        return self._badge

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        super().paintEvent(event)
        if not self._badge:
            return
        painter = QPainter(self)
        colour = QColor(style.MUTED if self.isEnabled() else "#7A7E85")
        painter.setPen(colour)
        painter.setFont(self.font())
        painter.drawText(
            self.rect().adjusted(0, 0, -24, 0),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            self._badge,
        )


def section_title(text: str) -> QLabel:
    title = label(text, role="title")
    title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return title


def inline_note(text: str = "", role: str = "muted") -> QLabel:
    widget = label(text, role=role)
    widget.setVisible(bool(text))
    return widget


__all__ = [
    "BarGrid",
    "BarMeter",
    "Card",
    "Combo",
    "ConfusionGrid",
    "DataTable",
    "EmptyState",
    "Figure",
    "FlowRow",
    "LabeledControl",
    "NavButton",
    "Page",
    "PageHeader",
    "ReflowRow",
    "ScorePanel",
    "SegmentedFilter",
    "SplitRow",
    "StackedBar",
    "chip",
    "frame",
    "inline_note",
    "rule",
    "score_rows",
    "section_title",
]
