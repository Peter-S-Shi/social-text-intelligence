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
    ("primary button", WHITE, s.INK),
    ("human action and chosen judgment", WHITE, s.ULTRAMARINE),
    ("failure on paper", s.VERMILION, s.PAPER),
    ("failure on raised", s.VERMILION, s.PAPER_RAISED),
    ("positive on raised", s.POSITIVE, s.PAPER_RAISED),
    ("neutral on raised", s.NEUTRAL, s.PAPER_RAISED),
    ("ink on sidebar", s.INK, s.SIDEBAR_BG),
    ("muted on sidebar", s.MUTED, s.SIDEBAR_BG),
    ("ink on selected nav item", s.INK, s.PAPER_RAISED),
    ("ink on hovered nav item", s.INK, s.PAPER_SUNK),
    ("selected segment", s.INK, s.PAPER_RAISED),
    ("unselected segment", s.MUTED, s.PAPER_SUNK),
    ("ink on AI card", s.INK, s.GRAPHITE_TINT),
    ("muted on AI card", s.MUTED, s.GRAPHITE_TINT),
    ("ink on human card", s.INK, s.ULTRAMARINE_PALE),
    ("muted on human card", s.MUTED, s.ULTRAMARINE_PALE),
    ("ready chip", s.POSITIVE, s.POSITIVE_TINT),
    ("caution chip", s.CAUTION_TEXT, s.CAUTION_BG),
    ("failure chip", s.VERMILION, s.VERMILION_TINT),
    ("human chip", s.ULTRAMARINE, s.ULTRAMARINE_PALE),
    ("machine chip", s.GRAPHITE, s.GRAPHITE_TINT),
]


@pytest.mark.parametrize(("name", "foreground", "background"), TEXT_PAIRS)
def test_text_meets_the_normal_text_contrast_of_4_5(
    name: str, foreground: str, background: str
) -> None:
    assert ratio(foreground, background) >= 4.5, name


@pytest.mark.parametrize(("matches", "level", "fill", "text"), s.CONFUSION_STYLES)
def test_every_confusion_cell_keeps_its_count_readable(
    matches: bool, level: int, fill: str, text: str
) -> None:
    assert ratio(text, fill) >= 4.5, (matches, level)


def test_a_control_and_its_focus_ring_are_visible_against_the_page() -> None:
    assert ratio(s.LINE_STRONG, s.PAPER_RAISED) >= 3.0  # input and combo borders
    assert ratio(s.LINE_STRONG, s.PAPER) >= 3.0
    assert ratio(s.FOCUS, s.PAPER) >= 3.0
    assert ratio(s.FOCUS, s.PAPER_RAISED) >= 3.0


LARGE_TEXT_PAIRS = [  # 22 pt and larger serif words and figures: WCAG large text, 3:1
    ("neutral word on card", s.NEUTRAL, s.PAPER_RAISED),
    ("neutral word on paper", s.NEUTRAL, s.PAPER),
    ("neutral word on AI card", s.NEUTRAL, s.GRAPHITE_TINT),
    ("section numeral on paper", s.LINE_STRONG, s.PAPER),
]


@pytest.mark.parametrize(("name", "foreground", "background"), LARGE_TEXT_PAIRS)
def test_large_serif_words_meet_the_large_text_contrast_of_3(
    name: str, foreground: str, background: str
) -> None:
    assert ratio(foreground, background) >= 3.0, name


@pytest.mark.parametrize(
    "surface",
    [
        s.PAPER_SUNK,
        s.SIDEBAR_BG,
        s.GRAPHITE_TINT,
        s.ULTRAMARINE_PALE,
        s.CAUTION_BG,
    ],
)
def test_a_control_border_is_visible_on_every_tinted_surface_it_sits_on(
    surface: str,
) -> None:
    assert ratio(s.LINE_STRONG, surface) >= 3.0


@pytest.mark.parametrize(
    "surface", [s.PAPER, s.PAPER_RAISED, s.GRAPHITE_TINT, s.ULTRAMARINE_PALE]
)
def test_text_in_the_failure_positive_and_caution_tones_is_readable_on_cards(
    surface: str,
) -> None:
    assert ratio(s.VERMILION, surface) >= 4.5
    assert ratio(s.POSITIVE, surface) >= 4.5


def test_the_focus_ring_of_a_filled_control_is_visible_against_its_fill() -> None:
    # a ring of the same blue as a human action would vanish (1.0:1): the ring there is
    # a 3 px ink border, 2.7:1 against the blue fill and 16:1 against the page
    assert ratio(s.FOCUS, s.ULTRAMARINE) < 1.5
    assert ratio(s.INK, s.ULTRAMARINE) >= 2.5
    assert ratio(s.INK, s.PAPER) >= 7.0
    assert ratio(s.FOCUS, s.PAPER) >= 3.0  # the ring against the page beside a button
    assert ratio("#FFFFFF", "#3A4048") >= 4.5  # the primary button's lifted fill
