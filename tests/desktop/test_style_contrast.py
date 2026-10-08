"""The palette meets WCAG 2.x contrast where it carries text or identifies a control."""

from __future__ import annotations

import pytest

from social_text_intelligence.desktop.qt import style as s

WHITE = "#FFFFFF"


def luminance(colour: str) -> float:
    r, g, b = (int(colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def linear(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return float(((channel + 0.055) / 1.055) ** 2.4)

    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def ratio(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


TEXT_PAIRS = [
    ("ink on paper", s.INK, s.PAPER),
    ("ink on raised", s.INK, s.PAPER_RAISED),
    ("ink on sunk", s.INK, s.PAPER_SUNK),
    ("ink on alternate row", s.INK, s.PAPER_ALT),
    ("ink on caution", s.INK, s.CAUTION_BG),
    ("ink on selection", s.INK, s.ULTRAMARINE_TINT),
    ("muted on paper", s.MUTED, s.PAPER),
    ("muted on raised", s.MUTED, s.PAPER_RAISED),
    ("muted on sunk", s.MUTED, s.PAPER_SUNK),
    ("muted on alternate row", s.MUTED, s.PAPER_ALT),
    ("link on paper", s.ULTRAMARINE, s.PAPER),
    ("link on raised", s.ULTRAMARINE, s.PAPER_RAISED),
    ("primary button", WHITE, s.ULTRAMARINE),
    ("failure on paper", s.VERMILION, s.PAPER),
    ("failure on raised", s.VERMILION, s.PAPER_RAISED),
    ("sidebar text", s.PAPER, s.GRAPHITE),
    ("sidebar text, selected", s.PAPER, s.GRAPHITE_SOFT),
    ("sidebar caption", s.SIDEBAR_MUTED, s.GRAPHITE),
    ("selected filter", WHITE, s.GRAPHITE),
]


@pytest.mark.parametrize(("name", "foreground", "background"), TEXT_PAIRS)
def test_text_meets_the_normal_text_contrast_of_4_5(
    name: str, foreground: str, background: str
) -> None:
    assert ratio(foreground, background) >= 4.5, name


@pytest.mark.parametrize(
    ("matches", "level", "fill", "text"), s.CONFUSION_STYLES
)
def test_every_confusion_cell_keeps_its_count_readable(
    matches: bool, level: int, fill: str, text: str
) -> None:
    assert ratio(text, fill) >= 4.5, (matches, level)


def test_a_control_and_its_focus_ring_are_visible_against_the_page() -> None:
    assert ratio(s.LINE_STRONG, s.PAPER_RAISED) >= 3.0  # input and combo borders
    assert ratio(s.LINE_STRONG, s.PAPER) >= 3.0
    assert ratio(s.FOCUS, s.PAPER) >= 3.0
    assert ratio(s.FOCUS, s.PAPER_RAISED) >= 3.0
