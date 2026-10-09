"""A bounded one-line excerpt of a record's text, for lists and tables.

The only way a row read model ever carries record text: whitespace is folded to
single spaces and the result is cut at a fixed length, so a long text is never held
whole by a view and a line break never reaches a table cell.
"""

from __future__ import annotations

import unicodedata

ROW_EXCERPT_LENGTH = 100
EMPTY_MARKER = "(empty)"


def _printable(text: str) -> str:
    """Drop control and format characters (including bidirectional overrides)."""

    return "".join(
        char
        for char in text
        if char.isspace() or unicodedata.category(char) not in {"Cc", "Cf"}
    )


def excerpt(text: str, limit: int = ROW_EXCERPT_LENGTH) -> str:
    # only the start can reach a cell, so a huge text is never copied whole
    flat = " ".join(_printable(text[: limit * 4]).split())
    if not flat:
        return EMPTY_MARKER
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


__all__ = ["EMPTY_MARKER", "ROW_EXCERPT_LENGTH", "excerpt"]
