"""Low-level SQLite helpers shared by the durable project store.

Nothing here logs, and failures are translated into fixed, content-free messages.
"""

from __future__ import annotations

import contextlib
import errno
import functools
import os
import re
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import ParamSpec, TypeVar

from ..contracts.errors import ProjectStorageError
from .os_errors import is_disk_full

PROJECT_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
# Every file name this store creates for a project: the database, a migration
# backup, and SQLite's WAL/SHM/journal sidecars of either.
_MANAGED_FILE = re.compile(
    r"([0-9a-f]{32})[.](?:sqlite3|pre-migration-v[0-9]+[.]sqlite3[.]bak)"
    r"(?:-wal|-shm|-journal)?"
)
_BUSY_TIMEOUT_SECONDS = 5.0

_P = ParamSpec("_P")
_R = TypeVar("_R")


SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


def touches_symlink(path: Path) -> bool:
    """True if this database path or any SQLite sidecar of it is a symlink.

    SQLite follows links when it opens a database and its WAL, shared-memory,
    or journal files, so a link here could lead a read or write outside the
    projects directory. Such a path is never opened."""

    return path.is_symlink() or any(
        path.with_name(path.name + suffix).is_symlink() for suffix in SIDECAR_SUFFIXES
    )


def is_regular_file(path: Path) -> bool:
    """True for a regular file, False only when the path is definitely absent.

    Any other failure to look at the file (a sharing violation or access-denied
    while a scanner, sync client or another instance has it open) is raised, never
    turned into "no such file": a project that exists must not read as missing.
    ``Path.is_file`` cannot be used because Python 3.13 and later swallow every
    ``OSError`` there, while earlier versions swallow only a few."""

    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def entry_may_exist(path: Path) -> bool:
    """False only when ``path`` is definitely absent or neither a file nor a link."""

    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return True  # unknown: keep it listed rather than let the project vanish
    return stat.S_ISREG(mode) or stat.S_ISLNK(mode)


def managed_project_id(file_name: str) -> str | None:
    """Return the project id a store-created file name belongs to, else None."""

    match = _MANAGED_FILE.fullmatch(file_name)
    return match.group(1) if match else None


def valid_project_id(token: str) -> str | None:
    """Accept only ids this store generates, so a token can never name a path."""

    return token if PROJECT_ID_PATTERN.fullmatch(token) else None


_FAILURES = {
    "unsupported_text": "The workspace contains text that cannot be stored.",
    "project_busy": "The project is in use by another operation; try again.",
    "storage_full": (
        "There is not enough free disk space to save this project. Free some "
        "disk space and try again. Nothing was changed."
    ),
    "storage_read_only": (
        "This project's file or folder cannot be written. It may be marked "
        "read-only, access may be denied, or another program may be holding it "
        "open. Clear the read-only setting or close that program, then try "
        "again. Nothing was changed."
    ),
    "storage_locked": (
        "This project's file could not be opened. Another program (a backup, "
        "sync or antivirus tool, or another copy of this app) may be using it, "
        "or access may be denied. Close it or wait a moment, then try again. "
        "Nothing was changed."
    ),
    "storage_failure": (
        "The project storage could not complete the operation. Check free disk "
        "space and the data folder's permissions, then try again."
    ),
}

# SQLite primary result codes (the low byte of an extended code).
_SQLITE_BUSY, _SQLITE_LOCKED, _SQLITE_READONLY = 5, 6, 8
_SQLITE_FULL, _SQLITE_CANTOPEN = 13, 14
_WIN_SHARING_VIOLATION, _WIN_LOCK_VIOLATION = 32, 33


def _failure(code: str) -> ProjectStorageError:
    return ProjectStorageError(code=code, message=_FAILURES[code])


def _classify_sqlite(error: sqlite3.Error) -> str:
    primary = getattr(error, "sqlite_errorcode", None)
    text = str(error).lower()
    if primary is not None:
        primary &= 0xFF
    if primary == _SQLITE_FULL or "disk is full" in text:
        return "storage_full"
    if primary == _SQLITE_READONLY or "readonly database" in text:
        return "storage_read_only"
    if primary in {_SQLITE_BUSY, _SQLITE_LOCKED} or "locked" in text:
        return "project_busy"
    if primary == _SQLITE_CANTOPEN or "unable to open database" in text:
        return "storage_locked"
    return "storage_failure"


def _classify_os(error: OSError) -> str:
    if is_disk_full(error):
        return "storage_full"
    # Windows reports a sharing or lock violation as errno EACCES too, so the
    # specific Windows error must be read before the generic errno.
    if getattr(error, "winerror", None) in {
        _WIN_SHARING_VIOLATION,
        _WIN_LOCK_VIOLATION,
    }:
        return "storage_locked"
    if error.errno in {errno.EROFS, errno.EACCES, errno.EPERM}:
        return "storage_read_only"
    return "storage_failure"


def storage_guarded(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """Translate low-level failures into content-free ``ProjectStorageError``.

    The new error is raised after the ``except`` block has finished, so it carries
    no ``__context__`` or ``__cause__``: the original failure (a Unicode error, for
    instance, holds the offending text) is not reachable from it. Disk-full,
    read-only, in-use and busy faults each get their own code and a fixed message
    that says what to do; the raw error text is never shown.
    """

    @functools.wraps(function)
    def guarded(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        code: str
        try:
            return function(*args, **kwargs)
        except ProjectStorageError:
            raise
        except sqlite3.Error as error:
            code = _classify_sqlite(error)
        except UnicodeEncodeError:
            code = "unsupported_text"
        except OSError as error:
            code = _classify_os(error)
        raise _failure(code)

    return guarded


def connect(path: Path) -> sqlite3.Connection:
    """Open a manual-transaction connection with the required safety pragmas."""

    connection = sqlite3.connect(
        path, timeout=_BUSY_TIMEOUT_SECONDS, isolation_level=None
    )
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
    except BaseException:
        connection.close()
        raise
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection, *, write: bool) -> Iterator[None]:
    """One transaction; a write takes the single-writer lock up front."""

    connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def checkpoint(connection: sqlite3.Connection) -> None:
    """Fold the WAL into the database after a write, so replaced content does not
    linger in write-ahead frames. Best effort: a concurrent reader may defer it."""

    with contextlib.suppress(sqlite3.Error):
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def purge_database(path: Path) -> None:
    """Best effort: overwrite stored content, fold the WAL, and leave no sidecars.

    ``secure_delete`` zeroes deleted cells and freed pages; the file is then
    removed by the caller. This is application-level removal, not forensic erasure.
    """

    if touches_symlink(path):
        return  # never overwrite a file outside the projects directory
    try:
        connection = connect(path)
    except sqlite3.Error:
        return
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        names = [
            str(row[0]).replace('"', '""')
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for name in names:
            connection.execute(f'DELETE FROM "{name}"')
        for name in names:
            connection.execute(f'DROP TABLE "{name}"')
        connection.execute("COMMIT")
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode = DELETE")
    except sqlite3.Error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
    finally:
        connection.close()
