"""Shared reading of operating-system error numbers."""

from __future__ import annotations

import errno

_WIN_DISK_FULL = 112
_WIN_HANDLE_DISK_FULL = 39


def is_disk_full(error: OSError) -> bool:
    """True for ENOSPC and the Windows disk-full errors."""

    return error.errno == errno.ENOSPC or getattr(error, "winerror", None) in {
        _WIN_DISK_FULL,
        _WIN_HANDLE_DISK_FULL,
    }


__all__ = ["is_disk_full"]
