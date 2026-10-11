"""Users can discover the Qt terms without opening a project or model."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def test_visible_qt_notice_opens_terms_and_replacement_information(
    qapp: Any, tmp_path: Path
) -> None:
    from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser

    from social_text_intelligence.desktop.qt.app import build_window
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    window, runner = build_window(AppDataLocations(tmp_path / "synthetic-data"))
    try:
        window.show()
        qapp.processEvents()
        buttons = [
            button
            for button in window.findChildren(QPushButton)
            if "Qt LGPL" in button.text()
        ]
        assert len(buttons) == 1 and buttons[0].isVisible()
        assert buttons[0].isEnabled()
        buttons[0].click()
        qapp.processEvents()
        dialogs = [d for d in window.findChildren(QDialog) if d.isVisible()]
        assert len(dialogs) == 1
        browser = dialogs[0].findChild(QTextBrowser)
        assert browser is not None
        text = browser.toPlainText()
        for required in (
            "LGPL version 3",
            "PySide6-Essentials",
            "shiboken6",
            "reverse engineering",
            "SOURCE_ACCESS.md",
            "QT_REPLACEMENT.md",
            "GNU-GPL-3.0.txt",
        ):
            assert required in text
        dialogs[0].close()
    finally:
        assert runner.wait_idle(5)
        window.close()
        qapp.processEvents()


def test_license_diagnostic_reports_loaded_qt_without_models() -> None:
    from PySide6.QtCore import qVersion

    from social_text_intelligence.desktop.qt.packaged_entry import license_info

    result = license_info()
    assert result["qt_version"] == qVersion()
    assert result["distribution_permitted"] is False
    assert result["models_loaded"] is False
