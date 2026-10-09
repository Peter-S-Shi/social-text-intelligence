# ruff: noqa: E501  (a stylesheet reads best one declaration per line)
"""One stylesheet in the approved visual language, using system-safe font fallbacks.

Warm-grey paper with white sheets, slate for the machine, ultramarine for the human,
vermilion only for disagreement and failure, and near-black for the one primary action
of a page (the Round 3 reference palette). The prototype's web fonts are not bundled:
their licences are unverified, so the Windows system faces (Segoe UI, Georgia,
Consolas) stand in. Every state also carries an icon and a word, so colour is never the
only signal.

The sheet is built from named tokens so the type scale, spacing, and colours are
decided in one place. Contrast (WCAG 2.x, measured on the surface each sits on, enforced by
``tests/desktop/test_style_contrast.py``): ink 16:1 or better, muted 5.5:1 or better,
ultramarine 5.7:1 or better, vermilion 4.8:1 or better; the border that identifies a
control (``LINE_STRONG``) is at least 3.3:1.
"""

from __future__ import annotations

# -- colour -------------------------------------------------------------------
PAPER = "#F2F0EB"
PAPER_RAISED = "#FFFFFF"
PAPER_SUNK = "#EAE7E0"
PAPER_ALT = "#F8F7F4"
INK = "#131518"
MUTED = "#565B62"
LINE = "#E0DCD3"
LINE_STRONG = "#7D828A"
GRAPHITE = "#33404F"
GRAPHITE_SOFT = "#4B5766"
GRAPHITE_TINT = "#EEF0F3"
GRAPHITE_LINE = "#CBD1D9"
ULTRAMARINE = "#2C47E0"
ULTRAMARINE_TINT = "#E6EAFE"
ULTRAMARINE_PALE = "#F1F3FF"
ULTRAMARINE_LINE = "#C9D1FB"
VERMILION = "#B8401F"
VERMILION_TINT = "#FCEBE5"
CAUTION_BG = "#FBF1DC"
CAUTION_LINE = "#97670F"
CAUTION_TEXT = "#5C3F00"
POSITIVE = "#1F6B80"
POSITIVE_TINT = "#E3F1F5"
POSITIVE_LINE = "#BFDCE5"
NEUTRAL = "#6B6F76"
FOCUS = "#2C47E0"
SIDEBAR_BG = "#F7F5F1"
SIDEBAR_MUTED = MUTED

# -- type ---------------------------------------------------------------------
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"
SIZE_BODY = "10pt"
SIZE_SMALL = "9pt"
SIZE_TITLE = "13pt"
SIZE_HEADLINE = "21pt"
SIZE_FIGURE = "28pt"
SIZE_DISPLAY = "34pt"
SIZE_WORD = "22pt"
SIZE_QUOTE = "15pt"

# -- space (pixels) -----------------------------------------------------------
SPACE_XS = 4
SPACE_S = 8
SPACE_M = 12
SPACE_L = 16
SPACE_XL = 24
PAGE_MARGIN_X = 28
PAGE_MARGIN_TOP = 22
RADIUS = 6
RADIUS_CARD = 8


# (matches the AI label?, shade level, fill, text): the count is always written inside
CONFUSION_STYLES: tuple[tuple[bool, int, str, str], ...] = tuple(
    (match, level, fill[level], text[level])
    for match, fill, text in (
        (
            True,
            ("#FFFFFF", "#DCE0E6", "#AEB6C2", "#566376", GRAPHITE),
            (INK, INK, INK, "#FFFFFF", "#FFFFFF"),
        ),
        (
            False,
            ("#FFFFFF", "#FCEBE5", "#F3C5B6", "#DE9479", VERMILION),
            (INK, INK, INK, INK, "#FFFFFF"),
        ),
    )
    for level in range(5)
)


def _confusion_rules() -> str:
    return "\n".join(
        f'QLabel[cell="true"][match="{str(match).lower()}"][level="{level}"] '
        f"{{ background: {fill}; color: {text}; }}"
        for match, level, fill, text in CONFUSION_STYLES
    )


STYLESHEET = f"""
QWidget {{
  background: {PAPER}; color: {INK}; font-family: {SANS}; font-size: {SIZE_BODY};
}}
QDialog, QMainWindow {{ background: {PAPER}; }}
QLabel {{ background: transparent; }}
QWidget[role="plain"] {{ background: transparent; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{
  background: {PAPER_RAISED}; color: {INK}; border: 1px solid {LINE_STRONG};
  padding: 4px 6px;
}}

/* -- type roles ---------------------------------------------------------------- */
QLabel[role="headline"] {{ font-family: {SERIF}; font-size: {SIZE_HEADLINE}; }}
QLabel[role="title"] {{ font-family: {SERIF}; font-size: {SIZE_TITLE}; }}
QLabel[role="figure"] {{ font-family: {SERIF}; font-size: {SIZE_FIGURE}; }}
QLabel[role="display"] {{ font-family: {SERIF}; font-size: {SIZE_DISPLAY}; }}
QLabel[role="numeral"] {{ font-family: {SERIF}; font-size: 20pt; color: {LINE_STRONG}; }}
QLabel[role="display"][size="hero"] {{ font-size: 25pt; }}
QWidget#setup-hero {{ background: {PAPER}; border-right: 1px solid {LINE}; }}
QLabel[role="word"] {{ font-family: {SERIF}; font-size: {SIZE_WORD}; }}
QLabel[quote="true"] {{ font-family: {SERIF}; font-size: {SIZE_QUOTE}; }}
QLabel[role="muted"] {{ color: {MUTED}; }}
QLabel[role="mono"] {{ font-family: {MONO}; color: {MUTED}; font-size: {SIZE_SMALL}; }}
QLabel[role="eyebrow"] {{
  font-family: {MONO}; color: {MUTED}; font-size: 8pt; letter-spacing: 1px;
}}
QLabel[role="error"] {{ color: {VERMILION}; }}
QLabel[role="subtitle"] {{ font-family: {MONO}; color: {MUTED}; font-size: {SIZE_SMALL}; }}
QLabel[role="cardhead"] {{ font-weight: 600; font-size: 10.5pt; }}
QLabel[role="cardhead"][side="ai"] {{ color: {GRAPHITE}; }}
QLabel[role="cardhead"][side="human"] {{ color: {ULTRAMARINE}; }}
QLabel[polarity="negative"] {{ color: {VERMILION}; }}
QLabel[polarity="positive"] {{ color: {POSITIVE}; }}
QLabel[polarity="neutral"] {{ color: {NEUTRAL}; }}
QLabel[polarity="caution"] {{ color: {CAUTION_TEXT}; }}

/* -- surfaces ------------------------------------------------------------------ */
QFrame[role="card"], QFrame[role="panel"] {{
  background: {PAPER_RAISED}; border: 1px solid {LINE}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="card"] QLabel, QFrame[role="panel"] QLabel {{ background: transparent; }}
QFrame[role="alert"] {{
  background: {PAPER_RAISED}; border: 2px solid {VERMILION}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="notice"] {{
  background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="caution"] {{
  background: {CAUTION_BG}; border: 1px solid {CAUTION_LINE}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="ai"] {{
  background: {GRAPHITE_TINT}; border: 1px solid {GRAPHITE_LINE}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="human"] {{
  background: {ULTRAMARINE_PALE}; border: 1px solid {ULTRAMARINE_LINE}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="quiet"] {{ background: transparent; border: none; }}
QFrame[role="empty"] {{
  background: transparent; border: 1px dashed {LINE_STRONG}; border-radius: {RADIUS_CARD}px;
}}
QFrame[role="alert"] QLabel, QFrame[role="notice"] QLabel, QFrame[role="caution"] QLabel,
QFrame[role="ai"] QLabel, QFrame[role="human"] QLabel, QFrame[role="empty"] QLabel,
QFrame[role="quiet"] QLabel {{
  background: transparent;
}}
QFrame[role="rule"] {{ background: {LINE}; border: none; max-height: 1px; min-height: 1px; }}
QGroupBox {{
  border: 1px solid {LINE}; border-radius: 4px; margin-top: 10px; padding: 8px;
  background: transparent;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QGroupBox[plain="true"] {{
  border: none; margin-top: 18px; padding: 2px 0 0 0; background: transparent;
}}
QGroupBox[plain="true"]::title {{
  subcontrol-origin: margin; left: 0; padding: 0; color: {MUTED};
  font-family: {MONO}; font-size: 8pt;
}}

/* -- buttons ------------------------------------------------------------------- */
QPushButton {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG}; border-radius: 6px;
  padding: 6px 14px; min-height: 22px;
}}
QPushButton:hover {{ background: {PAPER_ALT}; border-color: {INK}; }}
QPushButton:pressed {{ background: {PAPER_SUNK}; }}
QPushButton:disabled {{ color: #7A7E85; border-color: {LINE}; background: {PAPER}; }}
QPushButton[primary="true"] {{
  background: {INK}; color: #FFFFFF; border: 1px solid {INK};
}}
QPushButton[primary="true"]:hover {{ background: #2B3036; }}
QPushButton[primary="true"]:disabled {{
  background: {PAPER_SUNK}; color: {MUTED}; border: 1px solid {LINE};
}}
QPushButton[human="true"] {{
  background: {ULTRAMARINE}; color: #FFFFFF; border: 1px solid {ULTRAMARINE};
}}
QPushButton[human="true"]:hover {{ background: #2239B8; }}
QPushButton[human="true"]:disabled {{
  background: {ULTRAMARINE_TINT}; color: {MUTED}; border: 1px solid {ULTRAMARINE_LINE};
}}
QPushButton[ghost="true"] {{
  background: transparent; border: 1px solid transparent; padding: 4px 10px;
}}
QPushButton[ghost="true"]:hover {{ background: {PAPER_RAISED}; border-color: {LINE_STRONG}; }}
QPushButton[ghost="true"]:disabled {{ background: transparent; border-color: transparent; }}
QPushButton[danger="true"] {{ color: {VERMILION}; border-color: {VERMILION}; }}
QPushButton[danger="true"][ghost="true"] {{ border-color: transparent; }}
QPushButton[danger="true"][ghost="true"]:hover {{ border-color: {VERMILION}; }}
QPushButton:focus, QToolButton:focus {{
  border: 2px solid {FOCUS}; padding: 5px 13px;
}}
QPushButton[primary="true"]:focus, QPushButton[human="true"]:focus {{
  border: 2px solid {FOCUS}; padding: 5px 13px;
}}
QToolButton {{
  border: 1px solid transparent; color: {ULTRAMARINE}; text-decoration: underline;
  padding: 3px 4px; background: transparent;
}}

/* -- segmented filter ------------------------------------------------------------ */
QWidget[role="segtrack"] {{ background: {PAPER_SUNK}; border-radius: 8px; }}
QPushButton[seg="true"] {{
  border-radius: 6px; border: 1px solid transparent; padding: 5px 12px;
  background: transparent; color: {MUTED}; min-height: 20px;
}}
QPushButton[seg="true"]:hover {{ color: {INK}; background: transparent; border-color: transparent; }}
QPushButton[seg="true"]:checked {{
  background: {PAPER_RAISED}; color: {INK}; border: 1px solid {LINE};
}}
QPushButton[seg="true"]:focus {{ border: 2px solid {FOCUS}; padding: 4px 11px; }}
QPushButton[seg="true"]:disabled {{ color: #7A7E85; background: transparent; border-color: transparent; }}

/* -- inputs -------------------------------------------------------------------- */
QComboBox, QLineEdit, QPlainTextEdit, QListWidget {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG}; border-radius: 6px;
  padding: 3px 8px; selection-background-color: {ULTRAMARINE_TINT};
  selection-color: {INK};
}}
QComboBox {{ min-height: 22px; padding-right: 26px; }}
QComboBox::drop-down {{ border: none; width: 26px; background: transparent; }}
QComboBox QAbstractItemView {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG};
  selection-background-color: {ULTRAMARINE_TINT}; selection-color: {INK};
}}
QComboBox:disabled, QLineEdit:disabled, QPlainTextEdit:disabled {{
  color: #7A7E85; background: {PAPER}; border-color: {LINE};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus {{
  border: 2px solid {FOCUS};
}}
QRadioButton:focus, QCheckBox:focus {{ border: 2px solid {FOCUS}; border-radius: 3px; }}
QRadioButton, QCheckBox {{ spacing: 6px; background: transparent; }}
QRadioButton::indicator, QCheckBox::indicator, QListView::indicator {{
  width: 14px; height: 14px; border: 2px solid {GRAPHITE}; background: {PAPER_RAISED};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator, QListView::indicator {{ border-radius: 2px; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked,
QListView::indicator:checked {{
  background: {ULTRAMARINE}; border-color: {ULTRAMARINE};
}}
QTabBar::tab {{
  background: transparent; padding: 7px 14px; border: none;
  border-bottom: 2px solid transparent; color: {MUTED};
}}
QTabBar::tab:selected {{ color: {INK}; border-bottom: 2px solid {ULTRAMARINE}; }}
QTabBar::tab:focus {{ border-bottom: 2px solid {FOCUS}; }}

/* -- pill choices (context tags) ------------------------------------------------- */
QCheckBox[pill="true"] {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG}; border-radius: 11px;
  padding: 3px 10px; font-family: {MONO}; font-size: {SIZE_SMALL};
}}
QCheckBox[pill="true"]::indicator {{ width: 0; height: 0; border: none; }}
QCheckBox[pill="true"]:hover {{ border-color: {INK}; }}
QCheckBox[pill="true"]:checked {{
  background: {ULTRAMARINE_TINT}; border: 1px solid {ULTRAMARINE}; color: {ULTRAMARINE};
}}
QCheckBox[pill="true"]:focus {{ border: 2px solid {FOCUS}; padding: 2px 9px; }}
QCheckBox[pill="true"]:disabled {{ color: #7A7E85; border-color: {LINE}; }}

/* -- judgment choice (Accept AI / Correct / Uncertain) --------------------------- */
QRadioButton[choice="true"] {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG}; border-radius: 6px;
  padding: 5px 12px; color: {INK};
}}
QRadioButton[choice="true"]::indicator {{ width: 0; height: 0; border: none; }}
QRadioButton[choice="true"]:hover {{ border-color: {INK}; }}
QRadioButton[choice="true"]:checked {{
  background: {ULTRAMARINE}; color: #FFFFFF; border: 1px solid {ULTRAMARINE};
}}
QRadioButton[choice="true"]:focus {{
  border: 2px solid {FOCUS}; padding: 4px 11px; border-radius: 6px;
}}
QRadioButton[choice="true"]:disabled {{ color: #7A7E85; border-color: {LINE}; }}

QListWidget#review-queue {{ border: none; border-radius: 0; background: {PAPER_RAISED}; }}
QListWidget#review-queue:focus {{ border: 2px solid {FOCUS}; }}

/* -- tables -------------------------------------------------------------------- */
QTableWidget {{
  background: {PAPER_RAISED}; alternate-background-color: {PAPER_ALT};
  border: 1px solid {LINE}; border-radius: 6px; gridline-color: {LINE};
  selection-background-color: {ULTRAMARINE_TINT}; selection-color: {INK};
}}
QTableWidget:focus {{ border: 2px solid {FOCUS}; }}
QTableWidget::item {{ padding: 4px 8px; border: none; }}
QTableWidget::item:selected {{ background: {ULTRAMARINE_TINT}; color: {INK}; }}
QHeaderView::section {{
  background: {PAPER_RAISED}; color: {MUTED}; border: none;
  border-bottom: 1px solid {LINE_STRONG}; padding: 6px 8px; font-family: {MONO};
  font-size: 8pt;
}}
QTableCornerButton::section {{ background: {PAPER_RAISED}; border: none; }}

/* -- scrollbars ---------------------------------------------------------------- */
QScrollBar:vertical {{ background: transparent; width: 13px; margin: 0; }}
QScrollBar::handle:vertical {{
  background: {LINE_STRONG}; border-radius: 5px; min-height: 30px; margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {GRAPHITE_SOFT}; }}
QScrollBar:horizontal {{ background: transparent; height: 13px; margin: 0; }}
QScrollBar::handle:horizontal {{
  background: {LINE_STRONG}; border-radius: 5px; min-width: 30px; margin: 2px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* -- progress ------------------------------------------------------------------ */
QProgressBar {{
  border: 1px solid {LINE_STRONG}; border-radius: 4px; text-align: center;
  background: {PAPER_RAISED}; min-height: 16px;
}}
QProgressBar::chunk {{ background: {GRAPHITE}; border-radius: 3px; }}

/* -- sidebar ------------------------------------------------------------------- */
QFrame#sidebar {{
  background: {SIDEBAR_BG}; border: none; border-right: 1px solid {LINE}; border-radius: 0;
}}
QFrame#sidebar QWidget {{ background: transparent; }}
QFrame#sidebar QLabel {{ color: {INK}; background: transparent; }}
QFrame#sidebar QLabel[role="eyebrow"] {{ color: {MUTED}; }}
QFrame#sidebar QLabel[role="muted"] {{ color: {MUTED}; }}
QFrame#sidebar QLabel[role="mono"] {{ color: {MUTED}; }}
QFrame#sidebar QFrame[role="rule"] {{ background: {LINE}; }}
QLabel[role="brand"] {{ font-family: {SANS}; font-weight: 600; font-size: 11pt; }}
QLabel[role="project"] {{ font-family: {SANS}; font-weight: 600; font-size: 10.5pt; }}
QPushButton[nav="true"] {{
  background: transparent; color: {INK}; border: 1px solid transparent;
  border-radius: 6px; text-align: left; padding: 7px 12px; margin: 1px 10px;
}}
QPushButton[nav="true"]:hover {{ background: {PAPER_SUNK}; border-color: transparent; }}
QPushButton[nav="true"]:checked {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG};
}}
QPushButton[nav="true"]:disabled {{ color: #7A7E85; background: transparent; border-color: transparent; }}
QPushButton[nav="true"]:focus {{ border: 2px solid {FOCUS}; padding: 6px 11px; }}
QPushButton#models-status {{
  background: transparent; color: {MUTED}; border: 1px solid transparent;
  border-radius: 6px; text-align: left; padding: 8px 12px; font-family: {MONO};
  font-size: {SIZE_SMALL};
}}
QPushButton#models-status:hover {{ background: {PAPER_SUNK}; border-color: transparent; }}
QPushButton#models-status:focus {{ border: 2px solid {FOCUS}; padding: 7px 11px; }}
QFrame#sidebar QProgressBar {{
  border: 1px solid {LINE_STRONG}; background: {PAPER_RAISED};
}}
QFrame#sidebar QProgressBar::chunk {{ background: {GRAPHITE}; }}

/* -- chips and cells ------------------------------------------------------------- */
QLabel[chip="true"] {{
  border: 1px solid {LINE}; border-radius: 9px; padding: 1px 9px;
  background: {PAPER_SUNK}; color: {INK}; font-size: {SIZE_SMALL};
}}
QLabel[chip="true"][tone="ok"] {{
  border-color: {POSITIVE_LINE}; background: {POSITIVE_TINT}; color: {POSITIVE};
}}
QLabel[chip="true"][tone="warn"] {{
  border-color: {CAUTION_LINE}; background: {CAUTION_BG}; color: {CAUTION_TEXT};
}}
QLabel[chip="true"][tone="error"] {{
  border-color: #F1C3B5; background: {VERMILION_TINT}; color: {VERMILION};
}}
QLabel[chip="true"][tone="human"] {{
  border-color: {ULTRAMARINE_LINE}; background: {ULTRAMARINE_PALE}; color: {ULTRAMARINE};
}}
QLabel[chip="true"][tone="machine"] {{
  border-color: {GRAPHITE_LINE}; background: {GRAPHITE_TINT}; color: {GRAPHITE};
}}
QLabel[cell="true"] {{
  border: 1px solid {LINE}; font-family: {SERIF}; font-size: 18pt;
  min-width: 70px; min-height: 52px;
}}
{_confusion_rules()}
"""
