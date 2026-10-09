"""The project workspace: the list, and the six fixed pages of one open project.

The start window is the project list. An open project has Import & validation,
Results, Review, Agreement, and the two insight views; the sidebar chooses between
them and this page shows the chosen one, loading what it needs. Nothing here holds a
rule: each page renders a controller's state.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
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
from .components import (
    BarMeter,
    Card,
    Combo,
    DataTable,
    EmptyState,
    Figure,
    FlowRow,
    Page,
    PageHeader,
    SegmentedFilter,
    SplitRow,
    ViewportWatcher,
    chip,
    rule,
)
from .insights_page import InsightsPage
from .pages import AnalysisBlockBox
from .platform import DesktopPlatform
from .results_page import ResultsPage
from .review_page import ReviewPage
from .widgets import LanguageBox, NoticeBox, add_all, announce, frame, label

COLUMN_PLACEHOLDER = "Choose a column…"
COMPACT_ROWS_BELOW = (
    760  # page width under which a project's progress sits under its name
)
PROBLEM_COLUMNS = (("Row", 60), ("Record ID", 140), ("Reason", 200))
PREVIEW_COLUMNS = (("Row", 52), ("Record ID", 100), ("Text", 260), ("Check", 240))


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
    """One project line: name, size, review progress, then Open and Delete."""

    open_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(
        self,
        row: ProjectRowView,
        enabled: bool,
        parent: QWidget | None = None,
        *,
        primary: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "plain")
        self.setAccessibleName(row.accessible_name)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        box = QWidget()
        box.setProperty("role", "plain")
        self._inner = QHBoxLayout(box)
        self._inner.setContentsMargins(18, 14, 18, 14)
        self._inner.setSpacing(18)
        self._text = QVBoxLayout()
        self._text.setSpacing(2)
        self._text.addWidget(label(row.title, role="title"))
        self._text.addWidget(label(row.subtitle, role="subtitle"))
        self.rows_label = label(row.rows_line, role="mono")
        self.rows_label.setObjectName("project-rows")
        self.rows_label.setVisible(bool(row.rows_line))
        self._text.addWidget(self.rows_label)
        self._inner.addLayout(self._text, 1)
        # the review progress: a thin meter and the words that carry its numbers
        self.progress = QWidget()
        self.progress.setProperty("role", "plain")
        self.progress.setFixedWidth(240)
        progress = QVBoxLayout(self.progress)
        progress.setContentsMargins(0, 0, 0, 0)
        progress.setSpacing(2)
        self.meter = BarMeter(row.review_fraction, "ink")
        self.meter.setObjectName("project-meter")
        self.meter.setAccessibleName(row.review_line)
        self.review_label = label(row.review_line, role="mono")
        self.review_label.setObjectName("project-review")
        progress.addWidget(self.meter)
        progress.addWidget(self.review_label)
        self.progress.setVisible(bool(row.review_line))
        self._compact: bool | None = None
        self.open_button = QPushButton("Open")
        self.open_button.setAccessibleName(f"Open {row.title}")
        self.open_button.setEnabled(enabled and row.can_open)
        self.open_button.setVisible(row.can_open)
        self.open_button.setProperty("primary", primary and row.can_open)
        self.delete_button = QPushButton("Delete…")
        self.delete_button.setAccessibleName(f"Delete {row.title}")
        self.delete_button.setProperty("danger", True)
        self.delete_button.setProperty("ghost", True)
        self.delete_button.setEnabled(enabled)
        self.open_button.clicked.connect(
            lambda: self.open_requested.emit(row.project_id)
        )
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(row.project_id)
        )
        self._buttons = QHBoxLayout()
        self._buttons.setSpacing(8)
        self._buttons.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._buttons.addWidget(self.delete_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._inner.addLayout(self._buttons)
        outer.addWidget(box)
        self.rule = rule()
        outer.addWidget(self.rule)
        self.set_compact(False)

    def set_compact(self, compact: bool) -> None:
        """Wide: progress between the name and the buttons. Narrow: under the name."""

        if compact == self._compact:
            return
        self._compact = compact
        self._inner.removeWidget(self.progress)
        self._text.removeWidget(self.progress)
        if compact:
            self.progress.setFixedWidth(16_777_215)
            self.progress.setMinimumWidth(0)
            self._text.addWidget(self.progress)
        else:
            self.progress.setFixedWidth(240)
            self._inner.insertWidget(1, self.progress, 0, Qt.AlignmentFlag.AlignVCenter)


class ProjectsPage(QWidget):
    open_models = Signal()
    analyze_text_requested = Signal()
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
        self._review_filter = "all"
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
        self._list_watcher = ViewportWatcher(
            self, self._reflow_rows, area=self.list_page.scroller
        )
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
        self.analyze_text_button = QPushButton("Analyze one text")
        self.analyze_text_button.setObjectName("projects-analyze-text")
        self.analyze_text_button.setAccessibleName("Analyze one text, unsaved")
        self.analyze_text_button.clicked.connect(self.analyze_text_requested.emit)
        self.header.add_action(self.analyze_text_button)
        self.header.add_action(self.import_button)
        self.summary = self.header.subtitle
        self.summary.setObjectName("projects-summary")
        self.review_tabs = SegmentedFilter(noun="projects")
        self.review_tabs.setObjectName("projects-review-tabs")
        self.review_tabs.setAccessibleName("Review state filter")
        self.review_tabs.selected.connect(self._review_filter_chosen)
        self.review_tabs.setVisible(False)
        self.rows_card = frame("card")
        self.rows_card.setObjectName("projects-card")
        self.rows_box = QVBoxLayout(self.rows_card)
        self.rows_box.setContentsMargins(0, 0, 0, 0)
        self.rows_box.setSpacing(0)
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
        add_all(self.list_page.body, self.header, self.review_tabs)
        self.list_page.body.addWidget(self.rows_card)
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
        self.figure_ready = Figure("ready to analyse")
        self.figure_ready.setObjectName("figure-ready")
        self.figure_rejected = Figure("rejected at import", "negative")
        self.figure_rejected.setObjectName("figure-rejected")
        self.figure_language = Figure("not confirmed as English", "caution")
        self.figure_language.setObjectName("figure-language")
        figures = QHBoxLayout()
        figures.setSpacing(18)
        for figure in (self.figure_ready, self.figure_rejected, self.figure_language):
            figures.addWidget(figure, 1)
        self.metadata_caption = label("RECOGNISED METADATA COLUMNS", role="eyebrow")
        self.metadata_row = FlowRow()
        self.metadata_row.setObjectName("metadata-columns")
        self.metadata_note = label(
            "Groups in Insights come only from these columns. Nothing is inferred.",
            role="muted",
        )
        self._metadata_signature: object = None
        self.facts_card.layout_.addLayout(figures)
        add_all(self.facts_card.layout_, self.facts, self.ignored)
        add_all(
            self.facts_card.layout_,
            self.metadata_caption,
            self.metadata_row,
            self.metadata_note,
        )
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

        # every imported row with its check, as a scrolling table (a bounded
        # excerpt of each text, never the whole text)
        self.preview_card = Card("ROW PREVIEW · VALIDATION")
        self.all_ready = label(role="muted")
        self.all_ready.setObjectName("all-ready")
        self.preview_tabs = SegmentedFilter(noun="rows")
        self.preview_tabs.setObjectName("preview-tabs")
        self.preview_tabs.setAccessibleName("Rows to show")
        self.preview_tabs.selected.connect(self._preview_filter_chosen)
        self._preview_filter = "all"
        self.preview_table = DataTable()
        self.preview_table.setObjectName("preview-table")
        self.preview_table.setAccessibleName("Imported rows and their checks")
        self.preview_table.tone_column = 3
        self.preview_table.set_columns(
            [name for name, _ in PREVIEW_COLUMNS], [w for _, w in PREVIEW_COLUMNS]
        )
        self.preview_table.fit_rows(1)
        add_all(self.preview_card.layout_, self.all_ready)
        self.preview_card.layout_.addWidget(
            self.preview_tabs, 0, Qt.AlignmentFlag.AlignLeft
        )
        self.preview_card.add(self.preview_table)
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
        results_column = QWidget()
        results_column.setProperty("role", "plain")
        column_layout_right = QVBoxLayout(results_column)
        column_layout_right.setContentsMargins(0, 0, 0, 0)
        column_layout_right.setSpacing(16)
        add_all(
            column_layout_right,
            self.language_box,
            self.preview_card,
            self.failures_card,
        )
        column_layout_right.addStretch(1)
        self.detail_split = SplitRow(
            self.facts_card, results_column, side_width=360, stack_below=860
        )
        self.detail_page.body.addWidget(self.detail_split)
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

    # -- the project list ---------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._list_watcher.attach()
        self._reflow_rows()

    def _compact_rows(self) -> bool:
        """Under the width where name, progress and buttons share one line."""

        return self._list_watcher.available() < COMPACT_ROWS_BELOW

    def _reflow_rows(self) -> None:
        compact = self._compact_rows()
        for row in self._rows:
            row.set_compact(compact)

    def _preview_filter_chosen(self, value: str) -> None:
        self._preview_filter = value
        self._problem_signature = None
        self._show_problems(self._results.state)

    def _review_filter_chosen(self, value: str) -> None:
        self._review_filter = value
        self._row_signature = None
        self._show_list(self._controller.state)

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
        view = build_list_view(state, self._review_filter)
        listed_any = bool(view.tabs)
        self.header.set_subtitle(view.summary if view.rows or listed_any else "")
        self.import_button.setEnabled(view.import_enabled)
        empty = not listed_any and state.listed and not state.list_failed
        self.empty_list.setVisible(empty)
        self.review_tabs.setVisible(listed_any)
        if listed_any:
            self.review_tabs.set_options(view.tabs, view.selected_filter)
        self.rows_card.setVisible(bool(view.rows))
        self.note.setVisible(listed_any)
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
        for position, row in enumerate(view.rows):
            widget = ProjectRowWidget(
                row, view.row_actions_enabled, primary=position == 0
            )
            widget.open_requested.connect(self._controller.open_project)
            widget.delete_requested.connect(self._delete)
            widget.set_compact(self._compact_rows())
            self.rows_box.addWidget(widget)
            widget.show()
            self._rows.append(widget)
        if self._rows:
            self._rows[-1].rule.setVisible(False)

    def _show_detail(self, view: ProjectDetailView, *, had_focus: bool) -> None:
        self._detail_title = view.title
        self.detail_title_label.setText(view.title)
        self.state_line.setText(view.state_line)
        self.facts.setText("\n".join(view.facts))
        self.facts_card.setVisible(bool(view.facts))
        self._show_figures(view)
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

    def _show_figures(self, view: ProjectDetailView) -> None:
        figures = (
            (self.figure_ready, view.ready_count),
            (self.figure_rejected, view.rejected_count),
            (self.figure_language, view.language_count),
        )
        for figure, count in figures:
            figure.setVisible(count is not None)
            if count is not None:
                figure.set_value(str(count))
        shown = bool(view.metadata)
        self.metadata_caption.setVisible(shown)
        self.metadata_row.setVisible(shown)
        self.metadata_note.setVisible(shown)
        if view.metadata == self._metadata_signature:
            return
        self._metadata_signature = view.metadata
        flow = self.metadata_row.flow
        while flow.count():
            item = flow.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        for name, present in view.metadata:
            text = name if present else f"{name} — not in file"
            piece = chip(text, "human" if present else "neutral")
            piece.setAccessibleName(
                f"{name} column, {'in the file' if present else 'not in the file'}"
            )
            self.metadata_row.add(piece)
            piece.show()

    def _show_problems(self, state: ResultsState) -> None:
        view = build_validation_view(state)
        shown = view is not None
        self.preview_card.setVisible(shown)
        self.failures_card.setVisible(
            shown and view is not None and bool(view.failures)
        )
        if view is None or not shown:
            return
        signature = (
            view.preview,
            view.failures,
            view.all_ready_line,
            view.ignored_line,
            self._preview_filter,
        )
        self.ignored.setText(view.ignored_line)
        self.ignored.setVisible(bool(view.ignored_line))
        if signature == self._problem_signature:
            return
        self._problem_signature = signature
        self.all_ready.setText(view.all_ready_line)
        self.all_ready.setVisible(bool(view.all_ready_line))
        self.preview_tabs.set_options(view.preview_tabs, self._preview_filter)
        shown_rows = [
            item
            for item in view.preview
            if self._preview_filter == "all" or item.rejected
        ]
        self.preview_table.set_rows(
            [
                (
                    str(item.row),
                    item.record_id,
                    item.text,
                    item.check + (f" · {item.reason}" if item.reason else ""),
                )
                for item in shown_rows
            ],
            failed=[item.rejected for item in shown_rows],
            names=[item.accessible_name for item in shown_rows],
        )
        self.preview_table.fit_rows(len(shown_rows), cap=12)
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
