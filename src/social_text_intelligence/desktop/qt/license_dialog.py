"""Discoverable Qt notice, without network access or project/model operations."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import qVersion
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..license_notice import QT_NOTICE_TITLE, qt_notice_text
from .platform import DesktopPlatform


class LicenseDialog(QDialog):
    def __init__(self, platform: DesktopPlatform, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(QT_NOTICE_TITLE)
        self.resize(640, 500)
        layout = QVBoxLayout(self)
        text = QTextBrowser()
        text.setAccessibleName("Qt LGPL notice and replacement instructions")
        text.setPlainText(qt_notice_text(qVersion()))
        layout.addWidget(text)
        if getattr(sys, "frozen", False):
            folder = Path(getattr(sys, "_MEIPASS", ".")).parent / "legal"
        else:
            folder = Path(__file__).resolve().parents[4] / "distribution" / "legal"
        open_folder = QPushButton("Open license and source materials")
        open_folder.setEnabled(folder.is_dir())
        open_folder.clicked.connect(lambda: platform.open_folder(folder))
        layout.addWidget(open_folder)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
