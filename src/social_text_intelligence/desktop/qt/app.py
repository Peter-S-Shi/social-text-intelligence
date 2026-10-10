"""Desktop entry point: ``sti-desktop`` or ``python -m ...desktop``."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from ...contracts.errors import ProjectStorageError
from ...infrastructure.app_data import AppDataLocations, default_app_data_locations
from ..composition import build_desktop_services
from .main_window import APP_TITLE, MainWindow
from .platform import DesktopPlatform
from .runner import QtJobRunner
from .style import STYLESHEET


def build_window(
    locations: AppDataLocations, platform: DesktopPlatform | None = None
) -> tuple[MainWindow, QtJobRunner]:
    runner = QtJobRunner()
    window = MainWindow(build_desktop_services(locations), runner, platform)
    return window, runner


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(args)
    assert isinstance(app, QApplication)
    app.setApplicationName(APP_TITLE)
    app.setStyleSheet(STYLESHEET)
    try:
        locations = default_app_data_locations()
    except ProjectStorageError as error:
        sys.stderr.write(f"{error.message}\n")
        return 2
    window, runner = build_window(locations)
    window.show()
    window.start()
    code = app.exec()
    runner.wait_idle(5)
    return code


def packaged_smoke() -> dict[str, object]:
    """Bounded synthetic startup/storage smoke, never the per-user data directory."""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    app.setStyleSheet(STYLESHEET)
    with TemporaryDirectory(prefix="sti-m10-smoke-") as temporary:
        locations = AppDataLocations(Path(temporary) / "application-data")
        window, runner = build_window(locations)
        try:
            window.show()
            window.start()
            app.processEvents()
            services = build_desktop_services(locations)
            missing = all(
                model.readiness.value == "not_installed"
                for model in services.provisioning.status().models
            )
            details = services.workflow.import_csv(
                b"id,text\nSYN-01,This invented software feedback is synthetic.\n"
                b"SYN-02,\n",
                name="Packaging smoke (synthetic)",
            )
            if details.phase.value == "needs_column":
                details = services.workflow.choose_column(
                    details.summary.project_id, "text"
                )
            reopened = services.workflow.open_project(details.summary.project_id)
            return {
                "window": window.isVisible(),
                "models_unbundled": missing,
                "project_rows": details.row_count,
                "invalid_rows": details.invalid_rows,
                "reopened": reopened.row_count == details.row_count,
            }
        finally:
            if not runner.wait_idle(5):
                raise RuntimeError("Packaging smoke did not finish.")
            window.close()
            app.processEvents()
