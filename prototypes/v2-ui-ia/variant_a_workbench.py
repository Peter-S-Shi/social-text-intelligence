"""PROTOTYPE - Direction A: Evidence Workbench.

Desktop-native multi-pane workbench (IDE/mail-client metaphor): menu bar,
project navigator dock, record table centre, inspector dock with the AI record
and the human judgment side by side, jobs dock for long-running work, and a
status bar that always shows model/provenance state. Review is not a page; it
is what you do with the selected record anywhere in the project.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from common import (
    ACCENT,
    AGREEMENT,
    FLAG_TEXT,
    GROUPS,
    MODELS,
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

KEY = "A"
NAME = "Evidence Workbench"
SCREENS = [
    ("a_launcher", "Start window: recent projects"),
    ("a_review", "Workspace: review in table + inspector"),
    ("a_batch", "Workspace: import running, jobs dock, cancel"),
    ("a_insights", "Workspace: insights document tab"),
    ("a_quick", "Quick analysis (Direct) as a scratch dialog"),
]


# --------------------------------------------------------------------------
def build(screen: str, nav):
    if screen == "a_launcher":
        return _launcher(nav)
    return _workspace(screen, nav)


def _launcher(nav):
    page = QWidget()
    page.setObjectName("page")
    outer = QHBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    left = QFrame()
    left.setObjectName("side")
    left.setFixedWidth(330)
    left.setStyleSheet("QFrame#side { background:#FFFFFF; border-right:1px solid #DFDFD9; }")
    ll = QVBoxLayout(left)
    ll.setContentsMargins(28, 32, 28, 24)
    ll.setSpacing(10)
    ll.addWidget(lbl("SOCIAL TEXT INTELLIGENCE", "eyebrow"))
    ll.addWidget(lbl("Local review workbench", "h1"))
    ll.addWidget(lbl("Text never leaves this computer. Projects are saved to this "
                     "Windows account's local application data.", "muted", True))
    ll.addSpacing(18)
    b_new = QPushButton("New project…")
    b_new.setProperty("kind", "primary")
    b_new.clicked.connect(lambda: nav("a_review"))
    ll.addWidget(b_new)
    ll.addWidget(QPushButton("Open project file…"))
    ll.addWidget(QPushButton("Quick analysis (no project)…"))
    ll.addStretch(1)
    m, ml = card("sunken", 12, 4)
    ml.addWidget(lbl("Models", "h3"))
    for md in MODELS:
        ml.addWidget(lbl(f"● {md['short']}  {md['rev']}  ready", "mono"))
    ml.addWidget(lbl("Offline · no telemetry", "faint"))
    ll.addWidget(m)
    outer.addWidget(left)

    right = QWidget()
    rl = QVBoxLayout(right)
    rl.setContentsMargins(32, 32, 32, 24)
    rl.setSpacing(12)
    rl.addLayout(row(lbl("Recent projects", "h2"), None, QLineEdit(placeholderText="Filter projects")))
    t = QTableWidget(len(PROJECTS), 6)
    t.setHorizontalHeaderLabels(["Project", "Records", "Human reviewed", "", "Sources", "Last opened"])
    t.verticalHeader().hide()
    t.setShowGrid(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    for i, p in enumerate(PROJECTS):
        t.setItem(i, 0, QTableWidgetItem(p["name"]))
        t.setItem(i, 1, QTableWidgetItem(str(p["records"])))
        t.setItem(i, 2, QTableWidgetItem(f"{p['reviewed']} ({p['reviewed'] * 100 // p['records']}%)"))
        mb = MeterBar(p["reviewed"] / p["records"])
        w = wrap_layout(row(mb))
        w.layout().setContentsMargins(6, 0, 12, 0)
        t.setCellWidget(i, 3, w)
        t.setItem(i, 4, QTableWidgetItem(str(p["sources"])))
        t.setItem(i, 5, QTableWidgetItem(p["opened"]))
        t.setRowHeight(i, 38)
    t.selectRow(0)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    hh.resizeSection(3, 140)
    t.cellDoubleClicked.connect(lambda *_: nav("a_review"))
    rl.addWidget(t, 1)
    rl.addWidget(lbl("Double-click to open. Deleting a project removes it from this application's "
                     "data files; copies you exported are not affected.", "faint", True))
    outer.addWidget(right, 1)
    return page


# --------------------------------------------------------------------------
def _menus(win: QMainWindow, nav):
    mb = win.menuBar()
    spec = {
        "&File": ["New Project…", "Open Project…", "Close Project", "-",
                  "Import CSV into Project…", "Export Reviewed Dataset…", "-",
                  "Delete Project…"],
        "&Edit": ["Undo Review Change", "Find in Records…"],
        "&View": ["Navigator", "Inspector", "Jobs", "-", "Show Native Emotion Scores"],
        "&Analyze": ["Quick Analysis…  Ctrl+Shift+A", "Analyze Pending Records", "Cancel Running Job"],
        "&Review": ["Accept AI Labels  Enter", "Correct…  C", "Mark Uncertain  U", "Next Unreviewed  N"],
        "&Tools": ["Model Manager…", "Decision Practice… (if kept)"],
        "&Help": ["How to Read Results", "About and Licences"],
    }
    for title, items in spec.items():
        m = mb.addMenu(title)
        for it in items:
            if it == "-":
                m.addSeparator()
            else:
                a = QAction(it, win)
                if it.startswith("Quick Analysis"):
                    a.triggered.connect(lambda: nav("a_quick"))
                m.addAction(a)


def _toolbar(win: QMainWindow, nav):
    tb = QToolBar()
    tb.setMovable(False)
    crumb = lbl(f"  {PROJECTS[0]['name']}", "h3")
    tb.addWidget(crumb)
    tb.addWidget(lbl("  ·  saved", "faint"))
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tb.addWidget(spacer)
    s = QLineEdit(placeholderText="Search text, ID, note   Ctrl+F")
    s.setFixedWidth(260)
    tb.addWidget(s)
    for name, target in (("Import CSV", "a_batch"), ("Quick analysis", "a_quick"),
                         ("Insights", "a_insights"), ("Export…", None)):
        b = QPushButton(name)
        if target:
            b.clicked.connect(lambda _=False, t=target: nav(t))
        tb.addWidget(b)
    win.addToolBar(tb)


def _navigator(screen, nav):
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setIndentation(14)
    tree.setStyleSheet("QTreeWidget { border: none; } QTreeWidget::item { padding: 3px; }")

    def node(parent, text, count=None, target=None, bold=False):
        it = QTreeWidgetItem(parent, [text + (f"   {count}" if count is not None else "")])
        if bold:
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
        if target:
            it.setData(0, Qt.ItemDataRole.UserRole, target)
        return it

    ov = node(tree, "Overview", target="a_insights", bold=True)
    src = node(tree, "Sources", bold=True)
    s1 = node(src, "app_store_autumn.csv", 412, "a_batch")
    node(src, "support_inbox.csv", 188, "a_batch")
    rq = node(tree, "Review", bold=True)
    r1 = node(rq, "Unreviewed", 229, "a_review")
    node(rq, "Needs a second look (mixed / low margin)", 61, "a_review")
    node(rq, "Corrected", 38, "a_review")
    node(rq, "Uncertain", 12, "a_review")
    node(rq, "All records", 600, "a_review")
    ins = node(tree, "Insights", bold=True)
    i1 = node(ins, "Agreement (AI vs human)", None, "a_insights")
    node(ins, "Distributions", None, "a_insights")
    node(ins, "Groups", None, "a_insights")
    node(ins, "Context notes", 7, "a_insights")
    node(tree, "Exports", 2, bold=True)
    node(tree, "Model & provenance", bold=True)
    tree.expandAll()
    sel = {"a_review": r1, "a_batch": s1, "a_insights": i1, "a_quick": r1}.get(screen, ov)
    tree.setCurrentItem(sel)
    tree.itemClicked.connect(
        lambda it, _c: (t := it.data(0, Qt.ItemDataRole.UserRole)) and t != screen and nav(t))
    return tree


def _records_table(highlight=0, streaming=False):
    cols = ["", "ID", "Text", "AI sentiment", "AI emotion", "Signal", "Human"]
    recs = RECORDS
    t = QTableWidget(len(recs), len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().hide()
    t.setShowGrid(False)
    t.setAlternatingRowColors(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    for i, r in enumerate(recs):
        pending = streaming and i >= 7
        st = "unreviewed" if pending else r["status"]
        w = wrap_layout(row(status_dot(st)))
        w.layout().setContentsMargins(8, 0, 0, 0)
        t.setCellWidget(i, 0, w)
        t.setItem(i, 1, QTableWidgetItem(r["id"]))
        txt = r["text"] or "(row failed: input too long)"
        t.setItem(i, 2, QTableWidgetItem(txt))
        if pending:
            for c in (3, 4):
                it = QTableWidgetItem("queued")
                it.setForeground(QColor("#9A9E9B"))
                t.setItem(i, c, it)
        elif r["status"] == "failed":
            it = QTableWidgetItem("input_too_long")
            it.setForeground(QColor("#A2392A"))
            t.setItem(i, 3, it)
        else:
            it = QTableWidgetItem(r["sent"] + (" ?" if "low_margin" in r["flags"] else ""))
            it.setForeground(QColor(SENT[r["sent"]]))
            t.setItem(i, 3, it)
            t.setItem(i, 4, QTableWidgetItem(r["emo"] + (" ?" if r["flags"] else "")))
            flags = [f for f in r["flags"] if f != "failed"]
            if flags:
                bw = wrap_layout(row(*[Badge(FLAG_TEXT[f][0], "err" if f == "lang" else "warn") for f in flags], None))
                bw.layout().setContentsMargins(4, 0, 0, 0)
                t.setCellWidget(i, 5, bw)
            h = r["human"]
            if h:
                ht = "uncertain" if h["sent"] is None else f"{h['sent']} · {h['emo']}"
                hi = QTableWidgetItem(ht)
                hi.setForeground(QColor(ACCENT))
                t.setItem(i, 6, hi)
        t.setRowHeight(i, 30)
    hh = t.horizontalHeader()
    hh.resizeSection(0, 26)
    hh.resizeSection(1, 60)
    hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    hh.resizeSection(3, 92)
    hh.resizeSection(4, 104)
    hh.resizeSection(5, 118)
    hh.resizeSection(6, 128)
    t.setWordWrap(False)
    t.setTextElideMode(Qt.TextElideMode.ElideRight)
    t.selectRow(highlight)
    return t


def _inspector(rec):
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(10)
    lay.addLayout(row(lbl(rec["id"], "h3"), Badge(rec["src"]), Badge(rec["topic"]), None,
                      lbl("1 of 229 unreviewed", "faint")))
    tx = lbl(rec["text"], "body", True)
    tx.setStyleSheet("font-size:15px; padding:4px 0;")
    lay.addWidget(tx)

    ai, al = card("ai", 12, 6)
    al.addLayout(row(lbl("AI RECORD", "eyebrow"), lbl("\U0001F512 read-only", "faint"), None,
                     lbl("model output, kept as produced", "faint")))
    head = lbl(honest_headline(rec), "h3", True)
    al.addWidget(head)
    al.addWidget(sentiment_scores_widget(rec))
    al.addWidget(lbl(f"Emotion: {rec['emo']} {rec['emo_conf']:.2f}"
                     + (f"  ·  secondary: {', '.join(rec['secondary'])}" if rec["secondary"] else ""),
                     "muted"))
    for f in rec["flags"]:
        wf, wl = card("warn", 8, 2)
        wl.addWidget(lbl(f"<b>{FLAG_TEXT[f][0]}.</b> {FLAG_TEXT[f][1]}", None, True))
        al.addWidget(wf)
    al.addWidget(lbl(f"sentiment@{MODELS[0]['rev']} · emotion@{MODELS[1]['rev']} · threshold 0.50",
                     "mono"))
    lay.addWidget(ai)

    hu, hl = card("human", 12, 6)
    hl.addLayout(row(lbl("YOUR JUDGMENT", "eyebrow"), None, lbl("saved separately", "faint")))
    for dim, opts in (("Sentiment", ["Accept AI", "Correct", "Uncertain"]),
                      ("Emotion", ["Accept AI", "Correct", "Uncertain"])):
        g = QButtonGroup(hu)
        r = QHBoxLayout()
        r.addWidget(lbl(dim, "h3"))
        for j, o in enumerate(opts):
            rb = QRadioButton(o)
            if j == (1 if dim == "Emotion" else 0):
                rb.setChecked(True)
            g.addButton(rb)
            r.addWidget(rb)
        r.addStretch(1)
        hl.addLayout(r)
    cb = QComboBox()
    cb.addItems(["anger", "joy", "sadness", "fear", "disgust", "neutral"])
    hl.addLayout(row(lbl("Human emotion", "muted"), cb, lbl("+ secondary", "faint"), None))
    note = QPlainTextEdit()
    note.setPlaceholderText("Optional note (why you disagreed)")
    note.setFixedHeight(54)
    hl.addWidget(note)
    sv = QPushButton("Save && next unreviewed   Enter")
    sv.setProperty("kind", "primary")
    hl.addLayout(row(QPushButton("Skip"), None, sv))
    lay.addWidget(hu)
    lay.addStretch(1)
    sa.setWidget(body)
    return sa


def _status(win: QMainWindow, job: bool):
    sb = win.statusBar()
    sb.addWidget(lbl("● Models ready · offline", None))
    sb.addWidget(lbl(f"   sentiment@{MODELS[0]['rev']}   emotion@{MODELS[1]['rev']}", "mono"))
    if job:
        pb = QProgressBar()
        pb.setValue(46)
        pb.setFixedWidth(120)
        sb.addPermanentWidget(lbl("Analyzing support_inbox.csv  87 / 188", None))
        sb.addPermanentWidget(pb)
    sb.addPermanentWidget(lbl("600 records · 359 reviewed · saved 09:41", None))


def _jobs_dock():
    d = QDockWidget("Jobs")
    d.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(12, 8, 12, 8)
    pb = QProgressBar()
    pb.setValue(46)
    cancel = QPushButton("Cancel")
    cancel.setProperty("kind", "danger")
    lay.addLayout(row(lbl("Analyzing <b>support_inbox.csv</b>", None), lbl("87 of 188 rows · 2 failed · about 1 min left", "muted"),
                      None, QPushButton("Pause"), cancel))
    lay.addWidget(pb)
    lay.addWidget(lbl("Results are saved row by row. Cancelling keeps the 87 analyzed rows and leaves "
                      "the remaining 101 as 'queued'; nothing is half-written.", "faint", True))
    d.setWidget(w)
    return d


def _import_tab():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(10)
    lay.addLayout(row(lbl("support_inbox.csv", "h2"), Badge("188 rows"), Badge("186 valid", "ok"),
                      Badge("2 invalid", "err"), Badge("3 look non-English", "warn"), None,
                      lbl("Text column:", "muted"), _combo(["message_body", "subject"]),
                      lbl("Group by:", "muted"), _combo(["channel", "(none)"])))
    lay.addWidget(_records_table(highlight=6, streaming=True), 1)
    return w


def _combo(items):
    c = QComboBox()
    c.addItems(items)
    return c


def _insights_tab():
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    w = QWidget()
    w.setObjectName("doc")
    w.setStyleSheet("QWidget#doc { background:#FFFFFF; }")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.setSpacing(12)
    lay.addLayout(row(lbl("Agreement, not accuracy", "h2"), None,
                      lbl("Scope:", "muted"), _combo(["All sources", "app_store", "support", "forum"]),
                      QPushButton("Export insights CSV")))
    lay.addWidget(lbl("Compares saved human judgments with the immutable AI record. Uncertain reviews "
                      "are excluded from denominators. This describes this project's text only.", "muted", True))
    grid = QGridLayout()
    grid.setSpacing(10)
    a = AGREEMENT
    metrics = [
        (f"{a['rate'] * 100:.1f}%", "sentiment agreement", f"{a['agree']} of {a['definitive']} definitive reviews"),
        (f"{a['emo_rate'] * 100:.1f}%", "dominant-emotion agreement", f"{a['emo_agree']} of {a['emo_definitive']}"),
        (f"{a['reviewed']}", "records reviewed", f"of {a['total']} · {a['uncertain']} uncertain"),
        (f"{a['corrected']}", "corrections", "most common: positive → negative (sarcasm)"),
    ]
    for i, (n, cap, sub) in enumerate(metrics):
        c, cl = card("card", 12, 2)
        big = QLabel(n)
        big.setStyleSheet("font-size:28px; font-weight:300;")
        cl.addWidget(big)
        cl.addWidget(lbl(cap, "h3"))
        cl.addWidget(lbl(sub, "faint", True))
        grid.addWidget(c, 0, i)
    lay.addLayout(grid)

    lay.addWidget(lbl("By group", "h3"))
    t = QTableWidget(len(GROUPS), 5)
    t.setHorizontalHeaderLabels(["Group", "n (definitive)", "Sentiment agreement", "", "Note"])
    t.verticalHeader().hide()
    t.setShowGrid(False)
    for i, (g, n, sa_, ea, small) in enumerate(GROUPS):
        t.setItem(i, 0, QTableWidgetItem(g))
        t.setItem(i, 1, QTableWidgetItem(str(n)))
        t.setItem(i, 2, QTableWidgetItem(f"{sa_ * 100:.0f}%"))
        mw = wrap_layout(row(MeterBar(sa_, "#9A9E9B" if small else ACCENT)))
        mw.layout().setContentsMargins(6, 0, 12, 0)
        t.setCellWidget(i, 3, mw)
        if small:
            bw = wrap_layout(row(Badge("Small sample (n<20): do not generalise", "warn"), None))
            t.setCellWidget(i, 4, bw)
        t.setRowHeight(i, 32)
    t.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    t.horizontalHeader().resizeSection(3, 180)
    t.setFixedHeight(32 * len(GROUPS) + 36)
    t.horizontalHeader().resizeSection(2, 150)
    lay.addWidget(t)

    lay.addWidget(lbl("Sentiment confusion (AI rows × human columns, definitive only)", "h3"))
    cm = QGridLayout()
    labels = ["negative", "neutral", "positive"]
    vals = [[61, 4, 1], [6, 22, 3], [9, 6, 52]]
    for j, l in enumerate(labels):
        cm.addWidget(lbl(f"human {l}", "faint"), 0, j + 1)
    for i, l in enumerate(labels):
        cm.addWidget(lbl(f"AI {l}", "faint"), i + 1, 0)
        for j in range(3):
            cell = QLabel(str(vals[i][j]))
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            strength = vals[i][j] / 61
            bg = f"rgba(31,95,74,{0.08 + 0.6 * strength:.2f})" if i == j else f"rgba(180,83,60,{0.05 + 0.5 * vals[i][j] / 12:.2f})"
            cell.setStyleSheet(f"background:{bg}; padding:8px; border-radius:3px; font-weight:600;")
            cell.setFixedSize(110, 34)
            cm.addWidget(cell, i + 1, j + 1)
    cm.setColumnStretch(5, 1)
    lay.addLayout(cm)
    lay.addStretch(1)
    sa.setWidget(w)
    return sa


def _quick_overlay(parent):
    ov = QWidget(parent)
    ov.setObjectName("dim")
    ov.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    ov.setStyleSheet("QWidget#dim { background: rgba(20,24,22,0.28); }")
    dlg, dl = card("card", 18, 10)
    dlg.setFixedWidth(620)
    dl.addLayout(row(lbl("Quick analysis", "h2"), None, lbl("not saved unless you add it", "faint")))
    te = QPlainTextEdit("Love how fast the new editor is, but exporting a large report still freezes the whole app.")
    te.setFixedHeight(70)
    dl.addWidget(te)
    dl.addLayout(row(lbl("English only · 512 model tokens · 23 used", "faint"), None,
                     _primary("Analyze locally   Ctrl+Enter")))
    dl.addWidget(hline())
    rec = RECORDS[0]
    ai, al = card("ai", 12, 6)
    al.addWidget(lbl("AI RECORD", "eyebrow"))
    al.addWidget(lbl(honest_headline(rec), "h3", True))
    al.addWidget(StackBar([(v, SENT[n]) for n, v in zip(("negative", "neutral", "positive"), rec["scores"])]))
    al.addWidget(lbl("joy 0.41  ·  anger 0.38  ·  admiration 0.12  …  all 28 native scores ▸", "muted"))
    wf, wl = card("warn", 8, 2)
    wl.addWidget(lbl(f"<b>{FLAG_TEXT['mixed'][0]}.</b> {FLAG_TEXT['mixed'][1]}", None, True))
    al.addWidget(wf)
    dl.addWidget(ai)
    dl.addLayout(row(QPushButton("Discard"), None, lbl("Add to:", "muted"),
                     _combo([PROJECTS[0]["name"], "New project…"]), _primary("Add as record")))
    ol = QVBoxLayout(ov)
    ol.addStretch(1)
    ol.addLayout(row(None, dlg, None))
    ol.addStretch(2)
    return ov


def _primary(text):
    b = QPushButton(text)
    b.setProperty("kind", "primary")
    return b


def _workspace(screen, nav):
    win = QMainWindow()
    win.setDockOptions(QMainWindow.DockOption.AnimatedDocks)
    _menus(win, nav)
    _toolbar(win, nav)

    navd = QDockWidget("Project")
    navd.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
    navd.setWidget(_navigator(screen, nav))
    navd.setFixedWidth(230)
    win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, navd)

    tabs = QTabWidget()
    tabs.setDocumentMode(False)
    tabs.setTabsClosable(True)
    tabs.addTab(_records_table(0), "Review · Unreviewed (229)")
    if screen == "a_batch":
        tabs.addTab(_import_tab(), "Source · support_inbox.csv")
        tabs.setCurrentIndex(1)
    if screen == "a_insights":
        tabs.addTab(_insights_tab(), "Insights · Agreement")
        tabs.setCurrentIndex(1)
    central = QWidget()
    cl = QVBoxLayout(central)
    cl.setContentsMargins(8, 8, 8, 8)
    cl.addWidget(tabs)
    win.setCentralWidget(central)

    if screen in ("a_review", "a_batch", "a_quick"):
        insp = QDockWidget("Inspector")
        insp.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        insp.setWidget(_inspector(RECORDS[0]))
        insp.setMinimumWidth(400)
        insp.setMaximumWidth(400)
        win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, insp)
    if screen == "a_batch":
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, _jobs_dock())
    _status(win, screen == "a_batch")

    if screen == "a_quick":
        holder = QWidget()
        hl = QGridLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(win, 0, 0)
        hl.addWidget(_quick_overlay(holder), 0, 0)
        return holder
    return win
