"""Provisioning windows and the single action router.

``ProvisioningUi`` owns the setup window, the Models window, and the folder dialog,
re-renders them from the controller's state, and routes every action id to the
controller. Widgets hold no provisioning rules.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..controller import Activity, ControllerState, ProvisioningController
from ..formatting import format_bytes
from ..gate import AnalysisAvailability, AnalysisGate
from ..panel import (
    ActionId,
    ActionView,
    build_folder_view,
    build_panel,
    progress_for,
    report_for,
)
from .platform import DesktopPlatform
from .provisioning_panel import ProvisioningPanel
from .widgets import ActionRow, ProgressBlock, ReportBox, add_all, frame, label


class PanelDialog(QDialog):
    """A window that hosts the provisioning panel plus one closing button."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.setMinimumSize(640, 560)
        layout = QVBoxLayout(self)
        self.panel = ProvisioningPanel()
        layout.addWidget(self.panel, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("close-button")
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        layout.addLayout(row)


class FolderDialog(QDialog):
    """Pick a folder, read its findings (read-only), then import what is found."""

    def __init__(self, ui: ProvisioningUi, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui = ui
        self.setWindowTitle("Use a models folder")
        self.setAccessibleName("Use a models folder")
        self.setMinimumSize(560, 460)
        layout = QVBoxLayout(self)
        self.heading = label("Use a models folder", role="headline")
        self.path_label = label(role="mono")
        self.path_label.setObjectName("folder-path")
        self.status_label = label()
        self.status_label.setObjectName("folder-status")
        self.rows_box = QVBoxLayout()
        self.action_row = ActionRow()
        self.action_row.triggered.connect(ui.handle)
        self.progress = ProgressBlock()
        self.progress.setVisible(False)
        self.progress.stop_requested.connect(
            lambda: ui.handle(ActionView(ActionId.STOP, "Stop"))
        )
        self.report = ReportBox()
        self.report.setVisible(False)
        self.report.triggered.connect(ui.handle)
        self.error_box = ReportBox()
        self.error_box.setVisible(False)
        add_all(layout, self.heading, self.path_label, self.status_label)
        layout.addLayout(self.rows_box)
        add_all(layout, self.error_box, self.progress, self.report, self.action_row)
        layout.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("folder-close")
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        layout.addLayout(row)
        self._row_labels: list[QWidget] = []

    def show_state(
        self, state: ControllerState, availability: AnalysisAvailability
    ) -> None:
        view = build_folder_view(state.folder, busy=state.busy)
        self.path_label.setText(view.path_text)
        self.path_label.setVisible(bool(view.path_text))
        self.status_label.setText(view.status_line)
        for widget in self._row_labels:
            self.rows_box.removeWidget(widget)
            widget.deleteLater()
        self._row_labels = []
        for row in view.rows:
            box = frame("card")
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(label(row.title, role="title"))
            box_layout.addWidget(label(row.finding))
            if row.problems:
                box_layout.addWidget(label(", ".join(row.problems), role="mono"))
            box.setAccessibleName(f"{row.title}: {row.finding}")
            self.rows_box.addWidget(box)
            box.show()
            self._row_labels.append(box)
        if view.error is not None:
            self.error_box.setVisible(True)
            self.error_box.show_report(view.error)
        else:
            self.error_box.setVisible(False)
            self.error_box.clear()
        importing = state.activity is Activity.IMPORTING
        self.action_row.set_actions(() if importing else view.actions)
        progress = progress_for(state) if state.activity is Activity.IMPORTING else None
        if progress is not None:
            self.progress.setVisible(True)
            self.progress.show_progress(progress)
        else:
            self.progress.setVisible(False)
            self.progress.reset()
        report = report_for(state, availability)
        if (
            report is not None
            and state.report is not None
            and (state.report.kind is Activity.IMPORTING)
        ):
            self.report.setVisible(True)
            self.report.show_report(report)
        else:
            self.report.setVisible(False)
            self.report.clear()


class ProvisioningUi(QObject):
    def __init__(
        self,
        controller: ProvisioningController,
        gate: AnalysisGate,
        models_root: Callable[[], Path],
        platform: DesktopPlatform,
        parent_window: QWidget,
    ) -> None:
        super().__init__(parent_window)
        self.controller = controller
        self.gate = gate
        self._models_root = models_root
        self.platform = platform
        self._window = parent_window
        self.setup_dialog = PanelDialog("Set up models", parent_window)
        self.setup_dialog.setObjectName("setup-dialog")
        self.setup_dialog.panel.action_requested.connect(self.handle)
        self.models_dialog = PanelDialog("Models", parent_window)
        self.models_dialog.setObjectName("models-dialog")
        self.models_dialog.panel.action_requested.connect(self.handle)
        self.folder_dialog = FolderDialog(self, parent_window)
        self.folder_dialog.setObjectName("folder-dialog")
        self.message: Callable[[str], None] = lambda text: None
        controller.subscribe(self.render)
        self.render(controller.state)

    def availability(self) -> AnalysisAvailability:
        return self.gate.availability(self.controller.state.status)

    # -- rendering ----------------------------------------------------------

    def render(self, state: ControllerState) -> None:
        availability = self.gate.availability(state.status)
        setup = self.setup_dialog
        setup.panel.show_view(build_panel(state, availability, window="setup"))
        if state.busy:
            setup.close_button.setText("Continue while this runs")
        elif state.status.ready:
            setup.close_button.setText("Done")
        else:
            setup.close_button.setText("Later")
        setup.close_button.setAccessibleName(setup.close_button.text())
        self.models_dialog.panel.show_view(
            build_panel(state, availability, window="models")
        )
        self.folder_dialog.show_state(state, availability)
        if (
            self.folder_dialog.isVisible()
            and state.folder is None
            and not state.busy
            and state.report is not None
            and state.report.kind is Activity.IMPORTING
        ):
            self.folder_dialog.accept()

    # -- showing ------------------------------------------------------------

    def show_setup(self) -> None:
        self.setup_dialog.show()
        self.setup_dialog.raise_()
        self.setup_dialog.activateWindow()

    def show_models(self) -> None:
        self.setup_dialog.hide()
        self.models_dialog.show()
        self.models_dialog.raise_()
        self.models_dialog.activateWindow()

    def show_folder(self) -> None:
        self.controller.close_folder()
        self.render(self.controller.state)
        self.folder_dialog.show()
        self.folder_dialog.raise_()
        self.folder_dialog.activateWindow()

    # -- routing ------------------------------------------------------------

    def handle(self, action: ActionView) -> None:
        controller = self.controller
        match action.action:
            case ActionId.DOWNLOAD:
                controller.download(action.keys)
            case ActionId.STOP:
                controller.stop()
            case ActionId.DISCARD:
                self._discard(action)
            case ActionId.USE_FOLDER:
                self.show_folder()
            case ActionId.CHOOSE_FOLDER:
                self._choose_folder()
            case ActionId.IMPORT:
                controller.import_folder(action.keys)
            case ActionId.VERIFY:
                controller.verify()
            case ActionId.OPEN_FOLDER:
                self.open_models_folder()
            case ActionId.RETRY:
                controller.retry()
            case ActionId.DISMISS:
                controller.dismiss_report()
            case ActionId.OPEN_MODELS:
                self.show_models()
            case ActionId.CHECK_FOLDER:
                self._choose_folder()

    def _discard(self, action: ActionView) -> None:
        status = self.controller.state.status
        keys = action.keys or tuple(m.key for m in status.models)
        kept = sum(m.resumable_bytes for m in status.models if m.key in keys)
        text = (
            f"Discard {format_bytes(kept)} of partial download? "
            "Finished model files are not affected."
        )
        if self.platform.confirm(self._window, "Discard partial download", text):
            self.controller.discard(action.keys)

    def _choose_folder(self) -> None:
        parent = self.folder_dialog if self.folder_dialog.isVisible() else self._window
        path = self.platform.pick_folder(parent)
        if path is not None:
            self.controller.inspect_folder(path)

    def open_models_folder(self) -> None:
        if not self.platform.open_folder(self._models_root()):
            self.message("The models folder could not be opened.")
