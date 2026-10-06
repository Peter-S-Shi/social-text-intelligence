"""PROTOTYPE - STI V2 UI/IA exploration (throwaway, never ship).

Question: what desktop-native information architecture should STI V2 have?
Plan: round 2 directions D (Casebook), E (Instrument), F (Field); round 1
(A, B, C) and shared flows (S) kept for comparison,
switchable from a floating bottom bar, in one PySide6 window with synthetic data.

Run:      python prototypes/v2-ui-ia/run_prototype.py [--variant A] [--screen a_review]
Capture:  python prototypes/v2-ui-ia/run_prototype.py --capture prototypes/v2-ui-ia/screenshots
Keys:     Left/Right = previous/next direction, PageUp/PageDown = previous/next screen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QEvent, QObject, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import common  # noqa: E402
import shared_flows  # noqa: E402
import variant_a_workbench  # noqa: E402
import variant_b_pipeline  # noqa: E402
import variant_c_desk  # noqa: E402
import variant_d_casebook  # noqa: E402
import variant_e_instrument  # noqa: E402
import variant_f_field  # noqa: E402

# Round 2 (D, E, F) first; round 1 (A, B, C, S) kept for comparison.
VARIANTS = [variant_d_casebook, variant_e_instrument, variant_f_field,
            variant_a_workbench, variant_b_pipeline, variant_c_desk, shared_flows]
WIDTH, HEIGHT = 1600, 960


class Switcher(QFrame):
    """Floating prototype-only bar; visually distinct from the designs."""

    def __init__(self, shell: "Shell"):
        super().__init__(shell)
        self.shell = shell
        self.setStyleSheet(
            "QFrame { background: #111; border-radius: 18px; }"
            "QLabel { color: #fff; font-size: 12px; }"
            "QPushButton { background: #333; color: #fff; border: none; border-radius: 12px;"
            " padding: 4px 10px; font-weight: 600; }"
            "QPushButton:hover { background: #555; }"
            "QComboBox { background: #333; color: #fff; border: none; border-radius: 4px; padding: 3px 8px; }"
            "QComboBox QAbstractItemView { background: #222; color: #fff; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)
        tag = QLabel("PROTOTYPE")
        tag.setStyleSheet("color:#F2C94C;font-weight:700;font-size:11px;")
        prev_b = QPushButton("←")
        next_b = QPushButton("→")
        self.label = QLabel()
        self.label.setMinimumWidth(230)
        self.screens = QComboBox()
        self.screens.setMinimumWidth(260)
        prev_b.clicked.connect(lambda: shell.step_variant(-1))
        next_b.clicked.connect(lambda: shell.step_variant(1))
        self.screens.activated.connect(self._pick)
        for w in (tag, prev_b, self.label, next_b, self.screens):
            lay.addWidget(w)

    def _pick(self, idx: int):
        mod = VARIANTS[self.shell.v]
        self.shell.go(self.shell.v, mod.SCREENS[idx][0])

    def sync(self):
        mod = VARIANTS[self.shell.v]
        self.label.setText(f"{mod.KEY}  ({mod.NAME})")
        self.screens.blockSignals(True)
        self.screens.clear()
        for key, title in mod.SCREENS:
            self.screens.addItem(f"{key}  -  {title}")
        keys = [k for k, _ in mod.SCREENS]
        self.screens.setCurrentIndex(keys.index(self.shell.screen))
        self.screens.blockSignals(False)
        self.adjustSize()
        self.move((self.shell.width() - self.width()) // 2, self.shell.height() - self.height() - 14)
        self.raise_()


class Shell(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STI V2 UI/IA - PROTOTYPE")
        self.resize(WIDTH, HEIGHT)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.content: QWidget | None = None
        self.v = 0
        self.screen = VARIANTS[0].SCREENS[0][0]
        self.switcher = Switcher(self)

    def go(self, v: int, screen: str | None = None):
        self.v = v
        mod = VARIANTS[v]
        self.screen = screen or mod.SCREENS[0][0]
        if self.content is not None:
            self.lay.removeWidget(self.content)
            self.content.deleteLater()
        getattr(mod, "theme", common.apply_theme)(QApplication.instance())
        self.content = mod.build(self.screen, lambda s: QTimer.singleShot(0, lambda: self.go(self.v, s)))
        self.lay.addWidget(self.content)
        self.switcher.sync()

    def step_variant(self, d: int):
        self.go((self.v + d) % len(VARIANTS))

    def step_screen(self, d: int):
        keys = [k for k, _ in VARIANTS[self.v].SCREENS]
        self.go(self.v, keys[(keys.index(self.screen) + d) % len(keys)])

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.switcher.sync()


class Keys(QObject):
    TEXT_WIDGETS = (QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox, QComboBox)

    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.KeyPress:
            if isinstance(QApplication.focusWidget(), self.TEXT_WIDGETS):
                return False
            k = ev.key()
            if k == Qt.Key.Key_Left and ev.modifiers() == Qt.KeyboardModifier.NoModifier:
                self.shell.step_variant(-1)
                return True
            if k == Qt.Key.Key_Right and ev.modifiers() == Qt.KeyboardModifier.NoModifier:
                self.shell.step_variant(1)
                return True
            if k == Qt.Key.Key_PageDown:
                self.shell.step_screen(1)
                return True
            if k == Qt.Key.Key_PageUp:
                self.shell.step_screen(-1)
                return True
        return False


def capture(out: Path, only: str = ""):
    out.mkdir(parents=True, exist_ok=True)
    shell = Shell()
    shell.switcher.hide()
    shell.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    shell.show()
    for vi, mod in enumerate(VARIANTS):
        if only and mod.KEY not in only:
            continue
        for key, _title in mod.SCREENS:
            shell.go(vi, key)
            shell.switcher.hide()
            for _ in range(4):
                QApplication.processEvents()
            path = out / f"{key}.png"
            shell.grab().save(str(path))
            print("saved", path.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="D")
    ap.add_argument("--screen")
    ap.add_argument("--capture", type=Path)
    ap.add_argument("--only", default="", help="capture only these direction keys, e.g. DEF")
    args = ap.parse_args()
    app = QApplication(sys.argv)
    common.apply_theme(app)
    if args.capture:
        capture(args.capture, args.only.upper())
        return
    shell = Shell()
    keys = Keys(shell)
    app.installEventFilter(keys)
    vi = next((i for i, m in enumerate(VARIANTS) if m.KEY == args.variant.upper()), 0)
    shell.go(vi, args.screen)
    shell.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
