"""The Review surface: the queue, the immutable AI record, and the human's judgment.

Three zones, as in the approved Round 3 reference: the queue of records on the left,
and beside the open record two equal cards, the AI record (read-only, labels only) and
the human's own judgment. The queue is a view of the existing filtered queue; choosing
a line opens that record by its row identity. When the window is narrow the queue moves
above the record and the two cards stack, so nothing needs a horizontal scroll.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPen,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from ...application.review_workflow import Advance, ReviewDraft, ReviewJudgment
from ...contracts import EmotionLabel, SentimentLabel
from ..review import ReviewController, ReviewState
from ..review_view import (
    EXPORT_LABEL,
    JUDGMENT_WORDS,
    NATIVE_LABEL,
    AiRecordView,
    HumanJudgmentView,
    QueueItemView,
    RecordView,
    ReviewView,
    build_review_view,
    filters_from,
)
from . import style
from .components import (
    MAX_CONTENT_WIDTH,
    BarMeter,
    Combo,
    FlowRow,
    LabeledControl,
    Page,
    PageHeader,
    ScorePanel,
    SegmentedFilter,
    ViewportWatcher,
    relax_width,
)
from .platform import DesktopPlatform
from .widgets import LanguageBox, NoticeBox, add_all, announce, label

PLACEHOLDER = "Choose a label…"
EXPORT_FILE_NAME = "reviewed-results.csv"
DISCARD_TITLE = "Unsaved changes"
DISCARD_TEXT = "You have unsaved changes to this record. Discard them and continue?"
EXPORT_UNSAVED_TEXT = (
    "You have unsaved changes to this record. The export contains only what is "
    "already saved. Export anyway?"
)
QUEUE_WIDTH = 262
QUEUE_ROW_HEIGHT = 54
HUMAN_SAVED_NOTE = "saved separately · never changes the AI record"


def _lines(items: tuple[str, ...]) -> str:
    return "\n".join(items)


class QueueDelegate(QStyledItemDelegate):
    """Two lines per record: its identity (mono) and the start of its text."""

    ROLE_ID = int(Qt.ItemDataRole.UserRole) + 1
    ROLE_TEXT = int(Qt.ItemDataRole.UserRole) + 2
    ROLE_DONE = int(Qt.ItemDataRole.UserRole) + 3
    ROLE_OPEN = int(Qt.ItemDataRole.UserRole) + 4

    def sizeHint(  # noqa: N802 (Qt override)
        self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> QSize:
        return QSize(option.rect.width(), QUEUE_ROW_HEIGHT)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        painter.save()
        # the open record is tinted and barred; the keyboard cursor is a ring
        is_open = bool(index.data(self.ROLE_OPEN))
        cursor = bool(option.state & QStyle.StateFlag.State_HasFocus)
        rect: QRect = option.rect
        painter.fillRect(
            rect,
            QColor(style.ULTRAMARINE_TINT if is_open else style.PAPER_RAISED),
        )
        if is_open:
            painter.fillRect(QRect(rect.x(), rect.y(), 3, rect.height()), style.INK)
        painter.setPen(QColor(style.LINE))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        if cursor:
            painter.setPen(QPen(QColor(style.FOCUS), 2))
            painter.drawRect(rect.adjusted(2, 2, -2, -3))
        left = rect.x() + 12
        right = rect.right() - 10
        mono = QFont(option.font)
        mono.setFamilies(["Consolas", "Courier New"])
        mono.setPointSizeF(8.5)
        painter.setFont(mono)
        painter.setPen(QColor(style.MUTED))
        record_id = str(index.data(self.ROLE_ID))
        done = bool(index.data(self.ROLE_DONE))
        painter.drawText(
            QRect(left, rect.y() + 6, right - left - 20, 18),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            record_id,
        )
        if done:
            painter.drawText(
                QRect(right - 18, rect.y() + 6, 18, 18),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                "✓",
            )
        painter.setFont(option.font)
        painter.setPen(QColor(style.INK))
        metrics = painter.fontMetrics()
        painter.drawText(
            QRect(left, rect.y() + 26, right - left, 20),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            metrics.elidedText(
                str(index.data(self.ROLE_TEXT)),
                Qt.TextElideMode.ElideRight,
                right - left,
            ),
        )
        painter.restore()


class QueueList(QListWidget):
    """The filtered review queue. A line opens its record (click, Enter or Space)."""

    row_chosen = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("review-queue")
        self.setAccessibleName("Review queue")
        self.setItemDelegate(QueueDelegate(self))
        # no selection of its own: the open record is drawn from its identity, and
        # the arrow keys only move a cursor until Enter or Space opens that line
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._signature: object = None
        self._open_row: int | None = None
        # one signal for a click; Enter, Return and Space are handled below, so a
        # platform's single-click activation cannot choose a line twice
        self.itemClicked.connect(self._chosen)

    def set_entries(
        self, entries: tuple[QueueItemView, ...], selected_row: int | None
    ) -> None:
        """Show ``entries``; the open record is selected by its row identity."""

        self.blockSignals(True)
        try:
            rebuilt = entries != self._signature
            if rebuilt:
                self._signature = entries
                self.clear()
                for entry in entries:
                    item = QListWidgetItem()
                    item.setData(Qt.ItemDataRole.UserRole, entry.row_number)
                    item.setData(QueueDelegate.ROLE_ID, entry.record_id)
                    item.setData(QueueDelegate.ROLE_TEXT, entry.excerpt)
                    item.setData(QueueDelegate.ROLE_DONE, entry.reviewed)
                    item.setToolTip(entry.excerpt)
                    self.addItem(item)
            moved = rebuilt or selected_row != self._open_row
            self._open_row = selected_row
            for index in range(self.count()):
                item = self.item(index)
                if item is None:
                    continue
                is_open = item.data(Qt.ItemDataRole.UserRole) == selected_row
                item.setData(QueueDelegate.ROLE_OPEN, is_open)
                # the open line is named as such, so assistive technology can tell
                # which record is open (the list has no selection of its own)
                name = entries[index].accessible_name
                item.setData(
                    Qt.ItemDataRole.AccessibleTextRole,
                    f"{name} Open record." if is_open else name,
                )
                if is_open and moved:  # a state refresh must not undo the user's scroll
                    self.setCurrentItem(item)  # the cursor starts on the open line
                    self.scrollToItem(item)
        finally:
            self.blockSignals(False)

    def open_row(self) -> int | None:
        """The row of the record that is open (not the keyboard cursor)."""

        return self._open_row

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt override)
        keys = (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
        current = self.currentItem()
        if event.key() in keys and current is not None:
            self._chosen(current)
            return
        super().keyPressEvent(event)

    def _chosen(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if value is not None:
            self.row_chosen.emit(int(value))


class QueuePane(QFrame):
    """The queue with its heading and position, in one card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setObjectName("review-queue-pane")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 1)
        layout.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(14, 12, 14, 8)
        self.heading = label(role="eyebrow", wrap=False)
        self.heading.setObjectName("queue-heading")
        self.position = label(role="mono", wrap=False)
        self.position.setObjectName("queue-position")
        head.addWidget(self.heading, 1)
        head.addWidget(self.position)
        layout.addLayout(head)
        self.list = QueueList()
        layout.addWidget(self.list, 1)

    def show_queue(self, view: ReviewView) -> None:
        self.heading.setText(view.queue_heading.upper())
        self.position.setText(view.queue_position)
        self.list.set_entries(view.queue, view.selected_row)
        self.setAccessibleName(f"{view.queue_heading}. {view.queue_position}")


class AiBlock(QFrame):
    """Read-only by construction: only labels, never an input widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "ai")
        self.setObjectName("ai-record")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(6)
        self.heading = label(role="cardhead")
        self.heading.setProperty("side", "ai")
        self.heading.setObjectName("ai-heading")
        self.sentiment_eyebrow = label("SENTIMENT", role="eyebrow", wrap=False)
        self.sentiment_word = label(role="word", wrap=False)
        self.sentiment_word.setObjectName("ai-sentiment-word")
        self.sentiment = label(role="mono")
        self.sentiment.setObjectName("ai-sentiment")
        self.emotion_eyebrow = label("DOMINANT EMOTION", role="eyebrow", wrap=False)
        self.emotion_word = label(role="word", wrap=False)
        self.emotion_word.setObjectName("ai-emotion-word")
        self.emotion = label(role="mono")
        self.emotion.setObjectName("ai-emotion")
        self.secondary = label(role="muted")
        self.scores = ScorePanel()
        self.native_toggle = self.scores.native_toggle
        self.native = self.scores.native
        self.provenance = label(role="mono")
        layout.addWidget(self.heading)
        add_all(layout, self.sentiment_eyebrow, self.sentiment_word, self.sentiment)
        add_all(layout, self.emotion_eyebrow, self.emotion_word, self.emotion)
        add_all(layout, self.secondary, self.scores, self.provenance)
        layout.addStretch(1)

    def show_ai(self, view: AiRecordView) -> None:
        self.heading.setText(view.heading)
        self.sentiment_word.setText(view.sentiment_word)
        self.sentiment_word.setProperty("polarity", view.sentiment_value)
        self.sentiment_word.style().unpolish(self.sentiment_word)
        self.sentiment_word.style().polish(self.sentiment_word)
        self.sentiment.setText(view.sentiment_detail)
        self.emotion_word.setText(view.emotion_word)
        self.emotion.setText(view.emotion_detail)
        self.secondary.setText(view.secondary_line)
        self.scores.show_scores(view.scores)
        self.provenance.setText(_lines(view.provenance))
        self.setAccessibleName(view.accessible_name)

    @property
    def heading_text(self) -> str:
        return str(self.heading.text())


class HumanBlock(QFrame):
    """The human's own judgment; every change is reported as a draft."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "human")
        self.setObjectName("human-judgment")
        self._syncing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(6)
        self.heading = label(role="cardhead")
        self.heading.setProperty("side", "human")
        self.heading.setObjectName("human-heading")
        self.saved_note = label(HUMAN_SAVED_NOTE, role="muted")
        self.status = label()
        self.status.setObjectName("review-status")
        add_all(layout, self.heading, self.saved_note, self.status)

        self.sentiment_box = QGroupBox("SENTIMENT")
        self.sentiment_box.setAccessibleName("Sentiment judgment")
        self.sentiment_box.setProperty("plain", True)
        self.sentiment_group, self.sentiment_radios = self._radios("sentiment")
        self.sentiment_combo = self._combo(
            "sentiment-label", "Human sentiment", [s.value for s in SentimentLabel]
        )
        sentiment_layout = QVBoxLayout(self.sentiment_box)
        sentiment_layout.setContentsMargins(0, 4, 0, 0)
        self._add_radios(sentiment_layout, self.sentiment_radios)
        sentiment_layout.addWidget(self.sentiment_combo)

        self.emotion_box = QGroupBox("EMOTION")
        self.emotion_box.setAccessibleName("Emotion judgment")
        self.emotion_box.setProperty("plain", True)
        self.emotion_group, self.emotion_radios = self._radios("emotion")
        self.dominant_combo = self._combo(
            "dominant-emotion",
            "Human dominant emotion",
            [e.value for e in EmotionLabel],
        )
        self.secondary_box = QGroupBox("HUMAN SECONDARY EMOTIONS")
        self.secondary_box.setProperty("plain", True)
        self.secondary_boxes: dict[EmotionLabel, QCheckBox] = {}
        secondary_layout = QGridLayout(self.secondary_box)
        secondary_layout.setContentsMargins(0, 4, 0, 0)
        for position, emotion in enumerate(EmotionLabel):
            box = QCheckBox(emotion.value.capitalize())
            box.setAccessibleName(f"Secondary emotion {emotion.value}")
            box.toggled.connect(self._edited)
            self.secondary_boxes[emotion] = box
            secondary_layout.addWidget(box, position // 3, position % 3)
        emotion_layout = QVBoxLayout(self.emotion_box)
        emotion_layout.setContentsMargins(0, 4, 0, 0)
        self._add_radios(emotion_layout, self.emotion_radios)
        add_all(emotion_layout, self.dominant_combo, self.secondary_box)

        self.note = QPlainTextEdit()
        self.note.setObjectName("review-note")
        self.note.setAccessibleName("Review note (optional)")
        self.note.setPlaceholderText("Why you disagreed, if you did")
        self.note.setTabChangesFocus(True)  # Tab leaves the note, as in a form
        self.note.setFixedHeight(76)
        self.note.textChanged.connect(self._edited)
        self.counter = label(role="muted")
        self.counter.setObjectName("note-counter")
        self.unsaved = label()
        self.unsaved.setObjectName("unsaved-changes")
        self.error = label(role="error")
        self.error.setObjectName("review-field-error")
        self.error.setVisible(False)
        add_all(layout, self.sentiment_box, self.emotion_box)
        add_all(layout, label("Optional review note", role="muted"), self.note)
        add_all(layout, self.counter, self.unsaved, self.error)
        self.action_row = FlowRow()
        layout.addWidget(self.action_row)
        layout.addStretch(1)

    # -- construction helpers -------------------------------------------------

    def _radios(
        self, key: str
    ) -> tuple[QButtonGroup, dict[ReviewJudgment, QRadioButton]]:
        group = QButtonGroup(self)
        buttons: dict[ReviewJudgment, QRadioButton] = {}
        for judgment, word in JUDGMENT_WORDS:
            button = QRadioButton(word)
            button.setProperty("choice", True)
            button.setObjectName(f"{key}-{judgment.value}")
            button.setAccessibleName(f"{key.capitalize()} judgment: {word}")
            button.toggled.connect(self._edited)
            group.addButton(button)
            buttons[judgment] = button
        return group, buttons

    @staticmethod
    def _add_radios(
        layout: QVBoxLayout, buttons: dict[ReviewJudgment, QRadioButton]
    ) -> None:
        row = QHBoxLayout()
        row.setSpacing(6)
        for button in buttons.values():
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

    def _combo(self, name: str, accessible: str, values: list[str]) -> Combo:
        combo = Combo()
        combo.setObjectName(name)
        combo.setAccessibleName(accessible)
        combo.addItem(PLACEHOLDER, None)
        for value in values:
            combo.addItem(value.capitalize(), value)
        combo.currentIndexChanged.connect(self._edited)
        return combo

    # -- state <-> widgets ----------------------------------------------------

    def _edited(self, *_: object) -> None:
        if not self._syncing:
            self.changed.emit()

    def draft(self) -> ReviewDraft:
        def judgment(
            buttons: dict[ReviewJudgment, QRadioButton],
        ) -> ReviewJudgment | None:
            return next((j for j, b in buttons.items() if b.isChecked()), None)

        sentiment = self.sentiment_combo.currentData()
        dominant = self.dominant_combo.currentData()
        return ReviewDraft(
            sentiment_judgment=judgment(self.sentiment_radios),
            human_sentiment=SentimentLabel(sentiment) if sentiment else None,
            emotion_judgment=judgment(self.emotion_radios),
            human_dominant_emotion=EmotionLabel(dominant) if dominant else None,
            human_secondary_emotions=tuple(
                e for e, box in self.secondary_boxes.items() if box.isChecked()
            ),
            note=self.note.toPlainText(),
        )

    def show_human(self, view: HumanJudgmentView, *, unsaved: bool) -> None:
        self._syncing = True
        try:
            self.heading.setText(view.heading)
            self.status.setText(f"Status: {view.status}")
            self._set_radios(self.sentiment_radios, view.sentiment_judgment)
            self._set_radios(self.emotion_radios, view.emotion_judgment)
            self._set_combo(self.sentiment_combo, view.human_sentiment)
            self._set_combo(self.dominant_combo, view.human_dominant_emotion)
            for emotion, box in self.secondary_boxes.items():
                box.setChecked(emotion in view.human_secondary_emotions)
            if self.note.toPlainText() != view.note:
                self.note.setPlainText(view.note)
        finally:
            self._syncing = False
        self.sentiment_combo.setVisible(view.sentiment_label_visible)
        self.dominant_combo.setVisible(view.emotion_labels_visible)
        self.secondary_box.setVisible(view.emotion_labels_visible)
        self.counter.setText(view.note_counter)
        self.unsaved.setText("● Unsaved changes" if unsaved else "")
        self.unsaved.setVisible(unsaved)
        self.setAccessibleName(f"{view.heading}. {view.status}")

    @staticmethod
    def _set_radios(
        buttons: dict[ReviewJudgment, QRadioButton], chosen: ReviewJudgment | None
    ) -> None:
        for judgment, button in buttons.items():
            wanted = judgment is chosen
            if button.isChecked() != wanted:
                button.group().setExclusive(False)
                button.setChecked(wanted)
                button.group().setExclusive(True)

    @staticmethod
    def _set_combo(combo: Combo, chosen: SentimentLabel | EmotionLabel | None) -> None:
        index = 0 if chosen is None else combo.findData(chosen.value)
        if combo.currentIndex() != index:
            combo.setCurrentIndex(index)

    def show_error(self, message: str | None) -> None:
        """The validation message beside the form, where the person is looking."""

        self.error.setText(f"✕ {message}" if message else "")
        self.error.setVisible(bool(message))

    def focus_field(self, field: str | None) -> QWidget:
        target: QWidget = self.sentiment_radios[ReviewJudgment.ACCEPT]
        if field == "sentiment_judgment":
            target = self.sentiment_radios[ReviewJudgment.ACCEPT]
        elif field == "emotion_judgment":
            target = self.emotion_radios[ReviewJudgment.ACCEPT]
        elif field == "human_sentiment":
            target = self.sentiment_combo
        elif field == "human_dominant_emotion":
            target = self.dominant_combo
        elif field == "human_secondary_emotions":
            target = next(iter(self.secondary_boxes.values()))
        elif field == "review_note":
            target = self.note
        target.setFocus()
        return target

    def first_field(self) -> QWidget:
        return self.sentiment_radios[ReviewJudgment.ACCEPT]


class ReviewPage(Page):
    agreement_requested = Signal()

    def __init__(
        self,
        controller: ReviewController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._platform = platform
        self._shown_row: int | None = None
        self._was_active = False
        self._filters_signature: object = None
        self._focus_before_busy: QWidget | None = None
        self._stacked: bool | None = None
        self._watcher = ViewportWatcher(self, self._reflow, area=self.scroller)
        self._queue_has_the_floor = False

        self.header = PageHeader("Review")
        self.title = self.header.title
        self.title.setObjectName("review-title")
        self.position = self.header.subtitle
        self.position.setObjectName("review-position")
        self.agreement_button = QPushButton("View agreement")
        self.agreement_button.setObjectName("review-agreement")
        self.agreement_button.setAccessibleName("View agreement with the AI")
        self.agreement_button.clicked.connect(self.agreement_requested.emit)
        self.header.add_action(self.agreement_button)
        self.notice = NoticeBox()
        self.notice.setVisible(False)

        # the review-state tabs (with counts) and progress, then the two AI filters
        self.status_tabs = SegmentedFilter(noun="records")
        self.status_tabs.setObjectName("review-state-tabs")
        self.status_tabs.setAccessibleName("Review state filter")
        self.status_tabs.selected.connect(self._status_chosen)
        self.meter = BarMeter(0.0, "ai")
        self.meter.setObjectName("review-meter")
        self.meter.setFixedWidth(180)
        self.meter_text = label(role="mono", wrap=False)
        self.meter_text.setObjectName("review-meter-text")
        self.meter_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.meter_box = QWidget()
        meter_layout = QVBoxLayout(self.meter_box)
        meter_layout.setContentsMargins(0, 0, 0, 0)
        meter_layout.setSpacing(2)
        meter_layout.addWidget(self.meter)
        meter_layout.addWidget(self.meter_text)
        self.progress = label(role="mono")
        self.progress.setObjectName("review-progress")
        self.failed = label(role="muted")
        self.failed.setObjectName("review-failed")
        self.tabs_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.tabs_row.setContentsMargins(0, 0, 0, 0)
        self.tabs_row.setSpacing(8)
        self.tabs_row.addWidget(self.status_tabs, 0, Qt.AlignmentFlag.AlignLeft)
        self.tabs_row.addStretch(1)
        self.tabs_row.addWidget(self.meter_box)
        self.sentiment_filter = self._filter("filter-sentiment", "AI sentiment filter")
        self.emotion_filter = self._filter(
            "filter-emotion", "AI dominant emotion filter"
        )
        filters = FlowRow()
        for caption, combo in (
            ("AI sentiment", self.sentiment_filter),
            ("AI dominant emotion", self.emotion_filter),
        ):
            filters.add(LabeledControl(caption, combo))
        self.toolbar = QWidget()
        toolbar = QVBoxLayout(self.toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        toolbar.addLayout(self.tabs_row)
        toolbar.addWidget(self.progress)
        toolbar.addWidget(filters)
        toolbar.addWidget(self.failed)

        self.native_box = QCheckBox(NATIVE_LABEL)
        self.native_box.setObjectName("export-native")
        relax_width(self.native_box)
        self.export_button = QPushButton(EXPORT_LABEL)
        self.export_button.setObjectName("review-export")
        self.export_button.setAccessibleName("Export reviewed CSV")
        self.export_button.clicked.connect(self._export)
        export_row = FlowRow()
        export_row.add(self.export_button)
        export_row.add(self.native_box)

        self.empty = label()
        self.empty.setObjectName("review-empty")

        # -- the record area: header with navigation, text, language, the two cards
        self.record_box = QWidget()
        record_layout = QVBoxLayout(self.record_box)
        record_layout.setContentsMargins(0, 0, 0, 0)
        record_layout.setSpacing(12)
        self.record_title = label(role="title")
        self.record_title.setObjectName("record-title")
        self.previous_button = self._button("review-previous", "Previous", "‹ Previous")
        self.next_button = self._button("review-next", "Next", "Next ›")
        self.next_unreviewed_button = self._button(
            "review-next-unreviewed", "Next unreviewed", "Next unreviewed ›"
        )
        self.record_nav = QWidget()
        self.record_nav.setProperty("role", "plain")
        navigation = QHBoxLayout(self.record_nav)
        navigation.setContentsMargins(0, 0, 0, 0)
        navigation.setSpacing(2)
        navigation.addWidget(self.record_title, 1)
        for button in (
            self.previous_button,
            self.next_button,
            self.next_unreviewed_button,
        ):
            button.setProperty("ghost", True)
            navigation.addWidget(button)
        self.record_context = label(role="mono")
        self.record_context.setObjectName("record-context")
        self.record_text = label()
        self.record_text.setObjectName("record-text")
        self.record_text.setProperty("quote", True)
        self.record_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.language_box = LanguageBox("record-language", compact=True)
        self.ai = AiBlock()
        self.human = HumanBlock()
        self.human.changed.connect(
            lambda: self._controller.set_draft(self.human.draft())
        )
        self.columns = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.columns.setSpacing(16)
        self.columns.addWidget(self.ai, 1, Qt.AlignmentFlag.AlignTop)
        self.columns.addWidget(self.human, 1, Qt.AlignmentFlag.AlignTop)
        record_layout.addWidget(self.record_nav)
        add_all(record_layout, self.record_context, self.record_text)
        add_all(record_layout, self.language_box)
        record_layout.addLayout(self.columns)

        self.accept_button = self._button("review-accept-both", "Accept both")
        self.save_button = self._button("review-save", "Save")
        self.save_next_button = self._button("review-save-next", "Save and next")
        self.save_next_button.setProperty("human", True)
        for button in (self.accept_button, self.save_button, self.save_next_button):
            self.human.action_row.add(button)

        # -- the queue beside the record (above it when the page is narrow)
        self.queue_pane = QueuePane()
        self.queue = self.queue_pane.list
        self.queue.row_chosen.connect(self._queue_chosen)
        self.workspace = QWidget()
        self._grid = QGridLayout(self.workspace)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._arrange_workspace(stacked=False)

        add_all(self.body, self.header, self.notice, self.toolbar)
        add_all(self.body, self.empty, self.workspace)
        self.body.addWidget(export_row)
        self.body.addStretch(1)

        self.previous_button.clicked.connect(
            lambda: self._guarded(self._controller.previous)
        )
        self.next_button.clicked.connect(lambda: self._guarded(self._controller.next))
        self.next_unreviewed_button.clicked.connect(
            lambda: self._guarded(self._controller.next_unreviewed)
        )
        # lambdas, so the clicked(checked) argument is never taken as ``advance``
        self.accept_button.clicked.connect(lambda: self._controller.accept_both())
        self.save_button.clicked.connect(lambda: self._controller.save())
        self.save_next_button.clicked.connect(
            lambda: self._controller.save(Advance.NEXT)
        )
        for combo in (self.sentiment_filter, self.emotion_filter):
            combo.activated.connect(self._filters_changed)

        controller.subscribe(self.show_state)
        self.show_state(controller.state)

    # -- layout -------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._watcher.attach()
        self._reflow()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        """Choose the arrangement from what the two cards actually need.

        Peer weight comes first: the AI and human cards sit side by side whenever the
        page is wide enough for both, and the queue then takes the left column if
        there is room for it too, else it sits above the record. When the page cannot
        hold two cards the cards stack, and the queue beside them needs a single one.
        """

        # the width the scrolling viewport really offers, and never more than the
        # page's own content column
        content = max(
            min(
                self._watcher.available(),
                MAX_CONTENT_WIDTH - 2 * style.PAGE_MARGIN_X,
            ),
            0,
        )
        gap = 16
        ai_need = self.ai.minimumSizeHint().width()
        human_need = self.human.minimumSizeHint().width()
        # a record column also holds the navigation row: it sets the narrowest column
        one = max(ai_need, human_need, self.record_nav.minimumSizeHint().width())
        both = max(ai_need + gap + human_need, one)
        if content >= both:
            cards_side_by_side = True
            queue_beside = content >= both + gap + QUEUE_WIDTH
        else:
            cards_side_by_side = False
            queue_beside = content >= one + gap + QUEUE_WIDTH
        if (not queue_beside) != self._stacked:
            self._arrange_workspace(stacked=not queue_beside)
        direction = (
            QBoxLayout.Direction.LeftToRight
            if cards_side_by_side
            else QBoxLayout.Direction.TopToBottom
        )
        if self.columns.direction() != direction:
            self.columns.setDirection(direction)
        # the progress meter sits at the right of the tabs, or under them when narrow
        tabs = self.status_tabs.preferred_width()
        row = (
            QBoxLayout.Direction.LeftToRight
            if content >= tabs + gap + self.meter_box.minimumSizeHint().width()
            else QBoxLayout.Direction.TopToBottom
        )
        if self.tabs_row.direction() != row:
            self.tabs_row.setDirection(row)

    def _arrange_workspace(self, *, stacked: bool) -> None:
        self._stacked = stacked
        for widget in (self.queue_pane, self.record_box):
            self._grid.removeWidget(widget)
        if stacked:
            self.queue_pane.setMinimumWidth(0)
            self.queue_pane.setMaximumWidth(16_777_215)
            self.queue_pane.setMinimumHeight(190)
            self.queue_pane.setMaximumHeight(190)
            self._grid.addWidget(self.queue_pane, 0, 0)
            self._grid.addWidget(self.record_box, 1, 0)
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 0)
        else:
            self.queue_pane.setMinimumHeight(420)
            self.queue_pane.setMaximumHeight(16_777_215)
            self.queue_pane.setFixedWidth(QUEUE_WIDTH)
            self._grid.addWidget(self.queue_pane, 0, 0)
            self._grid.addWidget(self.record_box, 0, 1, Qt.AlignmentFlag.AlignTop)
            self._grid.setColumnStretch(0, 0)
            self._grid.setColumnStretch(1, 1)

    # -- construction helpers -------------------------------------------------

    @staticmethod
    def _filter(name: str, accessible: str) -> Combo:
        combo = Combo()
        combo.setObjectName(name)
        combo.setAccessibleName(accessible)
        return combo

    @staticmethod
    def _button(name: str, text: str, shown: str | None = None) -> QPushButton:
        button = QPushButton(shown or text)
        button.setObjectName(name)
        button.setAccessibleName(text)
        return button

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: ReviewState) -> None:
        had_focus = self._has_focus()
        if state.busy and had_focus and self._focus_before_busy is None:
            self._focus_before_busy = self.window().focusWidget()
        restore_focus = self._focus_before_busy if not state.busy else None
        is_new = self.notice.show_notice(state.notice)
        view = build_review_view(state)
        if view is None:
            self._was_active = False
            self._shown_row = None
            self._focus_before_busy = None
            return
        self._show_header(view)
        self._show_filters(view)
        record = view.record
        self.empty.setText(view.empty_line)
        self.empty.setVisible(record is None)
        self.workspace.setVisible(record is not None)
        if record is not None:
            self._show_record(record, view)
            self.queue_pane.show_queue(view)
        self._show_buttons(view)
        self._reflow()
        if state.busy:
            return
        self._focus_before_busy = None
        changed = record is not None and record.row_number != self._shown_row
        self._place_focus(
            record,
            had_focus=had_focus or restore_focus is not None,
            notice_is_new=is_new,
            view=view,
        )
        if (
            restore_focus is not None
            and not changed
            and not is_new
            and restore_focus.isEnabled()
            and restore_focus.isVisible()
        ):
            restore_focus.setFocus()

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_header(self, view: ReviewView) -> None:
        self.position.setText(view.position_line)
        self.progress.setText(view.progress_line)
        self.meter.set_value(view.progress_fraction, "ai")
        self.meter.setAccessibleName(view.progress_text)
        self.meter_text.setText(view.progress_text)
        self.failed.setText(view.failed_line)
        self.failed.setVisible(bool(view.failed_line))
        self.export_button.setEnabled(view.controls_enabled)
        self.native_box.setEnabled(view.controls_enabled)

    def _show_filters(self, view: ReviewView) -> None:
        status, sentiment, emotion = view.filters.as_values()
        self.status_tabs.set_options(view.status_tabs, status)
        self.status_tabs.setEnabled(view.controls_enabled)
        signature = (view.sentiment_filter_choices, view.emotion_filter_choices)
        if signature != self._filters_signature:
            self._filters_signature = signature
            for combo, choices in (
                (self.sentiment_filter, view.sentiment_filter_choices),
                (self.emotion_filter, view.emotion_filter_choices),
            ):
                combo.blockSignals(True)
                combo.clear()
                for text, value in choices:
                    combo.addItem(text, value)
                combo.blockSignals(False)
        wanted = (
            (self.sentiment_filter, sentiment),
            (self.emotion_filter, emotion),
        )
        for combo, value in wanted:
            combo.blockSignals(True)
            combo.setCurrentIndex(max(combo.findData(value), 0))
            combo.blockSignals(False)
            combo.setEnabled(view.controls_enabled)
        self.queue.setEnabled(view.controls_enabled)

    def _show_record(self, record: RecordView, view: ReviewView) -> None:
        self.record_title.setText(record.title)
        self.record_text.setText(record.text)
        self.record_text.setAccessibleName(f"Record text: {record.text}")
        self.record_context.setText(" · ".join(record.context))
        self.language_box.show_language(
            record.language_headline, record.language_detail, record.language_warns
        )
        self.ai.show_ai(record.ai)
        self.human.show_human(record.human, unsaved=view.unsaved)
        notice = view.notice
        self.human.show_error(
            notice.body if notice is not None and notice.field else None
        )
        for widget in (
            self.human.sentiment_box,
            self.human.emotion_box,
            self.human.note,
        ):
            widget.setEnabled(view.controls_enabled)

    def _show_buttons(self, view: ReviewView) -> None:
        self.previous_button.setEnabled(view.previous_enabled)
        self.next_button.setEnabled(view.next_enabled)
        self.next_unreviewed_button.setEnabled(view.next_unreviewed_enabled)
        self.accept_button.setEnabled(view.accept_both_enabled)
        self.save_button.setEnabled(view.save_enabled)
        self.save_next_button.setEnabled(view.save_enabled)
        self.agreement_button.setEnabled(view.controls_enabled)

    def _place_focus(
        self,
        record: RecordView | None,
        *,
        had_focus: bool,
        notice_is_new: bool,
        view: ReviewView,
    ) -> None:
        row = record.row_number if record is not None else None
        first = not self._was_active
        changed = row != self._shown_row
        self._was_active = True
        self._shown_row = row
        notice = view.notice
        if notice_is_new and notice is not None and notice.field and record is not None:
            self.scroller.ensureWidgetVisible(self.human.focus_field(notice.field))
        elif first:
            self.title.setFocus()
            if record is not None:
                announce(self.record_title, f"{view.position_line}. {record.title}")
        elif changed and record is not None and (had_focus or not self.isVisible()):
            keep_queue = self._queue_has_the_floor and self.queue.isEnabled()
            self._queue_has_the_floor = False
            if keep_queue:
                self.queue.setFocus()
            else:
                self.human.first_field().setFocus()
            announce(self.record_title, f"{view.position_line}. {record.title}")
        elif not self._focus_still_valid():
            self.title.setFocus()

    def _focus_still_valid(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and focused.isEnabled() and focused.isVisible()

    # -- actions ------------------------------------------------------------

    def _confirmed_discard(self) -> bool:
        if not self._controller.state.has_unsaved_changes:
            return True
        return self._platform.confirm(self, DISCARD_TITLE, DISCARD_TEXT)

    def _guarded(self, action: Callable[[], bool]) -> None:
        if self._confirmed_discard():
            action()
        else:
            self.show_state(self._controller.state)

    def _queue_chosen(self, row: int) -> None:
        """A queue line was chosen: open that record (after the discard check)."""

        if row == self._shown_row:
            return
        # the person is working down the queue: keep the keyboard there
        self._queue_has_the_floor = self.window().focusWidget() is self.queue
        self._guarded(lambda: self._controller.go_to(row))

    def _status_chosen(self, value: str) -> None:
        self._apply_filters(status=value)

    def _filters_changed(self, *_: object) -> None:
        self._apply_filters()

    def _apply_filters(self, status: str | None = None) -> None:
        current = self._controller.state.filters
        wanted = filters_from(
            status or current.status.value,
            str(self.sentiment_filter.currentData()),
            str(self.emotion_filter.currentData()),
        )
        if self._confirmed_discard():
            self._controller.set_filters(wanted)
        else:
            self.show_state(self._controller.state)  # put the filters back

    def _export(self) -> None:
        if self._controller.state.has_unsaved_changes and not self._platform.confirm(
            self, DISCARD_TITLE, EXPORT_UNSAVED_TEXT
        ):
            return
        path = self._platform.pick_save_csv(self, EXPORT_FILE_NAME)
        if path is not None:  # cancelling the dialog writes nothing
            self._controller.export(path, include_native=self.native_box.isChecked())
