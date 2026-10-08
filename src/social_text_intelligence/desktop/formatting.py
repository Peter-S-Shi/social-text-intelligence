"""Human-readable sizes, using Windows-style labels for binary units."""

from __future__ import annotations

_KIB = 1024
_MIB = _KIB * 1024
_GIB = _MIB * 1024


def format_bytes(size: int) -> str:
    """Return ``479.1 MB`` / ``1.50 GB`` for ``size`` bytes (1 MB = 1,048,576).

    Like Explorer, a value of 1000 or more switches to the next unit.
    """

    if size >= 1000 * _MIB:
        return f"{size / _GIB:.2f} GB"
    if size >= _MIB:
        return f"{size / _MIB:.1f} MB"
    if size >= _KIB:
        return f"{size / _KIB:.1f} KB"
    return f"{size} B"
