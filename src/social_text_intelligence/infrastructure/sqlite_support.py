"""Low-level SQLite helpers shared by the durable project store.

Nothing here logs, and failures are translated into fixed, content-free messages.
"""

from __future__ import annotations

import contextlib
import functools
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import ParamSpec, TypeVar

from ..contracts.errors import ProjectStorageError

PROJECT_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
_BUSY_TIMEOUT_SECONDS = 5.0

_P = ParamSpec("_P")
_R = TypeVar("_R")


def valid_project_id(token: str) -> str | None:
    """Accept only ids this store generates, so a token can never name a path."""

    return token if PROJECT_ID_PATTERN.fullmatch(token) else None


def _storage_failure(*, busy: bool = False, text: bool = False) -> ProjectStorageError:
    if text:
        return ProjectStorageError(
            code="unsupported_text",
            message="The workspace contains text that cannot be stored.",
        )
    if busy:
        return ProjectStorageError(
            code="project_busy",
            message="The project is in use by another operation; try again.",
        )
    return ProjectStorageError(
        code="storage_failure",
        message="The project storage could not complete the operation.",
    )


def storage_guarded(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """Translate low-level failures into content-free ``ProjectStorageError``.

    The new error is raised after the ``except`` block has finished, so it carries
    no ``__context__`` or ``__cause__``: the original failure (a Unicode error, for
    instance, holds the offending text) is not reachable from it.
    """

    @functools.wraps(function)
    def guarded(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        failure: ProjectStorageError
        try:
            return function(*args, **kwargs)
        except ProjectStorageError:
            raise
        except sqlite3.Error as error:
            failure = _storage_failure(busy="locked" in str(error).lower())
        except UnicodeEncodeError:
            failure = _storage_failure(text=True)
        except OSError:
            failure = _storage_failure()
        raise failure

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
