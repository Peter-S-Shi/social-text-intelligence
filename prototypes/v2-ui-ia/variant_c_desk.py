"""PROTOTYPE - Direction C: Review Desk + Report.

Human judgment is the whole product surface. A project opens on a "desk"
that answers "what needs my judgment now"; review is a keyboard-driven,
one-record-at-a-time focus view (Prodigy-like); insights are a written,
paginated report rather than a dashboard. Data/import and quick analysis are
secondary, reached from a slim rail and a Ctrl+K command palette.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from common import (
    ACCENT,
    AGREEMENT,
    BORDER,
    FLAG_TEXT,
    GROUPS,
    MUTED,
    PROJECTS,
    RECORDS,
    SENT,
    SERIF_FONT,
    Badge,
    MeterBar,
    StackBar,
    card,
    hline,
    honest_headline,
    lbl,
    row,
)

KEY = "C"
NAME = "Review Desk + Report"
SCREENS = [
    ("c_desk", "Desk: what needs judgment now"),
    ("c_review", "Focus review: one record, keyboard"),
    ("c_report", "Report: written insights"),
    ("c_data", "Data: sources and import drawer"),
    ("c_palette", "Ctrl+K palette: quick analysis"),
]

RAIL = [("c_desk", "Desk", "⌂"), ("c_review", "Review", "✓"), ("c_report", "Report", "¶"),
        ("c_data", "Data", "≡")]


def build(screen: str, nav):
    body = {"c_desk": _desk, "c_review": _review, "c_report": _report, "c_data": _data,
            "c_palette": _desk}[screen](nav)
    page = QWidget()
    page.setObjectName("page")
    lay = QHBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(_rail("c_desk" if screen == "c_palette" else screen, nav))
    lay.addWidget(body, 1)
    if screen != "c_palette":
        return page
    holder = QWidget()
    g = QGridLayout(holder)
    g.setContentsMargins(0, 0, 0, 0)
    g.addWidget(page, 0, 0)
    g.addWidget(_palette(holder), 0, 0)
    return holder


def _rail(current, nav):
    r = QFrame()
    r.setObjectName("rail")
    r.setFixedWidth(84)
    r.setStyleSheet("QFrame#rail { background:#1B1E1D; }"
                    "QPushButton { color:#B9BDBA; background:transparent; border:none; padding:10px 0;"
                    " font-size:11px; border-radius:6px; }"
                    "QPushButton:hover { background:#2A2E2C; }"
                    "QPushButton[on=\"true\"] { color:#FFFFFF; background:#1F5F4A; }"
                    "QLabel { color:#8C918E; font-size:10px; }")
    lay = QVBoxLayout(r)
    lay.setContentsMargins(8, 14, 8, 12)
    lay.setSpacing(6)
    proj = QPushButton("CF▾")
    proj.setStyleSheet("QPushButton { color:#fff; background:#2A2E2C; font-weight:700; font-size:13px;"
                       " padding:10px 0; border-radius:8px; }")
    proj.setToolTip(PROJECTS[0]["name"])
    lay.addWidget(proj)
    lay.addSpacing(10)
    for key, name, glyph in RAIL:
        b = QPushButton(f"{glyph}\n{name}")
        b.setProperty("on", "true" if key == current else "false")
        b.clicked.connect(lambda _=False, k=key: nav(k))
        lay.addWidget(b)
    lay.addStretch(1)
    pr = QPushButton("⚖\nPractice")
    pr.setToolTip("Decision Practice (only if kept at the UI/IA gate)")
    lay.addWidget(pr)
    lay.addWidget(QLabel("Ctrl+K"), 0, Qt.AlignmentFlag.AlignHCenter)
    return r


def _serif(text, size, weight=400):
    l = QLabel(text)
    l.setWordWrap(True)
    l.setStyleSheet(f"font-family:'{SERIF_FONT}'; font-size:{size}px; font-weight:{weight}; color:#1B1E1D;")
    return l


# --------------------------------------------------------------------------
def _desk(nav):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(56, 40, 56, 30)
    lay.setSpacing(14)
    lay.addLayout(row(lbl(PROJECTS[0]["name"].upper(), "eyebrow"), None,
                      lbl("saved 09:41 · models ready · offline", "faint")))
    lay.addWidget(_serif("229 records are waiting for your judgment.", 34))
    lay.addWidget(lbl("61 of them were flagged as mixed, low-margin, or possibly not English. "
                      "Start there: that is where the models are least reliable.", "muted", True))
    go = QPushButton("Start with flagged records   ↵")
    go.setProperty("kind", "primary")
    go.setMinimumHeight(38)
    go.clicked.connect(lambda: nav("c_review"))
    lay.addLayout(row(go, QPushButton("Review in import order"), None))
    lay.addSpacing(16)
    grid = QHBoxLayout()
    grid.setSpacing(16)
    a = AGREEMENT
    for n, cap, sub in (("359", "judged by you", "of 600 records"),
                        (f"{a['rate'] * 100:.0f}%", "agree with AI on sentiment", f"{a['agree']} of {a['definitive']} definitive"),
                        ("38", "corrections", "12 marked uncertain"),
                        ("2", "rows failed", "too long for the models; kept")):
        c, cl = card("card", 16, 2)
        big = _serif(n, 30)
        cl.addWidget(big)
        cl.addWidget(lbl(cap, "h3"))
        cl.addWidget(lbl(sub, "faint"))
        grid.addWidget(c)
    lay.addLayout(grid)
    lay.addSpacing(10)
    lay.addWidget(lbl("Recently judged", "h3"))
    for r in [x for x in RECORDS if x["human"]][:4]:
        h = r["human"]
        verdict = "uncertain" if h["sent"] is None else f"{h['sent']} · {h['emo']}"
        changed = r["status"] == "corrected"
        lay.addLayout(row(lbl(r["id"], "mono"), lbl(r["text"][:80], None),
                          None, Badge("you corrected" if changed else r["status"], "warn" if changed else "human"),
                          lbl(verdict, "muted")))
    lay.addStretch(1)
    return w


def _key(k, text):
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(6)
    kb = QLabel(k)
    kb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    kb.setMinimumWidth(22)
    kb.setStyleSheet("font-family:'Cascadia Mono'; font-size:11px; border:1px solid #CFCFC8;"
                     " border-bottom-width:2px; border-radius:3px; padding:1px 5px; background:#fff;")
    l.addWidget(kb)
    l.addWidget(lbl(text, "muted"))
    return w


def _choice(text, key, on=False, ai=False):
    b = QPushButton(f"{text}   {key}")
    b.setCheckable(True)
    b.setChecked(on)
    style = ("QPushButton { padding:8px 14px; border-radius:16px; border:1px solid #CFCFC8; background:#fff; }"
             "QPushButton:checked { background:#1F5F4A; border-color:#1F5F4A; color:white; font-weight:600; }")
    if ai and not on:
        style += "QPushButton { border:1px dashed #4A5568; }"
    b.setStyleSheet(style)
    return b


def _review(nav):
    w = QWidget()
    outer = QVBoxLayout(w)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    top = QFrame()
    top.setObjectName("top")
    top.setStyleSheet(f"QFrame#top {{ background:#fff; border-bottom:1px solid {BORDER}; }}")
    tl = QHBoxLayout(top)
    tl.setContentsMargins(28, 10, 28, 10)
    tl.addWidget(lbl("Flagged for a second look", "h3"))
    tl.addWidget(lbl("  1 of 61", "muted"))
    tl.addStretch(1)
    strip = QHBoxLayout()
    strip.setSpacing(3)
    for i in range(40):
        d = QFrame()
        d.setFixedSize(9, 9)
        c = "#1F5F4A" if i < 0 else ("#1B1E1D" if i == 0 else "#DADBD6")
        d.setStyleSheet(f"background:{c}; border-radius:2px;")
        strip.addWidget(d)
    tl.addLayout(strip)
    tl.addSpacing(16)
    tl.addWidget(QPushButton("Queue ▾"))
    outer.addWidget(top)

    rec = RECORDS[0]
    body = QWidget()
    bl = QVBoxLayout(body)
    bl.setContentsMargins(140, 40, 140, 20)
    bl.setSpacing(18)
    bl.addLayout(row(lbl(rec["id"], "mono"), Badge(rec["src"]), Badge(rec["topic"]), None,
                     Badge("Mixed signal", "warn")))
    bl.addWidget(_serif("“" + rec["text"] + "”", 26))
    bl.addWidget(hline())

    ai, al = card("ai", 14, 6)
    al.addLayout(row(lbl("THE MODELS READ IT AS", "eyebrow"), None, lbl("sentiment@3216a57 · emotion@d750483", "mono")))
    al.addWidget(lbl(honest_headline(rec), "h3"))
    al.addWidget(StackBar([(v, SENT[n]) for n, v in zip(("negative", "neutral", "positive"), rec["scores"])], 6))
    al.addWidget(lbl(f"{FLAG_TEXT['mixed'][1]}  Scores ▸", "muted", True))
    bl.addWidget(ai)

    bl.addWidget(lbl("YOUR JUDGMENT", "eyebrow"))
    s = QHBoxLayout()
    s.setSpacing(8)
    s.addWidget(lbl("Sentiment", "h3"))
    s.addSpacing(16)
    s.addWidget(_choice("negative", "1", on=True))
    s.addWidget(_choice("neutral", "2"))
    s.addWidget(_choice("positive", "3"))
    s.addWidget(_choice("not sure", "0"))
    s.addStretch(1)
    bl.addLayout(s)
    e = QHBoxLayout()
    e.setSpacing(8)
    e.addWidget(lbl("Emotion", "h3"))
    e.addSpacing(30)
    for name, k, on, ai_ in (("anger", "Q", True, False), ("joy", "W", False, True), ("sadness", "E", False, False),
                             ("fear", "R", False, False), ("disgust", "T", False, False), ("neutral", "Y", False, False)):
        e.addWidget(_choice(name, k, on, ai_))
    e.addStretch(1)
    bl.addLayout(e)
    bl.addWidget(lbl("Dashed outline = the AI's pick. Your choice is stored next to it; the AI record never changes.",
                     "faint"))
    bl.addStretch(1)
    keys = QHBoxLayout()
    keys.setSpacing(22)
    for k, t in (("A", "accept AI for both"), ("U", "not sure"), ("N", "add note"), ("↵", "save & next"),
                 ("←", "previous"), ("Esc", "leave queue")):
        keys.addWidget(_key(k, t))
    keys.addStretch(1)
    bl.addLayout(keys)
    outer.addWidget(body, 1)
    return w


def _report(nav):
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    paper = QWidget()
    paper.setObjectName("paper")
    paper.setStyleSheet("QWidget#paper { background:#FBFBF8; }")
    lay = QVBoxLayout(paper)
    lay.setContentsMargins(150, 40, 150, 40)
    lay.setSpacing(14)
    lay.addLayout(row(lbl("REPORT · DRAFT FROM CURRENT REVIEWS", "eyebrow"), None,
                      QPushButton("Export CSV"), QPushButton("Save as PDF…")))
    lay.addWidget(_serif("How far the models agree with you on checkout feedback", 32))
    a = AGREEMENT
    lay.addWidget(lbl(f"Written from {a['reviewed']} human judgments out of {a['total']} records "
                      f"(updated 09:41). Agreement is not accuracy: it describes this text and this reviewer.",
                      "muted", True))
    lay.addWidget(hline())
    nums = QHBoxLayout()
    nums.setSpacing(40)
    for n, cap in ((f"{a['rate'] * 100:.0f}%", f"sentiment agreement\n{a['agree']} of {a['definitive']} definitive reviews"),
                   (f"{a['emo_rate'] * 100:.0f}%", f"dominant-emotion agreement\n{a['emo_agree']} of {a['emo_definitive']}"),
                   ("23%", "of corrections were sarcasm\nread as positive (9 of 38)")):
        col = QVBoxLayout()
        col.addWidget(_serif(n, 56, 300))
        col.addWidget(lbl(cap, "muted"))
        nums.addLayout(col)
    nums.addStretch(1)
    lay.addLayout(nums)
    lay.addWidget(_serif("01  Where the models are weakest", 20))
    lay.addWidget(lbl("Sarcastic praise and complaints that open with a compliment are the main source of "
                      "disagreement. Treat positive readings of pricing feedback with care.", None, True))
    for name, n, sa_, _ea, small in GROUPS:
        r = QHBoxLayout()
        nm = lbl(name, None)
        nm.setFixedWidth(140)
        r.addWidget(nm)
        r.addWidget(MeterBar(sa_, "#9A9E9B" if small else ACCENT, 4), 1)
        v = lbl(f"{sa_ * 100:.0f}%   n={n}", "mono")
        v.setFixedWidth(110)
        r.addWidget(v)
        b = Badge("too few to generalise", "warn") if small else QLabel("")
        b.setFixedWidth(140)
        r.addWidget(b)
        lay.addLayout(r)
    lay.addWidget(_serif("02  Representative cases", 20))
    for rec, why in ((RECORDS[1], "AI positive → you: negative (sarcasm)"),
                     (RECORDS[4], "AI neutral fallback → you: anger")):
        q, ql = card("card", 14, 4)
        ql.addWidget(_serif("“" + rec["text"] + "”", 16))
        ql.addWidget(lbl(f"{rec['id']} · {why}", "faint"))
        lay.addWidget(q)
    lay.addWidget(lbl("Method: compact labels from two pinned local models; uncertain reviews excluded from "
                      "denominators; groups come only from columns in your file.", "faint", True))
    lay.addStretch(1)
    sa.setWidget(paper)
    return sa


def _data(nav):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    main = QVBoxLayout()
    main.setContentsMargins(40, 32, 24, 24)
    main.setSpacing(12)
    main.addWidget(_serif("Data in this project", 26))
    t = QTableWidget(3, 5)
    t.setHorizontalHeaderLabels(["Source", "Rows", "Analyzed", "Failed", "Added"])
    t.verticalHeader().hide()
    t.setShowGrid(False)
    for i, vals in enumerate((("app_store_autumn.csv", "412", "412", "0", "18 Sep"),
                              ("support_inbox.csv", "188", "186", "2", "Today"),
                              ("Quick analyses added by hand", "3", "3", "0", "various"))):
        for j, v in enumerate(vals):
            t.setItem(i, j, QTableWidgetItem(v))
        t.setRowHeight(i, 34)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    t.setFixedHeight(140)
    main.addWidget(t)
    main.addWidget(lbl("Project file: %LOCALAPPDATA%\\SocialTextIntelligence\\projects\\checkout-feedback.sti", "mono"))
    main.addLayout(row(QPushButton("Export reviewed dataset…"), _danger("Delete project…"), None))
    main.addStretch(1)
    lay.addLayout(main, 1)

    drawer = QFrame()
    drawer.setObjectName("drawer")
    drawer.setFixedWidth(420)
    drawer.setStyleSheet(f"QFrame#drawer {{ background:#fff; border-left:1px solid {BORDER}; }}")
    dl = QVBoxLayout(drawer)
    dl.setContentsMargins(22, 28, 22, 22)
    dl.setSpacing(10)
    dl.addWidget(lbl("Add a CSV", "h2"))
    dl.addWidget(lbl("support_inbox_october.csv · 96 rows", "muted"))
    dl.addLayout(row(lbl("Text column", "h3"), None, lbl("message_body ▾", None)))
    dl.addLayout(row(lbl("Group columns", "h3"), None, lbl("channel, product_area ▾", None)))
    dl.addWidget(hline())
    dl.addWidget(lbl("✓ 94 ready   × 1 empty   × 1 too long   ! 0 non-English", None))
    wf, wl = card("warn", 10, 2)
    wl.addWidget(lbl("New rows join the review queue after analysis. Your existing judgments are untouched.",
                     None, True))
    dl.addWidget(wf)
    dl.addStretch(1)
    go = QPushButton("Add and analyze 94 rows")
    go.setProperty("kind", "primary")
    dl.addLayout(row(QPushButton("Cancel"), None, go))
    lay.addWidget(drawer)
    return w


def _danger(t):
    b = QPushButton(t)
    b.setProperty("kind", "danger")
    return b


def _palette(parent):
    ov = QWidget(parent)
    ov.setObjectName("dim")
    ov.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    ov.setStyleSheet("QWidget#dim { background: rgba(20,24,22,0.30); }")
    box, bl = card("card", 0, 0)
    box.setFixedWidth(680)
    q = QLineEdit("> analyze  Fine.")
    q.setStyleSheet("QLineEdit { border:none; border-bottom:1px solid #DFDFD9; border-radius:0;"
                    " font-size:16px; padding:14px 16px; }")
    bl.addWidget(q)
    inner = QVBoxLayout()
    inner.setContentsMargins(16, 12, 16, 14)
    inner.setSpacing(8)
    rec = RECORDS[9]
    inner.addWidget(lbl("QUICK ANALYSIS · NOT SAVED", "eyebrow"))
    inner.addWidget(lbl(honest_headline(rec), "h3"))
    inner.addWidget(StackBar([(v, SENT[n]) for n, v in zip(("negative", "neutral", "positive"), rec["scores"])], 6))
    inner.addWidget(lbl("One-word texts carry little signal; read this as weak evidence.", "muted"))
    inner.addLayout(row(QPushButton("Add to this project as a record"), QPushButton("Copy result"), None))
    inner.addWidget(hline())
    for cmd, k in (("Go to next unreviewed", "N"), ("Open report", "Ctrl+R"),
                   ("Add a CSV to this project…", "Ctrl+I"), ("Switch project…", "Ctrl+O"),
                   ("Model manager…", "")):
        inner.addLayout(row(lbl(cmd, None), None, lbl(k, "mono")))
    bl.addLayout(inner)
    ol = QVBoxLayout(ov)
    ol.addSpacing(110)
    ol.addLayout(row(None, box, None))
    ol.addStretch(1)
    return ov
