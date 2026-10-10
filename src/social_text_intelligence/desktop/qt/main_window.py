"""The shell: a project-centred sidebar with persistent Models status, and the pages.

The sidebar has the open project's six fixed pages (when a project is open), the Start
area (the project list and unsaved single-text analysis), and the Models status at the
foot. A page that cannot be used yet is shown, disabled, with its reason. Leaving a page
with unsaved work always asks first; confirming discards that work explicitly.
"""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..agreement import AgreementController
from ..analysis import AnalysisPageController, AnalysisPageState
from ..composition import (
    DesktopServices,
    build_agreement_controller,
    build_analysis_controller,
    build_insights_controller,
    build_projects_controller,
    build_provisioning_controller,
    build_results_controller,
    build_review_controller,
)
from ..controller import (
    Activity,
    ControllerState,
    JobRunner,
    ProvisioningController,
)
from ..insights import InsightsController, InsightsState
from ..navigation import (
    INSIGHT_SECTIONS,
    LABELS,
    PROJECT_SECTIONS,
    START_SECTIONS,
    NavItem,
    NavView,
    Section,
    build_navigation,
)
from ..panel import build_sidebar_status
from ..projects import ProjectsActivity, ProjectsState
from ..results import ResultsController
from ..review import ReviewController, ReviewState
from .components import NavButton, rule
from .pages import AnalyzePage
from .platform import DesktopPlatform
from .projects_page import ProjectsPage
from .provisioning_ui import ProvisioningUi
from .widgets import add_all, announce, frame, label

APP_TITLE = "Social Text Intelligence"
SIDEBAR_WIDTH = 264
LEAVE_PAGE_TEXT = (
    "You have unsaved changes to a review. Leave this page and discard them?"
)
CLOSE_WINDOW_TEXT = "You have unsaved changes to a review. Close without saving them?"
LEAVE_NOTE_TEXT = (
    "You have a context note that is not saved. Leave this page and discard it?"
)
CLOSE_NOTE_TEXT = "You have a context note that is not saved. Close without saving it?"


class MainWindow(QMainWindow):
    def __init__(
        self,
        services: DesktopServices,
        runner: JobRunner,
        platform: DesktopPlatform | None = None,
    ) -> None:
        super().__init__()
        self.services = services
        self.runner = runner
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(900, 620)
        self.provisioning: ProvisioningController = build_provisioning_controller(
            services, runner
        )
        self.analysis: AnalysisPageController = build_analysis_controller(
            services, runner
        )
        self.projects = build_projects_controller(services, runner)
        self.review: ReviewController = build_review_controller(services, runner)
        self.insights: InsightsController = build_insights_controller(services, runner)
        self.results: ResultsController = build_results_controller(services, runner)
        self.agreement: AgreementController = build_agreement_controller(
            services, runner
        )
        platform = platform or DesktopPlatform()
        self._platform = platform
        self._closing = False

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_buttons: dict[str, NavButton] = {}
        self._section_buttons: dict[Section, NavButton] = {}
        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.projects_page = ProjectsPage(
            self.projects,
            self.review,
            self.insights,
            self.results,
            self.agreement,
            platform,
        )
        self.analyze_page = AnalyzePage()
        self.pages.addWidget(self.projects_page)
        self.pages.addWidget(self.analyze_page)
        layout.addWidget(self.pages, 1)

        self.ui = ProvisioningUi(
            self.provisioning,
            services.gate,
            lambda: services.provisioning.models_root,
            platform,
            self,
            lambda text: self.statusBar().showMessage(text, 8000),
        )

        self.models_button.clicked.connect(self.ui.show_models)
        self.projects_page.open_models.connect(self.ui.show_models)
        self.projects_page.analyze_text_requested.connect(
            lambda: self._open_section(Section.ANALYZE)
        )
        self.projects_page.section_changed.connect(self._on_section)
        self.projects_page.review_page.agreement_requested.connect(
            lambda: self._open_section(Section.AGREEMENT)
        )
        self.analyze_page.open_models.connect(self.ui.show_models)
        self.analyze_page.verify_requested.connect(self._verify_from_analysis)
        self.analyze_page.analyze_requested.connect(self.analysis.submit)

        self.provisioning.subscribe(self._on_provisioning)
        self.analysis.subscribe(self._on_analysis)
        self.projects.subscribe(self._on_projects)
        self.review.subscribe(self._on_review)
        self.insights.subscribe(self._on_insights)
        self.results.subscribe(self._on_idle_check)
        self.agreement.subscribe(self._on_idle_check)
        self._last_announced = ""
        self._navigation = build_navigation(self.projects.state)
        self._apply_navigation(self._navigation)
        self._sync_checked()

    # -- construction -------------------------------------------------------

    def _build_sidebar(self) -> QFrame:
        sidebar = frame("panel")
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 18, 0, 14)
        side.setSpacing(2)
        title = label(APP_TITLE, role="brand")
        title.setContentsMargins(18, 0, 16, 10)
        side.addWidget(title)
        self.no_project = QWidget()
        idle = QVBoxLayout(self.no_project)
        idle.setContentsMargins(0, 0, 0, 0)
        idle.setSpacing(0)
        idle_title = label("No project open", role="project")
        idle_title.setContentsMargins(18, 6, 16, 0)
        idle_hint = label("open one from Projects", role="mono")
        idle_hint.setContentsMargins(18, 0, 16, 8)
        add_all(idle, rule(), idle_title, idle_hint)
        side.addWidget(self.no_project)

        self.project_area = QWidget()
        project = QVBoxLayout(self.project_area)
        project.setContentsMargins(0, 0, 0, 0)
        project.setSpacing(2)
        project.addWidget(rule())
        eyebrow = label("PROJECT", role="eyebrow", wrap=False)
        eyebrow.setContentsMargins(18, 10, 16, 0)
        self.project_title = label(role="project")
        self.project_title.setObjectName("sidebar-project-title")
        self.project_title.setContentsMargins(18, 2, 16, 0)
        self.project_facts = label(role="mono")
        self.project_facts.setObjectName("sidebar-project-facts")
        self.project_facts.setContentsMargins(18, 0, 16, 6)
        add = project.addWidget
        add(eyebrow)
        add(self.project_title)
        add(self.project_facts)
        for section in PROJECT_SECTIONS:
            add(self._nav_button(section))
        side.addWidget(self.project_area)

        side.addWidget(rule())
        start = label("START", role="eyebrow", wrap=False)
        start.setContentsMargins(18, 10, 16, 0)
        side.addWidget(start)
        for section in START_SECTIONS:
            side.addWidget(self._nav_button(section))
        side.addStretch(1)

        side.addWidget(rule())
        self.models_button = QPushButton()
        self.models_button.setObjectName("models-status")
        self.models_meter = QProgressBar()
        self.models_meter.setRange(0, 1000)
        self.models_meter.setTextVisible(False)
        self.models_meter.setVisible(False)
        footer = QVBoxLayout()
        footer.setContentsMargins(12, 10, 12, 0)
        footer.addWidget(self.models_button)
        footer.addWidget(self.models_meter)
        side.addLayout(footer)
        return sidebar

    def _nav_button(self, section: Section) -> NavButton:
        name = LABELS[section]
        button = NavButton(name)
        button.setAccessibleName(name)
        button.setObjectName(f"nav-{section.value}")
        button.clicked.connect(lambda _=False, s=section: self._open_section(s))
        self.nav_buttons[name] = button
        self._section_buttons[section] = button
        return button

    # -- startup ------------------------------------------------------------

    def start(self) -> None:
        """Quick status at launch; show the setup window unless models are ready."""

        self.provisioning.refresh()
        self.projects.refresh()
        if not self.provisioning.state.status.ready:
            self.ui.show_setup()

    # -- navigation ---------------------------------------------------------

    def current_section(self) -> Section:
        if self.pages.currentWidget() is self.analyze_page:
            return Section.ANALYZE
        return self.projects_page.section

    def _open_section(self, section: Section) -> None:
        """A sidebar click: never silently drop an unsaved judgment or note."""

        current = self.current_section()
        item = self._item(section)
        if section is current or (item is not None and not item.enabled):
            self._sync_checked()
            return
        if self._guarded_busy(section):
            self._sync_checked()
            return
        if self._declines_to_leave(current, section):
            self._sync_checked()
            return
        if section is Section.ANALYZE:
            self.pages.setCurrentWidget(self.analyze_page)
        elif section is Section.PROJECTS:
            self.pages.setCurrentWidget(self.projects_page)
            if self.projects.state.current is not None:
                self.projects_page.leave_project()
        else:
            self.pages.setCurrentWidget(self.projects_page)
            self.projects_page.show_section(section)
        self._sync_checked()

    def show_page(self, name: str) -> None:
        """Switch between the two top-level pages directly (no unsaved-work prompt)."""

        self.pages.setCurrentWidget(
            self.analyze_page if name == LABELS[Section.ANALYZE] else self.projects_page
        )
        self._sync_checked()

    def _item(self, section: Section) -> NavItem | None:
        nav = self._navigation
        for item in (*nav.project_items, *nav.start_items):
            if item.section is section:
                return item
        return None

    def _guarded_busy(self, section: Section) -> bool:
        """Page data loads one operation at a time: ignore a click while one runs."""

        if section is Section.ANALYZE:
            return False
        if self.projects.state.activity is ProjectsActivity.ANALYZING:
            return section not in (Section.IMPORT, Section.ANALYZE)
        return any(
            c.state.busy
            for c in (self.review, self.insights, self.results, self.agreement)
        )

    def _declines_to_leave(self, leaving: Section, entering: Section) -> bool:
        """Ask before dropping unsaved work; True means stay where you are."""

        review_open = leaving is Section.REVIEW and entering is not Section.REVIEW
        note_open = leaving in INSIGHT_SECTIONS and entering not in INSIGHT_SECTIONS
        if review_open and self.review.state.has_unsaved_changes:
            if not self._platform.confirm(self, "Unsaved changes", LEAVE_PAGE_TEXT):
                return True
            self.review.discard_changes()  # confirmed: it must not come back later
        elif note_open and self.insights.state.has_unsaved_changes:
            if not self._platform.confirm(self, "Unsaved changes", LEAVE_NOTE_TEXT):
                return True
            self.insights.discard_changes()
        return False

    def _on_section(self, _section: object) -> None:
        self._sync_checked()

    def _sync_checked(self) -> None:
        current = self.current_section()
        for section, button in self._section_buttons.items():
            button.setChecked(section is current)

    def _apply_navigation(self, nav: NavView) -> None:
        self._navigation = nav
        self.project_area.setVisible(nav.project_title is not None)
        self.no_project.setVisible(nav.project_title is None)
        self.project_title.setText(nav.project_title or "")
        self.project_facts.setText(nav.project_facts)
        self.project_facts.setVisible(bool(nav.project_facts))
        for item in (*nav.project_items, *nav.start_items):
            button = self._section_buttons[item.section]
            button.setEnabled(item.enabled)
            button.set_badge(item.badge)
            button.setToolTip(item.reason)
            button.setAccessibleDescription(item.reason)
            name = f"{item.label}, {item.badge}" if item.badge else item.label
            button.setAccessibleName(name)

    # -- rendering ----------------------------------------------------------

    def _on_provisioning(self, state: ControllerState) -> None:
        availability = self.services.gate.availability(state.status)
        view = build_sidebar_status(state, availability)
        self.models_button.setText(f"{view.title}\n{view.line}")
        self.models_button.setAccessibleName(view.accessible_name)
        if view.accessible_name != self._last_announced:
            self._last_announced = view.accessible_name
            announce(self.models_button, view.accessible_name)
        self.models_meter.setVisible(view.meter is not None)
        if view.meter is not None:
            self.models_meter.setValue(int(view.meter * 1000))
            self.models_meter.setAccessibleName(view.accessible_name)
        self.analyze_page.render_availability(state.status, availability)
        self.projects_page.show_availability(
            state.status,
            availability,
            other_analysis_running=self.analysis.state.running,
        )

    def _on_projects(self, state: ProjectsState) -> None:
        self._apply_navigation(build_navigation(state))
        self._sync_checked()
        # one analysis at a time: text analysis waits while a project batch runs
        batch = state.activity is ProjectsActivity.ANALYZING
        self.analyze_page.set_external_busy(batch)
        # the gate can change without a provisioning event (H2 mid-batch)
        self._on_provisioning(self.provisioning.state)
        if self._closing and not state.busy:
            self._close_when_done()

    def _on_review(self, state: ReviewState) -> None:
        if self._closing and not state.busy:
            self._close_when_done()

    def _on_insights(self, state: InsightsState) -> None:
        if self._closing and not state.busy:
            self._close_when_done()

    def _on_idle_check(self, _state: object) -> None:
        if self._closing:
            self._close_when_done()

    def _on_analysis(self, state: AnalysisPageState) -> None:
        self.analyze_page.render_analysis(state)
        self._on_provisioning(self.provisioning.state)
        if self._closing and not state.running:
            self._close_when_done()

    def _verify_from_analysis(self) -> None:
        self.provisioning.verify()
        self.ui.show_models()

    # -- closing ------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        """Stop a stoppable operation and close when idle; Verify cannot be stopped."""

        state = self.provisioning.state
        if self._idle():
            if self._keep_unsaved_work(CLOSE_WINDOW_TEXT, CLOSE_NOTE_TEXT):
                event.ignore()
                return
            self.runner.wait_idle(5)
            event.accept()
            return
        event.ignore()
        if self._closing:
            return
        self._closing = True
        if self.provisioning.can_stop:
            self.provisioning.stop()
        if self.projects.can_cancel:
            self.projects.cancel()  # nothing is saved from a cancelled run
        self.statusBar().showMessage(
            "Finishing the current operation before closing…"
            if state.activity is not Activity.VERIFYING
            else "Verify is still running and cannot be stopped. The app closes when "
            "it finishes."
        )
        # the provisioning, analysis, and projects listeners all re-check on idle
        self.provisioning.when_idle(self._close_when_done)

    def _keep_unsaved_work(self, review_text: str, note_text: str) -> bool:
        """Ask before dropping unsaved work; True means stay where you are."""

        if self.review.state.has_unsaved_changes:
            text = review_text
        elif self.insights.state.has_unsaved_changes:
            text = note_text
        else:
            return False
        return not self._platform.confirm(self, "Unsaved changes", text)

    def _close_when_done(self) -> None:
        if not self._idle():
            return  # the next idle notification tries again
        self._closing = False
        self.close()

    def _idle(self) -> bool:
        return not (
            self.provisioning.state.busy
            or self.analysis.state.running
            or self.projects.state.busy
            or self.review.state.busy
            or self.insights.state.busy
            or self.results.state.busy
            or self.agreement.state.busy
        )
