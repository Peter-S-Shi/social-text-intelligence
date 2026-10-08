"""The project workspace: the list, and the six fixed pages of one open project.

The start window is the project list. An open project has Import & validation,
Results, Review, Agreement, and the two insight views; the sidebar chooses between
them and this page shows the chosen one, loading what it needs. Nothing here holds a
rule: each page renders a controller's state.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...application.model_provisioning import ModelsStatus
from ...application.project_workflow import ProjectDetails, ProjectPhase
from ..agreement import AgreementController, AgreementState
from ..gate import AnalysisAvailability
from ..insights import InsightsController, InsightsState
from ..navigation import (
    INSIGHT_SECTIONS,
    Section,
    default_section,
)
from ..projects import ProjectsController, ProjectsNotice, ProjectsState
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
from ..results import ResultsController, ResultsState
from ..results_view import build_validation_view
from ..review import ReviewController, ReviewState
from .agreement_page import AgreementPage
from .components import Card, Combo, DataTable, EmptyState, Page, PageHeader
from .insights_page import InsightsPage
from .pages import AnalysisBlockBox
from .platform import DesktopPlatform
from .results_page import ResultsPage
from .review_page import ReviewPage
from .widgets import LanguageBox, NoticeBox, add_all, announce, frame, label

COLUMN_PLACEHOLDER = "Choose a column…"
PROBLEM_COLUMNS = (("Row", 60), ("Record ID", 150), ("Reason", 520))


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
        layout.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignLeft)
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
        inner = QHBoxLayout(box)
        inner.setContentsMargins(16, 12, 16, 12)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(row.title, role="title"))
        text.addWidget(label(row.subtitle, role="subtitle"))
        inner.addLayout(text, 1)
        self.open_button = QPushButton("Open")
        self.open_button.setAccessibleName(f"Open {row.title}")
        self.open_button.setEnabled(enabled and row.can_open)
        self.open_button.setVisible(row.can_open)
        self.open_button.setProperty("primary", row.can_open)
        self.delete_button = QPushButton("Delete…")
        self.delete_button.setAccessibleName(f"Delete {row.title}")
        self.delete_button.setProperty("danger", True)
        self.delete_button.setEnabled(enabled)
        self.open_button.clicked.connect(
            lambda: self.open_requested.emit(row.project_id)
        )
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(row.project_id)
        )
        inner.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignVCenter)
        inner.addWidget(self.delete_button, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(box)


class ProjectsPage(QWidget):
    open_models = Signal()
    section_changed = Signal(object)  # the Section now shown

    def __init__(
        self,
        controller: ProjectsController,
        reviews: ReviewController,
        insights: InsightsController,
        results: ResultsController,
        agreement: AgreementController,
        platform: DesktopPlatform,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._reviews = reviews
        self._insights = insights
        self._results = results
        self._agreement = agreement
        self._platform = platform
        self._models = ModelsStatus(())
        self._availability = AnalysisAvailability.AVAILABLE
        self._other_analysis_running = False
        self._row_signature: object = None
        self._rows: list[ProjectRowWidget] = []
        self._detail_title = ""
        self._section = Section.PROJECTS
        self._last_phase: ProjectPhase | None = None
        self._results_signature: object = None
        self._problem_signature: object = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.block = AnalysisBlockBox(quiet=True)
        self.block.triggered.connect(lambda _: self.open_models.emit())
        self.notice = NoticeBox()
        self.notice.setVisible(False)
        self.stack = QStackedWidget()
        banner = QWidget()
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(28, 14, 28, 0)
        add_all(banner_layout, self.notice, self.block)
        self._banner = banner
        layout.addWidget(banner)
        layout.addWidget(self.stack, 1)

        self._build_list_page()
        self._build_detail_page()
        self.results_page = ResultsPage(results, platform)
        self.results_page.review_requested.connect(self._open_in_review)
        self.results_page.import_requested.connect(
            lambda: self.show_section(Section.IMPORT)
        )
        self.review_page = ReviewPage(reviews, platform)
        self.agreement_page = AgreementPage(agreement, platform)
        self.insights_page = InsightsPage(insights, platform)
        self.insights_page.review_requested.connect(self._open_in_review)
        for page in (
            self.results_page,
            self.review_page,
            self.agreement_page,
            self.insights_page,
        ):
            self.stack.addWidget(page)
        self._pages: dict[Section, QWidget] = {
            Section.PROJECTS: self.list_page,
            Section.IMPORT: self.detail_page,
            Section.RESULTS: self.results_page,
            Section.REVIEW: self.review_page,
            Section.AGREEMENT: self.agreement_page,
            Section.COMPARE: self.insights_page,
            Section.NOTES: self.insights_page,
        }

        controller.subscribe(self.show_state)
        results.subscribe(self._on_results)
        reviews.subscribe(self._on_review)
        insights.subscribe(self._on_insights)
        agreement.subscribe(self._on_agreement)
        self.show_state(controller.state)

    # -- construction -------------------------------------------------------

    def _build_list_page(self) -> None:
        self.list_page = Page()
        self.list_page.setObjectName("projects-list")
        self.header = PageHeader("Projects")
        self.heading = self.header.title
        self.import_button = QPushButton(IMPORT_LABEL)
        self.import_button.setObjectName("import-csv")
        self.import_button.setProperty("primary", True)
        self.import_button.setAccessibleName("Import a CSV file as a new project")
        self.import_button.clicked.connect(self._import)
        self.header.add_action(self.import_button)
        self.summary = self.header.subtitle
        self.summary.setObjectName("projects-summary")
        self.rows_box = QVBoxLayout()
        self.rows_box.setSpacing(10)
        self.empty_list = EmptyState(
            "No projects yet",
            "A project is one imported CSV and everything derived from it. Import "
            "a CSV to start one.",
        )
        self.empty_list.setObjectName("projects-empty")
        self.note = label(
            "A project is one imported CSV and everything derived from it. It "
            "stays on this computer until you delete it.",
            role="muted",
        )
        add_all(self.list_page.body, self.header)
        self.list_page.body.addLayout(self.rows_box)
        add_all(self.list_page.body, self.empty_list, self.note)
        self.list_page.body.addStretch(1)
        self.stack.addWidget(self.list_page)

    def _build_detail_page(self) -> None:
        self.detail_page = Page()
        self.detail_page.setObjectName("project-import")
        self.detail_header = PageHeader("Import & validation")
        self.detail_title_label = self.detail_header.title
        self.detail_title_label.setObjectName("project-title")
        self.state_line = self.detail_header.subtitle
        self.state_line.setObjectName("project-state")
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("project-analyze")
        self.analyze_button.setProperty("primary", True)
        self.analyze_button.clicked.connect(self._controller.analyze)
        self.delete_button = QPushButton("Delete project…")
        self.delete_button.setObjectName("project-delete")
        self.delete_button.setProperty("danger", True)
        self.delete_button.clicked.connect(self._delete_current)
        self.detail_header.add_action(self.analyze_button)
        self.detail_header.add_action(self.delete_button)

        self.project_name = label(role="eyebrow")
        self.project_name.setObjectName("project-name")
        self.facts = label()
        self.facts.setObjectName("project-facts")
        self.ignored = label(role="muted")
        self.ignored.setObjectName("project-ignored")
        self.facts_card = Card("THIS CSV")
        add_all(self.facts_card.layout_, self.facts, self.ignored)
        self.language_box = LanguageBox("project-language")
        self.column_box = frame("panel")
        self.column_box.setObjectName("column-step")
        column_layout = QVBoxLayout(self.column_box)
        column_layout.addWidget(label("Which column holds the text?", role="title"))
        self.column_combo = Combo()
        self.column_combo.setObjectName("column-combo")
        self.column_combo.setAccessibleName("Text column")
        self.choose_button = QPushButton("Use this column")
        self.choose_button.setObjectName("choose-column")
        self.choose_button.setProperty("primary", True)
        self.choose_button.clicked.connect(self._choose_column)
        self.column_combo.currentIndexChanged.connect(
            lambda _: self._sync_choose_button()
        )
        column_layout.addWidget(self.column_combo)
        column_layout.addWidget(self.choose_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.detail_block = AnalysisBlockBox()
        self.detail_block.triggered.connect(lambda _: self.open_models.emit())
        self.progress = RowProgress()
        self.progress.setVisible(False)
        self.progress.cancel_requested.connect(self._controller.cancel)

        self.problems_card = Card("ROWS REJECTED AT IMPORT")
        self.all_ready = label(role="muted")
        self.all_ready.setObjectName("all-ready")
        self.problems_table = self._problem_table(
            "problems-table", "Rows with problems"
        )
        add_all(self.problems_card.layout_, self.all_ready, self.problems_table)
        self.failures_card = Card("ROWS THAT FAILED IN ANALYSIS")
        self.failures_table = self._problem_table(
            "failures-table", "Rows that failed in analysis"
        )
        self.failures_card.add(self.failures_table)
        self.failures_card.add(
            label(
                "A failed row is kept with its reason; it does not change the counts "
                "of the rows that were analysed.",
                role="muted",
            )
        )
        add_all(self.detail_page.body, self.detail_header, self.detail_block)
        add_all(self.detail_page.body, self.column_box, self.progress)
        add_all(self.detail_page.body, self.facts_card, self.language_box)
        add_all(self.detail_page.body, self.problems_card, self.failures_card)
        self.detail_page.body.addStretch(1)
        self.stack.addWidget(self.detail_page)

    @staticmethod
    def _problem_table(name: str, accessible: str) -> DataTable:
        table = DataTable()
        table.setObjectName(name)
        table.setAccessibleName(accessible)
        table.set_columns(
            [c for c, _ in PROBLEM_COLUMNS], [w for _, w in PROBLEM_COLUMNS]
        )
        table.fit_rows(1)
        return table

    # -- inputs from the shell ----------------------------------------------

    @property
    def section(self) -> Section:
        return self._section

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

    # -- navigation ---------------------------------------------------------

    def show_section(self, section: Section) -> bool:
        """Show a page of the open project, loading what it needs.

        Callers have already confirmed that any unsaved work may be dropped.
        """

        current = self._controller.state.current
        if section is Section.PROJECTS or current is None:
            return False
        project_id = current.summary.project_id
        previous = self._section
        self._section = section
        if section is Section.REVIEW:
            self._open_review(project_id)
        elif section is Section.AGREEMENT:
            self._agreement.open(project_id)
        elif section in INSIGHT_SECTIONS:
            if previous not in INSIGHT_SECTIONS or self._insights.state.project_id != (
                project_id
            ):
                self._insights.open(project_id)
            self.insights_page.show_view(0 if section is Section.COMPARE else 1)
        self._show_page()
        return True

    def leave_project(self) -> bool:
        """Close the open project and show the list; False if work is running."""

        state = self._controller.state
        if state.busy or any(
            c.state.busy
            for c in (self._reviews, self._insights, self._results, self._agreement)
        ):
            return False
        self._section = Section.PROJECTS  # first, so closing is not read as a loss
        self._reviews.close()
        self._insights.close()
        self._results.close()
        self._agreement.close()
        self._results_signature = None
        self._last_phase = None
        self._controller.close_project()
        self._show_page()
        return True

    def _open_review(self, project_id: str, row: int | None = None) -> bool:
        same = self._reviews.state.project_id == project_id
        snapshot = self._reviews.state.snapshot
        record = snapshot.record if snapshot is not None else None
        filters = self._reviews.state.filters if same else None
        keep = record.row_number if (row is None and same and record) else row
        return self._reviews.open(project_id, filters, row=keep)

    def _open_in_review(self, row: int) -> None:
        """Open one record in Review (from Results or a representative case)."""

        current = self._controller.state.current
        if current is None:
            return
        project_id = current.summary.project_id
        if self._open_review(project_id, row):
            self._insights.close()  # a note, if any, was confirmed as discarded
            self._section = Section.REVIEW
            self._show_page()

    def _show_page(self) -> None:
        page = self._pages[self._section]
        self.stack.setCurrentWidget(page)
        self._banner.setVisible(self._section in (Section.PROJECTS, Section.IMPORT))
        self.section_changed.emit(self._section)

    # -- rendering ----------------------------------------------------------

    def show_state(self, state: ProjectsState) -> None:
        had_focus = self._has_focus()
        self.notice.show_notice(state.notice)
        details = state.current
        view = build_detail_view(
            state,
            self._availability,
            self._models,
            other_analysis_running=self._other_analysis_running,
        )
        if view is None or details is None:
            self._project_closed(state)
            return
        self.block.setVisible(False)
        phase = details.phase
        if self._section is Section.PROJECTS:
            self._section = default_section(details)
        elif (
            self._section is Section.IMPORT
            and phase is ProjectPhase.ANALYZED
            and self._last_phase is not ProjectPhase.ANALYZED
            and self._last_phase is not None
        ):
            self._section = Section.RESULTS  # the analysis just finished
        self._last_phase = phase
        self._sync_results(details)
        self._show_detail(view, had_focus=had_focus)
        self._show_page()

    def _project_closed(self, state: ProjectsState) -> None:
        was_open = self._section is not Section.PROJECTS
        self._section = Section.PROJECTS
        self._last_phase = None
        if was_open:  # the project went away under us: release its pages
            for controller in (
                self._reviews,
                self._insights,
                self._results,
                self._agreement,
            ):
                controller.close()
            self._results_signature = None
        self.block.show_block(self._models, self._availability)
        self._show_list(state)
        self._show_page()

    def _sync_results(self, details: ProjectDetails) -> None:
        signature = (
            details.summary.project_id,
            details.phase,
            details.analyzed_rows,
            details.failed_rows,
            details.invalid_rows,
        )
        if signature == self._results_signature:
            return
        self._results_signature = signature
        project_id = details.summary.project_id

        def load() -> None:
            self._results.open(project_id)

        self._results.when_idle(load)

    def _has_focus(self) -> bool:
        focused = self.window().focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_list(self, state: ProjectsState) -> None:
        view = build_list_view(state)
        self.header.set_subtitle(view.summary if view.rows else "")
        self.import_button.setEnabled(view.import_enabled)
        empty = not view.rows and state.listed and not state.list_failed
        self.empty_list.setVisible(empty)
        self.note.setVisible(bool(view.rows))
        if not view.rows and not empty:
            self.header.set_subtitle(view.summary)
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
        self.facts_card.setVisible(bool(view.facts))
        self.language_box.show_language(
            view.language_headline, view.language_detail, view.language_warns
        )

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
        self._show_problems(self._results.state)

    def _show_problems(self, state: ResultsState) -> None:
        view = build_validation_view(state)
        shown = view is not None and not self._controller.state.busy
        self.problems_card.setVisible(shown)
        self.failures_card.setVisible(
            shown and view is not None and bool(view.failures)
        )
        if view is None or not shown:
            return
        signature = (
            view.problems,
            view.failures,
            view.all_ready_line,
            view.ignored_line,
        )
        self.ignored.setText(view.ignored_line)
        self.ignored.setVisible(bool(view.ignored_line))
        if signature == self._problem_signature:
            return
        self._problem_signature = signature
        self.all_ready.setText(view.all_ready_line)
        self.all_ready.setVisible(bool(view.all_ready_line))
        self.problems_table.setVisible(bool(view.problems))
        self.problems_table.set_rows(
            [(str(p.row), p.record_id, p.reason) for p in view.problems]
        )
        self.problems_table.fit_rows(len(view.problems), cap=10)
        self.failures_table.set_rows(
            [(str(p.row), p.record_id, p.reason) for p in view.failures]
        )
        self.failures_table.fit_rows(len(view.failures), cap=10)

    # -- controllers that can end underneath a page ------------------------

    def _on_results(self, state: ResultsState) -> None:
        self._show_problems(state)
        if not state.active and self._section in (Section.IMPORT, Section.RESULTS):
            self._lost(state.notice)

    def _on_review(self, state: ReviewState) -> None:
        if not state.active and self._section is Section.REVIEW:
            self._lost(state.notice)

    def _on_insights(self, state: InsightsState) -> None:
        if not state.active and self._section in INSIGHT_SECTIONS:
            self._lost(state.notice)

    def _on_agreement(self, state: AgreementState) -> None:
        if not state.active and self._section is Section.AGREEMENT:
            self._lost(state.notice)

    def _lost(self, notice: object) -> None:
        """A page's data went away (the project may be gone): re-read the project."""

        shown = notice if isinstance(notice, ProjectsNotice) else None
        if not self._controller.reload_current(shown):
            self.show_state(self._controller.state)

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
