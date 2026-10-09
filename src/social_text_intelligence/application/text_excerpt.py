"""A bounded one-line excerpt of a record's text, for lists and tables.

The only way a row read model ever carries record text: whitespace is folded to
single spaces and the result is cut at a fixed length, so a long text is never held
whole by a view and a line break never reaches a table cell.
"""

from __future__ import annotations

ROW_EXCERPT_LENGTH = 100
EMPTY_MARKER = "(empty)"


def excerpt(text: str, limit: int = ROW_EXCERPT_LENGTH) -> str:
    flat = " ".join(text.split())
    if not flat:
        return EMPTY_MARKER
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


__all__ = ["EMPTY_MARKER", "ROW_EXCERPT_LENGTH", "excerpt"]
