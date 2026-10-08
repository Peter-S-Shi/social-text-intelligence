"""The Projects surface: list, import, column step, analysis progress, delete."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...application.model_provisioning import ModelsStatus
from ..gate import AnalysisAvailability
from ..insights import InsightsController, InsightsState
from ..projects import ProjectsController, ProjectsState
from ..projects_view import (
    IMPORT_LABEL,
    ProjectDetailView,
    ProjectProgressView,
    ProjectRowView,
    build_detail_view,
    build_list_view,
    delete_confirmation,
    row_view,
)
from ..review import ReviewController, ReviewState
from .insights_page import InsightsPage
from .pages import AnalysisBlockBox
from .platform import DesktopPlatform
from .review_page import ReviewPage
from .widgets import NoticeBox, add_all, announce, frame, label

COLUMN_PLACEHOLDER = "Choose a column…"


class RowProgress(QWidget):
    """One progress bar with written text, and Cancel; announces in 10% steps."""

    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.text = label()
        self.text.setObjectName("project-progress-text")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("project-cancel")
        self.cancel_button.setAccessibleName("Cancel analysis")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        add_all(layout, self.text, self.bar)
        layout.addWidget(self.cancel_button)
        self._last_step: tuple[str, int] | None = None

    def show_progress(self, view: ProjectProgressView) -> None:
        self.text.setText(view.text)
        self.bar.setValue(int(view.fraction * 1000))
        self.bar.setAccessibleName(view.text)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(view.can_cancel)
        step = (view.stage, int(view.fraction * 10))
        if step != self._last_step:
            self._last_step = step
            announce(self.text, view.text)

    def reset(self) -> None:
        self._last_step = None


class ProjectRowWidget(QWidget):
    open_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(
        self, row: ProjectRowView, enabled: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        box = frame("card")
        box.setAccessibleName(row.accessible_name)
        inner = QVBoxLayout(box)
        inner.addWidget(label(row.title, role="title"))
        inner.addWidget(label(row.subtitle, role="muted"))
        buttons = QHBoxLayout()
        self.open_button = QPushButton("Open")
        self.open_button.setAccessibleName(f"Open {row.title}")
        self.open_button.setEnabled(enabled and row.can_open)
        self.open_button.setVisible(row.can_open)
        self.delete_button = QPushButton("Delete…")
        self.delete_button.setAccessibleName(f"Delete {row.title}")
        self.delete_button.setEnabled(enabled)
        self.open_button.clicked.connect(
            lambda: self.open_requested.emit(row.project_id)
        )
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(row.project_id)
        )
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        inner.addLayout(buttons)
        outer.addWidget(box)


class ProjectsPage(QWidget):
    open_models = Signal()

    def __init__(
        self,
        controller: ProjectsController,
        reviews: ReviewController,
        insights: InsightsController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._reviews = reviews
        self._insights = insights
        self._review_was_active = False
        self._insights_was_active = False
        self._platform = platform
        self._models = ModelsStatus(())
        self._availability = AnalysisAvailability.AVAILABLE
        self._other_analysis_running = False
        self._row_signature: object = None
        self._rows: list[ProjectRowWidget] = []
        self._detail_title = ""

        layout = QVBoxLayout(self)
        self.block = AnalysisBlockBox(quiet=True)
        self.block.triggered.connect(lambda _: self.open_models.emit())
        self.stack = QStackedWidget()
        self.notice = NoticeBox()
        self.notice.setVisible(False)
        add_all(layout, self.notice, self.block)
        layout.addWidget(self.stack, 1)

        # -- list mode
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        self.heading = label("Projects", role="headline")
        self.import_button = QPushButton(IMPORT_LABEL)
        self.import_button.setObjectName("import-csv")
        self.import_button.setProperty("primary", True)
        self.import_button.setAccessibleName("Import a CSV file as a new project")
        self.import_button.clicked.connect(self._import)
        self.summary = label()
        self.summary.setObjectName("projects-summary")
        self.rows_box = QVBoxLayout()
        self.note = label(
            "A project is one imported CSV and everything derived from it. It "
            "stays on this computer until you delete it.",
            role="muted",
        )
        add_all(list_layout, self.heading, self.summary)
        list_layout.addWidget(self.import_button, 0, Qt.AlignmentFlag.AlignLeft)
        list_layout.addLayout(self.rows_box)
        list_layout.addWidget(self.note)
        list_layout.addStretch(1)
        self.stack.addWidget(self.list_page)

        # -- detail mode
        self.detail_page = QWidget()
        detail = QVBoxLayout(self.detail_page)
        self.back_button = QPushButton("← Projects")
        self.back_button.setObjectName("project-back")
        self.back_button.setAccessibleName("Back to the project list")
        self.back_button.clicked.connect(controller.close_project)
        self.detail_title_label = label(role="headline")
        self.detail_title_label.setObjectName("project-title")
        self.state_line = label()
        self.state_line.setObjectName("project-state")
        self.facts = label(role="muted")
        self.facts.setObjectName("project-facts")
        self.column_box = frame("panel")
        self.column_box.setObjectName("column-step")
        column_layout = QVBoxLayout(self.column_box)
        column_layout.addWidget(label("Which column holds the text?", role="title"))
        self.column_combo = QComboBox()
        self.column_combo.setObjectName("column-combo")
        self.column_combo.setAccessibleName("Text column")
        self.choose_button = QPushButton("Use this column")
        self.choose_button.setObjectName("choose-column")
        self.choose_button.setProperty("primary", True)
        self.choose_button.clicked.connect(self._choose_column)
        self.column_combo.currentIndexChanged.connect(
            lambda _: self._sync_choose_button()
        )
        add_all(column_layout, self.column_combo)
        column_layout.addWidget(self.choose_button)
        self.detail_block = AnalysisBlockBox()
        self.detail_block.triggered.connect(lambda _: self.open_models.emit())
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("project-analyze")
        self.analyze_button.setProperty("primary", True)
        self.analyze_button.clicked.connect(controller.analyze)
        self.progress = RowProgress()
        self.progress.setVisible(False)
        self.progress.cancel_requested.connect(controller.cancel)
        self.review_button = QPushButton("Review results")
        self.review_button.setObjectName("project-review")
        self.review_button.setProperty("primary", True)
        self.review_button.setAccessibleName("Review this project's results")
        self.review_button.clicked.connect(self._open_review)
        self.insights_button = QPushButton("Insights")
        self.insights_button.setObjectName("project-insights")
        self.insights_button.setAccessibleName("Open this project's insights")
        self.insights_button.clicked.connect(self._open_insights)
        self.delete_button = QPushButton("Delete project…")
        self.delete_button.setObjectName("project-delete")
        self.delete_button.clicked.connect(self._delete_current)
        detail.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        add_all(detail, self.detail_title_label, self.state_line)
        add_all(detail, self.facts, self.column_box, self.detail_block)
        detail.addWidget(self.analyze_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail.addWidget(self.progress)
        detail.addWidget(self.review_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail.addWidget(self.insights_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail.addWidget(self.delete_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail.addStretch(1)
        self.stack.addWidget(self.detail_page)
        self.review_page = ReviewPage(reviews, platform)
        self.stack.addWidget(self.review_page)
        self.insights_page = InsightsPage(insights, platform)
        self.insights_page.review_requested.connect(self._open_in_review)
        self.stack.addWidget(self.insights_page)

        controller.subscribe(self.show_state)
        reviews.subscribe(self._on_review)
        insights.subscribe(self._on_insights)
        self.show_state(controller.state)

    # -- inputs from the shell ----------------------------------------------

    def show_availability(
        self,
        status: ModelsStatus,
        availability: AnalysisAvailability,
        *,
        other_analysis_running: bool,
    ) -> None:
        self._models = status
        self._availability = availability
        self._other_analysis_running = other_analysis_running
        self.show_state(self._controller.state)

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: ProjectsState) -> None:
        had_focus = self._has_focus()
        if self._reviews.state.active:
            self.stack.setCurrentWidget(self.review_page)
            return
        if self._insights.state.active:
            self.stack.setCurrentWidget(self.insights_page)
            return
        self.notice.show_notice(state.notice)
        view = build_detail_view(
            state,
            self._availability,
            self._models,
            other_analysis_running=self._other_analysis_running,
        )
        if view is None:
            self.stack.setCurrentWidget(self.list_page)
            self.block.show_block(self._models, self._availability)
            self._show_list(state)
            return
        self.block.setVisible(False)
        self.stack.setCurrentWidget(self.detail_page)
        self._show_detail(view, had_focus=had_focus)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_list(self, state: ProjectsState) -> None:
        view = build_list_view(state)
        self.summary.setText(view.summary)
        self.import_button.setEnabled(view.import_enabled)
        signature = (view.rows, view.row_actions_enabled)
        if signature == self._row_signature:
            return
        self._row_signature = signature
        for widget in self._rows:
            self.rows_box.removeWidget(widget)
            widget.hide()  # a deleted widget is still painted until the loop runs
            widget.setParent(None)
            widget.deleteLater()
        self._rows = []
        for row in view.rows:
            widget = ProjectRowWidget(row, view.row_actions_enabled)
            widget.open_requested.connect(self._controller.open_project)
            widget.delete_requested.connect(self._delete)
            self.rows_box.addWidget(widget)
            widget.show()
            self._rows.append(widget)

    def _show_detail(self, view: ProjectDetailView, *, had_focus: bool) -> None:
        self._detail_title = view.title
        self.detail_title_label.setText(view.title)
        self.state_line.setText(view.state_line)
        self.facts.setText("\n".join(view.facts))
        self.facts.setVisible(bool(view.facts))
        self.back_button.setEnabled(not self._controller.state.busy)

        choosing = bool(view.column_choices)
        self.column_box.setVisible(choosing)
        wanted = [COLUMN_PLACEHOLDER, *view.column_choices]
        if (
            choosing
            and [
                self.column_combo.itemText(i) for i in range(self.column_combo.count())
            ]
            != wanted
        ):
            self.column_combo.clear()
            self.column_combo.addItems(wanted)  # an explicit choice, never a default
        self.column_combo.setEnabled(view.choose_enabled)
        self._sync_choose_button()

        self.detail_block.show_block(self._models, self._availability)
        self.detail_block.setVisible(view.block is not None)

        self.review_button.setVisible(view.show_review)
        self.review_button.setEnabled(view.review_enabled)
        self.insights_button.setVisible(view.show_insights)
        self.insights_button.setEnabled(view.insights_enabled)
        self.analyze_button.setVisible(view.show_analyze)
        self.analyze_button.setText(view.analyze_label)
        self.analyze_button.setAccessibleName(view.analyze_label)
        self.analyze_button.setEnabled(view.analyze_enabled)
        self.analyze_button.setAccessibleDescription(
            view.block.body if view.block is not None else ""
        )

        was_running = self.progress.isVisible()
        if view.progress is not None:
            self.progress.setVisible(True)
            self.progress.show_progress(view.progress)
            if not was_running and had_focus:
                self.progress.cancel_button.setFocus()
        else:
            self.progress.setVisible(False)
            self.progress.reset()
            if was_running and had_focus:
                self.detail_title_label.setFocus()
        self.delete_button.setEnabled(view.delete_enabled)
        self.delete_button.setAccessibleName("Delete this project")

    # -- review -------------------------------------------------------------

    def _open_review(self) -> None:
        current = self._controller.state.current
        if current is not None:
            self._reviews.open(current.summary.project_id)

    def _on_review(self, state: ReviewState) -> None:
        """Show the review while it is open; on leaving it, re-read the project."""

        if state.active:
            self._review_was_active = True
            self.block.setVisible(False)
            self.stack.setCurrentWidget(self.review_page)
            return
        if not self._review_was_active:
            return
        self._review_was_active = False
        notice = state.notice
        # the review changed the project, or the project may be gone
        if not self._controller.reload_current(notice):
            self.show_state(self._controller.state)

    # -- insights -----------------------------------------------------------

    def _open_insights(self) -> None:
        current = self._controller.state.current
        if current is not None:
            self._insights.open(current.summary.project_id)

    def _on_insights(self, state: InsightsState) -> None:
        """Show the insights while they are open; on leaving, re-read the project."""

        if state.active:
            self._insights_was_active = True
            self.block.setVisible(False)
            self.stack.setCurrentWidget(self.insights_page)
            return
        if not self._insights_was_active:
            return
        self._insights_was_active = False
        if self._reviews.state.active:
            return  # leaving for the review: it reloads the project when it closes
        # the project may be gone, or the notice explains why we came back
        if not self._controller.reload_current(state.notice):
            self.show_state(self._controller.state)

    def _open_in_review(self, row: int) -> None:
        """Open a case in Review: the review opens first so the page never flashes."""

        project_id = self._insights.state.project_id
        if project_id is not None and self._reviews.open(project_id, row=row):
            self._insights.close()  # the note, if any, was confirmed as discarded

    # -- actions ------------------------------------------------------------

    def _import(self) -> None:
        path = self._platform.pick_csv(self)
        if path is not None:
            self._controller.import_csv(path)

    def _sync_choose_button(self) -> None:
        picked = self.column_combo.currentIndex() > 0
        self.choose_button.setEnabled(
            picked
            and not self._controller.state.busy
            and self.column_box.isVisibleTo(self)
        )

    def _choose_column(self) -> None:
        if self.column_combo.currentIndex() > 0:
            self._controller.choose_column(self.column_combo.currentText())

    def _delete_current(self) -> None:
        current = self._controller.state.current
        if current is not None:
            self._confirm_delete(current.summary.project_id, self._detail_title)

    def _delete(self, project_id: str) -> None:
        title = "this project"
        for summary in self._controller.state.projects:
            if summary.project_id == project_id:
                title = row_view(summary).title
        self._confirm_delete(project_id, title)

    def _confirm_delete(self, project_id: str, title: str) -> None:
        heading, text = delete_confirmation(title)
        if self._platform.confirm(self, heading, text):
            self._controller.delete(project_id)
