"""Operating-system file locks for scoped cross-process exclusion.

One small lock file per scope. The lock is an OS byte-range/``flock`` lock on an open
handle, so it disappears with the process however it ends (including a hard kill);
no lock file content or existence ever means "held". Locks are tried without
waiting. Nothing here logs and nothing is written into the lock files.
"""

from __future__ import annotations

import contextlib
import errno
import os
import re
import sys
from pathlib import Path

from ..application.exclusion import ProcessLock

_SCOPE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
_CONTENDED = {errno.EACCES, errno.EAGAIN, errno.EDEADLK, getattr(errno, "EDEADLOCK", 0)}
_MAX_REOPEN = 8


def _try_lock(fd: int) -> bool:
    """Take an exclusive lock on ``fd`` without waiting; False if it is held."""

    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as error:
            if error.errno in _CONTENDED:
                return False
            raise
        return True
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in _CONTENDED:
            return False
        raise
    return True


def _unlock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        with contextlib.suppress(OSError):
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    with contextlib.suppress(OSError):
        fcntl.flock(fd, fcntl.LOCK_UN)


class _HeldLock:
    def __init__(self, fd: int, path: Path) -> None:
        self._fd: int | None = fd
        self._path = path

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        _unlock(fd)
        os.close(fd)

    def discard(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        # POSIX may unlink while holding; Windows refuses to unlink an open file,
        # so close first and ignore a refusal (another holder has it open: keep).
        if sys.platform != "win32":
            with contextlib.suppress(OSError):
                self._path.unlink()
        _unlock(fd)
        os.close(fd)
        if sys.platform == "win32":
            with contextlib.suppress(OSError):
                self._path.unlink()


class FileProcessLocks:
    """``ProcessLocks`` over lock files in one folder, created on first use."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def try_acquire(self, scope: str) -> ProcessLock | None:
        if not _SCOPE.fullmatch(scope):
            raise ValueError("Invalid lock scope.")
        path = self._directory / f"{scope}.lock"
        self._directory.mkdir(parents=True, exist_ok=True)
        for _ in range(_MAX_REOPEN):
            fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                if not _try_lock(fd):
                    os.close(fd)
                    return None
                if sys.platform == "win32" or _is_current_file(fd, path):
                    return _HeldLock(fd, path)
                # The file was replaced while we locked the old one: try again.
                _unlock(fd)
                os.close(fd)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.close(fd)
                raise
        return None


def _is_current_file(fd: int, path: Path) -> bool:
    try:
        return os.fstat(fd).st_ino == os.stat(path).st_ino
    except OSError:
        return False


__all__ = ["FileProcessLocks"]
