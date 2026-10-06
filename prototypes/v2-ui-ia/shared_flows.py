"""PROTOTYPE - Shared flows and states, independent of the chosen direction.

First run and model provisioning (download / pre-provisioned folder / later),
download progress and failure, a board of empty/loading/error/progress/cancel
states, and the two Moderation/Triage disposition alternatives.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from common import BORDER, MODELS, Badge, card, hline, lbl, row

KEY = "S"
NAME = "Shared flows, states, Decision Practice"
SCREENS = [
    ("s_welcome", "First run: privacy + model setup choice"),
    ("s_download", "Model download: progress, pause, cancel"),
    ("s_download_error", "Model download: interrupted / recover"),
    ("s_states", "State board: empty, loading, errors, cancel, delete"),
    ("s_practice_keep", "Decision Practice option P1: one demoted native window"),
    ("s_practice_retire", "Decision Practice option P2: retired"),
]


def build(screen: str, nav):
    fn = {"s_welcome": _welcome, "s_download": _download, "s_download_error": _download_error,
          "s_states": _states, "s_practice_keep": _practice_keep,
          "s_practice_retire": _practice_retire}[screen]
    return fn(nav)


def _primary(t):
    b = QPushButton(t)
    b.setProperty("kind", "primary")
    b.setMinimumHeight(32)
    return b


def _danger(t):
    b = QPushButton(t)
    b.setProperty("kind", "danger")
    return b


def _centered_dialog(title, width=640):
    page = QWidget()
    page.setObjectName("page")
    outer = QVBoxLayout(page)
    outer.addStretch(1)
    dlg = QFrame()
    dlg.setObjectName("dlg")
    dlg.setFixedWidth(width)
    dlg.setStyleSheet(f"QFrame#dlg {{ background:#fff; border:1px solid {BORDER}; border-radius:8px; }}")
    dl = QVBoxLayout(dlg)
    dl.setContentsMargins(0, 0, 0, 0)
    dl.setSpacing(0)
    tb = QFrame()
    tb.setObjectName("tb")
    tb.setStyleSheet(f"QFrame#tb {{ background:#F7F7F4; border-bottom:1px solid {BORDER};"
                     " border-top-left-radius:8px; border-top-right-radius:8px; }")
    tl = QHBoxLayout(tb)
    tl.setContentsMargins(14, 8, 10, 8)
    tl.addWidget(lbl(title, None))
    tl.addStretch(1)
    tl.addWidget(lbl("\u2014   \u2610   \u2715", "faint"))
    dl.addWidget(tb)
    body = QVBoxLayout()
    body.setContentsMargins(26, 22, 26, 22)
    body.setSpacing(12)
    dl.addLayout(body)
    outer.addLayout(row(None, dlg, None))
    outer.addStretch(1)
    return page, body


# --------------------------------------------------------------------------
def _welcome(nav):
    page, b = _centered_dialog("Social Text Intelligence - first run", 700)
    b.addWidget(lbl("Welcome", "h1"))
    b.addWidget(lbl("STI analyzes text on this computer. Your text is never uploaded. The only network "
                    "request STI ever makes is the one-time model download below, and only if you choose it.",
                    "muted", True))
    t, tl = card("sunken", 12, 6)
    tl.addWidget(lbl("Two pinned models are needed before the first analysis", "h3"))
    for m in MODELS:
        tl.addLayout(row(lbl(m["short"].capitalize(), "h3"), lbl(m["name"], "mono"), None,
                         Badge(m["license"]), lbl(f"rev {m['rev']} \u00B7 {m['size_mb']} MB", "mono")))
    tl.addWidget(lbl("About 1.0 GB to download, about 1.4 GB on disk with runtime files. "
                     "Stored in %LOCALAPPDATA%\\SocialTextIntelligence\\models.", "faint", True))
    b.addWidget(t)
    r1 = QRadioButton("Download now from huggingface.co (exact revisions above, verified after download)")
    r1.setChecked(True)
    b.addWidget(r1)
    b.addWidget(QRadioButton("Use a folder I already have (offline / pre-provisioned)\u2026"))
    b.addWidget(QRadioButton("Later: let me look around and import text; analysis stays disabled"))
    b.addWidget(hline())
    b.addLayout(row(QPushButton("Licences\u2026"), None, QPushButton("Quit"), _primary("Continue")))
    return page


def _download(nav):
    page, b = _centered_dialog("Model Manager", 640)
    b.addWidget(lbl("Downloading models", "h2"))
    b.addWidget(lbl("You can close this window; the download continues and STI tells you when analysis is ready.",
                    "muted", True))
    for m, pct, state in ((MODELS[0], 100, "\u2713 verified revision 3216a57"),
                          (MODELS[1], 38, "191 of 499 MB \u00B7 6.2 MB/s \u00B7 about 50 s")):
        c, cl = card("card", 12, 6)
        cl.addLayout(row(lbl(m["short"].capitalize(), "h3"), lbl(m["name"], "mono"), None, lbl(state, "muted")))
        pb = QProgressBar()
        pb.setValue(pct)
        cl.addWidget(pb)
        b.addWidget(c)
    b.addWidget(lbl("Partial files are resumed, never used. A model is only marked ready after its revision "
                    "and file hashes match the pinned record.", "faint", True))
    b.addLayout(row(QPushButton("Pause"), _danger("Cancel download"), None, QPushButton("Hide")))
    return page


def _download_error(nav):
    page, b = _centered_dialog("Model Manager", 640)
    b.addWidget(lbl("Download interrupted", "h2"))
    e, el = card("err", 12, 4)
    el.addWidget(lbl("<b>Emotion model: connection lost at 191 of 499 MB.</b> The sentiment model is ready and "
                     "verified. Nothing else was sent or received.", None, True))
    el.addWidget(lbl("network: ConnectionResetError (huggingface.co)", "mono"))
    b.addWidget(e)
    b.addWidget(lbl("What you can do", "h3"))
    b.addWidget(lbl("\u2022 Retry: resumes from 191 MB.\n\u2022 Use a folder: copy the pinned model files from "
                    "another machine and point STI at them.\n\u2022 Continue without: you can create projects and "
                    "import text; analysis waits until both models are ready.", None, True))
    b.addLayout(row(QPushButton("Use a folder\u2026"), QPushButton("Continue without models"), None,
                    _primary("Retry download")))
    b.addWidget(hline())
    b.addWidget(lbl("Pre-provisioned folder check", "h3"))
    b.addLayout(row(QLineEdit("D:\\offline\\sti-models"), QPushButton("Browse\u2026")))
    w, wl = card("warn", 10, 2)
    wl.addWidget(lbl("<b>Revision mismatch.</b> Found SamLowe/roberta-base-go_emotions at a different revision "
                     "(a1b2c3d). STI only uses the pinned revision d750483.", None, True))
    b.addWidget(w)
    return page


# --------------------------------------------------------------------------
def _state_card(title, kind, lines, buttons=()):
    c, cl = card(kind, 14, 6)
    cl.addWidget(lbl(title, "h3"))
    for ln in lines:
        cl.addWidget(lbl(ln, "muted", True))
    if buttons:
        cl.addLayout(row(None, *buttons))
    cl.addStretch(1)
    return c


def _states(nav):
    page = QWidget()
    page.setObjectName("page")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 22, 28, 22)
    lay.addWidget(lbl("State board (direction-independent copy and behaviour)", "h2"))
    lay.addWidget(lbl("Each card is the content of the state, not its final placement; each direction places it "
                      "in its own frame (A: status bar / jobs dock, B: stage body, C: desk / focus view).", "muted",
                      True))
    g = QGridLayout()
    g.setSpacing(12)
    pb = QProgressBar()
    pb.setRange(0, 0)
    cards = [
        _state_card("Empty project", "card",
                    ["No text yet. Add a CSV, or paste a single text with Quick analysis and add it here.",
                     "Nothing is analyzed until you ask."], (QPushButton("Quick analysis"), _primary("Add a CSV\u2026"))),
        _state_card("Warming up models", "card",
                    ["Loading the two models into memory (first analysis after start, about 10 s).",
                     "The window stays responsive; you can keep reviewing."], (pb,)),
        _state_card("Cancel analysis?", "warn",
                    ["87 rows are already analyzed and saved. Cancelling stops the remaining 99; they stay "
                     "queued and you can resume later.", "Nothing is half-written."],
                    (QPushButton("Keep running"), _danger("Cancel analysis"))),
        _state_card("Row-level failures", "err",
                    ["2 rows failed and are kept with their reason, never silently dropped:",
                     "R-0423 input_too_long (731 > 512 tokens, not truncated)\nR-0431 empty_text"],
                    (QPushButton("Show failed rows"),)),
        _state_card("Possibly not English", "warn",
                    ["3 rows look non-English (language check, not a model claim). The models are English-only.",
                     "They are analyzed but marked, and excluded from insights by default."],
                    (QPushButton("Review them"), QPushButton("Exclude"))),
        _state_card("Delete project?", "err",
                    ["\u201CSupport inbox pilot\u201D, 188 records and 22 human judgments, will be removed from this "
                     "application's data files.",
                     "Files you exported, backups and copies made by Windows are not affected. This is not "
                     "a secure erase."], (QPushButton("Export first\u2026"), _danger("Delete project"))),
        _state_card("Project open elsewhere", "warn",
                    ["This project is open in another STI window. Open it read-only here, or switch to that window."],
                    (QPushButton("Open read-only"), _primary("Switch"))),
        _state_card("Could not save", "err",
                    ["Your last judgment (R-0414) could not be written: the disk is full.",
                     "It is kept in memory; free space and choose Retry. Closing now would lose it."],
                    (_primary("Retry save"),)),
        _state_card("Analysis unavailable", "card",
                    ["Models are not installed yet. You can import and browse text; analysis starts when both "
                     "pinned models are ready."], (_primary("Open Model Manager"),)),
    ]
    for i, c in enumerate(cards):
        g.addWidget(c, i // 3, i % 3)
    lay.addLayout(g, 1)
    return page


# --------------------------------------------------------------------------
def _practice_keep(nav):
    page = QWidget()
    page.setObjectName("page")
    lay = QHBoxLayout(page)
    lay.setContentsMargins(28, 22, 28, 22)
    lay.setSpacing(20)
    left = QVBoxLayout()
    left.addWidget(lbl("Option P1 \u00B7 Keep as one demoted native surface", "h2"))
    left.addWidget(lbl("Moderation Training and Support Triage become two tabs of a single separate window, "
                       "reached only from Tools \u25B8 Decision Practice (A), the rail's bottom slot (C) or the "
                       "home Settings menu (B). Not in the main navigation, not part of projects.", "muted", True))
    for t in ("Ported from Flask to Qt once, then frozen: no new features.",
              "Synthetic built-in cases only; never touches project data.",
              "Nothing persists: the session ends when the window closes (V1 semantics).",
              "Cost: a native port of two workflows (\u22482.9k lines of V1 service code stays; UI is rebuilt).",
              "Keeps the portfolio story of 'decision practice' alive."):
        left.addWidget(lbl("\u2022 " + t, None, True))
    left.addStretch(1)
    lay.addLayout(left, 2)

    win = QFrame()
    win.setObjectName("dlg")
    win.setStyleSheet(f"QFrame#dlg {{ background:#fff; border:1px solid {BORDER}; border-radius:8px; }}")
    wl = QVBoxLayout(win)
    wl.setContentsMargins(0, 0, 0, 0)
    tb = QLabel("  Decision Practice \u2014 synthetic cases")
    tb.setStyleSheet(f"background:#F7F7F4; border-bottom:1px solid {BORDER}; padding:8px;")
    wl.addWidget(tb)
    ban = QLabel("  PRACTICE \u00B7 built-in synthetic cases \u00B7 nothing here is saved or added to projects")
    ban.setStyleSheet("background:#FBF1DC; color:#8A5A00; font-weight:600; font-size:12px; padding:6px;")
    wl.addWidget(ban)
    tabs = QTabWidget()
    mod = QWidget()
    ml = QVBoxLayout(mod)
    ml.setContentsMargins(18, 16, 18, 16)
    ml.setSpacing(10)
    ml.addLayout(row(lbl("Case 3 of 12", "muted"), None, lbl("policy: community guidelines v1 (synthetic)", "faint")))
    q = lbl("\u201CIf you post that build again I will make sure everyone knows where you work.\u201D", "body", True)
    q.setStyleSheet("font-size:17px;")
    ml.addWidget(q)
    ml.addWidget(lbl("Your decision", "h3"))
    for o in ("No action", "Warn", "Remove content", "Escalate to a human moderator"):
        ml.addWidget(QRadioButton(o))
    ml.addWidget(lbl("Model signal is shown after you decide, as a comparison, never as a recommendation.", "faint",
                     True))
    ml.addStretch(1)
    ml.addLayout(row(None, _primary("Record decision")))
    tabs.addTab(mod, "Moderation judgment")
    tabs.addTab(QWidget(), "Support triage")
    wl.addWidget(tabs, 1)
    win.setMinimumWidth(620)
    lay.addWidget(win, 3)
    return page


def _practice_retire(nav):
    page = QWidget()
    page.setObjectName("page")
    lay = QHBoxLayout(page)
    lay.setContentsMargins(28, 22, 28, 22)
    lay.setSpacing(20)
    left = QVBoxLayout()
    left.addWidget(lbl("Option P2 \u00B7 Retire from the V2 product surface", "h2"))
    left.addWidget(lbl("The V2 desktop app ships without Moderation Training and Support Triage. They remain "
                       "available in V1 0.10.0 (web) and in the repository history; their services are not "
                       "imported by the desktop build.", "muted", True))
    for t in ("Zero native port cost; smallest, most coherent product.",
              "Removes the 'half the product is simulation' critique from discovery.",
              "Flask can be retired at its own later gate without orphaning anything.",
              "Loses a portfolio talking point; V1 docs keep the evidence.",
              "Irreversible for V2.0 in practice (re-adding later = new scope)."):
        left.addWidget(lbl("\u2022 " + t, None, True))
    left.addStretch(1)
    lay.addLayout(left, 2)
    about, al = card("card", 22, 10)
    al.addWidget(lbl("Help \u25B8 About Social Text Intelligence", "faint"))
    al.addWidget(lbl("Social Text Intelligence 2.0", "h1"))
    al.addWidget(lbl("Local review workbench for text evidence.", "muted"))
    al.addWidget(hline())
    al.addWidget(lbl("Models", "h3"))
    for m in MODELS:
        al.addWidget(lbl(f"{m['name']}@{m['rev']}  ({m['license']})", "mono"))
    al.addWidget(hline())
    al.addWidget(lbl("What changed from V1", "h3"))
    al.addWidget(lbl("Projects are now saved locally. Review is the centre of the app. The Moderation Training "
                     "and Support Triage practice modes from V1 0.10.0 are not part of V2; see the V1 release "
                     "notes in the project repository.", None, True))
    al.addStretch(1)
    al.addLayout(row(None, QPushButton("Licences\u2026"), _primary("Close")))
    lay.addWidget(about, 3)
    return page
