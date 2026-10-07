"""Operating-system interactions behind one injectable seam (so tests need no OS UI)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def _pick_folder(parent: QWidget | None) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, "Choose a models folder")
    return Path(chosen) if chosen else None


def _open_folder(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))


def _confirm(parent: QWidget | None, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Cancel)
    return box.exec() == QMessageBox.StandardButton.Ok


@dataclass(frozen=True, slots=True)
class DesktopPlatform:
    pick_folder: Callable[[QWidget | None], Path | None] = _pick_folder
    open_folder: Callable[[Path], bool] = _open_folder
    confirm: Callable[[QWidget | None, str, str], bool] = _confirm
