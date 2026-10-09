"""Hold a real file open the way another program (scanner, sync client) can."""

from __future__ import annotations

import contextlib
import ctypes
from collections.abc import Iterator
from pathlib import Path

_GENERIC_READ_WRITE = 0xC0000000
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x80
_INVALID_HANDLE = ctypes.c_void_p(-1).value


@contextlib.contextmanager
def exclusive_handle(path: Path, share: int) -> Iterator[None]:
    """Keep ``path`` open with a Win32 share mode (0 allows no other opener)."""

    win_dll = getattr(ctypes, "WinDLL")  # noqa: B009 - Windows-only, absent elsewhere
    kernel32 = win_dll("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = ctypes.c_void_p
    handle = kernel32.CreateFileW(
        str(path),
        _GENERIC_READ_WRITE,
        share,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle in (None, _INVALID_HANDLE):
        last_error = getattr(ctypes, "get_last_error")  # noqa: B009
        raise OSError(last_error(), "could not hold the file open")
    try:
        yield
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
