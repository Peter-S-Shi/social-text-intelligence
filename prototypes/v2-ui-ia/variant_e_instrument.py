"""PROTOTYPE - Round 2, Direction E: Instrument.

Art direction: a dark measurement console (think audio workstation or lab
instrument). The project is a single recording-like evidence strip; the
machine is amber, the operator (you) is mint, disagreement is coral. Review is
a keyboard instrument: a readout of the machine's measurement next to big
keycaps for your judgment. Insights are calibration, not a dashboard.
Structure: one window, three modes (REVIEW, INGEST, CALIBRATE) under a
persistent strip and a command line.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from common import MODELS, PROJECTS, RECORDS
from common2 import (
    C,
    DENSE,
    DISPLAY,
    DISPLAY_COND,
    DISPLAY_LIGHT,
    MONO,
    EmotionRose,
    EvidenceStrip,
    Hairline,
    Ring,
    SentimentScale,
    band_agreement,
    by_source,
    font,
    text,
)

KEY = "E"
NAME = "Instrument (R2)"
SCREENS = [
    ("e_review", "REVIEW mode: strip, readout, keycaps"),
    ("e_ingest", "INGEST mode: live analysis, stop/resume"),
    ("e_calibrate", "CALIBRATE mode: agreement as calibration"),
    ("e_probe", "Command line probe (quick analysis)"),
    ("e_first", "First run: reader rack"),
]

BG = "#0D0F10"
PANEL = "#14171A"
PANEL2 = "#1A1E21"
LINE = "#272C30"
TXT = "#ECE9E2"
DIM = "#8D9392"
FAINT = "#5A6163"
AMBER = "#FFB547"
MINT = "#5BE3BA"
CORAL = "#FF6A55"

STRIP = {"unreviewed": "#3B4246", "agree": MINT, "disagree": CORAL, "uncertain": "#6F7A7E",
         "failed": "#FF3B30", "queued": "#24292C", "cursor": "#FFFFFF", "head": AMBER}
INST = {"neg": CORAL, "neu": DIM, "pos": MINT, "scale": FAINT, "ai": AMBER, "human": MINT,
        "grid": LINE, "threshold": FAINT, "label": DIM}

QSS = f"""
QWidget {{ color: {TXT}; }}
QWidget#bg {{ background: {BG}; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 4px; }}
QFrame#panel2 {{ background: {PANEL2}; border: 1px solid {LINE}; border-radius: 4px; }}
QPushButton {{ background: {PANEL2}; color: {TXT}; border: 1px solid {LINE}; border-radius: 4px;
  padding: 6px 12px; font-family: '{MONO}'; font-size: 12px; }}
QPushButton:hover {{ border-color: {DIM}; }}
QPushButton[kind="mode"] {{ background: transparent; border: none; color: {DIM}; padding: 6px 14px;
  letter-spacing: 2px; }}
QPushButton[kind="mode"][on="true"] {{ color: {BG}; background: {AMBER}; }}
QPushButton[kind="cap"] {{ font-family: '{DISPLAY}'; font-size: 15px; padding: 0; min-height: 62px;
  background: {PANEL2}; border: 1px solid {LINE}; border-bottom: 3px solid #0A0B0C; text-align: center; }}
QPushButton[kind="cap"][on="true"] {{ background: {MINT}; color: {BG}; border-color: {MINT}; font-weight: 600; }}
QPushButton[kind="cap"][ai="true"] {{ border: 1px dashed {AMBER}; border-bottom: 3px solid #0A0B0C; }}
QPushButton[kind="commit"] {{ background: {MINT}; color: {BG}; border: none; font-family: '{DISPLAY}';
  font-size: 16px; font-weight: 600; padding: 14px; }}
QPushButton[kind="stop"] {{ background: transparent; color: {CORAL}; border: 1px solid {CORAL};
  font-family: '{DISPLAY}'; font-size: 15px; padding: 12px 22px; }}
QPushButton[kind="chip"] {{ border-radius: 12px; padding: 4px 10px; color: {DIM}; font-size: 11px; }}
QPushButton[kind="chip"][on="true"] {{ color: {BG}; background: {TXT}; border-color: {TXT}; }}
QLineEdit {{ background: {BG}; border: none; border-top: 1px solid {LINE}; color: {TXT};
  font-family: '{MONO}'; font-size: 13px; padding: 10px 14px; }}
"""


def theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, c in ((QPalette.ColorRole.Window, BG), (QPalette.ColorRole.Base, PANEL),
                    (QPalette.ColorRole.Text, TXT), (QPalette.ColorRole.WindowText, TXT),
                    (QPalette.ColorRole.Button, PANEL2), (QPalette.ColorRole.ButtonText, TXT),
                    (QPalette.ColorRole.Highlight, AMBER), (QPalette.ColorRole.HighlightedText, BG),
                    (QPalette.ColorRole.PlaceholderText, FAINT)):
        pal.setColor(role, QColor(c))
    app.setPalette(pal)
    app.setFont(font(MONO, 12))
    app.setStyleSheet(QSS)


def build(screen, nav):
    return {"e_review": _review, "e_ingest": _ingest, "e_calibrate": _calibrate, "e_probe": _probe,
            "e_first": _first}[screen](nav)


# --------------------------------------------------------------------------
def _lab(s, color=DIM, px=11, spacing=1.8, weight=400):
    return text(s, MONO, px, color, weight, spacing, upper=True)


def _btn(t, kind=None, on=None, target=None, nav=None, ai=False):
    b = QPushButton(t)
    if kind:
        b.setProperty("kind", kind)
    if on is not None:
        b.setProperty("on", "true" if on else "false")
    if ai:
        b.setProperty("ai", "true")
    if target and nav:
        b.clicked.connect(lambda: nav(target))
    return b


def _panel(kind="panel", m=14, sp=8):
    f = QFrame()
    f.setObjectName(kind)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(m, m, m, m)
    lay.setSpacing(sp)
    return f, lay


def _row(*ws, sp=10):
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(sp)
    for w in ws:
        if w is None:
            h.addStretch(1)
        elif isinstance(w, int):
            h.addSpacing(w)
        else:
            h.addWidget(w)
    return h


def _frame(nav, mode, body, strip_kw=None, cmd=":goto R-0412    :filter unsettled    :analyze <text>    ? help"):
    page = QWidget()
    page.setObjectName("bg")
    page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    top = QHBoxLayout()
    top.setContentsMargins(16, 10, 16, 10)
    logo = text("STI", DISPLAY, 15, BG, 700, 1)
    logo.setStyleSheet(f"background:{TXT}; color:{BG}; padding:3px 7px; border-radius:3px;")
    top.addWidget(logo)
    top.addSpacing(12)
    top.addWidget(text("checkout-feedback-autumn ▾", MONO, 13, TXT))
    top.addStretch(1)
    for key, name in (("e_review", "REVIEW"), ("e_ingest", "INGEST"), ("e_calibrate", "CALIBRATE")):
        top.addWidget(_btn(name, "mode", key == mode, key, nav))
    top.addStretch(1)
    top.addWidget(text("●", MONO, 12, MINT))
    top.addWidget(_lab("readers 2/2 · offline · saved 09:41", DIM))
    lay.addLayout(top)
    lay.addWidget(Hairline(LINE))
    sw = QWidget()
    sl = QVBoxLayout(sw)
    sl.setContentsMargins(16, 10, 16, 8)
    sl.setSpacing(4)
    kw = {"cursor": 118}
    kw.update(strip_kw or {})
    sl.addWidget(EvidenceStrip(STRIP, 64, **kw))
    leg = QHBoxLayout()
    leg.addWidget(_lab("R-0001", FAINT))
    leg.addStretch(1)
    for c, t in ((MINT, f"agree {C['agree']}"), (CORAL, f"disagree {C['disagree']}"),
                 ("#6F7A7E", f"unsure {C['uncertain']}"), ("#3B4246", f"open {C['unreviewed']} · height = machine doubt")):
        leg.addWidget(_lab("■ " + t, c))
        leg.addSpacing(10)
    leg.addStretch(1)
    leg.addWidget(_lab("R-0600", FAINT))
    sl.addLayout(leg)
    lay.addWidget(sw)
    lay.addWidget(Hairline(LINE))
    lay.addWidget(body, 1)
    cl = QLineEdit()
    cl.setPlaceholderText("> " + cmd)
    lay.addWidget(cl)
    return page


# --------------------------------------------------------------------------
def _review(nav):
    body = QWidget()
    h = QHBoxLayout(body)
    h.setContentsMargins(16, 14, 16, 14)
    h.setSpacing(14)

    q, ql = _panel(m=0, sp=0)
    q.setFixedWidth(300)
    head = QVBoxLayout()
    head.setContentsMargins(12, 12, 12, 8)
    head.addWidget(_lab("Queue", TXT))
    chips = QHBoxLayout()
    chips.setSpacing(6)
    chips.addWidget(_btn(f"UNSETTLED {C['unsettled_open']}", "chip", True))
    chips.addWidget(_btn(f"OPEN {C['unreviewed']}", "chip", False))
    chips.addWidget(_btn(f"DISAGREE {C['disagree']}", "chip", False))
    chips.addStretch(1)
    head.addLayout(chips)
    ql.addLayout(head)
    ql.addWidget(Hairline(LINE))
    for k, r in enumerate(RECORDS[:10]):
        rw = QFrame()
        rw.setObjectName("qrow")
        bgc = PANEL2 if k == 0 else "transparent"
        rw.setStyleSheet(f"QFrame#qrow {{ background:{bgc}; border-left:2px solid {AMBER if k == 0 else 'transparent'}; }}")
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(12, 7, 12, 7)
        rl.setSpacing(2)
        st = {"unreviewed": ("OPEN", DIM), "accepted": ("AGREE", MINT), "corrected": ("DISAGREE", CORAL),
              "uncertain": ("UNSURE", "#6F7A7E"), "failed": ("FAILED", "#FF3B30")}[r["status"]]
        rl.addLayout(_row(text(r["id"], MONO, 11, TXT if k == 0 else DIM), None, _lab(st[0], st[1], 10)))
        rl.addWidget(text((r["text"] or "input_too_long · 731 > 512 tokens")[:40] + "…", DISPLAY, 13,
                          TXT if k == 0 else DIM))
        ql.addWidget(rw)
    ql.addStretch(1)
    h.addWidget(q)

    rec = RECORDS[0]
    mid = QVBoxLayout()
    mid.setSpacing(14)
    mid.addLayout(_row(_lab(f"{rec['id']} · app_store · export", DIM), None,
                       _lab("▲ split emotion reading", AMBER)))
    big = text(rec["text"], "Segoe UI Variable Display Light", 34, TXT, wrap=True)
    big.setMinimumHeight(130)
    mid.addWidget(big)
    inst = QHBoxLayout()
    inst.setSpacing(14)
    a, al = _panel("panel", 14, 6)
    al.addLayout(_row(_lab("Machine · sentiment", AMBER), None, _lab(f"@{MODELS[0]['rev']}", FAINT)))
    al.addWidget(text("NEG 0.61", DISPLAY_LIGHT, 44, TXT))
    al.addWidget(_lab("margin 0.34 over neutral · settled", DIM))
    al.addSpacing(30)
    al.addWidget(SentimentScale(INST, rec, "negative", 110))
    al.addSpacing(20)
    al.addWidget(_lab("Spread", DIM))
    for nm, v, c in (("neg", 0.61, CORAL), ("neu", 0.27, DIM), ("pos", 0.12, MINT)):
        al.addLayout(_row(_lab(nm, DIM), _bar(v, c), text(f"{v:.2f}", MONO, 12, TXT)))
    al.addStretch(1)
    inst.addWidget(a, 1)
    b, bl = _panel("panel", 14, 6)
    bl.addLayout(_row(_lab("Machine · emotion", AMBER), None, _lab(f"@{MODELS[1]['rev']}", FAINT)))
    bl.addWidget(text("JOY 0.41 / ANGER 0.38", DISPLAY_LIGHT, 30, TXT))
    bl.addWidget(_lab("Δ 0.03 · below 0.50 threshold · unresolved", AMBER))
    bl.addWidget(EmotionRose(INST, {"joy": 0.41, "anger": 0.38, "admiration": 0.12, "sadness": 0.08,
                                    "fear": 0.04, "disgust": 0.03, "neutral": 0.18, "amusement": 0.05,
                                    "gratitude": 0.02}, "anger", 290), 0, Qt.AlignmentFlag.AlignHCenter)
    bl.addStretch(1)
    inst.addWidget(b, 1)
    mid.addLayout(inst, 1)
    h.addLayout(mid, 1)

    op, ol = _panel("panel", 16, 10)
    op.setFixedWidth(380)
    ol.addLayout(_row(_lab("Operator · you", MINT), None, _lab("stored apart from machine", FAINT)))
    ol.addWidget(_lab("Sentiment", DIM))
    g = QGridLayout()
    g.setSpacing(8)
    for i, (k, t, on, ai) in enumerate((("1", "NEG", True, True), ("2", "NEU", False, False),
                                        ("3", "POS", False, False), ("0", "UNSURE", False, False))):
        g.addWidget(_btn(f"{t}\n{k}", "cap", on, ai=ai), 0, i)
    ol.addLayout(g)
    ol.addWidget(_lab("Emotion", DIM))
    g2 = QGridLayout()
    g2.setSpacing(8)
    emos = (("Q", "JOY", False, True), ("W", "AMUSE", False, False), ("E", "ADMIRE", False, False),
            ("A", "ANGER", True, False), ("S", "SAD", False, False), ("D", "FEAR", False, False),
            ("Z", "DISGUST", False, False), ("X", "GRATITUDE", False, False), ("C", "NEUTRAL", False, False))
    for i, (k, t, on, ai) in enumerate(emos):
        g2.addWidget(_btn(f"{t}\n{k}", "cap", on, ai=ai), i // 3, i % 3)
    ol.addLayout(g2)
    ol.addWidget(text("dashed = machine's pick. machine record is never edited.", MONO, 10, FAINT, wrap=True))
    ol.addStretch(1)
    ol.addWidget(_btn("COMMIT && NEXT   ⏎", "commit"))
    ol.addLayout(_row(_lab("N note", FAINT), _lab("← prev", FAINT), _lab("space accept machine", FAINT), None))
    h.addWidget(op)
    return _frame(nav, "e_review", body)


# --------------------------------------------------------------------------
def _ingest(nav):
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(14)
    top, tl = _panel("panel", 18, 10)
    tl.addLayout(_row(_lab("Ingest · support_inbox.csv → message_body · group: channel, product_area",
                           AMBER), None, _lab("recording", CORAL)))
    meters = QHBoxLayout()
    meters.setSpacing(36)
    for n, cap, col in (("087", "/ 186 read", TXT), ("3.1", "rows / s", TXT), ("00:58", "remaining", TXT),
                        ("2", "failed, kept", CORAL), ("3", "marked non-EN", AMBER)):
        c = QVBoxLayout()
        c.setSpacing(0)
        c.addWidget(text(n, DISPLAY_LIGHT, 64, col))
        c.addWidget(_lab(cap, DIM))
        meters.addLayout(c)
    meters.addStretch(1)
    meters.addWidget(_btn("PAUSE"), 0, Qt.AlignmentFlag.AlignBottom)
    meters.addWidget(_btn("STOP · KEEP 87", "stop"), 0, Qt.AlignmentFlag.AlignBottom)
    tl.addLayout(meters)
    tl.addWidget(EvidenceStrip(STRIP, 120, progress=499 / 600, highlight=(412, 600), hl_color=AMBER))
    tl.addWidget(_lab("amber region = this source · rows commit one by one · stop leaves the rest queued, "
                      "resumable, never half-written", FAINT))
    v.addWidget(top)
    log, ll = _panel("panel2", 14, 3)
    ll.addWidget(_lab("Log", TXT))
    lines = [
        ("09:41:07", "R-0499", "NEG 0.88", "fear 0.33 < thr", AMBER),
        ("09:41:07", "R-0500", "POS 0.93", "gratitude 0.91", DIM),
        ("09:41:08", "R-0501", "NEG 0.72", "no emotion ≥ 0.50", AMBER),
        ("09:41:08", "R-0502", "NEU 0.50", "language check: fr?  marked", AMBER),
        ("09:41:08", "R-0503", "—", "input_too_long 731 > 512 · not truncated · kept", CORAL),
        ("09:41:09", "R-0504", "POS 0.49", "approval 0.55 · margin 0.02", AMBER),
        ("09:41:09", "R-0505", "NEG 0.83", "amusement 0.62", DIM),
    ]
    for t, i, s, e, c in lines:
        ll.addLayout(_row(text(t, MONO, 12, FAINT), text(i, MONO, 12, TXT), text(s.ljust(9), MONO, 12, TXT),
                          text(e, MONO, 12, c), None, sp=18))
    ll.addStretch(1)
    v.addWidget(log, 1)
    return _frame(nav, "e_ingest", body, {"progress": 499 / 600, "cursor": None},
                  cmd=":pause    :stop    :review-ready  (review analyzed rows while ingest runs)")


# --------------------------------------------------------------------------
class Calib(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(260)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bands = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.45), (0.45, 0.6), (0.6, 0.8), (0.8, 1.01)]
        w, h = self.width(), self.height() - 46
        p.setPen(QPen(QColor(LINE), 1))
        for k in (0.25, 0.5, 0.75, 1.0):
            y = 8 + h * (1 - k)
            p.drawLine(40, int(y), w, int(y))
            p.setFont(font(MONO, 10))
            p.setPen(QColor(FAINT))
            p.drawText(0, int(y) + 4, f"{int(k * 100)}%")
            p.setPen(QPen(QColor(LINE), 1))
        bw = (w - 40) / len(bands)
        for i, (lo, hi) in enumerate(bands):
            rate, n = band_agreement(lo, hi)
            x = 40 + i * bw
            segs = 20
            for s in range(segs):
                lit = s < rate * segs
                c = QColor((CORAL if lo < 0.3 else MINT) if lit else "#20262A")
                y = 8 + h - (s + 1) * h / segs
                p.fillRect(QRectF(x + bw * 0.18, y + 1.5, bw * 0.64, h / segs - 3), c)
            p.setPen(QColor(TXT))
            p.setFont(font(MONO, 11))
            p.drawText(QRectF(x, 8 + h + 6, bw, 16), Qt.AlignmentFlag.AlignCenter, f"{lo:.2f}–{min(hi, 1):.2f}")
            p.setPen(QColor(FAINT))
            p.drawText(QRectF(x, 8 + h + 22, bw, 16), Qt.AlignmentFlag.AlignCenter, f"{rate * 100:.0f}% n={n}")
        p.end()


def _calibrate(nav):
    body = QWidget()
    h = QHBoxLayout(body)
    h.setContentsMargins(16, 14, 16, 14)
    h.setSpacing(14)
    left, ll = _panel("panel", 18, 10)
    left.setFixedWidth(330)
    ll.addWidget(_lab("Agreement · sentiment", MINT))
    ll.addWidget(Ring(C["rate"], MINT, "#20262A", 210, 10, f"{C['rate'] * 100:.0f}%", TXT, DISPLAY_LIGHT, 54),
                 0, Qt.AlignmentFlag.AlignHCenter)
    ll.addWidget(_lab(f"{C['agree']} / {C['definitive']} definitive · {C['uncertain']} unsure excluded", DIM))
    ll.addSpacing(10)
    ll.addWidget(Hairline(LINE))
    for k, v, c in (("operator", "1 (you)", TXT), ("reviewed", f"{C['reviewed']} / 600", TXT),
                    ("emotion agreement", "61%", TXT), ("failed rows", "2 (kept)", CORAL)):
        ll.addLayout(_row(_lab(k, DIM), None, text(v, MONO, 13, c)))
    ll.addStretch(1)
    ll.addWidget(text("agreement ≠ accuracy. one operator, this text.", MONO, 10, FAINT, wrap=True))
    h.addWidget(left)

    mid = QVBoxLayout()
    mid.setSpacing(14)
    c1, cl1 = _panel("panel", 18, 8)
    cl1.addLayout(_row(_lab("Calibration · agreement by machine certainty", AMBER), None,
                       _lab("coral = unsettled zone (margin < 0.30)", CORAL)))
    cl1.addWidget(Calib(), 1)
    mid.addWidget(c1, 3)
    c2, cl2 = _panel("panel", 18, 6)
    cl2.addWidget(_lab("Per channel · same strip, filtered", AMBER))
    for name, n, rate in by_source():
        cl2.addLayout(_row(text(name.ljust(10), MONO, 12, TXT), _strip_mini(name),
                           text(f"{rate * 100:.0f}%  n={n}", MONO, 12, DIM)))
    cl2.addLayout(_row(text("forum/pricing", MONO, 12, TXT), _lab("n=14 · below 20, not shown as a rate", CORAL), None))
    mid.addWidget(c2, 2)
    h.addLayout(mid, 1)

    right, rl = _panel("panel", 18, 8)
    right.setFixedWidth(330)
    rl.addWidget(_lab("Machine × operator", AMBER))
    grid = QGridLayout()
    grid.setSpacing(4)
    labs = ["NEG", "NEU", "POS"]
    order = ["negative", "neutral", "positive"]
    vals = [[sum(1 for r in DENSE if r["sent"] == a and r["human"] == b and r["status"] in ("agree", "disagree"))
             for b in order] for a in order]
    top = max(vals[i][i] for i in range(3))
    off = max(vals[i][j] for i in range(3) for j in range(3) if i != j)
    for j, l in enumerate(labs):
        grid.addWidget(_lab("you " + l, MINT, 10), 0, j + 1)
        grid.addWidget(_lab("ai " + l, AMBER, 10), j + 1, 0)
    for i in range(3):
        for j in range(3):
            v = vals[i][j]
            cell = text(str(v), DISPLAY_LIGHT, 22, BG if i == j else TXT)
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            a = min(1.0, v / top)
            col = f"rgba(91,227,186,{0.25 + 0.75 * a:.2f})" if i == j else f"rgba(255,106,85,{0.12 + 0.8 * v / off:.2f})"
            cell.setStyleSheet(f"background:{col}; color:{BG if i == j else TXT}; border-radius:3px;")
            cell.setFixedSize(76, 64)
            grid.addWidget(cell, i + 1, j + 1)
    rl.addLayout(grid)
    rl.addSpacing(8)
    rl.addWidget(_lab("Largest off-diagonal", CORAL))
    rl.addWidget(text(f"AI POS → you NEG: {vals[2][0]}\nmostly sarcasm and compliment-then-complaint",
                      MONO, 12, TXT, wrap=True))
    rl.addStretch(1)
    rl.addWidget(_btn("EXPORT CALIBRATION CSV"))
    rl.addWidget(_btn("EXPORT REVIEWED DATASET"))
    h.addWidget(right)
    return _frame(nav, "e_calibrate", body, {"cursor": None},
                  cmd=":band 0.0-0.3  (jump to unsettled rows)    :export    :print")


def _bar(v, c):
    from common import MeterBar
    m = MeterBar(v, c, 6)
    m.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return m


def _strip_mini(src):
    s = EvidenceStrip(STRIP, 22, rows=[r for r in DENSE if r["src"] == src])
    s.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return s


# --------------------------------------------------------------------------
def _probe(nav):
    page = _review(nav)
    ov = QWidget(page)
    ov.setObjectName("dim")
    ov.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    ov.setStyleSheet("QWidget#dim { background: rgba(5,6,7,0.72); }")
    box, bl = _panel("panel", 0, 0)
    box.setFixedWidth(820)
    cmd = QLineEdit(":analyze  Brilliant, another price rise right after you removed offline mode. Truly great work.")
    cmd.setStyleSheet(f"QLineEdit {{ border:none; border-bottom:1px solid {LINE}; font-size:15px; padding:16px; color:{AMBER}; }}")
    bl.addWidget(cmd)
    inner = QHBoxLayout()
    inner.setContentsMargins(18, 16, 18, 16)
    inner.setSpacing(18)
    rec = RECORDS[1]
    c1 = QVBoxLayout()
    c1.addWidget(_lab("Probe · not saved", AMBER))
    c1.addWidget(text("POS 0.57", DISPLAY_LIGHT, 48, TXT))
    c1.addWidget(_lab("margin 0.26 · unsettled", CORAL))
    c1.addWidget(SentimentScale(INST, rec, None, 90))
    inner.addLayout(c1, 1)
    c2 = QVBoxLayout()
    c2.addWidget(_lab("In this project", DIM))
    sim = [r for r in DENSE if r["sent"] == "positive" and r["margin"] < 0.3 and r["status"] in ("agree", "disagree")]
    over = sum(r["status"] == "disagree" for r in sim) / max(1, len(sim))
    c2.addWidget(text(f"Texts the machine read like this\n(POS, margin < 0.30) were overruled\n"
                      f"by you {over * 100:.0f}% of the time (n={len(sim)}).", MONO, 13, TXT, wrap=True))
    c2.addStretch(1)
    c2.addLayout(_row(_btn("ADD TO PROJECT  ⏎"), _btn("DISCARD  esc"), None))
    inner.addLayout(c2, 1)
    bl.addLayout(inner)
    ol = QVBoxLayout(ov)
    ol.addSpacing(170)
    ol.addLayout(_row(None, box, None))
    ol.addStretch(1)
    holder = QWidget()
    g = QGridLayout(holder)
    g.setContentsMargins(0, 0, 0, 0)
    g.addWidget(page, 0, 0)
    ov.setParent(holder)
    g.addWidget(ov, 0, 0)
    return holder


# --------------------------------------------------------------------------
class VU(QWidget):
    def __init__(self, v, col):
        super().__init__()
        self.v, self.col = v, col
        self.setFixedSize(46, 300)

    def paintEvent(self, _):
        p = QPainter(self)
        segs = 30
        for s in range(segs):
            lit = s < self.v * segs
            y = self.height() - (s + 1) * self.height() / segs
            p.fillRect(QRectF(0, y + 2, self.width(), self.height() / segs - 4),
                       QColor(self.col if lit else "#1E2326"))
        p.end()


def _first(nav):
    page = QWidget()
    page.setObjectName("bg")
    page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QHBoxLayout(page)
    lay.setContentsMargins(70, 60, 70, 60)
    lay.setSpacing(50)
    left = QVBoxLayout()
    left.setSpacing(14)
    logo = text("STI", DISPLAY, 22, BG, 700, 1)
    logo.setStyleSheet(f"background:{TXT}; color:{BG}; padding:4px 10px; border-radius:3px;")
    left.addWidget(logo, 0, Qt.AlignmentFlag.AlignLeft)
    left.addSpacing(30)
    left.addWidget(_lab("Reader rack · first run", AMBER, 12))
    left.addWidget(text("Two readers. Fetched once.\nThen nothing leaves this machine.", DISPLAY_LIGHT, 46, TXT))
    left.addWidget(text("The readers are pinned model revisions, about 1 GB, not bundled with the app. "
                        "huggingface.co is the only host ever contacted, and only for this.",
                        DISPLAY, 15, DIM, wrap=True))
    left.addSpacing(16)
    for k, t, d in (("⏎", "fetch now", "resumable · verified against pinned revision"),
                    ("F", "load from folder", "offline machines · exact revision required"),
                    ("L", "later", "import and browse; analysis stays off")):
        left.addLayout(_row(_btn(k), text(t, DISPLAY, 18, TXT), _lab(d, FAINT), None, sp=14))
    left.addStretch(1)
    lay.addLayout(left, 3)
    rack, rl = _panel("panel", 22, 12)
    rack.setFixedWidth(420)
    rl.addWidget(_lab("Rack", DIM))
    ch = QHBoxLayout()
    ch.setSpacing(30)
    for m, v, col, st in ((MODELS[0], 1.0, MINT, "READY"), (MODELS[1], 0.38, AMBER, "191/499 MB")):
        c = QVBoxLayout()
        c.setSpacing(8)
        c.addWidget(VU(v, col), 0, Qt.AlignmentFlag.AlignHCenter)
        c.addWidget(_lab(m["short"], TXT, 12), 0, Qt.AlignmentFlag.AlignHCenter)
        c.addWidget(_lab(st, col, 11), 0, Qt.AlignmentFlag.AlignHCenter)
        c.addWidget(text(f"@{m['rev']}\n{m['license']}", MONO, 10, FAINT), 0, Qt.AlignmentFlag.AlignHCenter)
        ch.addLayout(c)
    rl.addLayout(ch)
    rl.addStretch(1)
    rl.addLayout(_row(_btn("PAUSE"), _btn("STOP", "stop"), None))
    lay.addWidget(rack)
    return page
