"""One stylesheet in the approved visual language, using system-safe font fallbacks.

Warm paper, graphite for the machine, ultramarine for the human, vermilion only for
disagreement and failure. The prototype's web fonts are not bundled: their licences
are unverified, so the Windows system faces (Segoe UI, Georgia, Consolas) stand in.
Every state also carries an icon and a word, so colour is never the only signal.

The sheet is built from named tokens so the type scale, spacing, and colours are
decided in one place. Contrast (WCAG 2.x, measured on the surface each sits on, enforced by
``tests/desktop/test_style_contrast.py``): ink 15.2:1, muted 6.2 to 7.2:1,
ultramarine 8.0:1, vermilion 5.3:1, graphite 8.8:1; the border that identifies a
control (``LINE_STRONG``) is at least 3.2:1.
"""

from __future__ import annotations

# -- colour -------------------------------------------------------------------
PAPER = "#F6F1E7"
PAPER_RAISED = "#FBF8F1"
PAPER_SUNK = "#EFE8D8"
PAPER_ALT = "#F3EDDF"
INK = "#1F1B16"
MUTED = "#5A5348"
LINE = "#D6CDBB"
LINE_STRONG = "#8F8672"
GRAPHITE = "#3F434A"
GRAPHITE_SOFT = "#565B63"
ULTRAMARINE = "#2B3FA0"
ULTRAMARINE_TINT = "#DDE2F4"
VERMILION = "#B3380E"
VERMILION_TINT = "#F4D9CE"
CAUTION_BG = "#FAF0D6"
CAUTION_LINE = "#B98A1F"
FOCUS = "#2B3FA0"
SIDEBAR_MUTED = "#C9C4B6"

# -- type ---------------------------------------------------------------------
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"
SIZE_BODY = "10pt"
SIZE_SMALL = "9pt"
SIZE_TITLE = "13pt"
SIZE_HEADLINE = "21pt"
SIZE_FIGURE = "27pt"

# -- space (pixels) -----------------------------------------------------------
SPACE_XS = 4
SPACE_S = 8
SPACE_M = 12
SPACE_L = 16
SPACE_XL = 24
PAGE_MARGIN_X = 28
PAGE_MARGIN_TOP = 22
RADIUS = 6


# (matches the AI label?, shade level, fill, text): the count is always written inside
CONFUSION_STYLES: tuple[tuple[bool, int, str, str], ...] = tuple(
    (match, level, fill[level], text[level])
    for match, fill, text in (
        (
            True,
            ("#FBF8F1", "#D9DBDF", "#B1B5BC", "#5F646C", "#3F434A"),
            (INK, INK, INK, "#FFFFFF", "#FFFFFF"),
        ),
        (
            False,
            ("#FBF8F1", "#F6E3DA", "#EDC3B1", "#DE9479", "#B3380E"),
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
QLabel[role="muted"] {{ color: {MUTED}; }}
QLabel[role="mono"] {{ font-family: {MONO}; color: {MUTED}; font-size: {SIZE_SMALL}; }}
QLabel[role="eyebrow"] {{
  font-family: {MONO}; color: {MUTED}; font-size: 8pt; letter-spacing: 1px;
}}
QLabel[role="error"] {{ color: {VERMILION}; }}
QLabel[role="subtitle"] {{ font-family: {MONO}; color: {MUTED}; font-size: {SIZE_SMALL}; }}

/* -- surfaces ------------------------------------------------------------------ */
QFrame[role="card"], QFrame[role="panel"] {{
  background: {PAPER_RAISED}; border: 1px solid {LINE}; border-radius: {RADIUS}px;
}}
QFrame[role="card"] QLabel, QFrame[role="panel"] QLabel {{ background: transparent; }}
QFrame[role="alert"] {{
  background: {PAPER_RAISED}; border: 2px solid {VERMILION}; border-radius: {RADIUS}px;
}}
QFrame[role="notice"] {{
  background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; border-radius: {RADIUS}px;
}}
QFrame[role="caution"] {{
  background: {CAUTION_BG}; border: 1px solid {CAUTION_LINE}; border-radius: {RADIUS}px;
}}
QFrame[role="ai"] {{
  background: {PAPER_RAISED}; border: 2px solid {GRAPHITE}; border-radius: {RADIUS}px;
}}
QFrame[role="human"] {{
  background: {PAPER_RAISED}; border: 2px solid {ULTRAMARINE}; border-radius: {RADIUS}px;
}}
QFrame[role="empty"] {{
  background: transparent; border: 1px dashed {LINE_STRONG}; border-radius: {RADIUS}px;
}}
QFrame[role="alert"] QLabel, QFrame[role="notice"] QLabel, QFrame[role="caution"] QLabel,
QFrame[role="ai"] QLabel, QFrame[role="human"] QLabel, QFrame[role="empty"] QLabel {{
  background: transparent;
}}
QFrame[role="rule"] {{ background: {LINE}; border: none; max-height: 1px; min-height: 1px; }}
QGroupBox {{
  border: 1px solid {LINE}; border-radius: 4px; margin-top: 10px; padding: 8px;
  background: transparent;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}

/* -- buttons ------------------------------------------------------------------- */
QPushButton {{
  background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; border-radius: 5px;
  padding: 6px 14px; min-height: 22px;
}}
QPushButton:hover {{ background: {PAPER_SUNK}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:disabled {{ color: #7A7366; border-color: {LINE}; background: {PAPER}; }}
QPushButton[primary="true"] {{
  background: {ULTRAMARINE}; color: #FFFFFF; border: 1px solid {ULTRAMARINE};
}}
QPushButton[primary="true"]:hover {{ background: #22328A; }}
QPushButton[primary="true"]:disabled {{
  background: #E4DED0; color: {MUTED}; border: 1px solid {LINE};
}}
QPushButton[danger="true"] {{ color: {VERMILION}; border-color: {VERMILION}; }}
QPushButton:focus, QToolButton:focus {{
  border: 2px solid {FOCUS}; padding: 5px 13px;
}}
QPushButton[primary="true"]:focus {{ border: 2px solid {INK}; }}
QToolButton {{
  border: 1px solid transparent; color: {ULTRAMARINE}; text-decoration: underline;
  padding: 3px 4px; background: transparent;
}}

/* -- segmented filter ------------------------------------------------------------ */
QPushButton[seg="true"] {{
  border-radius: 0; border: 1px solid {LINE_STRONG}; padding: 5px 14px;
  background: {PAPER_RAISED};
}}
QPushButton[seg="true"][pos="first"] {{
  border-top-left-radius: 5px; border-bottom-left-radius: 5px;
}}
QPushButton[seg="true"][pos="last"] {{
  border-top-right-radius: 5px; border-bottom-right-radius: 5px;
}}
QPushButton[seg="true"]:checked {{
  background: {GRAPHITE}; color: #FFFFFF; border-color: {GRAPHITE};
}}
QPushButton[seg="true"]:focus {{ border: 2px solid {FOCUS}; padding: 4px 13px; }}

/* -- inputs -------------------------------------------------------------------- */
QComboBox, QLineEdit, QPlainTextEdit, QListWidget {{
  background: {PAPER_RAISED}; border: 1px solid {LINE_STRONG}; border-radius: 4px;
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
  color: #7A7366; background: {PAPER}; border-color: {LINE};
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

/* -- tables -------------------------------------------------------------------- */
QTableWidget {{
  background: {PAPER_RAISED}; alternate-background-color: {PAPER_ALT};
  border: 1px solid {LINE}; border-radius: 4px; gridline-color: {LINE};
  selection-background-color: {ULTRAMARINE_TINT}; selection-color: {INK};
}}
QTableWidget:focus {{ border: 2px solid {FOCUS}; }}
QTableWidget::item {{ padding: 4px 8px; border: none; }}
QTableWidget::item:selected {{ background: {ULTRAMARINE_TINT}; color: {INK}; }}
QHeaderView::section {{
  background: {PAPER_SUNK}; color: {MUTED}; border: none;
  border-bottom: 1px solid {LINE_STRONG}; padding: 6px 8px; font-family: {MONO};
  font-size: 8pt;
}}
QTableCornerButton::section {{ background: {PAPER_SUNK}; border: none; }}

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
  border: 1px solid {GRAPHITE}; border-radius: 4px; text-align: center;
  background: {PAPER_RAISED}; min-height: 16px;
}}
QProgressBar::chunk {{ background: {GRAPHITE}; border-radius: 3px; }}

/* -- sidebar ------------------------------------------------------------------- */
QFrame#sidebar {{ background: {GRAPHITE}; border: none; border-radius: 0; }}
QFrame#sidebar QWidget {{ background: transparent; }}
QFrame#sidebar QLabel {{ color: {PAPER}; background: transparent; }}
QFrame#sidebar QLabel[role="eyebrow"] {{ color: {SIDEBAR_MUTED}; }}
QFrame#sidebar QLabel[role="muted"] {{ color: {SIDEBAR_MUTED}; }}
QFrame#sidebar QLabel[role="mono"] {{ color: {SIDEBAR_MUTED}; }}
QFrame#sidebar QFrame[role="rule"] {{ background: {GRAPHITE_SOFT}; }}
QPushButton[nav="true"] {{
  background: transparent; color: {PAPER}; border: none; border-left: 3px solid transparent;
  border-radius: 0; text-align: left; padding: 8px 14px;
}}
QPushButton[nav="true"]:hover {{ background: {GRAPHITE_SOFT}; }}
QPushButton[nav="true"]:checked {{
  background: {GRAPHITE_SOFT}; border-left: 3px solid {PAPER};
}}
QPushButton[nav="true"]:disabled {{ color: #A39E90; background: transparent; }}
QPushButton[nav="true"]:focus {{ border: 2px solid {PAPER}; padding: 6px 12px; }}
QPushButton#models-status {{
  background: {GRAPHITE_SOFT}; color: {PAPER}; border: 1px solid {SIDEBAR_MUTED};
  text-align: left; padding: 8px 12px;
}}
QPushButton#models-status:focus {{ border: 2px solid #FFFFFF; padding: 7px 11px; }}
QFrame#sidebar QProgressBar {{
  border: 1px solid {SIDEBAR_MUTED}; background: {GRAPHITE};
}}
QFrame#sidebar QProgressBar::chunk {{ background: {PAPER}; }}

/* -- chips and cells ------------------------------------------------------------- */
QLabel[chip="true"] {{
  border: 1px solid {LINE_STRONG}; border-radius: 9px; padding: 1px 9px;
  background: {PAPER_RAISED}; font-size: {SIZE_SMALL};
}}
QLabel[chip="true"][tone="ok"] {{ border-color: {GRAPHITE}; }}
QLabel[chip="true"][tone="warn"] {{ border-color: {CAUTION_LINE}; background: {CAUTION_BG}; }}
QLabel[chip="true"][tone="error"] {{ border-color: {VERMILION}; color: {VERMILION}; }}
QLabel[cell="true"] {{
  border: 1px solid {LINE}; font-family: {SERIF}; font-size: 15pt;
  min-width: 70px; min-height: 44px;
}}
{_confusion_rules()}
"""
