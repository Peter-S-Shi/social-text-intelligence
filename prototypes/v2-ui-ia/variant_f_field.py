"""PROTOTYPE - Round 2, Direction F: Field.

Art direction: bold, light, graphic. The project opens on a FIELD: every text
is a mark placed by how the machine read it (x = negative..positive, y = how
sure it was). Rings are still open, dots are agreed, crosses are where you
overruled the machine. The field is both the navigation and the insight:
you select a region (for example the unsettled zone) and review it as a
stack; groups are small multiples of the same field; a quick analysis is a
probe dropped onto the field. Structure: lenses | field | brief.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from common import MODELS, PROJECTS, RECORDS
from common2 import (
    C,
    DENSE,
    DISPLAY,
    DISPLAY_COND,
    MONO,
    EmotionRose,
    FieldPlot,
    Hairline,
    SentimentScale,
    band_agreement,
    by_source,
    font,
    text,
)

KEY = "F"
NAME = "Field (R2)"
SCREENS = [
    ("f_field", "Field: lenses / field / brief"),
    ("f_review", "Select a region, review it as a stack"),
    ("f_groups", "Groups as small multiples"),
    ("f_ingest", "Ingest: new texts land on the field"),
    ("f_probe", "Probe: where would this text land?"),
    ("f_first", "First run: the empty field"),
]

BG = "#FAFAF6"
INK = "#101212"
INK2 = "#5D6262"
FAINT = "#A3A7A4"
LINE = "#E4E4DE"
BLUE = "#2F4BFF"
VERM = "#E8512A"
TEAL = "#169C8C"
SUN = "#FFF0C2"

FIELD = {"band": SUN, "grid": LINE, "axis": INK2, "band_text": "#9A7400", "ring": "#B9BCB8",
         "agree": INK, "disagree": VERM, "uncertain": FAINT, "select": BLUE, "note": INK,
         "probe": BLUE, "probe_fill": "#DCE2FF"}
PEN = {"neg": VERM, "neu": FAINT, "pos": TEAL, "scale": FAINT, "ai": INK, "human": BLUE,
       "grid": LINE, "threshold": FAINT, "label": INK2}

HEAD = "Segoe UI Variable Display Semibold"
HEAD_L = "Segoe UI Variable Display Light"
BODY = "Segoe UI Variable Text"

QSS = f"""
QWidget {{ color: {INK}; }}
QWidget#bg {{ background: {BG}; }}
QFrame#sheet {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; }}
QFrame#ghost {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; }}
QPushButton {{ background: #FFFFFF; border: 1px solid #D6D7D1; border-radius: 18px; padding: 7px 16px;
  font-family: '{BODY}'; font-size: 13px; }}
QPushButton:hover {{ border-color: {INK}; }}
QPushButton[kind="go"] {{ background: {INK}; color: #FFFFFF; border: none; font-weight: 600; padding: 10px 20px; }}
QPushButton[kind="blue"] {{ background: {BLUE}; color: #FFFFFF; border: none; font-weight: 600; padding: 10px 20px; }}
QPushButton[kind="lens"] {{ border: none; border-radius: 6px; text-align: left; padding: 5px 8px; color: {INK2}; }}
QPushButton[kind="lens"][on="true"] {{ background: #ECEEFF; color: {BLUE}; font-weight: 600; }}
QPushButton[kind="judge"] {{ font-family: '{HEAD}'; font-size: 18px; padding: 14px 10px; border-radius: 12px; }}
QPushButton[kind="judge"][on="true"] {{ background: {BLUE}; color: #FFFFFF; border-color: {BLUE}; }}
QPushButton[kind="judge"][ai="true"] {{ border: 2px dashed {INK}; }}
QPushButton[kind="tab"] {{ border: none; background: transparent; color: {INK2}; font-size: 14px; padding: 6px 12px; }}
QPushButton[kind="tab"][on="true"] {{ color: {INK}; border-bottom: 2px solid {INK}; border-radius: 0; font-weight: 600; }}
QLineEdit {{ background: #FFFFFF; border: 1px solid #D6D7D1; border-radius: 22px; padding: 10px 18px;
  font-family: '{BODY}'; font-size: 15px; }}
QProgressBar {{ background: {LINE}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 3px; }}
"""


def theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, c in ((QPalette.ColorRole.Window, BG), (QPalette.ColorRole.Base, "#FFFFFF"),
                    (QPalette.ColorRole.Text, INK), (QPalette.ColorRole.WindowText, INK),
                    (QPalette.ColorRole.Button, "#FFFFFF"), (QPalette.ColorRole.ButtonText, INK),
                    (QPalette.ColorRole.Highlight, BLUE), (QPalette.ColorRole.HighlightedText, "#FFFFFF"),
                    (QPalette.ColorRole.PlaceholderText, FAINT)):
        pal.setColor(role, QColor(c))
    app.setPalette(pal)
    app.setFont(font(BODY, 13))
    app.setStyleSheet(QSS)


def build(screen, nav):
    return {"f_field": _field, "f_review": _review, "f_groups": _groups, "f_ingest": _ingest,
            "f_probe": _probe, "f_first": _first}[screen](nav)


# --------------------------------------------------------------------------
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


def _cap(s, color=INK2):
    return text(s, MONO, 11, color, 400, 1.2, upper=True)


def _sheet(kind="sheet", m=20, sp=10):
    f = QFrame()
    f.setObjectName(kind)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(m, m, m, m)
    lay.setSpacing(sp)
    return f, lay


def _frame(nav, here, body):
    page = QWidget()
    page.setObjectName("bg")
    page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 18, 28, 18)
    lay.setSpacing(12)
    top = QHBoxLayout()
    mark = text("●○✕", MONO, 14, INK)
    top.addWidget(mark)
    top.addSpacing(8)
    top.addWidget(text("Checkout feedback", HEAD, 24, INK))
    top.addWidget(text("  600 texts · "
                       f"{C['reviewed']} judged · {C['disagree']} overruled", BODY, 14, INK2))
    top.addStretch(1)
    for key, name in (("f_field", "Field"), ("f_review", "Review"), ("f_groups", "Groups"), ("f_ingest", "Add texts")):
        top.addWidget(_btn(name, "tab", key == here, key, nav))
    top.addSpacing(14)
    top.addWidget(_btn("Probe a text…", None, None, "f_probe", nav))
    lay.addLayout(top)
    lay.addWidget(body, 1)
    foot = QHBoxLayout()
    foot.addWidget(_cap(f"readers sentiment@{MODELS[0]['rev']} emotion@{MODELS[1]['rev']} · offline · saved", FAINT))
    foot.addStretch(1)
    foot.addWidget(_cap("x = machine polarity · y = machine certainty · ○ open  ● agreed  ✕ overruled", FAINT))
    lay.addLayout(foot)
    return page


def _lenses(active="unsettled"):
    col = QVBoxLayout()
    col.setSpacing(2)
    sections = [
        ("Machine", [("unsettled", f"Unsettled zone   {C['unsettled']}"), ("split", "Split emotion   61"),
                     ("lang", "Not English?   3")]),
        ("You", [("open", f"Open   {C['unreviewed']}"), ("agree", f"Agreed   {C['agree']}"),
                 ("over", f"Overruled   {C['disagree']}"), ("unsure", f"Unsure   {C['uncertain']}")]),
        ("Source", [(s, f"{s}   {sum(1 for r in DENSE if r['src'] == s)}") for s, _n, _ in by_source()]),
    ]
    for title, items in sections:
        col.addSpacing(10)
        col.addWidget(_cap(title))
        col.addSpacing(4)
        for key, label in items:
            col.addWidget(_btn(label, "lens", key == active))
    col.addStretch(1)
    w = QWidget()
    w.setLayout(col)
    w.setFixedWidth(210)
    return w


NOTES = [(0.42, 0.12, "sarcasm & compliment-then-complaint\nmost overrules live here", 40, -70),
         (-0.82, 0.86, "machine sure, you agree", 30, -20),
         (0.0, 0.05, "neutral readings: few, all unsure", -40, -110)]


# --------------------------------------------------------------------------
def _field(nav):
    body = QWidget()
    h = QHBoxLayout(body)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(18)
    h.addWidget(_lenses())
    fs, fl = _sheet(m=10)
    fl.addWidget(FieldPlot(FIELD, notes=NOTES, selection=QRectF(-1, 0, 2, 0.3)), 1)
    h.addWidget(fs, 1)
    brief = QVBoxLayout()
    brief.setSpacing(12)
    lo, lo_n = band_agreement(0, 0.3)
    hi, hi_n = band_agreement(0.3, 1.01)
    brief.addWidget(_cap("What the field says"))
    brief.addWidget(text(f"{C['rate'] * 100:.0f}%", HEAD_L, 84, INK))
    brief.addWidget(text(f"of your {C['definitive']} definitive judgments agree with the machine.", BODY, 14, INK2,
                         wrap=True))
    brief.addWidget(Hairline(LINE))
    brief.addWidget(text(f"{lo * 100:.0f}%", HEAD_L, 56, VERM))
    brief.addWidget(text(f"inside the unsettled zone (n={lo_n}), against {hi * 100:.0f}% outside it (n={hi_n}).",
                         BODY, 14, INK2, wrap=True))
    brief.addWidget(Hairline(LINE))
    brief.addWidget(text(f"{C['unsettled_open']} texts in the zone are still open.", HEAD, 18, INK, wrap=True))
    go = _btn(f"Review the unsettled zone  →", "blue", None, "f_review", nav)
    brief.addWidget(go)
    brief.addStretch(1)
    brief.addWidget(text("Agreement is not accuracy: one reviewer, this text. Unsure judgments are left out.",
                         BODY, 12, FAINT, wrap=True))
    bw = QWidget()
    bw.setLayout(brief)
    bw.setFixedWidth(300)
    h.addWidget(bw)
    return _frame(nav, "f_field", body)


# --------------------------------------------------------------------------
def _review(nav):
    body = QWidget()
    h = QHBoxLayout(body)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(18)
    left = QVBoxLayout()
    left.setSpacing(8)
    left.addWidget(_cap("Selection · unsettled zone · 3 of " + str(C["unsettled_open"])))
    fs, fl = _sheet(m=8)
    fs.setFixedWidth(470)
    sub = [r for r in DENSE if r["margin"] < 0.45]
    fl.addWidget(FieldPlot(FIELD, selection=QRectF(-1, 0, 2, 0.3), subset=sub,
                           probe=(0.26, 0.26, "R-0413 here")), 1)
    left.addWidget(fs, 1)
    left.addLayout(_row(_btn("Change selection"), _btn("Sort: least sure first"), None))
    h.addLayout(left)

    stack = QGridLayout()
    stack.setContentsMargins(0, 0, 0, 0)
    for k in (2, 1):
        g, _ = _sheet("ghost")
        g.setContentsMargins(0, 0, 0, 0)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(18 * k, 0, 18 * k, 0)
        wl.addSpacing(0)
        wl.addWidget(g)
        wl.setStretch(0, 1)
        g.setFixedHeight(40)
        stack.addWidget(wrap, 0, 0, Qt.AlignmentFlag.AlignTop)
    card, cl = _sheet("sheet", 28, 14)
    rec = RECORDS[1]
    cl.addLayout(_row(_cap(f"{rec['id']} · app_store · pricing"), None,
                      _cap("margin 0.26 · unsettled", VERM)))
    cl.addWidget(text(rec["text"], HEAD_L, 32, INK, wrap=True))
    mach = QHBoxLayout()
    mach.setSpacing(18)
    mc = QVBoxLayout()
    mc.addWidget(_cap("Machine read"))
    mc.addWidget(text("leans positive", HEAD, 22, TEAL))
    mc.addWidget(text("0.57 vs 0.31 negative · hears admiration 0.52", BODY, 13, INK2))
    mc.addWidget(SentimentScale(PEN, rec, "negative", 86))
    mach.addLayout(mc, 3)
    mach.addWidget(EmotionRose(PEN, {"admiration": 0.52, "joy": 0.21, "anger": 0.18, "amusement": 0.12,
                                     "disgust": 0.09, "neutral": 0.1, "sadness": 0.05, "fear": 0.02,
                                     "gratitude": 0.03}, "anger", 220), 2)
    cl.addLayout(mach)
    cl.addWidget(Hairline(LINE))
    cl.addWidget(_cap("You", BLUE))
    j = QHBoxLayout()
    j.setSpacing(10)
    for t, on, ai in (("Negative  1", True, False), ("Neutral  2", False, False), ("Positive  3", False, True),
                      ("Not sure  0", False, False)):
        j.addWidget(_btn(t, "judge", on, ai=ai))
    cl.addLayout(j)
    j2 = QHBoxLayout()
    j2.setSpacing(8)
    for t, on, ai in (("anger", True, False), ("admiration", False, True), ("disgust", False, False),
                      ("sadness", False, False), ("joy", False, False), ("neutral", False, False), ("more…", False, False)):
        j2.addWidget(_btn(t, None if not on else "blue", None, ai=ai))
    j2.addStretch(1)
    cl.addLayout(j2)
    cl.addLayout(_row(_cap("dashed = machine's pick · machine record never changes", FAINT), None,
                      _btn("Skip"), _btn("Save & next  ⏎".replace("&", "&&"), "go")))
    wrapc = QWidget()
    wlc = QVBoxLayout(wrapc)
    wlc.setContentsMargins(0, 22, 0, 0)
    wlc.addWidget(card)
    wlc.addStretch(1)
    stack.addWidget(wrapc, 0, 0)
    sw = QWidget()
    sw.setLayout(stack)
    h.addWidget(sw, 1)
    return _frame(nav, "f_review", body)


# --------------------------------------------------------------------------
def _groups(nav):
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(12)
    v.addLayout(_row(text("Same field, split by the columns in your file", HEAD, 22, INK), None,
                     _cap("group by"), _btn("channel ▾"), _btn("Export as image…")))
    g = QHBoxLayout()
    g.setSpacing(16)
    for src, n, rate in by_source():
        s, sl = _sheet(m=14, sp=4)
        sl.addLayout(_row(text(src, HEAD, 18, INK), None, _cap(f"n={n} definitive")))
        fp = FieldPlot(FIELD, subset=[r for r in DENSE if r["src"] == src], compact=True)
        fp.setMinimumHeight(330)
        sl.addWidget(fp, 1)
        sl.addLayout(_row(text(f"{rate * 100:.0f}%", HEAD_L, 54, INK), text("agree", BODY, 14, INK2), None))
        g.addWidget(s, 1)
    s4, l4 = _sheet(m=14, sp=6)
    s4.setFixedWidth(250)
    l4.addWidget(text("forum / pricing", HEAD, 18, INK))
    l4.addWidget(_cap("n=14", VERM))
    l4.addStretch(1)
    l4.addWidget(text("Too few judgments to draw. The field would suggest a pattern that 14 texts cannot "
                      "support.", BODY, 14, INK2, wrap=True))
    l4.addWidget(_btn("Show the 14 texts"))
    l4.addStretch(1)
    g.addWidget(s4)
    v.addLayout(g, 1)
    v.addWidget(text("Groups exist only because your CSV has a channel column. STI never infers who wrote a text "
                     "or which community they belong to.", BODY, 13, FAINT, wrap=True))
    return _frame(nav, "f_groups", body)


# --------------------------------------------------------------------------
def _ingest(nav):
    body = QWidget()
    h = QHBoxLayout(body)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(18)
    s, sl = _sheet(m=24, sp=12)
    s.setFixedWidth(420)
    sl.addWidget(_cap("Adding support_inbox.csv"))
    sl.addWidget(text("188 rows", HEAD_L, 60, INK))
    for k, v, c in (("text column", "message_body", INK), ("group columns", "channel, product_area", INK),
                    ("ready", "186", INK), ("refused", "2: empty; 731 > 512 tokens", VERM),
                    ("not English?", "3, analyzed and marked", "#9A7400")):
        sl.addLayout(_row(_cap(k), None, text(v, BODY, 14, c)))
        sl.addWidget(Hairline(LINE))
    sl.addSpacing(10)
    sl.addLayout(_row(text("87 of 186", HEAD, 22, INK), None, text("about a minute", BODY, 14, INK2)))
    pb = QProgressBar()
    pb.setValue(47)
    sl.addWidget(pb)
    sl.addWidget(text("Each text is saved as it lands. Stop keeps the 87 that have landed; the rest wait.",
                      BODY, 13, INK2, wrap=True))
    sl.addStretch(1)
    sl.addLayout(_row(_btn("Pause"), _btn("Stop, keep 87"), None, _btn("Review what landed →", "go", None,
                                                                        "f_review", nav)))
    h.addWidget(s)
    fs, fl = _sheet(m=10)
    newrows = [r for r in DENSE if r["i"] >= 412 and r["i"] < 412 + 87]
    fl.addWidget(_cap("  new texts landing (rings) · existing project faded"))
    fl.addWidget(FieldPlot(dict(FIELD, ring=BLUE), subset=newrows), 1)
    h.addWidget(fs, 1)
    return _frame(nav, "f_ingest", body)


# --------------------------------------------------------------------------
def _probe(nav):
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(14)
    q = QLineEdit("Brilliant, another price rise right after you removed offline mode. Truly great work.")
    v.addLayout(_row(text("Where would this land?", HEAD, 22, INK), q, _btn("Probe  ⏎", "blue"), sp=14))
    h = QHBoxLayout()
    h.setSpacing(18)
    fs, fl = _sheet(m=10)
    fl.addWidget(FieldPlot(FIELD, probe=(0.26, 0.26, "your text"), notes=NOTES[:1]), 1)
    h.addWidget(fs, 1)
    side = QVBoxLayout()
    side.setSpacing(12)
    sim = [r for r in DENSE if r["sent"] == "positive" and r["margin"] < 0.3 and r["status"] in ("agree", "disagree")]
    over = sum(r["status"] == "disagree" for r in sim) / max(1, len(sim))
    side.addWidget(_cap("Probe · not saved"))
    side.addWidget(text("Leans positive, unsettled", HEAD, 22, INK, wrap=True))
    side.addWidget(SentimentScale(PEN, RECORDS[1], None, 80))
    side.addWidget(Hairline(LINE))
    side.addWidget(text(f"{over * 100:.0f}%", HEAD_L, 64, VERM))
    side.addWidget(text(f"of texts you judged in this part of the field were overruled (n={len(sim)}). "
                        "Read this machine output with care.", BODY, 14, INK2, wrap=True))
    side.addStretch(1)
    side.addLayout(_row(_btn("Discard"), None, _btn("Add to project", "go")))
    sw = QWidget()
    sw.setLayout(side)
    sw.setFixedWidth(320)
    h.addWidget(sw)
    v.addLayout(h, 1)
    return _frame(nav, "f_field", body)


# --------------------------------------------------------------------------
def _first(nav):
    page = QWidget()
    page.setObjectName("bg")
    page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    g = QGridLayout(page)
    g.setContentsMargins(28, 28, 28, 28)
    fs, fl = _sheet(m=10)
    fl.addWidget(FieldPlot(FIELD, subset=[]), 1)
    g.addWidget(fs, 0, 0)
    card, cl = _sheet("sheet", 30, 12)
    card.setFixedWidth(560)
    cl.addWidget(text("●○✕", MONO, 16, INK))
    cl.addWidget(text("The field fills once the two readers are here.", HEAD, 30, INK, wrap=True))
    cl.addWidget(text("They are pinned model revisions (about 1 GB), fetched once from huggingface.co. After that "
                      "nothing leaves this computer.", BODY, 15, INK2, wrap=True))
    for m, pct, st in ((MODELS[0], 100, "ready · verified 3216a57"), (MODELS[1], 38, "191 of 499 MB")):
        cl.addLayout(_row(text(m["short"], HEAD, 16, INK), _cap(f"{m['license']} · @{m['rev']}"), None,
                          text(st, BODY, 13, TEAL if pct == 100 else INK2)))
        pb = QProgressBar()
        pb.setValue(pct)
        cl.addWidget(pb)
    cl.addLayout(_row(_btn("Use a folder (offline)…"), _btn("Later"), None, _btn("Pause")))
    g.addWidget(card, 0, 0, Qt.AlignmentFlag.AlignCenter)
    return page
