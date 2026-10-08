"""The Review surface: the immutable AI record beside the human's own judgment."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QToolButton,
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
    RecordView,
    ReviewView,
    build_review_view,
    filters_from,
)
from .platform import DesktopPlatform
from .widgets import LanguageBox, NoticeBox, add_all, announce, frame, label

PLACEHOLDER = "Choose a label…"
EXPORT_FILE_NAME = "reviewed-results.csv"
DISCARD_TITLE = "Unsaved changes"
DISCARD_TEXT = "You have unsaved changes to this record. Discard them and continue?"
EXPORT_UNSAVED_TEXT = (
    "You have unsaved changes to this record. The export contains only what is "
    "already saved. Export anyway?"
)


def _lines(items: tuple[str, ...]) -> str:
    return "\n".join(items)


def _inline(items: tuple[str, ...]) -> str:
    return "  ·  ".join(items)


class AiBlock(QFrame):
    """Read-only by construction: only labels, never an input widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "ai")
        self.setObjectName("ai-record")
        layout = QVBoxLayout(self)
        self.heading = label(role="title")
        self.sentiment = label()
        self.sentiment_scores = label(role="mono")
        self.emotion = label()
        self.secondary = label()
        self.emotion_scores = label(role="mono")
        self.native_toggle = QToolButton()
        self.native_toggle.setText("Inspect all model-native emotion scores")
        self.native_toggle.setCheckable(True)
        self.native_toggle.setObjectName("native-toggle")
        self.native = label(role="mono")
        self.native.setVisible(False)
        self.native_toggle.toggled.connect(self.native.setVisible)
        self.provenance = label(role="mono")
        add_all(layout, self.heading, self.sentiment, self.sentiment_scores)
        add_all(layout, self.emotion, self.secondary, self.emotion_scores)
        layout.addWidget(self.native_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        add_all(layout, self.native, self.provenance)
        layout.addStretch(1)

    def show_ai(self, view: AiRecordView) -> None:
        self.heading.setText(view.heading)
        self.sentiment.setText(f"Sentiment: {view.sentiment_line}")
        self.sentiment_scores.setText(_inline(view.sentiment_scores))
        self.emotion.setText(f"Emotion: {view.emotion_line}")
        self.secondary.setText(view.secondary_line)
        self.emotion_scores.setText(_inline(view.emotion_scores))
        self.native.setText(_inline(view.native_scores))
        self.provenance.setText(_lines(view.provenance))
        self.setAccessibleName(view.accessible_name)


class HumanBlock(QFrame):
    """The human's own judgment; every change is reported as a draft."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "human")
        self.setObjectName("human-judgment")
        self._syncing = False
        layout = QVBoxLayout(self)
        self.heading = label(role="title")
        self.status = label()
        self.status.setObjectName("review-status")
        add_all(layout, self.heading, self.status)

        self.sentiment_box = QGroupBox("Sentiment judgment")
        self.sentiment_group, self.sentiment_radios = self._radios("sentiment")
        self.sentiment_combo = self._combo(
            "sentiment-label", "Human sentiment", [s.value for s in SentimentLabel]
        )
        sentiment_layout = QVBoxLayout(self.sentiment_box)
        self._add_radios(sentiment_layout, self.sentiment_radios)
        sentiment_layout.addWidget(self.sentiment_combo)

        self.emotion_box = QGroupBox("Emotion judgment")
        self.emotion_group, self.emotion_radios = self._radios("emotion")
        self.dominant_combo = self._combo(
            "dominant-emotion",
            "Human dominant emotion",
            [e.value for e in EmotionLabel],
        )
        self.secondary_box = QGroupBox("Human secondary emotions")
        self.secondary_boxes: dict[EmotionLabel, QCheckBox] = {}
        secondary_layout = QVBoxLayout(self.secondary_box)
        for emotion in EmotionLabel:
            box = QCheckBox(emotion.value.capitalize())
            box.setAccessibleName(f"Secondary emotion {emotion.value}")
            box.toggled.connect(self._edited)
            self.secondary_boxes[emotion] = box
            secondary_layout.addWidget(box)
        emotion_layout = QVBoxLayout(self.emotion_box)
        self._add_radios(emotion_layout, self.emotion_radios)
        add_all(emotion_layout, self.dominant_combo, self.secondary_box)

        self.note = QPlainTextEdit()
        self.note.setObjectName("review-note")
        self.note.setAccessibleName("Review note (optional)")
        self.note.setTabChangesFocus(True)  # Tab leaves the note, as in a form
        self.note.setFixedHeight(80)
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

    # -- construction helpers -------------------------------------------------

    def _radios(
        self, key: str
    ) -> tuple[QButtonGroup, dict[ReviewJudgment, QRadioButton]]:
        group = QButtonGroup(self)
        buttons: dict[ReviewJudgment, QRadioButton] = {}
        for judgment, word in JUDGMENT_WORDS:
            button = QRadioButton(word)
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
        for button in buttons.values():
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

    def _combo(self, name: str, accessible: str, values: list[str]) -> QComboBox:
        combo = QComboBox()
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
    def _set_combo(
        combo: QComboBox, chosen: SentimentLabel | EmotionLabel | None
    ) -> None:
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


class ReviewPage(QWidget):
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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroller = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        layout = QVBoxLayout(body)

        self.back_button = QPushButton("← Project")
        self.back_button.setObjectName("review-back")
        self.back_button.setAccessibleName("Back to the project")
        self.back_button.clicked.connect(self._back)
        self.title = label("Review", role="headline")
        self.title.setObjectName("review-title")
        self.title.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.notice = NoticeBox()
        self.notice.setVisible(False)

        self.status_filter = self._filter("filter-status", "Review state filter")
        self.sentiment_filter = self._filter("filter-sentiment", "AI sentiment filter")
        self.emotion_filter = self._filter(
            "filter-emotion", "AI dominant emotion filter"
        )
        filters = QHBoxLayout()
        for caption, combo in (
            ("Review state", self.status_filter),
            ("AI sentiment", self.sentiment_filter),
            ("AI dominant emotion", self.emotion_filter),
        ):
            filters.addWidget(label(caption, role="muted", wrap=False))
            filters.addWidget(combo)
        filters.addStretch(1)

        self.position = label()
        self.position.setObjectName("review-position")
        self.progress = label()
        self.progress.setObjectName("review-progress")
        self.failed = label(role="muted")
        self.failed.setObjectName("review-failed")
        self.agreement_box = frame("panel")
        self.agreement_box.setObjectName("review-agreement")
        agreement_layout = QVBoxLayout(self.agreement_box)
        self.agreement_heading = label("Agreement with the AI", role="title")
        self.agreement_lines = label()
        self.agreement_note = label(role="muted")
        add_all(
            agreement_layout,
            self.agreement_heading,
            self.agreement_lines,
            self.agreement_note,
        )

        self.native_box = QCheckBox(NATIVE_LABEL)
        self.native_box.setObjectName("export-native")
        self.export_button = QPushButton(EXPORT_LABEL)
        self.export_button.setObjectName("review-export")
        self.export_button.setAccessibleName("Export reviewed CSV")
        self.export_button.clicked.connect(self._export)
        export_row = QHBoxLayout()
        export_row.addWidget(self.export_button)
        export_row.addWidget(self.native_box)
        export_row.addStretch(1)

        self.empty = label()
        self.empty.setObjectName("review-empty")
        self.record_box = QWidget()
        record_layout = QVBoxLayout(self.record_box)
        record_layout.setContentsMargins(0, 0, 0, 0)
        self.record_title = label(role="title")
        self.record_title.setObjectName("record-title")
        self.record_text = label()
        self.record_text.setObjectName("record-text")
        self.record_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.record_context = label(role="muted")
        self.language_box = LanguageBox("record-language")
        self.ai = AiBlock()
        self.human = HumanBlock()
        self.human.changed.connect(
            lambda: self._controller.set_draft(self.human.draft())
        )
        columns = QHBoxLayout()
        columns.addWidget(self.ai, 1)
        columns.addWidget(self.human, 1)
        add_all(
            record_layout,
            self.record_title,
            self.record_text,
            self.record_context,
            self.language_box,
        )
        record_layout.addLayout(columns)

        self.previous_button = self._button("review-previous", "Previous")
        self.next_button = self._button("review-next", "Next")
        self.next_unreviewed_button = self._button(
            "review-next-unreviewed", "Next unreviewed"
        )
        self.accept_button = self._button("review-accept-both", "Accept both")
        self.save_button = self._button("review-save", "Save")
        self.save_next_button = self._button("review-save-next", "Save and next")
        self.save_next_button.setProperty("primary", True)
        actions = QHBoxLayout()
        for button in (
            self.previous_button,
            self.next_button,
            self.next_unreviewed_button,
            self.accept_button,
            self.save_button,
            self.save_next_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        record_layout.addLayout(actions)

        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        add_all(layout, self.title, self.notice)
        layout.addLayout(filters)
        add_all(layout, self.position, self.progress, self.failed)
        add_all(layout, self.empty, self.record_box, self.agreement_box)
        layout.addLayout(export_row)
        layout.addStretch(1)

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
        for combo in (self.status_filter, self.sentiment_filter, self.emotion_filter):
            combo.activated.connect(self._filters_changed)

        controller.subscribe(self.show_state)
        self.show_state(controller.state)

    # -- construction helpers -------------------------------------------------

    @staticmethod
    def _filter(name: str, accessible: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(name)
        combo.setAccessibleName(accessible)
        return combo

    @staticmethod
    def _button(name: str, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setAccessibleName(text)
        return button

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: ReviewState) -> None:
        had_focus = self._has_focus()
        is_new = self.notice.show_notice(state.notice)
        view = build_review_view(state)
        if view is None:
            self._was_active = False
            self._shown_row = None
            return
        self._show_header(view)
        self._show_filters(view)
        record = view.record
        self.empty.setText(view.empty_line)
        self.empty.setVisible(record is None)
        self.record_box.setVisible(record is not None)
        if record is not None:
            self._show_record(record, view)
        self._show_buttons(view)
        self._place_focus(record, had_focus=had_focus, notice_is_new=is_new, view=view)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_header(self, view: ReviewView) -> None:
        self.position.setText(view.position_line)
        self.progress.setText(view.progress_line)
        self.failed.setText(view.failed_line)
        self.failed.setVisible(bool(view.failed_line))
        self.agreement_lines.setText("\n".join(view.agreement_lines))
        self.agreement_note.setText(view.agreement_note)
        self.export_button.setEnabled(view.controls_enabled)
        self.native_box.setEnabled(view.controls_enabled)

    def _show_filters(self, view: ReviewView) -> None:
        signature = (
            view.status_filter_choices,
            view.sentiment_filter_choices,
            view.emotion_filter_choices,
        )
        if signature != self._filters_signature:
            self._filters_signature = signature
            for combo, choices in (
                (self.status_filter, view.status_filter_choices),
                (self.sentiment_filter, view.sentiment_filter_choices),
                (self.emotion_filter, view.emotion_filter_choices),
            ):
                combo.blockSignals(True)
                combo.clear()
                for text, value in choices:
                    combo.addItem(text, value)
                combo.blockSignals(False)
        status, sentiment, emotion = view.filters.as_values()
        wanted = (
            (self.status_filter, status),
            (self.sentiment_filter, sentiment),
            (self.emotion_filter, emotion),
        )
        for combo, value in wanted:
            combo.blockSignals(True)
            combo.setCurrentIndex(max(combo.findData(value), 0))
            combo.blockSignals(False)
            combo.setEnabled(view.controls_enabled)

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
        self.back_button.setEnabled(view.controls_enabled)

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

    def _filters_changed(self, *_: object) -> None:
        wanted = filters_from(
            str(self.status_filter.currentData()),
            str(self.sentiment_filter.currentData()),
            str(self.emotion_filter.currentData()),
        )
        if self._confirmed_discard():
            self._controller.set_filters(wanted)
        else:
            self.show_state(self._controller.state)  # put the filters back

    def _back(self) -> None:
        if self._confirmed_discard():
            self._controller.close()

    def _export(self) -> None:
        if self._controller.state.has_unsaved_changes and not self._platform.confirm(
            self, DISCARD_TITLE, EXPORT_UNSAVED_TEXT
        ):
            return
        path = self._platform.pick_save_csv(self, EXPORT_FILE_NAME)
        if path is not None:  # cancelling the dialog writes nothing
            self._controller.export(path, include_native=self.native_box.isChecked())
