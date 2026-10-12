"""Render the approved application icon into a multi-size Windows ICO (M10 S5-UI-001).

The geometry is assets/icon/sti-icon.svg (design A, "text to evidence") on a
64-unit grid, drawn with QtGui only, so no image library is added. Each size is
stored as a PNG entry, which Windows Vista and later read at every size. Run it
only to regenerate src/social_text_intelligence/desktop/qt/resources/sti.ico.
The pixels are fixed by the design; the PNG bytes may differ with the Qt or zlib
version, so tests compare decoded pixels rather than file bytes.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import APPLICATION_ICON, ICON_SIZES  # noqa: E402  (one source of truth)

# The approved 16 px variant keeps one, thicker bar so the mark stays legible.
SINGLE_BAR_SIZE = 16
ULTRAMARINE, GRAPHITE, WHITE = "#2C47E0", "#33404F", "#FFFFFF"


def render(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 64, size / 64)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ULTRAMARINE))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 14, 14)
    bubble = QPainterPath()
    bubble.addRoundedRect(QRectF(10, 16, 44, 28), 4, 4)
    tail = QPainterPath()
    tail.moveTo(QPointF(30, 44))
    tail.lineTo(QPointF(20, 52))
    tail.lineTo(QPointF(20, 43))
    tail.closeSubpath()
    painter.setBrush(QColor(WHITE))
    painter.drawPath(bubble.united(tail))
    painter.setBrush(QColor(GRAPHITE))
    if size == SINGLE_BAR_SIZE:
        painter.drawRoundedRect(QRectF(18, 23, 26, 6), 3, 3)
    else:
        painter.drawRoundedRect(QRectF(18, 23, 26, 5), 2.5, 2.5)
        painter.setBrush(QColor(ULTRAMARINE))
        painter.drawRoundedRect(QRectF(18, 32, 16, 5), 2.5, 2.5)
    painter.end()
    return image


def png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise ValueError("The icon image could not be encoded.")
    return bytes(data.data())


def ico(images: dict[int, bytes]) -> bytes:
    """An ICO container with one 32-bit PNG entry per size."""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries, blobs = b"", b""
    offset = 6 + 16 * len(images)
    for size, blob in sorted(images.items()):
        side = 0 if size == 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    return header + entries + blobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=APPLICATION_ICON)
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(ico({size: png(render(size)) for size in ICON_SIZES}))
    print(f"Wrote {len(ICON_SIZES)} sizes to {args.output.name}.")
    return 0 if app is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
