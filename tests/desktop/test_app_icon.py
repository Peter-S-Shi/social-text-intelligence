"""The approved application icon at run time (M10 S5-UI-001)."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage

from social_text_intelligence.desktop.qt import app as desktop_app
from social_text_intelligence.desktop.qt.app_icon import ICON_PATH, application_icon

SIZES = [16, 20, 24, 32, 40, 48, 64, 256]


def entries() -> dict[int, QImage]:
    data = ICON_PATH.read_bytes()
    count = struct.unpack_from("<HHH", data)[2]
    images = {}
    for index in range(count):
        width, _, _, _, _, _, size, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        images[width or 256] = QImage.fromData(data[offset : offset + size])
    return images


def close(actual: QColor, expected: str) -> bool:
    target = QColor(expected)
    return all(
        abs(a - b) <= 6
        for a, b in zip(
            (actual.red(), actual.green(), actual.blue()),
            (target.red(), target.green(), target.blue()),
            strict=True,
        )
    )


def test_the_icon_carries_every_windows_size(qapp: Any) -> None:
    images = entries()

    assert sorted(images) == SIZES
    assert all(
        image.width() == image.height() == size for size, image in images.items()
    )
    icon = application_icon()
    assert icon is not None
    assert {QSize(size, size) for size in SIZES} <= set(icon.availableSizes())


def test_the_icon_is_the_approved_text_to_evidence_design(qapp: Any) -> None:
    large = entries()[256]
    # 256 px is 4 x the 64-unit design grid (assets/icon/sti-icon.svg).
    assert large.pixelColor(0, 0).alpha() == 0  # rounded corner
    assert close(large.pixelColor(4 * 4, 4 * 32), "#2C47E0")  # tile
    assert close(large.pixelColor(4 * 12, 4 * 30), "#FFFFFF")  # bubble
    assert close(large.pixelColor(4 * 22, 4 * 47), "#FFFFFF")  # bubble tail
    assert close(large.pixelColor(4 * 30, 4 * 25 + 2), "#33404F")  # first bar
    assert close(large.pixelColor(4 * 25, 4 * 34 + 2), "#2C47E0")  # second bar
    small = entries()[16]
    # At 20 px and below the second bar is left out: its place stays bubble white.
    assert close(small.pixelColor(6, 9), "#FFFFFF")


def test_a_missing_or_unreadable_icon_falls_back_safely(
    qapp: Any, tmp_path: Path
) -> None:
    broken = tmp_path / "sti.ico"
    broken.write_bytes(b"not an icon")

    assert application_icon(tmp_path / "absent.ico") is None
    assert application_icon(broken) is None


def test_the_application_sets_the_icon_and_tolerates_its_absence(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert desktop_app.apply_application_icon(qapp) is True
    assert not qapp.windowIcon().isNull()

    monkeypatch.setattr(desktop_app, "application_icon", lambda: None)
    assert desktop_app.apply_application_icon(qapp) is False
