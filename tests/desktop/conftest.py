"""Qt smoke tests run headless; the whole module skips if Qt cannot be imported."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp() -> Iterator[Any]:
    if os.environ.get("STI_REQUIRE_QT") == "1":
        # CI must prove the Qt shell really loads, never skip it silently.
        import PySide6.QtWidgets as widgets
    else:
        widgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    app: Any = widgets.QApplication.instance() or widgets.QApplication([])
    from social_text_intelligence.desktop.qt.style import STYLESHEET

    app.setStyleSheet(STYLESHEET)
    yield app


@pytest.fixture
def pump(qapp: Any) -> Callable[[Callable[[], bool], float], None]:
    import time

    from PySide6.QtCore import QCoreApplication

    def wait(until: Callable[[], bool], timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while not until():
            assert time.monotonic() < deadline, "timed out waiting for the UI"
            QCoreApplication.processEvents()
            time.sleep(0.002)
        QCoreApplication.processEvents()

    return wait


class FakePlatform:
    """Operating-system seam double: records calls and returns scripted answers."""

    def __init__(self) -> None:
        self.folder: Path | None = None
        self.csv_file: Path | None = None
        self.opened: list[Path] = []
        self.confirmed = True
        self.confirmations: list[str] = []

    def pick_folder(self, parent: Any) -> Path | None:
        return self.folder

    def pick_csv(self, parent: Any) -> Path | None:
        return self.csv_file

    def open_folder(self, path: Path) -> bool:
        self.opened.append(path)
        return True

    def confirm(self, parent: Any, title: str, text: str) -> bool:
        self.confirmations.append(text)
        return self.confirmed


@pytest.fixture
def make_shell(qapp: Any, tmp_path: Path) -> Iterator[Callable[..., Any]]:
    from PySide6.QtCore import QCoreApplication

    from .fakes import FakeProvisioning, ImmediateRunner
    from .qt_support import Shell

    shells: list[Shell] = []

    def factory(
        fake: FakeProvisioning,
        runner: Any = None,
        platform: Any = None,
        gateway: Any = None,
    ) -> Shell:
        shell = Shell(tmp_path, fake, runner or ImmediateRunner(), platform, gateway)
        shells.append(shell)
        return shell

    yield factory
    for shell in shells:
        for dialog in (
            shell.window.ui.setup_dialog,
            shell.window.ui.models_dialog,
            shell.window.ui.folder_dialog,
        ):
            dialog.hide()
        shell.window.hide()
        shell.window.deleteLater()
    QCoreApplication.processEvents()
