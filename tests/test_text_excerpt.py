"""The bounded one-line excerpt used by the row read models."""

from __future__ import annotations

from social_text_intelligence.application.text_excerpt import (
    EMPTY_MARKER,
    ROW_EXCERPT_LENGTH,
    excerpt,
)


def test_whitespace_is_folded_and_a_short_text_is_kept() -> None:
    assert excerpt("  two\n\tlines   here ") == "two lines here"


def test_an_empty_or_blank_text_gets_a_marker() -> None:
    assert excerpt("") == EMPTY_MARKER and excerpt(" \n\t ") == EMPTY_MARKER


def test_a_long_text_is_cut_with_an_ellipsis_inside_the_limit() -> None:
    shown = excerpt("word " * 500)

    assert len(shown) <= ROW_EXCERPT_LENGTH and shown.endswith("…")


def test_control_and_direction_override_characters_never_reach_a_cell() -> None:
    shown = excerpt("safe\u202etxet\x00\x07 and more")

    assert "\u202e" not in shown and "\x00" not in shown and "\x07" not in shown
    assert shown.startswith("safetxet") or shown.startswith("safe")


def test_a_huge_text_is_not_copied_whole() -> None:
    huge = "a" * 5_000_000

    assert len(excerpt(huge)) <= ROW_EXCERPT_LENGTH
