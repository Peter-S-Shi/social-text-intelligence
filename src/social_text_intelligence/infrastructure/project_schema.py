"""Versioned SQLite schema for one durable project file, with migration safety.

``PRAGMA application_id`` marks a file as ours and ``PRAGMA user_version`` holds the
schema version. Migrations are forward-only, run in one transaction, and are
preceded by a consistent file copy; a file written by a newer version is refused
without being touched.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path

from ..contracts.errors import ProjectStorageError

APPLICATION_ID = 0x53544932  # "STI2"
SCHEMA_VERSION = 1

Migration = Callable[[sqlite3.Connection], None]

# Key N migrates a file from schema version N to N + 1. Version 1 is the baseline.
MIGRATIONS: dict[int, Migration] = {}

_SINGLETON = "singleton INTEGER PRIMARY KEY CHECK (singleton = 1)"

CREATE_STATEMENTS: tuple[str, ...] = (
    f"""CREATE TABLE project (
        {_SINGLETON},
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        revision INTEGER NOT NULL,
        has_reviews INTEGER NOT NULL,
        has_insights INTEGER NOT NULL
    )""",
    f"""CREATE TABLE pending_upload (
        {_SINGLETON},
        content BLOB NOT NULL,
        headers_json TEXT NOT NULL
    )""",
    f"""CREATE TABLE batch_preview (
        {_SINGLETON},
        text_column TEXT NOT NULL,
        headers_json TEXT NOT NULL,
        ignored_columns_json TEXT NOT NULL
    )""",
    """CREATE TABLE prepared_row (
        row_number INTEGER PRIMARY KEY,
        identity TEXT NOT NULL,
        input_values_json TEXT NOT NULL,
        record_json TEXT,
        error_code TEXT,
        error_message TEXT
    )""",
    f"""CREATE TABLE analysis_result (
        {_SINGLETON},
        aggregates_json TEXT NOT NULL
    )""",
    """CREATE TABLE analysis_outcome (
        row_number INTEGER PRIMARY KEY
            REFERENCES prepared_row(row_number) ON DELETE CASCADE,
        status TEXT NOT NULL,
        error_code TEXT,
        error_message TEXT,
        report_json TEXT
    )""",
    """CREATE TABLE human_review (
        position INTEGER PRIMARY KEY,
        record_id TEXT NOT NULL UNIQUE,
        sentiment_judgment TEXT,
        human_sentiment TEXT,
        emotion_judgment TEXT,
        human_dominant_emotion TEXT,
        human_secondary_emotions_json TEXT NOT NULL,
        note TEXT,
        reviewed_at TEXT
    )""",
    f"""CREATE TABLE insight_selection (
        {_SINGLETON},
        selection_json TEXT NOT NULL
    )""",
    """CREATE TABLE context_note (
        position INTEGER PRIMARY KEY,
        note_id TEXT NOT NULL UNIQUE,
        association TEXT NOT NULL,
        association_value TEXT NOT NULL,
        phrase TEXT NOT NULL,
        explanation TEXT NOT NULL,
        context_importance TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    # AI records and imported input are never edited in place; a new analysis or
    # import replaces them by delete and insert inside one transaction.
    *(
        f"""CREATE TRIGGER {table}_is_immutable BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT, 'immutable project records'); END"""
        for table in (
            "prepared_row",
            "batch_preview",
            "pending_upload",
            "analysis_result",
            "analysis_outcome",
        )
    ),
)


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the current schema; the caller owns the surrounding transaction."""

    for statement in CREATE_STATEMENTS:
        connection.execute(statement)
    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def read_identity(connection: sqlite3.Connection) -> tuple[int, int]:
    """Return ``(application_id, user_version)`` without modifying the file."""

    application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    return application_id, version


def backup_path_for(database: Path, version: int) -> Path:
    return database.with_name(f"{database.stem}.pre-migration-v{version}.sqlite3.bak")


def check_identity(
    connection: sqlite3.Connection, *, target_version: int | None = None
) -> int:
    """Refuse files that are not ours or come from a newer version; return the
    stored version. Never modifies the file."""

    target = SCHEMA_VERSION if target_version is None else target_version
    application_id, version = read_identity(connection)
    if application_id != APPLICATION_ID or version < 1:
        raise ProjectStorageError(
            code="not_a_project",
            message="This file is not a project created by this application.",
        )
    if version > target:
        raise ProjectStorageError(
            code="unsupported_schema_version",
            message=(
                "This project was saved by a newer version of the application "
                "and was left unchanged."
            ),
        )
    return version


def ensure_current(
    connection: sqlite3.Connection,
    database: Path,
    *,
    target_version: int | None = None,
    migrations: Mapping[int, Migration] | None = None,
) -> None:
    """Accept, refuse, or migrate an opened project file."""

    target = SCHEMA_VERSION if target_version is None else target_version
    steps = MIGRATIONS if migrations is None else migrations
    version = check_identity(connection, target_version=target)
    if version == target:
        return
    if any(step not in steps for step in range(version, target)):
        raise ProjectStorageError(
            code="migration_unavailable",
            message="This project cannot be upgraded by this version.",
        )
    _migrate(connection, database, version, target, steps)


def _migrate(
    connection: sqlite3.Connection,
    database: Path,
    version: int,
    target: int,
    steps: Mapping[int, Migration],
) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        if read_identity(connection)[1] != version:
            # Another connection upgraded the file while this one waited for the
            # write lock; there is nothing left to do.
            connection.execute("ROLLBACK")
            return
        # With the write lock held no one can change the data, so a separate
        # reader sees exactly the committed state that is about to be migrated.
        source = sqlite3.connect(database)
        backup = sqlite3.connect(backup_path_for(database, version))
        try:
            backup.execute("PRAGMA secure_delete = ON")
            source.backup(backup)
        finally:
            backup.close()
            source.close()
        for step in range(version, target):
            steps[step](connection)
            connection.execute(f"PRAGMA user_version = {step + 1}")
        connection.execute("COMMIT")
        return
    except BaseException as error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        if not isinstance(error, Exception):
            raise
    # Raised outside the handler so a failure that quotes project content is not
    # chained onto the error.
    raise ProjectStorageError(
        code="migration_failed",
        message=(
            "The project could not be upgraded and was left unchanged; "
            "a copy from before the upgrade was kept."
        ),
    )
