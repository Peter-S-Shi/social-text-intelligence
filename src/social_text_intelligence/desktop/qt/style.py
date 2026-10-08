"""One stylesheet in the approved visual language, using system-safe font fallbacks.

Warm paper, graphite for the machine, ultramarine for the human, vermilion only for
disagreement and failure. The prototype's web fonts are not bundled: their licences
are unverified, so Georgia, Segoe UI and Consolas stand in (M5.2 scope decision).
Every state also carries an icon and a word, so colour is never the only signal.
"""

from __future__ import annotations

PAPER = "#F6F1E7"
PAPER_RAISED = "#FBF8F1"
INK = "#1F1B16"
MUTED = "#5A5348"
LINE = "#CFC6B4"
GRAPHITE = "#3F434A"
ULTRAMARINE = "#2B3FA0"
VERMILION = "#B3380E"
FOCUS = "#2B3FA0"

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"

STYLESHEET = f"""
QWidget {{ background: {PAPER}; color: {INK}; font-family: {SANS}; font-size: 10pt; }}
QDialog, QMainWindow {{ background: {PAPER}; }}
QLabel {{ background: transparent; }}
QLabel[role="headline"] {{ font-family: {SERIF}; font-size: 20pt; }}
QLabel[role="title"] {{ font-family: {SERIF}; font-size: 13pt; }}
QLabel[role="muted"] {{ color: {MUTED}; }}
QLabel[role="mono"] {{ font-family: {MONO}; color: {MUTED}; }}
QLabel[role="error"] {{ color: {VERMILION}; }}
QFrame[role="card"], QFrame[role="panel"] {{
  background: {PAPER_RAISED}; border: 1px solid {LINE}; border-radius: 6px;
}}
QFrame[role="card"] QLabel, QFrame[role="panel"] QLabel {{ background: transparent; }}
QFrame[role="alert"] {{
  background: {PAPER_RAISED}; border: 2px solid {VERMILION}; border-radius: 6px;
}}
QFrame[role="notice"] {{
  background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; border-radius: 6px;
}}
QFrame[role="ai"] {{
  background: {PAPER_RAISED}; border: 2px solid {GRAPHITE}; border-radius: 6px;
}}
QFrame[role="human"] {{
  background: {PAPER_RAISED}; border: 2px solid {ULTRAMARINE}; border-radius: 6px;
}}
QFrame[role="ai"] QLabel, QFrame[role="human"] QLabel {{ background: transparent; }}
QGroupBox {{
  border: 1px solid {LINE}; border-radius: 4px; margin-top: 10px; padding: 8px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QRadioButton:focus, QCheckBox:focus, QComboBox:focus {{ border: 2px solid {FOCUS}; }}
QRadioButton::indicator, QCheckBox::indicator, QListView::indicator {{
  width: 14px; height: 14px; border: 2px solid {GRAPHITE}; background: {PAPER};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator, QListView::indicator {{ border-radius: 2px; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked,
QListView::indicator:checked {{
  background: {ULTRAMARINE}; border-color: {ULTRAMARINE};
}}
QFrame#sidebar {{ background: {GRAPHITE}; border: none; }}
QFrame#sidebar QLabel {{ color: {PAPER}; }}
QPushButton {{
  background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; border-radius: 4px;
  padding: 6px 14px; min-height: 22px;
}}
QPushButton:hover {{ background: #EFE8D8; }}
QPushButton:disabled {{ color: #7A7366; border-color: {LINE}; background: {PAPER}; }}
QPushButton[primary="true"] {{
  background: {ULTRAMARINE}; color: #FFFFFF; border: 1px solid {ULTRAMARINE};
}}
QPushButton[primary="true"]:disabled {{
  background: #E4DED0; color: #5A5348; border: 1px solid {LINE};
}}
QPushButton:focus, QPlainTextEdit:focus, QToolButton:focus {{
  border: 2px solid {FOCUS};
}}
QPushButton[nav="true"] {{
  background: transparent; color: {PAPER}; border: none; text-align: left;
  padding: 8px 12px;
}}
QPushButton[nav="true"]:checked {{ background: #565B63; }}
QPushButton[nav="true"]:focus {{ border: 2px solid {PAPER}; }}
QPushButton#models-status {{
  background: #565B63; color: {PAPER}; border: 1px solid {PAPER}; text-align: left;
  padding: 8px 12px;
}}
QPushButton#models-status:focus {{ border: 2px solid #FFFFFF; }}
QProgressBar {{
  border: 1px solid {GRAPHITE}; border-radius: 4px; text-align: center;
  background: {PAPER}; min-height: 16px;
}}
QProgressBar::chunk {{ background: {GRAPHITE}; }}
QPlainTextEdit {{ background: {PAPER_RAISED}; border: 1px solid {GRAPHITE}; }}
QToolButton {{ border: none; color: {ULTRAMARINE}; text-decoration: underline; }}
"""
