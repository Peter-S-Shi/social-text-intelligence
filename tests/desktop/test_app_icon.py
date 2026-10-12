"""The approved application icon at run time (M10 S5-UI-001)."""

from __future__ import annotations

import importlib.util
import struct
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage

from social_text_intelligence.desktop.qt import app as desktop_app
from social_text_intelligence.desktop.qt.app_icon import ICON_PATH, application_icon

SIZES = [16, 20, 24, 32, 40, 48, 64, 256]
RENDER = Path(__file__).resolve().parents[2] / "tools/m10/render_icon.py"


def ico_entries() -> dict[int, QImage]:
    data = ICON_PATH.read_bytes()
    count = struct.unpack_from("<HHH", data)[2]
    images = {}
    for index in range(count):
        width, *_, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * index)
        images[width or 256] = QImage.fromData(data[offset : offset + size])
    return images


def near_colour(actual: QColor, expected: str) -> bool:
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
    images = ico_entries()

    assert sorted(images) == SIZES
    assert all(
        image.width() == image.height() == size for size, image in images.items()
    )
    icon = application_icon()
    assert icon is not None
    assert {QSize(size, size) for size in SIZES} <= set(icon.availableSizes())


def test_the_icon_is_the_approved_text_to_evidence_design(qapp: Any) -> None:
    large = ico_entries()[256]
    # 256 px is 4 x the 64-unit design grid (assets/icon/sti-icon.svg).
    assert large.pixelColor(0, 0).alpha() == 0  # rounded corner
    assert near_colour(large.pixelColor(4 * 4, 4 * 32), "#2C47E0")  # tile
    assert near_colour(large.pixelColor(4 * 12, 4 * 30), "#FFFFFF")  # bubble
    assert near_colour(large.pixelColor(4 * 22, 4 * 47), "#FFFFFF")  # bubble tail
    assert near_colour(large.pixelColor(4 * 30, 4 * 25 + 2), "#33404F")  # first bar
    assert near_colour(large.pixelColor(4 * 25, 4 * 34 + 2), "#2C47E0")  # second bar
    small = ico_entries()[16]
    # The approved 16 px variant leaves the second bar out: its place stays white.
    assert near_colour(small.pixelColor(6, 9), "#FFFFFF")
    # From 20 px up both bars are drawn.
    twenty = ico_entries()[20]
    assert near_colour(twenty.pixelColor(8, 10), "#2C47E0")


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


def test_the_committed_icon_matches_a_fresh_render(qapp: Any) -> None:
    spec = importlib.util.spec_from_file_location("render_icon", RENDER)
    assert spec is not None and spec.loader is not None
    render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render)
    committed = ico_entries()

    assert list(render.ICON_SIZES) == SIZES
    for size in SIZES:
        fresh = render.render(size).convertToFormat(QImage.Format.Format_ARGB32)
        stored = committed[size].convertToFormat(QImage.Format.Format_ARGB32)
        # A Qt patch release may shift anti-aliased edges by a step or two.
        differing = sum(
            max(
                abs(
                    ((fresh.pixel(x, y) >> shift) & 0xFF)
                    - ((stored.pixel(x, y) >> shift) & 0xFF)
                )
                for shift in (0, 8, 16, 24)
            )
            > 3
            for y in range(size)
            for x in range(size)
        )
        assert differing == 0, (size, differing)
