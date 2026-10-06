"""PROTOTYPE - throwaway V2 UI/IA exploration. Not production code.

Shared synthetic data, palette tokens, and tiny display widgets. Variants share
only these leaf widgets; each variant owns its own layout and navigation.
All text below is synthetic and written for this prototype.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------
BG = "#F5F5F2"
SURFACE = "#FFFFFF"
SUNKEN = "#EEEEEA"
BORDER = "#DFDFD9"
TEXT = "#1B1E1D"
MUTED = "#686D6A"
FAINT = "#9A9E9B"
ACCENT = "#1F5F4A"  # STI green, carried from V1
ACCENT_SOFT = "#E3EEE9"
AI = "#4A5568"  # slate: machine record
AI_SOFT = "#ECEEF2"
WARN = "#8A5A00"
WARN_SOFT = "#FBF1DC"
ERR = "#A2392A"
ERR_SOFT = "#FAE8E4"
SENT = {"negative": "#B4533C", "neutral": "#8C918E", "positive": "#2E7A5A"}

UI_FONT = "Segoe UI"
MONO_FONT = "Cascadia Mono"
SERIF_FONT = "Georgia"

BASE_QSS = f"""
* {{ font-family: '{UI_FONT}'; font-size: 13px; color: {TEXT}; }}
QMainWindow, QDialog, #page {{ background: {BG}; }}
QLabel[role="h1"] {{ font-size: 22px; font-weight: 600; }}
QLabel[role="h2"] {{ font-size: 16px; font-weight: 600; }}
QLabel[role="h3"] {{ font-size: 13px; font-weight: 600; }}
QLabel[role="eyebrow"] {{ font-size: 11px; font-weight: 600; color: {MUTED}; letter-spacing: 1px; }}
QLabel[role="muted"] {{ color: {MUTED}; }}
QLabel[role="faint"] {{ color: {FAINT}; font-size: 12px; }}
QLabel[role="mono"] {{ font-family: '{MONO_FONT}'; font-size: 12px; color: {MUTED}; }}
QLabel[role="body"] {{ font-size: 14px; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#sunken {{ background: {SUNKEN}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#ai {{ background: {AI_SOFT}; border: 1px solid #D5DAE2; border-radius: 6px; }}
QFrame#human {{ background: {ACCENT_SOFT}; border: 1px solid #C6DDD3; border-radius: 6px; }}
QFrame#warn {{ background: {WARN_SOFT}; border: 1px solid #EBD6A8; border-radius: 6px; }}
QFrame#err {{ background: {ERR_SOFT}; border: 1px solid #EBC3BA; border-radius: 6px; }}
QFrame#hline {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#vline {{ background: {BORDER}; max-width: 1px; min-width: 1px; border: none; }}
QPushButton {{ background: {SURFACE}; border: 1px solid #CFCFC8; border-radius: 4px; padding: 5px 12px; }}
QPushButton:hover {{ background: #F0F0EB; }}
QPushButton[kind="primary"] {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: #184C3B; }}
QPushButton[kind="danger"] {{ color: {ERR}; border-color: #E2B7AE; }}
QPushButton[kind="flat"] {{ border: none; background: transparent; color: {ACCENT}; }}
QPushButton:disabled {{ color: {FAINT}; background: #F3F3F0; }}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{ background: {SURFACE}; border: 1px solid #CFCFC8; border-radius: 4px; padding: 4px 6px; }}
QTableWidget, QTreeWidget, QListWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; gridline-color: #EFEFEA; selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QHeaderView::section {{ background: #F7F7F4; border: none; border-bottom: 1px solid {BORDER}; border-right: 1px solid #EFEFEA; padding: 4px 6px; color: {MUTED}; font-size: 12px; font-weight: 600; }}
QProgressBar {{ background: {SUNKEN}; border: none; border-radius: 3px; max-height: 8px; min-height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QMenuBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QStatusBar {{ background: {SURFACE}; border-top: 1px solid {BORDER}; color: {MUTED}; }}
QStatusBar QLabel {{ color: {MUTED}; font-size: 12px; }}
QToolBar {{ background: {SURFACE}; border: none; border-bottom: 1px solid {BORDER}; spacing: 6px; padding: 4px; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; background: {SURFACE}; top: -1px; }}
QTabBar::tab {{ background: transparent; padding: 6px 14px; border: 1px solid transparent; color: {MUTED}; }}
QTabBar::tab:selected {{ background: {SURFACE}; border: 1px solid {BORDER}; border-bottom-color: {SURFACE}; color: {TEXT}; }}
QDockWidget {{ font-size: 12px; color: {MUTED}; }}
QDockWidget::title {{ background: #F7F7F4; padding: 5px 8px; border-bottom: 1px solid {BORDER}; }}
QRadioButton, QCheckBox {{ spacing: 6px; }}
QScrollArea {{ border: none; background: transparent; }}
"""

# --------------------------------------------------------------------------
# Synthetic data
# --------------------------------------------------------------------------
MODELS = [
    {
        "name": "cardiffnlp/twitter-roberta-base-sentiment-latest",
        "short": "sentiment",
        "rev": "3216a57",
        "license": "CC-BY-4.0",
        "size_mb": 499,
    },
    {
        "name": "SamLowe/roberta-base-go_emotions",
        "short": "emotion",
        "rev": "d750483",
        "license": "MIT",
        "size_mb": 499,
    },
]

PROJECTS = [
    {"name": "Checkout feedback - autumn sample", "records": 600, "reviewed": 359,
     "opened": "Today 09:12", "sources": 2, "size": "4.8 MB"},
    {"name": "Community forum - onboarding thread", "records": 214, "reviewed": 214,
     "opened": "3 Oct", "sources": 1, "size": "1.9 MB"},
    {"name": "Support inbox pilot", "records": 188, "reviewed": 22,
     "opened": "28 Sep", "sources": 1, "size": "1.4 MB"},
    {"name": "Domain evaluation set (Q5 gate)", "records": 120, "reviewed": 120,
     "opened": "21 Sep", "sources": 1, "size": "0.9 MB"},
]

_E = "emotion"


def _r(rid, src, topic, text, sent, scores, emo, emo_conf, secondary=(), flags=(),
       status="unreviewed", human=None):
    return {
        "id": rid, "src": src, "topic": topic, "text": text, "sent": sent,
        "scores": scores, "emo": emo, "emo_conf": emo_conf,
        "secondary": list(secondary), "flags": list(flags), "status": status,
        "human": human,
    }


RECORDS = [
    _r("R-0412", "app_store", "export",
       "Love how fast the new editor is, but exporting a large report still freezes the whole app.",
       "negative", (0.61, 0.27, 0.12), "joy", 0.41, ["anger"], ["mixed"]),
    _r("R-0413", "app_store", "pricing",
       "Brilliant, another price rise right after you removed offline mode. Truly great work.",
       "positive", (0.31, 0.12, 0.57), "admiration", 0.52, [], ["low_margin"]),
    _r("R-0414", "support", "sync",
       "Sync has been stuck on 'pending' since yesterday and I have a client meeting in an hour.",
       "negative", (0.88, 0.10, 0.02), "fear", 0.33, ["annoyance"], ["fallback"]),
    _r("R-0415", "forum", "onboarding",
       "The tutorial was clear and the sample project helped a lot. Thanks to whoever wrote it.",
       "positive", (0.01, 0.06, 0.93), "gratitude", 0.91, ["admiration"], [], "accepted",
       {"sent": "positive", "emo": "gratitude"}),
    _r("R-0416", "support", "billing",
       "I was charged twice this month. Please refund the duplicate payment.",
       "negative", (0.72, 0.26, 0.02), "neutral", 0.48, [], ["fallback"], "corrected",
       {"sent": "negative", "emo": "anger"}),
    _r("R-0417", "app_store", "export",
       "Export to CSV works fine now.",
       "positive", (0.04, 0.47, 0.49), "approval", 0.55, [], ["low_margin"], "uncertain",
       {"sent": None, "emo": None}),
    _r("R-0418", "forum", "sync",
       "Merci, la nouvelle version est beaucoup plus rapide.",
       "neutral", (0.12, 0.50, 0.38), "neutral", 0.61, [], ["lang"]),
    _r("R-0419", "support", "export",
       "so bad it's good honestly, the crash animation is art at this point",
       "negative", (0.83, 0.12, 0.05), "amusement", 0.62, [], ["mixed"]),
    _r("R-0420", "app_store", "onboarding",
       "Couldn't find where to change the language. Gave up after ten minutes.",
       "negative", (0.79, 0.19, 0.02), "disappointment", 0.44, ["annoyance"], [], "accepted",
       {"sent": "negative", "emo": "disappointment"}),
    _r("R-0421", "support", "sync",
       "Fine.",
       "neutral", (0.21, 0.66, 0.13), "neutral", 0.71, [], []),
    _r("R-0422", "forum", "pricing",
       "Happy to pay for this. It replaced three other tools for our team.",
       "positive", (0.01, 0.04, 0.95), "joy", 0.58, ["approval"], [], "accepted",
       {"sent": "positive", "emo": "joy"}),
    _r("R-0423", "support", "export",
       "", "", (0, 0, 0), "", 0.0, [], ["failed"], "failed"),
]
RECORDS[-1]["error"] = "input_too_long: 731 tokens exceeds the 512-token model limit; not truncated"

FLAG_TEXT = {
    "mixed": ("Mixed signal", "Two emotions score within 0.05 of each other; the headline is not decisive."),
    "low_margin": ("Low margin", "Top sentiment beats the runner-up by less than 0.30; treat as unsettled."),
    "fallback": ("Threshold fallback", "No compact emotion reached 0.50; 'neutral' here is a fallback, not a finding."),
    "lang": ("Not English?", "Language check suggests French. Models are English-only; output is unreliable."),
    "failed": ("Failed", "Row was not analyzed."),
}

STATUS_TEXT = {
    "unreviewed": "Unreviewed",
    "accepted": "Accepted",
    "corrected": "Corrected",
    "uncertain": "Uncertain",
    "failed": "Failed",
}

AGREEMENT = {
    "definitive": 164, "agree": 135, "rate": 0.823, "reviewed": 359, "total": 600,
    "uncertain": 12, "corrected": 38, "emo_definitive": 158, "emo_agree": 97,
    "emo_rate": 0.614,
}

GROUPS = [
    ("app_store", 312, 0.85, 0.63, False),
    ("support", 201, 0.80, 0.58, False),
    ("forum", 87, 0.79, 0.67, False),
    ("forum / pricing", 14, 0.71, 0.50, True),
]


# --------------------------------------------------------------------------
# Leaf widgets
# --------------------------------------------------------------------------
def lbl(text: str, role: str | None = None, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if role:
        w.setProperty("role", role)
    w.setWordWrap(wrap)
    w.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return w


def hline() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    return f


def vline() -> QFrame:
    f = QFrame()
    f.setObjectName("vline")
    return f


def card(kind: str = "card", margins: int = 14, spacing: int = 8) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName(kind)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(spacing)
    return f, lay


def row(*widgets, spacing: int = 8, stretch_last: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        if w is None:
            lay.addStretch(1)
        elif isinstance(w, int):
            lay.addSpacing(w)
        else:
            lay.addWidget(w)
    if stretch_last:
        lay.addStretch(1)
    return lay


def wrap_layout(layout) -> QWidget:
    w = QWidget()
    w.setLayout(layout)
    return w


class Badge(QLabel):
    STYLES = {
        "ai": (AI, AI_SOFT),
        "human": (ACCENT, ACCENT_SOFT),
        "warn": (WARN, WARN_SOFT),
        "err": (ERR, ERR_SOFT),
        "muted": (MUTED, SUNKEN),
        "ok": (ACCENT, ACCENT_SOFT),
    }

    def __init__(self, text: str, kind: str = "muted"):
        super().__init__(text)
        fg, bg = self.STYLES.get(kind, self.STYLES["muted"])
        self.setStyleSheet(
            f"QLabel {{ color: {fg}; background: {bg}; border-radius: 3px;"
            f" padding: 1px 6px; font-size: 11px; font-weight: 600; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


def sentiment_badge(label: str) -> QLabel:
    b = QLabel(label or "-")
    c = SENT.get(label, MUTED)
    b.setStyleSheet(f"QLabel {{ color: {c}; font-weight: 600; }}")
    return b


class StackBar(QWidget):
    """Horizontal stacked bar for a 3-way sentiment split."""

    def __init__(self, parts, height: int = 8):
        super().__init__()
        self.parts = parts  # [(value, color)]
        self.setFixedHeight(height)
        self.setMinimumWidth(80)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(v for v, _ in self.parts) or 1
        x = 0.0
        w = self.width()
        for v, c in self.parts:
            seg = w * v / total
            p.fillRect(QRectF(x, 0, seg, self.height()), QColor(c))
            x += seg
        p.end()


class MeterBar(QWidget):
    """Single-value thin bar on a track."""

    def __init__(self, value: float, color: str = ACCENT, height: int = 6):
        super().__init__()
        self.value = value
        self.color = color
        self.setFixedHeight(height)
        self.setMinimumWidth(60)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(SUNKEN))
        p.fillRect(QRectF(0, 0, self.width() * max(0.0, min(1.0, self.value)), self.height()),
                   QColor(self.color))
        p.end()


class Dot(QWidget):
    def __init__(self, color: str, size: int = 8, hollow: bool = False):
        super().__init__()
        self.color = color
        self.hollow = hollow
        self.setFixedSize(QSize(size, size))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.hollow:
            p.setPen(QPen(QColor(self.color), 1.5))
            p.drawEllipse(1, 1, self.width() - 2, self.height() - 2)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.color))
            p.drawEllipse(0, 0, self.width(), self.height())
        p.end()


STATUS_DOT = {
    "unreviewed": ("#B7BBB8", True),
    "accepted": (ACCENT, False),
    "corrected": ("#C08A1E", False),
    "uncertain": ("#7C8CA6", False),
    "failed": (ERR, False),
}


def status_dot(status: str) -> Dot:
    c, hollow = STATUS_DOT[status]
    return Dot(c, 9, hollow)


def sentiment_scores_widget(rec) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    for name, v in zip(("negative", "neutral", "positive"), rec["scores"]):
        r = QHBoxLayout()
        r.setSpacing(8)
        n = lbl(name, "muted")
        n.setFixedWidth(64)
        r.addWidget(n)
        r.addWidget(MeterBar(v, SENT[name]), 1)
        val = lbl(f"{v:.2f}", "mono")
        val.setFixedWidth(34)
        r.addWidget(val)
        lay.addLayout(r)
    return w


def honest_headline(rec) -> str:
    """V2 headline semantics: never present an unsettled result as a verdict."""
    if "failed" in rec["flags"]:
        return "Not analyzed"
    parts = []
    if "low_margin" in rec["flags"]:
        parts.append(f"Unsettled sentiment (leans {rec['sent']})")
    else:
        parts.append(f"{rec['sent'].capitalize()} sentiment")
    if "mixed" in rec["flags"]:
        parts.append(f"mixed emotion: {rec['emo']} / {rec['secondary'][0] if rec['secondary'] else '?'}")
    elif "fallback" in rec["flags"]:
        parts.append("no emotion above threshold")
    else:
        parts.append(rec["emo"])
    return " · ".join(parts)


def mono_font(size: int = 11) -> QFont:
    f = QFont(MONO_FONT)
    f.setPointSize(size)
    return f


def apply_theme(app) -> None:
    """Deterministic light theme regardless of the Windows dark/light setting."""
    from PySide6.QtGui import QPalette

    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setStyle("Fusion")
    pal = QPalette()
    for role, c in (
        (QPalette.ColorRole.Window, BG), (QPalette.ColorRole.Base, SURFACE),
        (QPalette.ColorRole.AlternateBase, "#F7F7F4"), (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.WindowText, TEXT), (QPalette.ColorRole.Button, SURFACE),
        (QPalette.ColorRole.ButtonText, TEXT), (QPalette.ColorRole.Highlight, ACCENT),
        (QPalette.ColorRole.HighlightedText, "#FFFFFF"), (QPalette.ColorRole.PlaceholderText, FAINT),
        (QPalette.ColorRole.ToolTipBase, SURFACE), (QPalette.ColorRole.ToolTipText, TEXT),
    ):
        pal.setColor(role, QColor(c))
    app.setPalette(pal)
    app.setStyleSheet(BASE_QSS)
