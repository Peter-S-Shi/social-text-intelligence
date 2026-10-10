"""Small reusable widgets that render the pure view models."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..panel import (
    ActionId,
    ActionView,
    CardView,
    ProgressView,
    ReportKind,
    ReportView,
)
from ..projects import NoticeKind, ProjectsNotice

# a readiness chip's icon decides its tint (the word is always written beside it)
_CHIP_TONES = {"✓": "ok", "○": "neutral", "◆": "warn", "◇": "warn", "✕": "error"}

_REPORT_PREFIX = {
    ReportKind.SUCCESS: "✓",
    ReportKind.INFO: "ℹ",
    ReportKind.WARNING: "◆",
    ReportKind.ERROR: "✕",
}


def label(text: str = "", *, role: str | None = None, wrap: bool = True) -> QLabel:
    widget = QLabel(text)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if role:
        widget.setProperty("role", role)
    return widget


def add_all(layout: QBoxLayout, *widgets: QWidget) -> None:
    """Add several widgets to a box layout, in order."""

    for item in widgets:
        layout.addWidget(item)


def frame(role: str) -> QFrame:
    box = QFrame()
    box.setProperty("role", role)
    box.setFrameShape(QFrame.Shape.StyledPanel)
    return box


def announce(widget: QWidget, text: str, *, assertive: bool = False) -> None:
    """Expose ``text`` to assistive technology as a (live) name change or alert."""

    widget.setAccessibleName(text)
    event = QAccessibleEvent(
        widget,
        QAccessible.Event.Alert if assertive else QAccessible.Event.NameChanged,
    )
    QAccessible.updateAccessibility(event)


class ActionRow(QWidget):
    """A row of buttons for ``ActionView``s that keeps keyboard focus across updates."""

    triggered = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = FlowLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._identity: tuple[tuple[ActionId, str, tuple[str, ...] | None], ...] = ()
        self._buttons: list[tuple[ActionView, QPushButton]] = []

    @property
    def buttons(self) -> list[QPushButton]:
        return [button for _, button in self._buttons]

    def set_actions(self, actions: tuple[ActionView, ...]) -> None:
        identity = tuple((a.action, a.label, a.keys) for a in actions)
        if identity == self._identity:
            for (_, button), view in zip(self._buttons, actions, strict=True):
                button.setEnabled(view.enabled)
            self._buttons = [
                (view, button)
                for (_, button), view in zip(self._buttons, actions, strict=True)
            ]
            return
        focused = self.window().focusWidget()
        focus_identity = None
        for old, button in self._buttons:
            if button is focused:
                focus_identity = (old.action, old.keys)
        for _, button in self._buttons:
            self._layout.removeWidget(button)
            button.setParent(None)
            button.deleteLater()
        self._buttons = []
        for view in actions:
            button = QPushButton(view.label)
            button.setEnabled(view.enabled)
            button.setProperty("primary", view.primary)
            button.setAccessibleName(view.label)
            button.clicked.connect(lambda _=False, v=view: self.triggered.emit(v))
            self._layout.addWidget(button)
            button.show()  # widgets added to a shown parent stay hidden otherwise
            self._buttons.append((view, button))
            if focus_identity == (view.action, view.keys) and view.enabled:
                button.setFocus()
        self._identity = identity


class ProgressBlock(QFrame):
    """Progress at three levels with written values, Stop, and a polite live line."""

    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self.setObjectName("progress-block")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(6)
        self.title = label(role="title")
        self.title.setObjectName("progress-title")
        self.status_line = label()
        self.status_line.setObjectName("progress-status")
        self.file_label = label(role="mono")
        layout.addWidget(self.title)
        layout.addWidget(self.status_line)
        layout.addWidget(self.file_label)
        self._bars: list[tuple[QLabel, QProgressBar]] = []
        for _ in range(3):
            caption = label(role="muted")
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setTextVisible(True)
            layout.addWidget(caption)
            layout.addWidget(bar)
            self._bars.append((caption, bar))
        self.note = label(role="muted")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stop-button")
        self.stop_button.setAccessibleName("Stop")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        layout.addWidget(self.note)
        row = QHBoxLayout()
        row.addWidget(self.stop_button)
        row.addStretch(1)
        layout.addLayout(row)
        self._last_step: tuple[str, int] | None = None

    def show_progress(self, view: ProgressView) -> None:
        self.title.setText(view.title)
        self.file_label.setText(view.file_name)
        self.file_label.setVisible(bool(view.file_name))
        for (caption, bar), data in zip(self._bars, view.bars, strict=True):
            caption.setText(data.label)
            bar.setValue(int(data.fraction * 1000))
            bar.setFormat(data.text)
            bar.setAccessibleName(f"{data.label}: {data.text}")
        self.note.setText(view.note)
        self.stop_button.setVisible(view.can_stop or view.stopping)
        self.stop_button.setEnabled(view.can_stop)
        overall = view.bars[-1]
        percent = int(overall.fraction * 100)
        step = (view.title, percent // 10)
        if step != self._last_step:
            self._last_step = step
            text = f"{view.title}, {percent} percent. {overall.text}."
            self.status_line.setText(text)
            announce(self.status_line, text)

    def reset(self) -> None:
        self._last_step = None


class ReportBox(QFrame):
    """The result of the last operation: a title, the fixed message, a code, actions."""

    triggered = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("report-box")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(6)
        self.title = label(role="title")
        self.body = label()
        self.code = label(role="mono")
        self.action_row = ActionRow()
        self.action_row.triggered.connect(self.triggered.emit)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        layout.addWidget(self.code)
        layout.addWidget(self.action_row)
        self._last: ReportView | None = None

    def show_report(self, view: ReportView) -> bool:
        """Show ``view``; True when it is new content (so the caller may focus it)."""

        if view == self._last:
            self.action_row.set_actions(view.actions)
            return False
        self._last = view
        self.setProperty("role", "alert" if view.assertive else "notice")
        self.style().unpolish(self)
        self.style().polish(self)
        self.title.setText(f"{_REPORT_PREFIX[view.kind]} {view.title}")
        self.body.setText(view.body)
        self.code.setText(view.code or "")
        self.code.setVisible(view.code is not None)
        self.action_row.set_actions(view.actions)
        text = f"{view.title}. {view.body}"
        announce(self, text, assertive=view.assertive)
        self.setAccessibleDescription(view.code or "")
        return True

    def clear(self) -> None:
        self._last = None


def _report(notice: ProjectsNotice) -> ReportView:
    kind = ReportKind.ERROR if notice.kind is NoticeKind.ERROR else ReportKind.INFO
    return ReportView(kind, notice.title, notice.body, notice.code, ())


class NoticeBox(ReportBox):
    """The last notice (an error or a plain confirmation) in a project surface."""

    def show_notice(self, notice: ProjectsNotice | None) -> bool:
        """Show ``notice``; True when it is new (so the caller may move focus)."""

        if notice is None:
            self.setVisible(False)
            self.clear()
            return False
        self.setVisible(True)
        return self.show_report(_report(notice))


class LanguageBox(QFrame):
    """The language check beside model labels: a quiet panel, or a notice if it warns.

    A warning is an icon and words, never colour alone. Hidden until it has text.
    """

    def __init__(
        self, name: str, parent: QWidget | None = None, *, compact: bool = False
    ) -> None:
        super().__init__(parent)
        self._compact = compact  # a quiet check shows only its headline
        self.setObjectName(name)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("role", "panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)
        self.headline = label(role="title")
        self.headline.setObjectName(f"{name}-headline")
        self.detail = label(role="muted")
        self.detail.setObjectName(f"{name}-detail")
        add_all(layout, self.headline, self.detail)
        self.setVisible(False)

    def show_language(self, headline: str | None, detail: str, warns: bool) -> None:
        self.setVisible(headline is not None)
        if headline is None:
            return
        self.headline.setText(f"⚠ {headline}" if warns else headline)
        self.detail.setText(detail)
        quiet = self._compact and not warns
        self.detail.setVisible(not quiet)
        self.headline.setProperty("role", "mono" if quiet else "title")
        self.headline.style().unpolish(self.headline)
        self.headline.style().polish(self.headline)
        self.setToolTip(detail if quiet else "")
        self.setAccessibleName(f"Language check. {headline}")
        self.setAccessibleDescription(detail)
        self.setProperty("role", "notice" if warns else "panel")
        self.style().unpolish(self)
        self.style().polish(self)


class CardWidget(QFrame):
    """One model: state chip (icon + word), sentence, files, actions, details."""

    triggered = Signal(object)

    def __init__(self, key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.setProperty("role", "card")
        self.setObjectName(f"card-{key}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)
        head = QHBoxLayout()
        self.title = label(role="title", wrap=False)
        self.chip = label(wrap=False)
        self.chip.setProperty("chip", True)
        self.chip.setObjectName(f"chip-{key}")
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.chip)
        self.sentence = label()
        self.problems = label(role="mono")
        self.also = label(role="muted")
        self.action_row = ActionRow()
        self.action_row.triggered.connect(self.triggered.emit)
        self.details_toggle = QToolButton()
        self.details_toggle.setText("Details and provenance")
        self.details_toggle.setCheckable(True)
        self.details_toggle.setAccessibleName("Details and provenance")
        self.details = label(role="mono")
        self.details.setVisible(False)
        self.details_toggle.toggled.connect(self.details.setVisible)
        layout.addLayout(head)
        for item in (self.sentence, self.problems, self.also):
            layout.addWidget(item)
        layout.addWidget(self.action_row)
        layout.addWidget(self.details_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.details)

    def show_card(self, view: CardView) -> None:
        self.title.setText(view.title)
        self.chip.setText(view.chip)
        self.chip.setProperty("tone", _CHIP_TONES.get(view.chip_icon, "neutral"))
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)
        self.sentence.setText(view.sentence)
        self.problems.setText(", ".join(view.problem_files))
        self.problems.setVisible(bool(view.problem_files))
        self.also.setText(view.also_found or "")
        self.also.setVisible(view.also_found is not None)
        self.action_row.set_actions(view.actions)
        self.details.setText("\n".join(f"{k}: {v}" for k, v in view.details))
        self.setAccessibleName(view.accessible_name)


class FlowLayout(QLayout):
    """Left-to-right layout that wraps to new rows, so actions never overflow."""

    def __init__(
        self,
        parent: QWidget | None = None,
        spacing: int = 8,
        *,
        one_line_hint: bool = False,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        # a wide preferred size (everything on one line) that can still shrink and wrap
        self._one_line_hint = one_line_hint

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 (Qt override)
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        if not self._one_line_hint:
            return self.minimumSize()
        width = sum(item.sizeHint().width() for item in self._items)
        width += self._spacing * max(len(self._items) - 1, 0)
        height = max((item.sizeHint().height() for item in self._items), default=0)
        margins = self.contentsMargins()
        return QSize(
            width + margins.left() + margins.right(),
            height + margins.top() + margins.bottom(),
        )

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )

    def _arrange(self, rect: QRect, *, apply: bool) -> int:
        x, y, row_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and row_height > 0:
                x = rect.x()
                y += row_height + self._spacing
                row_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            row_height = max(row_height, hint.height())
        return y + row_height - rect.y()
