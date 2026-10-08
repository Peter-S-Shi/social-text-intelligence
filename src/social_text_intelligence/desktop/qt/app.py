"""Desktop entry point: ``sti-desktop`` or ``python -m ...desktop``."""

from __future__ import annotations

import sys
from collections.abc import Sequence

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
