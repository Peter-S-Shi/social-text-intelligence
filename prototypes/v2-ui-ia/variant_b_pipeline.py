"""PROTOTYPE - Direction B: Guided Evidence Pipeline.

A project is a linear pipeline: Import -> Analyze -> Review -> Insights ->
Export. A stage rail sits at the top of every project screen; the body shows
one stage at a time with one primary action in a fixed bottom action bar.
Optimised for legibility and first-time / reviewer comprehension; trades away
multi-pane density.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
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
    STATUS_TEXT,
    Badge,
    MeterBar,
    StackBar,
    card,
    hline,
    honest_headline,
    lbl,
    row,
    sentiment_scores_widget,
    status_dot,
    wrap_layout,
)

KEY = "B"
NAME = "Guided Pipeline"
SCREENS = [
    ("b_home", "Home: project cards + try-one-text"),
    ("b_import", "Stage 1 Import: mapping + validation"),
    ("b_analyze", "Stage 2 Analyze: progress + cancel"),
    ("b_review", "Stage 3 Review: list + judgment"),
    ("b_insights", "Stage 4 Insights: stage report"),
]

STAGES = [("b_import", "Import", "2 sources · 600 rows"),
          ("b_analyze", "Analyze", "598 analyzed · 2 failed"),
          ("b_review", "Review", "359 / 598 reviewed"),
          ("b_insights", "Insights", "ready"),
          (None, "Export", "2 exports")]


def build(screen: str, nav):
    if screen == "b_home":
        return _home(nav)
    body = {"b_import": _import, "b_analyze": _analyze, "b_review": _review,
            "b_insights": _insights}[screen]()
    return _project_frame(screen, nav, body)


def _primary(text):
    b = QPushButton(text)
    b.setProperty("kind", "primary")
    b.setMinimumHeight(34)
    return b


# --------------------------------------------------------------------------
def _home(nav):
    page = QWidget()
    page.setObjectName("page")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(48, 36, 48, 30)
    lay.setSpacing(14)
    lay.addLayout(row(lbl("SOCIAL TEXT INTELLIGENCE", "eyebrow"), None,
                      lbl("● models ready · offline", "faint"), QPushButton("Settings")))
    lay.addWidget(lbl("Your projects", "h1"))
    lay.addWidget(lbl("Each project keeps its imported text, the AI record, and your review decisions "
                      "on this computer until you delete it.", "muted"))
    grid = QGridLayout()
    grid.setSpacing(14)
    for i, p in enumerate(PROJECTS[:3]):
        c, cl = card("card", 16, 8)
        c.setMinimumHeight(170)
        cl.addWidget(lbl(p["name"], "h2", True))
        cl.addWidget(lbl(f"{p['records']} records · opened {p['opened']}", "muted"))
        cl.addStretch(1)
        stages = QHBoxLayout()
        stages.setSpacing(4)
        done = 4 if p["reviewed"] == p["records"] else 2
        for j, (_, name, _) in enumerate(STAGES):
            seg = QLabel(name)
            seg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            on = j < done
            cur = j == done
            seg.setStyleSheet(
                f"font-size:11px; padding:3px; border-radius:3px;"
                f" background:{'#1F5F4A' if on else ('#E3EEE9' if cur else '#EEEEEA')};"
                f" color:{'white' if on else ('#1F5F4A' if cur else '#9A9E9B')}; font-weight:600;")
            stages.addWidget(seg)
        cl.addLayout(stages)
        nxt = "Continue review" if p["reviewed"] < p["records"] else "Open insights"
        b = _primary(nxt + "  →")
        b.clicked.connect(lambda _=False: nav("b_review"))
        cl.addLayout(row(lbl(f"{p['reviewed']} reviewed", "faint"), None, b))
        grid.addWidget(c, 0, i)
    new, nl = card("sunken", 16, 8)
    new.setMinimumHeight(170)
    nl.addStretch(1)
    nb = QPushButton("+  New project from CSV…")
    nb.clicked.connect(lambda: nav("b_import"))
    nl.addWidget(nb, 0, Qt.AlignmentFlag.AlignCenter)
    nl.addWidget(lbl("Starts at stage 1, Import", "faint"), 0, Qt.AlignmentFlag.AlignCenter)
    nl.addStretch(1)
    grid.addWidget(new, 0, 3)
    lay.addLayout(grid)

    lay.addSpacing(10)
    sand, sl = card("card", 18, 10)
    sl.addLayout(row(lbl("Try one text", "h2"), Badge("not saved"), None,
                     lbl("A sandbox outside any project. Use it to see how the models read a sentence.", "muted")))
    te = QPlainTextEdit("Brilliant, another price rise right after you removed offline mode. Truly great work.")
    te.setFixedHeight(60)
    rec = RECORDS[1]
    res, rl = card("ai", 12, 4)
    rl.addWidget(lbl("AI RECORD", "eyebrow"))
    rl.addWidget(lbl(honest_headline(rec), "h3", True))
    rl.addWidget(StackBar([(v, SENT[n]) for n, v in zip(("negative", "neutral", "positive"), rec["scores"])]))
    rl.addWidget(lbl(f"<b>{FLAG_TEXT['low_margin'][0]}.</b> {FLAG_TEXT['low_margin'][1]} "
                     "Sarcasm is a known weak spot.", "muted", True))
    h = QHBoxLayout()
    left = QVBoxLayout()
    left.addWidget(te)
    left.addLayout(row(lbl("English only · 512 model tokens", "faint"), None, _primary("Analyze")))
    h.addLayout(left, 1)
    h.addSpacing(12)
    h.addWidget(res, 1)
    sl.addLayout(h)
    lay.addWidget(sand)
    lay.addStretch(1)
    return page


# --------------------------------------------------------------------------
def _rail(current, nav):
    bar = QFrame()
    bar.setStyleSheet(f"QFrame#rail {{ background:#FFFFFF; border-bottom:1px solid {BORDER}; }}")
    bar.setObjectName("rail")
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(24, 10, 24, 10)
    lay.setSpacing(0)
    keys = [k for k, *_ in STAGES]
    cur_i = keys.index(current)
    for i, (key, name, sub) in enumerate(STAGES):
        btn = QPushButton()
        btn.setFlat(True)
        done = i < cur_i
        on = i == cur_i
        num = "✓" if done else str(i + 1)
        btn.setText(f"  {num}   {name}\n        {sub}")
        btn.setStyleSheet(
            "QPushButton { text-align:left; border:none; padding:6px 14px; border-radius:6px;"
            f" background:{'#E3EEE9' if on else 'transparent'};"
            f" color:{'#1F5F4A' if (on or done) else '#686D6A'}; font-weight:{600 if on else 400}; }}"
            "QPushButton:hover { background:#F0F0EB; }")
        if key:
            btn.clicked.connect(lambda _=False, k=key: nav(k))
        lay.addWidget(btn)
        if i < len(STAGES) - 1:
            arrow = QLabel("——")
            arrow.setStyleSheet("color:#C9CBC6; padding:0 4px;")
            lay.addWidget(arrow)
    lay.addStretch(1)
    return bar


def _project_frame(screen, nav, body):
    page = QWidget()
    page.setObjectName("page")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    top = QFrame()
    top.setObjectName("top")
    top.setStyleSheet("QFrame#top { background:#FFFFFF; }")
    tl = QHBoxLayout(top)
    tl.setContentsMargins(24, 12, 24, 0)
    back = QPushButton("←  Projects")
    back.setProperty("kind", "flat")
    back.clicked.connect(lambda: nav("b_home"))
    tl.addWidget(back)
    tl.addWidget(lbl(PROJECTS[0]["name"], "h2"))
    tl.addStretch(1)
    tl.addWidget(lbl("saved 09:41 · ● models ready · offline", "faint"))
    tl.addWidget(QPushButton("Project ▾"))
    lay.addWidget(top)
    lay.addWidget(_rail(screen, nav))
    inner = QWidget()
    il = QVBoxLayout(inner)
    il.setContentsMargins(32, 20, 32, 12)
    il.addWidget(body)
    lay.addWidget(inner, 1)

    actions = {
        "b_import": ("Back", "Analyze 586 valid rows  →", "b_analyze",
                     "2 invalid rows will be kept as failed records with their reason."),
        "b_analyze": ("Run in background", "Continue to Review  →", "b_review",
                      "You can start reviewing analyzed rows while the rest finish."),
        "b_review": ("Previous", "Save & next  Enter", None, "229 unreviewed · 61 flagged for a second look"),
        "b_insights": ("Back to Review", "Export reviewed dataset…", None,
                       "Exports include the AI record, your judgment, provenance and failures."),
    }[screen]
    ab = QFrame()
    ab.setObjectName("actionbar")
    ab.setStyleSheet(f"QFrame#actionbar {{ background:#FFFFFF; border-top:1px solid {BORDER}; }}")
    al = QHBoxLayout(ab)
    al.setContentsMargins(32, 10, 32, 10)
    al.addWidget(QPushButton(actions[0]))
    al.addSpacing(12)
    al.addWidget(lbl(actions[3], "muted"))
    al.addStretch(1)
    p = _primary(actions[1].replace("&", "&&"))
    if actions[2]:
        p.clicked.connect(lambda: nav(actions[2]))
    al.addWidget(p)
    lay.addWidget(ab)
    return page


# --------------------------------------------------------------------------
def _import():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    lay.addWidget(lbl("Bring text into this project", "h1"))
    h = QHBoxLayout()
    h.setSpacing(16)
    drop, dl = card("sunken", 18, 6)
    drop.setFixedWidth(330)
    dl.addWidget(lbl("✓  support_inbox.csv", "h3"))
    dl.addWidget(lbl("188 rows · 41 KB · UTF-8", "muted"))
    dl.addWidget(QPushButton("Choose a different file…"))
    dl.addWidget(hline())
    dl.addWidget(lbl("Which column holds the text?", "h3"))
    c1 = QComboBox()
    c1.addItems(["message_body", "subject", "channel"])
    dl.addWidget(c1)
    dl.addWidget(lbl("Optional grouping columns", "h3"))
    for col, on in (("channel", True), ("product_area", True), ("created_at", False)):
        dl.addWidget(lbl(("☑ " if on else "☐ ") + col, None))
    dl.addWidget(lbl("Groups are only what your file says; STI never infers communities.", "faint", True))
    dl.addStretch(1)
    h.addWidget(drop)

    right = QVBoxLayout()
    checks = QHBoxLayout()
    for n, cap, kind in (("186", "ready to analyze", "ok"), ("2", "invalid (empty / too long)", "err"),
                         ("3", "look non-English", "warn")):
        c, cl = card("card", 12, 0)
        big = QLabel(n)
        big.setStyleSheet("font-size:26px; font-weight:300;")
        cl.addWidget(big)
        cl.addWidget(lbl(cap, "muted"))
        checks.addWidget(c)
    right.addLayout(checks)
    wf, wl = card("warn", 10, 4)
    wl.addWidget(lbl("<b>3 rows look non-English.</b> The models are English-only. "
                     "They will be analyzed and marked 'Not English?' so you can exclude them in Review.", None, True))
    wl.addWidget(lbl("◉ Analyze and mark     ○ Skip them", "muted"))
    right.addWidget(wf)
    t = QTableWidget(8, 4)
    t.setHorizontalHeaderLabels(["Row", "message_body", "channel", "Check"])
    t.verticalHeader().hide()
    t.setShowGrid(False)
    rows = [(r["text"] or "(1 410 characters)", r["src"]) for r in RECORDS[:8]]
    for i, (txt, ch) in enumerate(rows):
        t.setItem(i, 0, QTableWidgetItem(str(i + 2)))
        t.setItem(i, 1, QTableWidgetItem(txt))
        t.setItem(i, 2, QTableWidgetItem(ch))
        chk = "not English?" if i == 6 else "ready"
        it = QTableWidgetItem(chk)
        it.setForeground(Qt.GlobalColor.darkYellow if i == 6 else Qt.GlobalColor.darkGreen)
        t.setItem(i, 3, it)
    t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    t.horizontalHeader().resizeSection(0, 50)
    right.addWidget(lbl("Preview (first 8 of 188)", "h3"))
    right.addWidget(t, 1)
    h.addLayout(right, 1)
    lay.addLayout(h, 1)
    return w


def _analyze():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(14)
    lay.addWidget(lbl("Analyzing on this computer", "h1"))
    lay.addWidget(lbl("Nothing is uploaded. Each row is saved to the project as soon as it is analyzed.", "muted"))
    big, bl = card("card", 24, 10)
    bl.addLayout(row(lbl("87", None), lbl("of 186 rows", "muted"), None,
                     lbl("about 1 min left · 3.1 rows/s", "muted")))
    bl.itemAt(0).layout().itemAt(0).widget().setStyleSheet("font-size:44px; font-weight:300;")
    pb = QProgressBar()
    pb.setValue(47)
    bl.addWidget(pb)
    stats = QHBoxLayout()
    for n, cap in (("85", "analyzed"), ("2", "failed (kept with reason)"), ("3", "marked not English?"),
                   ("99", "queued")):
        stats.addWidget(lbl(f"<span style='font-size:18px'>{n}</span>  {cap}", "muted"))
    bl.addLayout(stats)
    cancel = QPushButton("Cancel analysis…")
    cancel.setProperty("kind", "danger")
    bl.addLayout(row(QPushButton("Pause"), cancel, None,
                     lbl("Cancel keeps the 87 finished rows; the rest stay queued and can be resumed.", "faint")))
    lay.addWidget(big)
    lay.addWidget(lbl("Just analyzed", "h3"))
    lst = QListWidget()
    for r in RECORDS[:6]:
        it = QListWidgetItem(f"{r['id']}   {honest_headline(r)}   —   {r['text'][:70]}")
        lst.addItem(it)
    lay.addWidget(lst, 1)
    return w


def _review():
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)
    left = QVBoxLayout()
    f = QComboBox()
    f.addItems(["Unreviewed (229)", "Flagged for a second look (61)", "Corrected (38)", "Uncertain (12)", "All (600)"])
    left.addWidget(f)
    lst = QListWidget()
    lst.setFixedWidth(360)
    lst.setStyleSheet("QListWidget::item { padding:8px 6px; border-bottom:1px solid #EFEFEA; }")
    for r in RECORDS[:11]:
        mark = {"unreviewed": "○", "accepted": "●", "corrected": "◑", "uncertain": "?",
                "failed": "×"}[r["status"]]
        lst.addItem(QListWidgetItem(f"{mark}  {r['id']}  {r['text'][:42]}…"))
    lst.setCurrentRow(0)
    left.addWidget(lst, 1)
    lay.addLayout(left)

    rec = RECORDS[0]
    main = QVBoxLayout()
    main.setSpacing(12)
    main.addLayout(row(lbl(rec["id"], "h2"), Badge(rec["src"]), Badge(rec["topic"]), None,
                       lbl("1 / 229", "muted")))
    txt = lbl(rec["text"], None, True)
    txt.setStyleSheet("font-size:18px; padding:6px 0 10px 0;")
    main.addWidget(txt)
    cols = QHBoxLayout()
    cols.setSpacing(14)
    ai, al = card("ai", 14, 6)
    al.addWidget(lbl("WHAT THE MODELS SAID", "eyebrow"))
    al.addWidget(lbl(honest_headline(rec), "h3", True))
    al.addWidget(sentiment_scores_widget(rec))
    wf, wl = card("warn", 8, 2)
    wl.addWidget(lbl(f"<b>{FLAG_TEXT['mixed'][0]}.</b> {FLAG_TEXT['mixed'][1]}", None, True))
    al.addWidget(wf)
    al.addStretch(1)
    cols.addWidget(ai, 1)
    hu, hl = card("human", 14, 8)
    hl.addWidget(lbl("WHAT YOU DECIDE", "eyebrow"))
    for dim in ("Sentiment", "Dominant emotion"):
        hl.addWidget(lbl(dim, "h3"))
        g = QButtonGroup(hu)
        r = QHBoxLayout()
        for j, o in enumerate(("Agree with AI", "Correct it", "Not sure")):
            rb = QRadioButton(o)
            rb.setChecked(j == (0 if dim == "Sentiment" else 1))
            g.addButton(rb)
            r.addWidget(rb)
        r.addStretch(1)
        hl.addLayout(r)
    cb = QComboBox()
    cb.addItems(["anger", "joy", "sadness", "fear", "neutral"])
    hl.addLayout(row(lbl("Your emotion label", "muted"), cb, None))
    note = QPlainTextEdit()
    note.setPlaceholderText("Optional note")
    note.setFixedHeight(56)
    hl.addWidget(note)
    hl.addStretch(1)
    cols.addWidget(hu, 1)
    main.addLayout(cols, 1)
    lay.addLayout(main, 1)
    return w


def _insights():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(14)
    lay.addWidget(lbl("What the review shows", "h1"))
    a = AGREEMENT
    lay.addWidget(lbl(f"Based on {a['reviewed']} of {a['total']} records reviewed by you. "
                      "Agreement compares your decisions with the AI record; it is not accuracy.", "muted", True))
    h = QHBoxLayout()
    h.setSpacing(14)
    for n, cap, sub in ((f"{a['rate'] * 100:.0f}%", "agree on sentiment", f"{a['agree']} / {a['definitive']}"),
                        (f"{a['emo_rate'] * 100:.0f}%", "agree on emotion", f"{a['emo_agree']} / {a['emo_definitive']}"),
                        ("38", "corrections", "mostly sarcasm read as positive")):
        c, cl = card("card", 18, 2)
        big = QLabel(n)
        big.setStyleSheet("font-size:40px; font-weight:300;")
        cl.addWidget(big)
        cl.addWidget(lbl(cap, "h3"))
        cl.addWidget(lbl(sub, "faint"))
        h.addWidget(c)
    lay.addLayout(h)
    g, gl = card("card", 18, 8)
    gl.addWidget(lbl("Sentiment agreement by channel", "h3"))
    for name, n, sa_, _ea, small in GROUPS:
        r = QHBoxLayout()
        nm = lbl(name, None)
        nm.setFixedWidth(130)
        r.addWidget(nm)
        r.addWidget(MeterBar(sa_, "#9A9E9B" if small else ACCENT, 10), 1)
        r.addWidget(lbl(f"{sa_ * 100:.0f}%  n={n}", "mono"))
        if small:
            r.addWidget(Badge("small sample", "warn"))
        gl.addLayout(r)
    lay.addWidget(g)
    lay.addStretch(1)
    return w
