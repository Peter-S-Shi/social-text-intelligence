"""The smallest real shell: sidebar with persistent Models status, two pages."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..analysis import AnalysisPageController, AnalysisPageState
from ..composition import (
    DesktopServices,
    build_analysis_controller,
    build_projects_controller,
    build_provisioning_controller,
)
from ..controller import (
    Activity,
    ControllerState,
    JobRunner,
    ProvisioningController,
)
from ..panel import build_sidebar_status
from ..projects import ProjectsActivity, ProjectsState
from .pages import AnalyzePage
from .platform import DesktopPlatform
from .projects_page import ProjectsPage
from .provisioning_ui import ProvisioningUi
from .widgets import announce, frame, label

APP_TITLE = "Social Text Intelligence"
PAGES = ("Projects", "Analyze one text")  # sidebar order = stacked page order


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
        platform = platform or DesktopPlatform()
        self._closing = False

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = frame("panel")
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(250)
        side = QVBoxLayout(self.sidebar)
        side.addWidget(label(APP_TITLE, role="title"))
        self.nav = QButtonGroup(self)
        self.nav_buttons: dict[str, QPushButton] = {}
        for name in PAGES:
            button = QPushButton(name)
            button.setCheckable(True)
            button.setProperty("nav", True)
            button.setAccessibleName(name)
            button.setObjectName(f"nav-{name.split()[0].lower()}")
            self.nav.addButton(button)
            self.nav_buttons[name] = button
            side.addWidget(button)
        side.addStretch(1)
        self.models_button = QPushButton()
        self.models_button.setObjectName("models-status")
        self.models_meter = QProgressBar()
        self.models_meter.setRange(0, 1000)
        self.models_meter.setTextVisible(False)
        self.models_meter.setVisible(False)
        side.addWidget(self.models_button)
        side.addWidget(self.models_meter)
        layout.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.projects_page = ProjectsPage(self.projects, platform)
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

        for name, button in self.nav_buttons.items():
            button.clicked.connect(lambda _=False, page=name: self.show_page(page))
        self.models_button.clicked.connect(self.ui.show_models)
        self.projects_page.open_models.connect(self.ui.show_models)
        self.analyze_page.open_models.connect(self.ui.show_models)
        self.analyze_page.verify_requested.connect(self._verify_from_analysis)
        self.analyze_page.analyze_requested.connect(self.analysis.submit)

        self.provisioning.subscribe(self._on_provisioning)
        self.analysis.subscribe(self._on_analysis)
        self.projects.subscribe(self._on_projects)
        self._last_announced = ""
        self.show_page(PAGES[0])

    # -- startup ------------------------------------------------------------

    def start(self) -> None:
        """Quick status at launch; show the setup window unless models are ready."""

        self.provisioning.refresh()
        self.projects.refresh()
        if not self.provisioning.state.status.ready:
            self.ui.show_setup()

    # -- rendering ----------------------------------------------------------

    def show_page(self, name: str) -> None:
        self.pages.setCurrentIndex(PAGES.index(name))
        for page, button in self.nav_buttons.items():
            button.setChecked(page == name)

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
        # one analysis at a time: text analysis waits while a project batch runs
        batch = state.activity is ProjectsActivity.ANALYZING
        self.analyze_page.set_external_busy(batch)
        # the gate can change without a provisioning event (H2 mid-batch)
        self._on_provisioning(self.provisioning.state)
        if self._closing and not state.busy:
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
        )
