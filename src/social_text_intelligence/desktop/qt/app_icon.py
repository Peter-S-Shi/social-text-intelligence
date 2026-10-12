"""The application icon (M10 S5-UI-001), shared by source and frozen runs.

The frozen build places the same file at the same package-relative path, and
embeds it in both executables, so the window, taskbar, Start Menu and uninstall
entry all show one icon. At run time a missing or unreadable file only leaves
Qt's default icon; the build itself refuses a missing icon.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

ICON_PATH = Path(__file__).resolve().parent / "resources" / "sti.ico"


def application_icon(path: Path = ICON_PATH) -> QIcon | None:
    """The icon with its sizes, or None when it cannot be read."""
    if not path.is_file():
        return None
    icon = QIcon(str(path))
    return icon if icon.availableSizes() else None
