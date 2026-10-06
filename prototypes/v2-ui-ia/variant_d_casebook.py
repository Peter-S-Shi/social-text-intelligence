"""PROTOTYPE - Round 2, Direction D: Casebook.

Art direction: an editor's casebook. Warm paper, black ink, one red pen.
The machine's reading is pencil marginalia; your judgment is a red-pen ruling
(uphold / overrule / abstain). Text is set large in a serif like a quoted
exhibit; labels are condensed caps; provenance is monospace. Structure: an
index of casebooks -> a manuscript view (docket, exhibit, margin) -> findings
written as front matter. Every surface carries the evidence strip of the
whole project (one tick per text).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
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
    DISPLAY_COND_LIGHT,
    DISPLAY_LIGHT,
    MONO,
    SERIF,
    SERIF_TEXT,
    EmotionRose,
    EvidenceStrip,
    Hairline,
    SentimentScale,
    band_agreement,
    by_source,
    text,
)

KEY = "D"
NAME = "Casebook (R2)"
SCREENS = [
    ("d_index", "Index of casebooks + loose sheet"),
    ("d_review", "Manuscript: docket / exhibit / marginalia / ruling"),
    ("d_findings", "Findings as front matter"),
    ("d_intake", "Intake slip + live reading"),
    ("d_first", "First run: before the first reading"),
]

PAPER = "#F2EEE5"
PAPER2 = "#E8E2D4"
INK = "#151514"
INK2 = "#57534B"
RULE = "#CDC6B5"
PENCIL = "#86827A"
RED = "#C8372D"

STRIP = {"unreviewed": "#BEB7A7", "agree": INK, "disagree": RED, "uncertain": "#9A958A",
         "failed": RED, "queued": "#D6CFBF", "cursor": RED, "head": RED}
PEN = {"neg": INK, "neu": PENCIL, "pos": INK, "scale": PENCIL, "ai": INK2, "human": RED,
       "grid": RULE, "threshold": PENCIL, "label": INK2}

QSS = f"""
QWidget {{ color: {INK}; }}
QWidget#paper {{ background: {PAPER}; }}
QWidget#paper2 {{ background: {PAPER2}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QPushButton {{ background: transparent; border: none; color: {INK}; font-family: '{DISPLAY_COND}';
  font-size: 13px; letter-spacing: 1px; padding: 6px 2px; text-align: left; }}
QPushButton:hover {{ color: {RED}; }}
QPushButton[kind="ink"] {{ background: {INK}; color: {PAPER}; padding: 9px 18px; }}
QPushButton[kind="ink"]:hover {{ background: #000; color: #fff; }}
QPushButton[kind="red"] {{ color: {RED}; }}
QPushButton[kind="ruling"] {{ font-family: '{DISPLAY_COND_LIGHT}'; font-size: 30px; letter-spacing: 2px;
  color: {PENCIL}; padding: 0 18px 0 0; }}
QPushButton[kind="ruling"][on="true"] {{ color: {RED}; font-family: '{DISPLAY_COND}'; }}
QPushButton[kind="word"] {{ font-family: '{SERIF_TEXT}'; font-size: 17px; letter-spacing: 0; color: {INK2};
  padding: 2px 8px; border-bottom: 1px solid transparent; }}
QPushButton[kind="word"][on="true"] {{ color: {RED}; border-bottom: 2px solid {RED}; }}
QPlainTextEdit {{ background: transparent; border: none; border-bottom: 1px solid {RULE};
  font-family: '{SERIF_TEXT}'; font-size: 18px; }}
QComboBox {{ background: transparent; border: none; border-bottom: 2px solid {INK}; padding: 0 4px;
  font-family: '{SERIF_TEXT}'; font-size: 22px; color: {RED}; min-width: 160px; }}
QComboBox::drop-down {{ border: none; width: 14px; }}
"""


def theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, c in ((QPalette.ColorRole.Window, PAPER), (QPalette.ColorRole.Base, PAPER),
                    (QPalette.ColorRole.Text, INK), (QPalette.ColorRole.WindowText, INK),
                    (QPalette.ColorRole.Button, PAPER), (QPalette.ColorRole.ButtonText, INK),
                    (QPalette.ColorRole.Highlight, RED), (QPalette.ColorRole.HighlightedText, PAPER),
                    (QPalette.ColorRole.PlaceholderText, PENCIL)):
        pal.setColor(role, QColor(c))
    app.setPalette(pal)
    from common2 import font
    app.setFont(font(DISPLAY, 13))
    app.setStyleSheet(QSS)


def build(screen, nav):
    return {"d_index": _index, "d_review": _review, "d_findings": _findings, "d_intake": _intake,
            "d_first": _first}[screen](nav)


# --------------------------------------------------------------------------
def _caps(s, color=INK2, px=12, spacing=2.2, weight=600):
    return text(s, DISPLAY_COND, px, color, weight, spacing, upper=True)


def _btn(t, kind=None, on=None, target=None, nav=None):
    b = QPushButton(t)
    if kind:
        b.setProperty("kind", kind)
    if on is not None:
        b.setProperty("on", "true" if on else "false")
    if target and nav:
        b.clicked.connect(lambda: nav(target))
    b.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return b


def _page(name="paper"):
    w = QWidget()
    w.setObjectName(name)
    w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return w


def _masthead(nav, right=""):
    bar = QHBoxLayout()
    bar.setContentsMargins(0, 0, 0, 0)
    wm = text("SOCIAL TEXT INTELLIGENCE", DISPLAY_COND, 13, INK, 700, 3.5)
    bar.addWidget(wm)
    bar.addSpacing(14)
    bar.addWidget(text("a local casebook for text evidence", SERIF_TEXT, 14, INK2, italic=True))
    bar.addStretch(1)
    if right:
        bar.addWidget(text(right, MONO, 11, PENCIL))
    return bar


# --------------------------------------------------------------------------
def _index(nav):
    page = _page()
    outer = QHBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    main = QVBoxLayout()
    main.setContentsMargins(64, 36, 48, 30)
    main.setSpacing(0)
    main.addLayout(_masthead(nav, "offline · 2 readers ready"))
    main.addSpacing(40)
    main.addWidget(_caps("Index", RED, 13))
    main.addSpacing(6)
    main.addWidget(Hairline(INK, weight=2))
    for k, p in enumerate(PROJECTS):
        row = QVBoxLayout()
        row.setContentsMargins(0, 16, 0, 14)
        row.setSpacing(6)
        h = QHBoxLayout()
        num = text(f"{k + 1:02d}", DISPLAY_LIGHT, 40, PENCIL)
        num.setFixedWidth(78)
        h.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
        tcol = QVBoxLayout()
        tcol.setSpacing(4)
        title = text(p["name"], SERIF, 34, INK)
        tcol.addWidget(title)
        over = [C["disagree"], 0, 3, 9][k]
        ruled = C["reviewed"] if k == 0 else p["reviewed"]
        tcol.addWidget(text(f"{p['records']} texts   ·   {ruled} ruled   ·   "
                            f"{over} overruled   ·   last opened {p['opened']}", MONO, 11, INK2))
        if k == 0:
            tcol.addSpacing(4)
            tcol.addWidget(EvidenceStrip(STRIP, 22))
        h.addLayout(tcol, 1)
        h.addWidget(_btn("OPEN →", target="d_review", nav=nav), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(h)
        main.addLayout(row)
        main.addWidget(Hairline(RULE))
    main.addSpacing(18)
    main.addLayout(_hrow(_btn("+ NEW CASEBOOK FROM A CSV", "ink", target="d_intake", nav=nav),
                         _btn("OPEN A CASEBOOK FILE…"), None))
    main.addStretch(1)
    main.addWidget(text("Casebooks live in this Windows account's local application data and stay until you "
                        "delete them.", SERIF_TEXT, 13, PENCIL, italic=True))
    outer.addLayout(main, 1)

    side = _page("paper2")
    side.setFixedWidth(430)
    sl = QVBoxLayout(side)
    sl.setContentsMargins(34, 104, 34, 30)
    sl.setSpacing(10)
    sl.addWidget(_caps("Loose sheet", RED, 13))
    sl.addWidget(text("Read one text without filing it.", SERIF_TEXT, 15, INK2, italic=True))
    te = QPlainTextEdit("Brilliant, another price rise right after you removed offline mode. Truly great work.")
    te.setFixedHeight(96)
    sl.addWidget(te)
    sl.addLayout(_hrow(text("english · 23 / 512 tokens", MONO, 11, PENCIL), None, _btn("READ IT →", "ink")))
    sl.addSpacing(18)
    sl.addWidget(_caps("The machine's reading", PENCIL))
    sl.addWidget(text("Leans positive, but only just: 0.57 against 0.31. "
                      "It hears admiration. Sarcasm is where it is most often overruled.",
                      SERIF_TEXT, 17, INK2, wrap=True, italic=True))
    sl.addWidget(SentimentScale(PEN, RECORDS[1], None, 70))
    sl.addStretch(1)
    sl.addLayout(_hrow(_btn("DISCARD"), None, _btn("FILE INTO 01 →", "red")))
    outer.addWidget(side)
    return page


def _hrow(*ws):
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(14)
    for w in ws:
        if w is None:
            h.addStretch(1)
        else:
            h.addWidget(w)
    return h


# --------------------------------------------------------------------------
def _topbar(nav, here):
    top = QVBoxLayout()
    top.setSpacing(8)
    h = QHBoxLayout()
    back = _btn("← INDEX", target="d_index", nav=nav)
    h.addWidget(back)
    h.addSpacing(18)
    h.addWidget(text(PROJECTS[0]["name"], SERIF, 22, INK))
    h.addStretch(1)
    for key, name in (("d_review", "MANUSCRIPT"), ("d_findings", "FINDINGS"), ("d_intake", "INTAKE")):
        b = _btn(name, "red" if key == here else None, target=key, nav=nav)
        h.addWidget(b)
        h.addSpacing(10)
    h.addWidget(text("saved · offline", MONO, 11, PENCIL))
    top.addLayout(h)
    return top


def _review(nav):
    page = _page()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(40, 22, 40, 18)
    outer.setSpacing(10)
    outer.addLayout(_topbar(nav, "d_review"))
    strip_row = QHBoxLayout()
    strip_row.addWidget(EvidenceStrip(STRIP, 40, cursor=118), 1)
    outer.addLayout(strip_row)
    legend = QHBoxLayout()
    for c, t in ((INK, f"upheld {C['agree']}"), (RED, f"overruled {C['disagree']}"),
                 ("#9A958A", f"abstained {C['uncertain']}"), ("#BEB7A7", f"awaiting {C['unreviewed']}  (taller = machine less sure)")):
        legend.addWidget(text("▌ " + t, MONO, 11, c))
        legend.addSpacing(14)
    legend.addStretch(1)
    legend.addWidget(text("R-0119 of 600", MONO, 11, INK2))
    outer.addLayout(legend)
    outer.addWidget(Hairline(INK, weight=2))

    body = QHBoxLayout()
    body.setSpacing(0)
    # docket
    dock = QVBoxLayout()
    dock.setContentsMargins(0, 14, 22, 0)
    dock.setSpacing(2)
    dock.addWidget(_caps("Docket · machine unsure first", RED))
    dock.addSpacing(6)
    for k, r in enumerate(RECORDS[:11]):
        mark = {"unreviewed": "○", "accepted": "✓", "corrected": "✕", "uncertain": "—",
                "failed": "!"}[r["status"]]
        col = RED if r["status"] in ("corrected", "failed") else (INK if k == 0 else INK2)
        line = text(f"{mark}  {r['id']}   {(r['text'] or 'refused: too long')[:24]}…", MONO, 11, col)
        if k == 0:
            line.setStyleSheet(f"color:{INK}; background:{PAPER2}; padding:4px 6px; border-left:3px solid {RED};")
        else:
            line.setStyleSheet(f"color:{col}; padding:4px 6px;")
        dock.addWidget(line)
    dock.addStretch(1)
    dw = QWidget()
    dw.setLayout(dock)
    dw.setFixedWidth(290)
    body.addWidget(dw)
    body.addWidget(Hairline(RULE, vertical=True))

    # exhibit
    rec = RECORDS[0]
    ex = QVBoxLayout()
    ex.setContentsMargins(40, 18, 40, 0)
    ex.setSpacing(14)
    ex.addLayout(_hrow(_caps(f"Exhibit {rec['id']}", INK, 13), _caps("app_store · export", PENCIL, 11), None,
                       _caps("split reading", RED, 11)))
    quote = text("“" + rec["text"] + "”", SERIF, 38, INK, wrap=True)
    quote.setMinimumHeight(150)
    ex.addWidget(quote)
    ex.addWidget(_caps("The machine's reading", PENCIL))
    ex.addWidget(text("Negative, 0.61, fairly sure. On emotion it is split: joy 0.41 against anger 0.38, "
                      "a difference it cannot settle, so it should not headline either.",
                      SERIF_TEXT, 19, INK2, wrap=True, italic=True))
    ex.addSpacing(10)
    ex.addWidget(Hairline(RULE))
    ex.addWidget(_caps("Your ruling", RED))
    rl = QHBoxLayout()
    rl.setSpacing(0)
    rl.addWidget(_btn("UPHOLD", "ruling", False))
    rl.addWidget(_btn("OVERRULE", "ruling", True))
    rl.addWidget(_btn("ABSTAIN", "ruling", False))
    rl.addStretch(1)
    ex.addLayout(rl)
    wl = QHBoxLayout()
    wl.setSpacing(2)
    wl.addWidget(text("sentiment", MONO, 11, PENCIL))
    wl.addSpacing(8)
    for w, on in (("negative", True), ("neutral", False), ("positive", False)):
        wl.addWidget(_btn(w, "word", on))
    wl.addSpacing(26)
    wl.addWidget(text("emotion", MONO, 11, PENCIL))
    wl.addSpacing(8)
    for w, on in (("anger", True), ("joy", False), ("sadness", False), ("fear", False), ("disgust", False),
                  ("neutral", False)):
        wl.addWidget(_btn(w, "word", on))
    wl.addStretch(1)
    ex.addLayout(wl)
    note = QPlainTextEdit()
    note.setPlaceholderText("Margin note: why you overruled (optional)")
    note.setFixedHeight(40)
    ex.addWidget(note)
    ex.addStretch(1)
    ex.addWidget(text("U uphold · O overrule · A abstain · 1-3 sentiment · Q-Y emotion · "
                      "Enter file & next · ← previous", MONO, 11, PENCIL))
    exw = QWidget()
    exw.setLayout(ex)
    body.addWidget(exw, 1)
    body.addWidget(Hairline(RULE, vertical=True))

    # margin
    mg = QVBoxLayout()
    mg.setContentsMargins(24, 18, 0, 0)
    mg.setSpacing(8)
    mg.addWidget(_caps("Marginalia · pencil = machine", PENCIL))
    mg.addWidget(SentimentScale(PEN, rec, "negative", 92))
    mg.addSpacing(6)
    rose = EmotionRose(PEN, {"joy": 0.41, "anger": 0.38, "admiration": 0.12, "sadness": 0.08,
                              "fear": 0.04, "disgust": 0.03, "neutral": 0.18, "amusement": 0.05,
                              "gratitude": 0.02}, "anger", 250)
    mg.addWidget(rose, 0, Qt.AlignmentFlag.AlignHCenter)
    mg.addWidget(text("dashed ring = 0.50 threshold; nothing crosses it", SERIF_TEXT, 13, PENCIL, italic=True))
    mg.addStretch(1)
    mg.addWidget(text(f"sentiment@{MODELS[0]['rev']}\nemotion@{MODELS[1]['rev']}\nread 18 Sep 10:02, kept as read",
                      MONO, 10, PENCIL))
    mw = QWidget()
    mw.setLayout(mg)
    mw.setFixedWidth(330)
    body.addWidget(mw)
    outer.addLayout(body, 1)
    return page


# --------------------------------------------------------------------------
class BandChart(QWidget):
    """Agreement by machine-certainty band, drawn as ruled columns."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(250)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bands = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.45), (0.45, 0.6), (0.6, 0.8), (0.8, 1.01)]
        w = self.width()
        top = 34
        h = self.height() - 50 - top
        bw = w / len(bands)
        p.setPen(QPen(QColor(RULE), 1))
        for k in (0.25, 0.5, 0.75, 1.0):
            y = top + h * (1 - k)
            p.drawLine(0, int(y), w, int(y))
        for i, (lo, hi) in enumerate(bands):
            rate, n = band_agreement(lo, hi)
            x = i * bw + bw * 0.22
            bh = h * rate
            col = QColor(RED if lo < 0.3 else INK)
            p.fillRect(QRectF(x, top + h - bh, bw * 0.56, bh), col)
            p.setPen(QColor(INK))
            p.setFont(_f(DISPLAY_LIGHT, 22))
            p.drawText(QRectF(x - 10, top + h - bh - 32, bw * 0.56 + 20, 28), Qt.AlignmentFlag.AlignCenter,
                       f"{rate * 100:.0f}")
            p.setPen(QColor(PENCIL))
            p.setFont(_f(MONO, 10))
            p.drawText(QRectF(i * bw, top + h + 6, bw, 16), Qt.AlignmentFlag.AlignCenter,
                       f"{lo:.2f}–{min(hi, 1):.2f}")
            p.drawText(QRectF(i * bw, top + h + 22, bw, 16), Qt.AlignmentFlag.AlignCenter, f"n={n}")
        p.end()


def _f(fam, px):
    from common2 import font
    return font(fam, px)


def _findings(nav):
    page = _page()
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    inner = _page()
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(40, 22, 40, 30)
    lay.setSpacing(12)
    lay.addLayout(_topbar(nav, "d_findings"))
    lay.addWidget(Hairline(INK, weight=2))
    body = QHBoxLayout()
    body.setSpacing(48)
    left = QVBoxLayout()
    left.setSpacing(12)
    left.addSpacing(10)
    left.addWidget(_caps("Findings · drawn from your rulings so far", RED, 13))
    left.addWidget(text("The machine agrees with you three times in four, and least of all where it is unsure.",
                        SERIF, 44, INK, wrap=True))
    nums = QHBoxLayout()
    nums.setSpacing(42)
    lo_rate, lo_n = band_agreement(0, 0.3)
    hi_rate, hi_n = band_agreement(0.3, 1.01)
    for big, cap in ((f"{C['rate'] * 100:.0f}", f"in 100 rulings upheld\n{C['agree']} of {C['definitive']} definitive"),
                     (f"{lo_rate * 100:.0f}", f"upheld when the machine\nwas unsure (n={lo_n})"),
                     (f"{hi_rate * 100:.0f}", f"upheld when it was\nsure (n={hi_n})")):
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(text(big, DISPLAY_LIGHT, 120, RED if big == f"{lo_rate * 100:.0f}" else INK))
        col.addWidget(text(cap, MONO, 11, INK2))
        nums.addLayout(col)
    nums.addStretch(1)
    left.addLayout(nums)
    left.addSpacing(8)
    left.addWidget(_caps("I. Agreement by how sure the machine was (margin bands)", INK))
    left.addWidget(BandChart())
    left.addWidget(text("Red columns sit in the unsettled zone. Abstentions are left out of every denominator. "
                        "This describes these texts and this reader only; it is not accuracy.",
                        SERIF_TEXT, 14, INK2, wrap=True, italic=True))
    body.addLayout(left, 3)

    right = QVBoxLayout()
    right.setSpacing(10)
    right.addSpacing(16)
    right.addWidget(_caps("II. Overruled, in their own words", INK))
    for r, why in ((RECORDS[1], "machine: positive · you: negative · sarcasm"),
                   (RECORDS[4], "machine: no emotion · you: anger"),
                   (RECORDS[7], "machine: negative · you: positive · slang praise")):
        q = text("“" + r["text"] + "”", SERIF_TEXT, 18, INK, wrap=True, italic=True)
        right.addWidget(q)
        right.addWidget(text("✕ " + why + f"   {r['id']}", MONO, 11, RED))
        right.addSpacing(8)
        right.addWidget(Hairline(RULE))
    right.addSpacing(10)
    right.addWidget(_caps("III. By channel", INK))
    for name, n, rate, small in [(a, b, c, False) for a, b, c in by_source()] + [("forum / pricing", 14, 0.71, True)]:
        right.addLayout(_hrow(text(name, SERIF_TEXT, 16, INK), None,
                              text(f"{rate * 100:.0f}%   n={n}" + ("   too few to generalise" if small else ""),
                                   MONO, 11, RED if small else INK2)))
    right.addStretch(1)
    right.addLayout(_hrow(_btn("EXPORT RULINGS CSV"), _btn("PRINT FINDINGS…", "ink"), None))
    body.addLayout(right, 2)
    lay.addLayout(body, 1)
    sa.setWidget(inner)
    v = QVBoxLayout(page)
    v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(sa)
    return page


# --------------------------------------------------------------------------
def _intake(nav):
    page = _page()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(40, 22, 40, 26)
    lay.setSpacing(12)
    lay.addLayout(_topbar(nav, "d_intake"))
    lay.addWidget(Hairline(INK, weight=2))
    lay.addSpacing(14)
    lay.addWidget(_caps("Intake · support_inbox.csv · 188 rows · 41 KB", RED, 13))
    sent = QHBoxLayout()
    sent.setSpacing(10)
    sent.addWidget(text("Read the text from", SERIF, 30, INK))
    c1 = QComboBox()
    c1.addItems(["message_body", "subject"])
    sent.addWidget(c1)
    sent.addWidget(text(", group it by", SERIF, 30, INK))
    c2 = QComboBox()
    c2.addItems(["channel", "(nothing)"])
    sent.addWidget(c2)
    sent.addWidget(text("and", SERIF, 30, INK))
    c3 = QComboBox()
    c3.addItems(["product_area", "(nothing)"])
    sent.addWidget(c3)
    sent.addWidget(text(".", SERIF, 30, INK))
    sent.addStretch(1)
    lay.addLayout(sent)
    lay.addWidget(text("Groups come only from your columns. The casebook never guesses who wrote a text.",
                       SERIF_TEXT, 14, PENCIL, italic=True))
    lay.addSpacing(16)
    g = QHBoxLayout()
    g.setSpacing(56)
    for n, cap, col in (("186", "ready to read", INK), ("2", "refused, with reasons:\nempty text; 731 tokens > 512", RED),
                        ("3", "possibly not English;\nread, but marked", RED)):
        c = QVBoxLayout()
        c.setSpacing(0)
        c.addWidget(text(n, DISPLAY_LIGHT, 88, col))
        c.addWidget(text(cap, MONO, 11, INK2))
        g.addLayout(c)
    g.addStretch(1)
    lay.addLayout(g)
    lay.addSpacing(20)
    lay.addWidget(_caps("Reading now · 87 of 186 · about a minute left", INK))
    lay.addWidget(EvidenceStrip(STRIP, 64, progress=87 / 186, rows=DENSE[412:598]))
    lay.addLayout(_hrow(text("Each text is filed the moment it is read. Stopping keeps the 87 already read; the "
                             "rest wait, unread, until you resume.", SERIF_TEXT, 15, INK2, italic=True),
                        None, _btn("PAUSE"), _btn("STOP AFTER THIS TEXT", "red")))
    lay.addSpacing(18)
    lay.addWidget(_caps("Just read", PENCIL))
    for r in RECORDS[:5]:
        lay.addLayout(_hrow(text(r["id"], MONO, 11, PENCIL),
                            text("“" + r["text"][:78] + "…”", SERIF_TEXT, 16, INK, italic=True), None,
                            text(("split reading" if "mixed" in r["flags"] else
                                  "unsettled" if "low_margin" in r["flags"] else
                                  "no emotion above threshold" if "fallback" in r["flags"] else r["sent"]),
                                 MONO, 11, RED if r["flags"] else INK2)))
    lay.addStretch(1)
    lay.addLayout(_hrow(None, _btn("START RULING ON WHAT IS READ →", "ink", target="d_review", nav=nav)))
    return page


# --------------------------------------------------------------------------
def _first(nav):
    page = _page()
    lay = QHBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    left = _page()
    ll = QVBoxLayout(left)
    ll.setContentsMargins(72, 46, 56, 40)
    ll.setSpacing(14)
    ll.addLayout(_masthead(nav))
    ll.addSpacing(60)
    ll.addWidget(_caps("Before the first reading", RED, 13))
    ll.addWidget(text("Two readers have to be fetched once. After that, nothing you file ever leaves this "
                      "computer.", SERIF, 40, INK, wrap=True))
    ll.addSpacing(18)
    for i, (m, pct, st) in enumerate(((MODELS[0], 1.0, "fetched and checked against 3216a57"),
                                      (MODELS[1], 0.38, "191 of 499 MB · about 50 s"))):
        ll.addWidget(text(f"[{i + 1}]  {m['name'].split('/')[0]}. {m['name'].split('/')[1]}. "
                          f"Revision {m['rev']}. Licence {m['license']}. {m['size_mb']} MB.",
                          SERIF_TEXT, 17, INK, wrap=True))
        bar = QHBoxLayout()
        bar.setSpacing(0)
        bar.addWidget(Hairline(RED if pct < 1 else INK, weight=3), int(pct * 100))
        if pct < 1:
            bar.addWidget(Hairline(RULE, weight=3), int((1 - pct) * 100))
        ll.addLayout(bar)
        ll.addWidget(text(st, MONO, 11, RED if pct < 1 else INK2))
        ll.addSpacing(8)
    ll.addStretch(1)
    ll.addLayout(_hrow(_btn("PAUSE"), _btn("STOP"), None, _btn("CONTINUE IN THE BACKGROUND →", "ink")))
    lay.addWidget(left, 3)
    side = _page("paper2")
    sl = QVBoxLayout(side)
    sl.setContentsMargins(40, 150, 40, 40)
    sl.setSpacing(14)
    sl.addWidget(_caps("Other ways in", INK))
    for n, t, d in (("i.", "Use a folder you already have", "For machines with no network. Only the exact pinned "
                     "revisions are accepted."),
                    ("ii.", "Not now", "Open and file texts; reading waits until both readers are here."),
                    ("iii.", "Why a download at all?", "The readers are about 1 GB and are not bundled. huggingface.co "
                     "is the only address ever contacted, and only for this.")):
        sl.addWidget(text(f"{n}  {t}", SERIF, 22, INK, wrap=True))
        sl.addWidget(text(d, SERIF_TEXT, 14, INK2, wrap=True, italic=True))
        sl.addSpacing(6)
    sl.addStretch(1)
    sl.addWidget(text("If the fetch breaks, it resumes where it stopped. A half-fetched reader is never used.",
                      MONO, 11, PENCIL, wrap=True))
    lay.addWidget(side, 2)
    return page
