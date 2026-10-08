"""The Insights surface: grouped views, context notes, and representative cases."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from ...application.insights_workflow import (
    ContextAssociation,
    ContextTag,
    ExampleControls,
    ExampleMode,
    GroupingDimension,
    InsightMetric,
    InsightPerspective,
    NoteDraft,
)
from ...contracts import EmotionLabel, SentimentLabel
from ..insights import InsightsController, InsightsState
from ..insights_view import (
    CASES_NOTE,
    EXPORT_NOTE,
    LIMITATIONS,
    NOTES_NOTE,
    CaseView,
    GroupCardView,
    InsightsView,
    NoteView,
    build_insights_view,
)
from .platform import DesktopPlatform
from .widgets import NoticeBox, add_all, announce, frame, label

EXPORT_FILE_NAME = "insights.csv"
DISCARD_TITLE = "Unsaved note"
DISCARD_TEXT = "You have a note that is not saved. Discard it and continue?"
EXPORT_UNSAVED_TEXT = (
    "You have a note that is not saved. The export contains only saved notes. "
    "Export anyway?"
)
NOTE_FIELD_WIDGETS = {
    "association": "association_combo",
    "association_value": "value_combo",
    "phrase": "phrase_edit",
    "explanation": "explanation_edit",
    "context_importance": "importance_edit",
    "tags": "tag_boxes",
}
VIEW_FIELD_WIDGETS = {
    "date_from": "date_from_edit",
    "date_to": "date_to_edit",
    "date_range": "date_from_edit",
    "groups": "group_list",
    "grouping": "grouping_combo",
    "perspective": "perspective_combo",
    "metric": "metric_combo",
}


def _combo(name: str, accessible: str) -> QComboBox:
    combo = QComboBox()
    combo.setObjectName(name)
    combo.setAccessibleName(accessible)
    return combo


def _fill(combo: QComboBox, choices: tuple[tuple[str, str], ...], value: str) -> None:
    """Set a combo's items and selection without sending change signals."""

    combo.blockSignals(True)
    wanted = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    if wanted != list(choices):
        combo.clear()
        for text, data in choices:
            combo.addItem(text, data)
    combo.setCurrentIndex(max(combo.findData(value), 0))
    combo.blockSignals(False)


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.hide()  # a deleted widget is still painted until the loop runs
            widget.setParent(None)
            widget.deleteLater()


class GroupCardWidget(QFrame):
    def __init__(self, view: GroupCardView) -> None:
        super().__init__()
        self.setProperty("role", "card")
        self.setAccessibleName(view.accessible_name)
        layout = QVBoxLayout(self)
        layout.addWidget(label(view.heading, role="title"))
        add_all(layout, label(view.context_line), label(view.failed_line, role="muted"))
        if view.sample_line:
            warning = label(f"◆ {view.sample_line}")
            warning.setObjectName("sample-warning")
            layout.addWidget(warning)
        for row in view.rows:
            line = label(f"{row.label}: {row.count_text} · {row.percent_text}")
            line.setObjectName("metric-row")
            layout.addWidget(line)
        if view.review_line:
            layout.addWidget(label(view.review_line, role="muted"))


class NoteWidget(QFrame):
    delete_requested = Signal(str)

    def __init__(self, view: NoteView) -> None:
        super().__init__()
        self.setProperty("role", "human")
        self.setAccessibleName(f"{view.heading}: {view.phrase}")
        layout = QVBoxLayout(self)
        add_all(
            layout, label(view.heading, role="muted"), label(view.phrase, role="title")
        )
        add_all(layout, label(view.subtitle), label(view.explanation))
        add_all(layout, label(view.importance), label(view.tags_line, role="muted"))
        layout.addWidget(label(view.created_line, role="muted"))
        button = QPushButton("Delete note…")
        button.setObjectName("delete-note")
        button.setAccessibleName(view.delete_label)
        button.clicked.connect(lambda: self.delete_requested.emit(view.note_id))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)


class CaseWidget(QFrame):
    review_requested = Signal(int)

    def __init__(self, view: CaseView) -> None:
        super().__init__()
        self.setProperty("role", "card")
        layout = QVBoxLayout(self)
        add_all(
            layout, label(view.reason, role="muted"), label(view.title, role="title")
        )
        layout.addWidget(label(view.text))
        columns = QHBoxLayout()
        ai, human = frame("ai"), frame("human")
        ai_layout, human_layout = QVBoxLayout(ai), QVBoxLayout(human)
        add_all(ai_layout, label(view.ai_heading, role="title"), label(view.ai_line))
        add_all(
            human_layout,
            label(view.human_heading, role="title"),
            label(view.human_line),
        )
        columns.addWidget(ai, 1)
        columns.addWidget(human, 1)
        layout.addLayout(columns)
        button = QPushButton("Open this record in Review")
        button.setObjectName("open-in-review")
        button.setAccessibleName(f"Open {view.title} in Review")
        button.clicked.connect(lambda: self.review_requested.emit(view.row_number))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)


class InsightsPage(QWidget):
    review_requested = Signal(int)  # a row number to open in Review

    def __init__(
        self,
        controller: InsightsController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._platform = platform
        self._syncing = False
        self._was_active = False
        self._signatures: dict[str, object] = {}

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
        self.back_button.setObjectName("insights-back")
        self.back_button.setAccessibleName("Back to the project")
        self.back_button.clicked.connect(self._back)
        self.title = label("Insights", role="headline")
        self.title.setObjectName("insights-title")
        self.title.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.notice = NoticeBox()
        self.notice.setVisible(False)
        # a tab bar over two plain pages: only the shown page takes any space
        self.tabs = QTabBar()
        self.tabs.setObjectName("insights-tabs")
        self.tabs.setAccessibleName("Insight views")
        self.tabs.addTab("Group insights")
        self.tabs.addTab("Notes and cases")
        self._pages = (self._build_view_tab(), self._build_notes_tab())
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        add_all(layout, self.title, self.notice)
        layout.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignLeft)
        for page in self._pages:
            layout.addWidget(page)
        layout.addStretch(1)
        self.tabs.currentChanged.connect(self._show_tab)
        self._show_tab()

        controller.subscribe(self.show_state)
        self.show_state(controller.state)

    # -- construction ---------------------------------------------------------

    def _build_view_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        controls = frame("panel")
        controls_layout = QVBoxLayout(controls)
        self.grouping_combo = _combo("grouping", "Trusted grouping")
        self.perspective_combo = _combo("perspective", "Perspective")
        self.metric_combo = _combo("metric", "Metric")
        self.sentiment_combo = _combo("filter-sentiment", "AI sentiment filter")
        self.emotion_combo = _combo("filter-emotion", "AI dominant emotion filter")
        self.date_from_edit = QLineEdit()
        self.date_from_edit.setObjectName("date-from")
        self.date_from_edit.setAccessibleName("From date, YYYY-MM-DD")
        self.date_from_edit.setPlaceholderText("YYYY-MM-DD")
        self.date_to_edit = QLineEdit()
        self.date_to_edit.setObjectName("date-to")
        self.date_to_edit.setAccessibleName("To date, YYYY-MM-DD")
        self.date_to_edit.setPlaceholderText("YYYY-MM-DD")
        self.compare_box = QCheckBox("Compare 2 to 4 groups")
        self.compare_box.setObjectName("compare")
        self.group_list = QListWidget()
        self.group_list.setObjectName("groups")
        self.group_list.setAccessibleName("Groups to show")
        self.group_list.setMaximumHeight(130)
        self.group_hint = label(role="muted")
        self.field_error = label(role="error")
        self.field_error.setObjectName("insights-field-error")
        self.field_error.setVisible(False)
        self.apply_button = QPushButton("Show this view")
        self.apply_button.setObjectName("insights-apply")
        self.apply_button.setProperty("primary", True)
        self.apply_button.setAccessibleName("Show this view")
        for caption, widget in (
            ("Group by (as supplied in your file)", self.grouping_combo),
            ("Perspective", self.perspective_combo),
            ("Metric", self.metric_combo),
            ("AI sentiment filter", self.sentiment_combo),
            ("AI dominant emotion filter", self.emotion_combo),
            ("From date", self.date_from_edit),
            ("To date", self.date_to_edit),
        ):
            row = QHBoxLayout()
            row.addWidget(label(caption, role="muted", wrap=False))
            row.addWidget(widget, 1)
            controls_layout.addLayout(row)
        add_all(controls_layout, self.compare_box, self.group_list, self.group_hint)
        add_all(controls_layout, self.field_error)
        controls_layout.addWidget(self.apply_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.filters_line = label(role="muted")
        self.definition = label()
        self.definition.setObjectName("metric-definition")
        self.caution = label()
        self.caution.setObjectName("comparison-caution")
        self.cards_box = QVBoxLayout()
        self.limitations = label(LIMITATIONS, role="muted")
        self.provenance = label(role="mono")
        self.native_box = QCheckBox("Include model-native emotion scores")
        self.native_box.setObjectName("export-native")
        self.records_box = QCheckBox("Include supporting record text and metadata")
        self.records_box.setObjectName("export-records")
        self.export_button = QPushButton("Export insights CSV…")
        self.export_button.setObjectName("insights-export")
        self.export_button.setAccessibleName("Export insights CSV")
        export_row = QHBoxLayout()
        export_row.addWidget(self.export_button)
        export_row.addStretch(1)

        add_all(layout, controls, self.filters_line, self.definition, self.caution)
        layout.addLayout(self.cards_box)
        add_all(layout, self.limitations, self.provenance)
        add_all(layout, self.records_box, self.native_box)
        layout.addLayout(export_row)
        layout.addWidget(label(EXPORT_NOTE, role="muted"))

        self.grouping_combo.activated.connect(self._grouping_changed)
        self.perspective_combo.activated.connect(self._perspective_changed)
        for widget in (self.metric_combo, self.sentiment_combo, self.emotion_combo):
            widget.activated.connect(self._filters_changed)
        self.date_from_edit.textEdited.connect(self._filters_changed)
        self.date_to_edit.textEdited.connect(self._filters_changed)
        self.compare_box.toggled.connect(self._compare_changed)
        self.group_list.itemChanged.connect(self._groups_changed)
        self.apply_button.clicked.connect(lambda: self._controller.apply())
        self.export_button.clicked.connect(self._export)
        return tab

    def _build_notes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = frame("human")
        form_layout = QVBoxLayout(form)
        form_layout.addWidget(
            label("Add a context note (written by you)", role="title")
        )
        form_layout.addWidget(label(NOTES_NOTE, role="muted"))
        self.association_combo = _combo("note-association", "Note association")
        self.value_combo = _combo("note-value", "Association value")
        self.value_combo.setEditable(True)
        line = self.value_combo.lineEdit()
        assert line is not None
        line.setAccessibleName("Association value")
        self.phrase_edit = QLineEdit()
        self.phrase_edit.setObjectName("note-phrase")
        self.phrase_edit.setAccessibleName("Phrase or expression")
        self.phrase_edit.setMaxLength(500)
        self.explanation_edit = QPlainTextEdit()
        self.explanation_edit.setObjectName("note-explanation")
        self.explanation_edit.setAccessibleName("Your explanation")
        self.explanation_edit.setTabChangesFocus(True)
        self.explanation_edit.setFixedHeight(64)
        self.importance_edit = QPlainTextEdit()
        self.importance_edit.setObjectName("note-importance")
        self.importance_edit.setAccessibleName("Why the context matters")
        self.importance_edit.setTabChangesFocus(True)
        self.importance_edit.setFixedHeight(64)
        self.tag_boxes: dict[ContextTag, QCheckBox] = {}
        for caption, widget in (
            ("Association", self.association_combo),
            ("Association value", self.value_combo),
            ("Phrase or expression", self.phrase_edit),
            ("Your explanation", self.explanation_edit),
            ("Why the context matters", self.importance_edit),
        ):
            form_layout.addWidget(label(caption, role="muted"))
            form_layout.addWidget(widget)
        form_layout.addWidget(label("Optional context tags", role="muted"))
        for tag in ContextTag:
            box = QCheckBox(tag.value.replace("_", " ").capitalize())
            box.setAccessibleName(f"Tag {tag.value.replace('_', ' ')}")
            box.toggled.connect(self._note_changed)
            self.tag_boxes[tag] = box
            form_layout.addWidget(box)
        self.note_error = label(role="error")
        self.note_error.setObjectName("note-field-error")
        self.note_error.setVisible(False)
        self.unsaved_note = label()
        self.unsaved_note.setObjectName("unsaved-note")
        self.add_note_button = QPushButton("Add note")
        self.add_note_button.setObjectName("add-note")
        self.add_note_button.setProperty("primary", True)
        self.add_note_button.setAccessibleName("Add this note")
        add_all(form_layout, self.note_error, self.unsaved_note)
        form_layout.addWidget(self.add_note_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.notes_box = QVBoxLayout()
        self.no_notes = label("No context notes yet.", role="muted")
        self.no_notes.setObjectName("no-notes")

        self.mode_combo = _combo("example-mode", "Case selection rule")
        self.example_emotion_combo = _combo(
            "example-emotion", "Emotion for the score rule"
        )
        self.example_tag_combo = _combo("example-tag", "Context-note tag")
        self.record_list = QListWidget()
        self.record_list.setObjectName("example-records")
        self.record_list.setAccessibleName("Records to select")
        self.record_list.setMaximumHeight(130)
        self.select_button = QPushButton("Select cases")
        self.select_button.setObjectName("select-cases")
        self.select_button.setAccessibleName("Select cases by this rule")
        cases_panel = frame("panel")
        cases_layout = QVBoxLayout(cases_panel)
        cases_layout.addWidget(label("Representative cases", role="title"))
        for caption, control in (
            ("Selection rule", self.mode_combo),
            ("Emotion for the highest-score rule", self.example_emotion_combo),
            ("Context-note tag (optional)", self.example_tag_combo),
            ("Records for the selected-records rule", self.record_list),
        ):
            cases_layout.addWidget(label(caption, role="muted"))
            cases_layout.addWidget(control)
        cases_layout.addWidget(self.select_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.cases_box = QVBoxLayout()
        self.cases_empty = label()
        self.cases_empty.setObjectName("cases-empty")

        layout.addWidget(form)
        layout.addWidget(label("Your context notes", role="title"))
        add_all(layout, self.no_notes)
        layout.addLayout(self.notes_box)
        add_all(layout, cases_panel, label(CASES_NOTE, role="muted"), self.cases_empty)
        layout.addLayout(self.cases_box)

        self.association_combo.activated.connect(self._association_changed)
        self.value_combo.currentTextChanged.connect(self._note_changed)
        self.phrase_edit.textChanged.connect(self._note_changed)
        self.explanation_edit.textChanged.connect(self._note_changed)
        self.importance_edit.textChanged.connect(self._note_changed)
        self.add_note_button.clicked.connect(lambda: self._controller.add_note())
        for combo in (
            self.mode_combo,
            self.example_emotion_combo,
            self.example_tag_combo,
        ):
            combo.activated.connect(self._examples_changed)
        self.record_list.itemChanged.connect(self._examples_changed)
        self.select_button.clicked.connect(lambda: self._controller.select_cases())
        return tab

    def _show_tab(self, *_: object) -> None:
        """Show the chosen page; the other one takes no space."""

        for index, page in enumerate(self._pages):
            page.setVisible(index == self.tabs.currentIndex())

    # -- rendering ------------------------------------------------------------

    def show_state(self, state: InsightsState) -> None:
        had_focus = self._has_focus()
        is_new = self.notice.show_notice(state.notice)
        view = build_insights_view(state)
        if view is None:
            self._was_active = False
            return
        self._syncing = True
        try:
            self._show_controls(view)
            self._show_results(view)
            self._show_notes_tab(view, state)
            self._show_cases(view)
        finally:
            self._syncing = False
        self._place_focus(view, had_focus=had_focus, notice_is_new=is_new)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_controls(self, view: InsightsView) -> None:
        echo = view.controls_echo
        _fill(self.grouping_combo, view.grouping_choices, echo.grouping)
        _fill(self.perspective_combo, view.perspective_choices, echo.perspective)
        _fill(self.metric_combo, view.metric_choices, echo.metric)
        _fill(self.sentiment_combo, view.sentiment_choices, echo.sentiment)
        _fill(self.emotion_combo, view.emotion_choices, echo.emotion)
        for edit, text in (
            (self.date_from_edit, echo.date_from),
            (self.date_to_edit, echo.date_to),
        ):
            if edit.text() != text:
                edit.setText(text)
        self.compare_box.setChecked(echo.comparison)
        self._fill_checks(self.group_list, view.group_choices)
        self.group_hint.setText(view.group_hint)
        notice = view.notice
        message = view.error_message
        if notice is not None and self._is_view_field(notice.field):
            message = notice.body
        self.field_error.setText(f"✕ {message}" if message else "")
        self.field_error.setVisible(bool(message))
        for widget in (
            self.grouping_combo,
            self.perspective_combo,
            self.metric_combo,
            self.sentiment_combo,
            self.emotion_combo,
            self.date_from_edit,
            self.date_to_edit,
            self.compare_box,
            self.group_list,
        ):
            widget.setEnabled(view.controls_enabled)
        self.apply_button.setEnabled(view.apply_enabled)
        self.export_button.setEnabled(view.export_enabled)
        self.records_box.setEnabled(view.export_enabled)
        self.native_box.setEnabled(view.export_enabled)

    @staticmethod
    def _is_view_field(field: str | None) -> bool:
        return field in VIEW_FIELD_WIDGETS

    @staticmethod
    def _fill_checks(
        widget: QListWidget, choices: tuple[tuple[str, bool], ...]
    ) -> None:
        current = [
            (
                widget.item(i).text(),
                widget.item(i).checkState() is Qt.CheckState.Checked,
            )
            for i in range(widget.count())
        ]
        if current == list(choices):
            return
        widget.clear()
        for text, checked in choices:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            widget.addItem(item)

    def _show_results(self, view: InsightsView) -> None:
        self.filters_line.setText(view.filters_line)
        self.definition.setText(f"Metric and denominator: {view.definition_line}")
        self.caution.setText(
            f"◆ {view.comparison_caution}" if view.comparison_caution else ""
        )
        self.caution.setVisible(bool(view.comparison_caution))
        self.provenance.setText("\n".join(view.provenance_lines))
        signature = view.cards
        if signature != self._signatures.get("cards"):
            self._signatures["cards"] = signature
            _clear_layout(self.cards_box)
            for card in view.cards:
                card_widget = GroupCardWidget(card)
                self.cards_box.addWidget(card_widget)
                card_widget.show()

    def _show_notes_tab(self, view: InsightsView, state: InsightsState) -> None:
        draft = state.note_draft
        _fill(self.association_combo, view.association_choices, draft.association.value)
        values = view.note_value_choices.get(draft.association, ())
        if self._signatures.get("values") != (draft.association, values):
            self._signatures["values"] = (draft.association, values)
            self.value_combo.blockSignals(True)
            self.value_combo.clear()
            self.value_combo.addItems(list(values))
            self.value_combo.setEditText(draft.association_value)
            self.value_combo.blockSignals(False)
        elif self.value_combo.currentText() != draft.association_value:
            self.value_combo.setEditText(draft.association_value)
        for edit, text in (
            (self.phrase_edit, draft.phrase),
            (self.explanation_edit, draft.explanation),
            (self.importance_edit, draft.context_importance),
        ):
            if isinstance(edit, QPlainTextEdit):
                if edit.toPlainText() != text:
                    edit.setPlainText(text)
            elif edit.text() != text:
                edit.setText(text)
        for tag, box in self.tag_boxes.items():
            box.setChecked(tag in draft.tags)
            box.setEnabled(view.controls_enabled)
        notice = view.notice
        message = (
            notice.body
            if notice is not None and notice.field in NOTE_FIELD_WIDGETS
            else ""
        )
        self.note_error.setText(f"✕ {message}" if message else "")
        self.note_error.setVisible(bool(message))
        self.unsaved_note.setText("● Unsaved note" if view.unsaved else "")
        self.unsaved_note.setVisible(view.unsaved)
        self.add_note_button.setEnabled(view.add_note_enabled)
        for widget in (
            self.association_combo,
            self.value_combo,
            self.phrase_edit,
            self.explanation_edit,
            self.importance_edit,
        ):
            widget.setEnabled(view.controls_enabled)
        signature = view.notes
        if signature != self._signatures.get("notes"):
            self._signatures["notes"] = signature
            _clear_layout(self.notes_box)
            for note in view.notes:
                note_widget = NoteWidget(note)
                note_widget.delete_requested.connect(self._delete_note)
                self.notes_box.addWidget(note_widget)
                note_widget.show()
        self.no_notes.setVisible(not view.notes)

    def _show_cases(self, view: InsightsView) -> None:
        echo = view.controls_echo
        _fill(self.mode_combo, view.example_mode_choices, echo.example_mode)
        _fill(
            self.example_emotion_combo,
            view.example_emotion_choices,
            echo.example_emotion,
        )
        _fill(self.example_tag_combo, view.example_tag_choices, echo.example_tag)
        self._fill_checks(self.record_list, view.record_choices)
        for widget in (
            self.mode_combo,
            self.example_emotion_combo,
            self.example_tag_combo,
            self.record_list,
        ):
            widget.setEnabled(view.controls_enabled)
        self.select_button.setEnabled(view.controls_enabled)
        self.cases_empty.setText(view.cases_empty_line)
        self.cases_empty.setVisible(bool(view.cases_empty_line))
        signature = view.cases
        if signature != self._signatures.get("cases"):
            self._signatures["cases"] = signature
            _clear_layout(self.cases_box)
            for case in view.cases:
                case_widget = CaseWidget(case)
                case_widget.review_requested.connect(self._open_case)
                self.cases_box.addWidget(case_widget)
                case_widget.show()

    def _place_focus(
        self, view: InsightsView, *, had_focus: bool, notice_is_new: bool
    ) -> None:
        first = not self._was_active
        self._was_active = True
        notice = view.notice
        if notice_is_new and notice is not None and notice.field:
            target = self._field_widget(notice.field)
            if target is not None:
                if notice.field in NOTE_FIELD_WIDGETS:
                    self.tabs.setCurrentIndex(1)
                target.setFocus()
                self.scroller.ensureWidgetVisible(target)
                return
        if first:
            self.title.setFocus()
            announce(self.title, f"Insights. {view.filters_line}")
        elif had_focus and not self._focus_still_valid():
            self.title.setFocus()

    def _field_widget(self, field: str) -> QWidget | None:
        name = NOTE_FIELD_WIDGETS.get(field) or VIEW_FIELD_WIDGETS.get(field)
        if name is None:
            return None
        target: object = getattr(self, name)
        if isinstance(target, dict):
            target = next(iter(target.values()))
        assert isinstance(target, QWidget)
        return target

    def _focus_still_valid(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and focused.isEnabled() and focused.isVisible()

    # -- inputs -----------------------------------------------------------------

    def _grouping_changed(self, *_: object) -> None:
        if not self._syncing:
            self._controller.set_grouping(
                GroupingDimension(str(self.grouping_combo.currentData()))
            )

    def _perspective_changed(self, *_: object) -> None:
        if not self._syncing:
            self._controller.set_perspective(
                InsightPerspective(str(self.perspective_combo.currentData()))
            )

    def _filters_changed(self, *_: object) -> None:
        if self._syncing:
            return
        # read every widget first: each controller change re-renders the controls
        metric = InsightMetric(str(self.metric_combo.currentData()))
        sentiment = str(self.sentiment_combo.currentData())
        emotion = str(self.emotion_combo.currentData())
        self._controller.set_filters(
            metric=metric,
            sentiment=SentimentLabel(sentiment) if sentiment else None,
            emotion=EmotionLabel(emotion) if emotion else None,
            date_from=self.date_from_edit.text().strip(),
            date_to=self.date_to_edit.text().strip(),
        )

    def _compare_changed(self, checked: bool) -> None:
        if not self._syncing:
            self._controller.set_comparison(checked)

    def _groups_changed(self, *_: object) -> None:
        if self._syncing:
            return
        groups = tuple(
            self.group_list.item(i).text()
            for i in range(self.group_list.count())
            if self.group_list.item(i).checkState() is Qt.CheckState.Checked
        )
        self._controller.set_groups(groups)

    def _association_changed(self, *_: object) -> None:
        if self._syncing:
            return
        draft = self._note_draft()
        self._controller.set_note_draft(
            NoteDraft(
                association=ContextAssociation(
                    str(self.association_combo.currentData())
                ),
                association_value="",
                phrase=draft.phrase,
                explanation=draft.explanation,
                context_importance=draft.context_importance,
                tags=draft.tags,
            )
        )

    def _note_draft(self) -> NoteDraft:
        return NoteDraft(
            association=ContextAssociation(str(self.association_combo.currentData())),
            association_value=self.value_combo.currentText(),
            phrase=self.phrase_edit.text(),
            explanation=self.explanation_edit.toPlainText(),
            context_importance=self.importance_edit.toPlainText(),
            tags=tuple(t for t, box in self.tag_boxes.items() if box.isChecked()),
        )

    def _note_changed(self, *_: object) -> None:
        if not self._syncing:
            self._controller.set_note_draft(self._note_draft())

    def _examples_changed(self, *_: object) -> None:
        if self._syncing:
            return
        tag = str(self.example_tag_combo.currentData())
        records = tuple(
            self.record_list.item(i).text()
            for i in range(self.record_list.count())
            if self.record_list.item(i).checkState() is Qt.CheckState.Checked
        )
        self._controller.set_examples(
            ExampleControls(
                mode=ExampleMode(str(self.mode_combo.currentData())),
                emotion=EmotionLabel(str(self.example_emotion_combo.currentData())),
                tag=ContextTag(tag) if tag else None,
                record_ids=records,
            )
        )

    # -- actions ----------------------------------------------------------------

    def _confirmed_discard(self) -> bool:
        if not self._controller.state.has_unsaved_changes:
            return True
        return self._platform.confirm(self, DISCARD_TITLE, DISCARD_TEXT)

    def _back(self) -> None:
        if self._confirmed_discard():
            self._controller.close()

    def _open_case(self, row: int) -> None:
        """Open a case in Review, unless something is running or the note is unsaved."""

        if self._controller.state.busy:
            return
        if self._confirmed_discard():
            self.review_requested.emit(row)

    def _delete_note(self, note_id: str) -> None:
        if self._platform.confirm(
            self, "Delete note", "Delete this context note? This cannot be undone."
        ):
            self._controller.remove_note(note_id)

    def _export(self) -> None:
        if self._controller.state.has_unsaved_changes and not self._platform.confirm(
            self, DISCARD_TITLE, EXPORT_UNSAVED_TEXT
        ):
            return
        path = self._platform.pick_save_csv(self, EXPORT_FILE_NAME)
        if path is not None:  # cancelling the dialog writes nothing
            self._controller.export(
                path,
                include_records=self.records_box.isChecked(),
                include_native=self.native_box.isChecked(),
            )
