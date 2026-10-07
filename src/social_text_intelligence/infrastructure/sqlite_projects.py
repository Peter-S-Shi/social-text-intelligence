"""Durable local projects: one SQLite file per project behind ``ProjectRepository``.

Each operation opens its own short-lived connection and closes it, so no file
handle outlives a call and deletion never races a lingering connection. Leases are
process-local by design (a crashed analysis therefore never blocks a project); a
per-project revision counter makes a lease commit fail instead of overwriting
changes another process made meanwhile. Nothing here logs, and no message or error
includes project text. Deletion is application-level removal of the project's files
(contents overwritten first, WAL folded and removed), not forensic erasure.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
import threading
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..application.projects import (
    BatchAnalysisLease,
    BatchWorkspace,
    ProjectStage,
    ProjectStatus,
    ProjectSummary,
)
from ..application.workspace_mutation import StoredWorkspace, apply_atomic_mutation
from ..contracts.errors import ProjectStorageError, ValidationError
from ..services.batch import BatchOutcome, BatchResult, PreparedBatchRow
from ..services.insights import InsightState
from ..services.review import ReviewState
from . import project_schema as schema
from . import workspace_codec as codec
from .app_data import AppDataLocations

DEFAULT_PROJECT_NAME = "Untitled project"
MAX_PROJECT_NAME_LENGTH = 120
_PROJECT_ID = re.compile(r"[0-9a-f]{32}")
_BUSY_TIMEOUT_SECONDS = 5.0
_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


@dataclass(slots=True)
class _Lease:
    analysis_id: str
    revision: int


@dataclass(frozen=True, slots=True)
class _Encoded:
    """Validated column values for one workspace, ready to be written."""

    pending: tuple[bytes, str] | None
    preview: tuple[str, str, str] | None
    rows: tuple[tuple[object, ...], ...]
    aggregates: str | None
    outcomes: tuple[tuple[object, ...], ...]
    reviews: tuple[tuple[object, ...], ...] | None
    selection: str | None
    notes: tuple[tuple[object, ...], ...] | None


def _unsupported_workspace() -> ProjectStorageError:
    return ProjectStorageError(
        code="unsupported_workspace",
        message="This workspace cannot be stored as a project.",
    )


def _encode_workspace(workspace: BatchWorkspace) -> _Encoded:
    """Validate the shape this store supports, then encode it without side effects."""

    preview = workspace.preview
    result = workspace.result
    rows: tuple[PreparedBatchRow, ...] = () if preview is None else preview.rows
    numbers = [row.row_number for row in rows]
    if numbers != sorted(set(numbers)):
        raise _unsupported_workspace()
    outcomes: tuple[BatchOutcome, ...] = ()
    if result is not None:
        if preview is None or result.preview != preview:
            raise _unsupported_workspace()
        outcomes = result.outcomes
        if len(outcomes) != len(rows) or any(
            outcome.prepared != row for outcome, row in zip(outcomes, rows, strict=True)
        ):
            raise _unsupported_workspace()
        if any(
            outcome.report is not None
            and outcome.report.record != outcome.prepared.record
            for outcome in outcomes
        ):
            raise _unsupported_workspace()
    insights = workspace.insights
    return _Encoded(
        pending=(
            None
            if workspace.pending is None
            else codec.encode_pending(workspace.pending)
        ),
        preview=None if preview is None else codec.encode_preview(preview),
        rows=tuple(codec.encode_row(row) for row in rows),
        aggregates=(
            None if result is None else codec.encode_aggregates(result.aggregates)
        ),
        outcomes=tuple(codec.encode_outcome(outcome) for outcome in outcomes),
        reviews=(
            None
            if workspace.reviews is None
            else tuple(codec.encode_review(item) for item in workspace.reviews.reviews)
        ),
        selection=(
            None
            if insights is None or insights.selection is None
            else codec.encode_selection(insights.selection)
        ),
        notes=(
            None
            if insights is None
            else tuple(codec.encode_note(note) for note in insights.notes)
        ),
    )


def _write_workspace(
    connection: sqlite3.Connection,
    old: BatchWorkspace,
    new: BatchWorkspace,
    encoded: _Encoded,
) -> None:
    """Persist only the sections that changed; AI records are replaced, never edited."""

    if old.pending != new.pending:
        connection.execute("DELETE FROM pending_upload")
        if encoded.pending is not None:
            connection.execute(
                "INSERT INTO pending_upload VALUES (1, ?, ?)", encoded.pending
            )
    preview_changed = old.preview != new.preview
    result_changed = old.result != new.result
    if preview_changed or result_changed:
        connection.execute("DELETE FROM analysis_outcome")
        connection.execute("DELETE FROM analysis_result")
    if preview_changed:
        connection.execute("DELETE FROM prepared_row")
        connection.execute("DELETE FROM batch_preview")
        if encoded.preview is not None:
            connection.execute(
                "INSERT INTO batch_preview VALUES (1, ?, ?, ?)", encoded.preview
            )
            connection.executemany(
                "INSERT INTO prepared_row VALUES (?, ?, ?, ?, ?, ?)", encoded.rows
            )
    if (preview_changed or result_changed) and encoded.aggregates is not None:
        connection.execute(
            "INSERT INTO analysis_result VALUES (1, ?)", (encoded.aggregates,)
        )
        connection.executemany(
            "INSERT INTO analysis_outcome VALUES (?, ?, ?, ?, ?)", encoded.outcomes
        )
    if old.reviews != new.reviews:
        connection.execute("DELETE FROM human_review")
        connection.executemany(
            "INSERT INTO human_review VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(index, *item) for index, item in enumerate(encoded.reviews or ())],
        )
    if old.insights != new.insights:
        connection.execute("DELETE FROM insight_selection")
        connection.execute("DELETE FROM context_note")
        if encoded.selection is not None:
            connection.execute(
                "INSERT INTO insight_selection VALUES (1, ?)", (encoded.selection,)
            )
        connection.executemany(
            "INSERT INTO context_note VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(index, *item) for index, item in enumerate(encoded.notes or ())],
        )


def _read_workspace(connection: sqlite3.Connection) -> tuple[BatchWorkspace, int]:
    """Rebuild a workspace through the original constructors (re-validating it)."""

    project = connection.execute(
        "SELECT revision, has_reviews, has_insights FROM project"
    ).fetchone()
    if project is None:
        raise ValueError("missing project row")
    revision, has_reviews, has_insights = project

    pending_row = connection.execute(
        "SELECT content, headers_json FROM pending_upload"
    ).fetchone()
    pending = None if pending_row is None else codec.decode_pending(*pending_row)

    preview = None
    rows: dict[int, PreparedBatchRow] = {}
    preview_row = connection.execute(
        "SELECT text_column, headers_json, ignored_columns_json FROM batch_preview"
    ).fetchone()
    if preview_row is not None:
        for stored in connection.execute(
            "SELECT row_number, identity, input_values_json, record_json, "
            "error_code, error_message FROM prepared_row ORDER BY row_number"
        ):
            rows[stored[0]] = codec.decode_row(*stored)
        text_column, headers_json, ignored_json = preview_row
        preview = codec.decode_preview(
            text_column, headers_json, ignored_json, tuple(rows.values())
        )

    result = None
    aggregates_row = connection.execute(
        "SELECT aggregates_json FROM analysis_result"
    ).fetchone()
    if aggregates_row is not None:
        if preview is None:
            raise ValueError("analysis without input")
        outcomes = tuple(
            codec.decode_outcome(rows[stored[0]], *stored[1:])
            for stored in connection.execute(
                "SELECT row_number, status, error_code, error_message, report_json "
                "FROM analysis_outcome ORDER BY row_number"
            )
        )
        result = BatchResult(
            preview=preview,
            outcomes=outcomes,
            aggregates=codec.decode_aggregates(aggregates_row[0]),
        )

    reviews = None
    if has_reviews:
        reviews = ReviewState(
            reviews=tuple(
                codec.decode_review(*stored)
                for stored in connection.execute(
                    "SELECT record_id, sentiment_judgment, human_sentiment, "
                    "emotion_judgment, human_dominant_emotion, "
                    "human_secondary_emotions_json, note, reviewed_at "
                    "FROM human_review ORDER BY position"
                )
            )
        )

    insights = None
    if has_insights:
        selection_row = connection.execute(
            "SELECT selection_json FROM insight_selection"
        ).fetchone()
        insights = InsightState(
            notes=tuple(
                codec.decode_note(*stored)
                for stored in connection.execute(
                    "SELECT note_id, association, association_value, phrase, "
                    "explanation, context_importance, tags_json, created_at "
                    "FROM context_note ORDER BY position"
                )
            ),
            selection=(
                None
                if selection_row is None
                else codec.decode_selection(selection_row[0])
            ),
        )
    workspace = BatchWorkspace(
        pending=pending,
        preview=preview,
        result=result,
        reviews=reviews,
        insights=insights,
    )
    return workspace, int(revision)


def _load(connection: sqlite3.Connection) -> tuple[BatchWorkspace, int]:
    try:
        return _read_workspace(connection)
    except sqlite3.Error:
        raise
    except Exception:  # noqa: BLE001 - any contract or parse failure means bad data
        pass
    # Raised outside the handler so the cause, which could quote project content,
    # is not chained onto the error.
    raise ProjectStorageError(
        code="project_data_invalid",
        message="The project file contains data this version cannot read.",
    )


def _clean_name(name: str) -> str:
    cleaned = unicodedata.normalize("NFC", name).strip()
    if (
        not cleaned
        or len(cleaned) > MAX_PROJECT_NAME_LENGTH
        or any(unicodedata.category(char) in {"Cc", "Cs"} for char in cleaned)
    ):
        raise ValidationError(
            field="name",
            code="invalid_name",
            message=(
                f"Project name must be 1 to {MAX_PROJECT_NAME_LENGTH} characters "
                "without control characters."
            ),
        )
    return cleaned


def _valid_id(token: str) -> str | None:
    return token if _PROJECT_ID.fullmatch(token) else None


@contextmanager
def _guard_storage() -> Iterator[None]:
    """Translate low-level failures into content-free storage errors."""

    try:
        yield
    except ProjectStorageError:
        raise
    except sqlite3.Error as error:
        busy = "locked" in str(error).lower()
        raise ProjectStorageError(
            code="project_busy" if busy else "storage_failure",
            message=(
                "The project is in use by another operation; try again."
                if busy
                else "The project storage could not complete the operation."
            ),
        ) from None
    except OSError:
        raise ProjectStorageError(
            code="storage_failure",
            message="The project storage could not complete the operation.",
        ) from None
    except UnicodeEncodeError:
        raise ProjectStorageError(
            code="unsupported_text",
            message="The workspace contains text that cannot be stored.",
        ) from None


def _connect(path: Path) -> sqlite3.Connection:
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
def _transaction(connection: sqlite3.Connection, *, write: bool) -> Iterator[None]:
    connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def _purge_database(path: Path) -> None:
    """Best effort: overwrite stored content, fold the WAL, and leave no sidecars."""

    try:
        connection = _connect(path)
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


class SqliteProjectRepository:
    """``PersistentProjectRepository`` backed by one SQLite file per project."""

    def __init__(
        self,
        locations: AppDataLocations,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._locations = locations
        self._clock = clock
        self._leases: dict[str, _Lease] = {}
        self._lock = threading.Lock()

    # --- identity -----------------------------------------------------------------

    def _path(self, project_id: str) -> Path:
        return self._locations.projects_dir / f"{project_id}.sqlite3"

    @contextmanager
    def _open(self, project_id: str) -> Iterator[sqlite3.Connection | None]:
        path = self._path(project_id)
        if not path.is_file():
            yield None
            return
        connection = _connect(path)
        try:
            schema.ensure_current(connection, path)
            yield connection
        finally:
            connection.close()

    def _summary(self, connection: sqlite3.Connection) -> ProjectSummary:
        project_id, name, created_at, updated_at = connection.execute(
            "SELECT project_id, name, created_at, updated_at FROM project"
        ).fetchone()
        if connection.execute("SELECT 1 FROM analysis_result").fetchone():
            stage = ProjectStage.ANALYZED
        elif connection.execute("SELECT 1 FROM batch_preview").fetchone():
            stage = ProjectStage.READY
        elif connection.execute("SELECT 1 FROM pending_upload").fetchone():
            stage = ProjectStage.AWAITING_COLUMN
        else:
            stage = ProjectStage.EMPTY
        row_count = connection.execute("SELECT COUNT(*) FROM prepared_row").fetchone()[
            0
        ]
        return ProjectSummary(
            project_id=project_id,
            status=ProjectStatus.OK,
            name=name,
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
            stage=stage,
            row_count=int(row_count),
        )

    # --- create / list / rename ---------------------------------------------------

    def create(self, workspace: BatchWorkspace) -> str:
        return self.create_project(workspace, name=DEFAULT_PROJECT_NAME).project_id

    def create_project(self, workspace: BatchWorkspace, *, name: str) -> ProjectSummary:
        cleaned = _clean_name(name)
        encoded = _encode_workspace(workspace)
        with _guard_storage():
            self._locations.ensure_projects_dir()
            while True:
                project_id = secrets.token_hex(16)
                path = self._path(project_id)
                try:
                    path.touch(exist_ok=False)
                except FileExistsError:
                    continue
                break
            try:
                connection = _connect(path)
                try:
                    connection.execute("PRAGMA journal_mode = WAL")
                    now = self._clock().isoformat()
                    with _transaction(connection, write=True):
                        schema.create_schema(connection)
                        connection.execute(
                            "INSERT INTO project VALUES (1, ?, ?, ?, ?, 1, ?, ?)",
                            (
                                project_id,
                                cleaned,
                                now,
                                now,
                                int(workspace.reviews is not None),
                                int(workspace.insights is not None),
                            ),
                        )
                        _write_workspace(
                            connection, BatchWorkspace(), workspace, encoded
                        )
                    return self._summary(connection)
                finally:
                    connection.close()
            except BaseException:
                self._remove_files(project_id)
                raise

    def list_projects(self) -> tuple[ProjectSummary, ...]:
        directory = self._locations.projects_dir
        if not directory.is_dir():
            return ()
        summaries = [
            self._list_entry(path)
            for path in sorted(directory.glob("*.sqlite3"))
            if _PROJECT_ID.fullmatch(path.stem)
        ]
        epoch = datetime.min.replace(tzinfo=UTC)
        return tuple(
            sorted(
                summaries,
                key=lambda item: (
                    item.status is not ProjectStatus.OK,
                    -(item.updated_at or epoch).timestamp(),
                    item.project_id,
                ),
            )
        )

    def _list_entry(self, path: Path) -> ProjectSummary:
        project_id = path.stem
        try:
            with _guard_storage(), self._open(project_id) as connection:
                if connection is None:
                    return ProjectSummary(project_id, ProjectStatus.UNREADABLE)
                with _transaction(connection, write=False):
                    return self._summary(connection)
        except ProjectStorageError as error:
            status = (
                ProjectStatus.UNSUPPORTED_VERSION
                if error.code == "unsupported_schema_version"
                else ProjectStatus.UNREADABLE
            )
            return ProjectSummary(project_id, status)
        except (ValueError, TypeError):
            return ProjectSummary(project_id, ProjectStatus.UNREADABLE)

    def rename_project(self, token: str, name: str) -> ProjectSummary | None:
        cleaned = _clean_name(name)
        project_id = _valid_id(token)
        if project_id is None:
            return None
        with self._lock, _guard_storage(), self._open(project_id) as connection:
            if connection is None:
                return None
            with _transaction(connection, write=True):
                connection.execute(
                    "UPDATE project SET name = ?, updated_at = ?",
                    (cleaned, self._clock().isoformat()),
                )
                return self._summary(connection)

    # --- workspace access ---------------------------------------------------------

    def get(self, token: str) -> BatchWorkspace | None:
        project_id = _valid_id(token)
        if project_id is None:
            return None
        with _guard_storage(), self._open(project_id) as connection:
            if connection is None:
                return None
            with _transaction(connection, write=False):
                return _load(connection)[0]

    def mutate(
        self,
        token: str,
        mutation: Callable[[BatchWorkspace], BatchWorkspace],
    ) -> BatchWorkspace | None:
        """Apply one current-state mutation atomically; never accept stale state."""

        project_id = _valid_id(token)
        if project_id is None:
            return None
        with self._lock, _guard_storage(), self._open(project_id) as connection:
            if connection is None:
                return None
            with _transaction(connection, write=True):
                current, revision = _load(connection)
                lease = self._leases.get(project_id)
                cell = StoredWorkspace(
                    workspace=current,
                    expires_at=0.0,
                    active_operation_id=None if lease is None else lease.analysis_id,
                )
                updated = apply_atomic_mutation(
                    cell,
                    mutation,
                    expires_at=0.0,
                    blocked_message=(
                        "This project is being analyzed. Retry the mutation "
                        "after analysis finishes."
                    ),
                )
                if updated != current:
                    self._commit_change(connection, current, updated, revision)
                return updated

    def _commit_change(
        self,
        connection: sqlite3.Connection,
        current: BatchWorkspace,
        updated: BatchWorkspace,
        revision: int,
    ) -> None:
        encoded = _encode_workspace(updated)
        _write_workspace(connection, current, updated, encoded)
        connection.execute(
            "UPDATE project SET revision = ?, updated_at = ?, "
            "has_reviews = ?, has_insights = ?",
            (
                revision + 1,
                self._clock().isoformat(),
                int(updated.reviews is not None),
                int(updated.insights is not None),
            ),
        )

    # --- analysis leases ----------------------------------------------------------

    def begin_analysis(self, token: str) -> BatchAnalysisLease | None:
        """Reserve a project so another analysis or mutation cannot interleave."""

        project_id = _valid_id(token)
        if project_id is None:
            return None
        with self._lock:
            if project_id in self._leases:
                raise RuntimeError(
                    "This project is already being analyzed. Wait for the "
                    "active analysis to finish before trying again."
                )
            with _guard_storage(), self._open(project_id) as connection:
                if connection is None:
                    return None
                with _transaction(connection, write=False):
                    workspace, revision = _load(connection)
            analysis_id = secrets.token_urlsafe(24)
            self._leases[project_id] = _Lease(analysis_id, revision)
            return BatchAnalysisLease(
                token=project_id, analysis_id=analysis_id, workspace=workspace
            )

    def complete_analysis(
        self, lease: BatchAnalysisLease, workspace: BatchWorkspace
    ) -> bool:
        """Commit an analysis in one transaction only if its lease is still current."""

        with self._lock:
            held = self._leases.get(lease.token)
            if held is None or held.analysis_id != lease.analysis_id:
                return False
            encoded = _encode_workspace(workspace)
            with _guard_storage(), self._open(lease.token) as connection:
                if connection is None:
                    del self._leases[lease.token]
                    return False
                with _transaction(connection, write=True):
                    current, revision = _load(connection)
                    if revision != held.revision:
                        del self._leases[lease.token]
                        return False
                    _write_workspace(connection, current, workspace, encoded)
                    connection.execute(
                        "UPDATE project SET revision = ?, updated_at = ?, "
                        "has_reviews = ?, has_insights = ?",
                        (
                            revision + 1,
                            self._clock().isoformat(),
                            int(workspace.reviews is not None),
                            int(workspace.insights is not None),
                        ),
                    )
            del self._leases[lease.token]
            return True

    def cancel_analysis(self, lease: BatchAnalysisLease) -> bool:
        """Release a lease after analysis fails without changing the project."""

        with self._lock:
            held = self._leases.get(lease.token)
            if held is None or held.analysis_id != lease.analysis_id:
                return False
            del self._leases[lease.token]
            return True

    # --- deletion -----------------------------------------------------------------

    def delete(self, token: str) -> bool:
        """Remove a project from the application's data files; not forensic erasure."""

        project_id = _valid_id(token)
        if project_id is None:
            return False
        with self._lock:
            if project_id in self._leases:
                raise RuntimeError(
                    "This project is being analyzed and cannot be deleted "
                    "until the active analysis finishes."
                )
            path = self._path(project_id)
            if not path.is_file():
                return False
            with _guard_storage():
                for candidate in (path, *self._backups(project_id)):
                    _purge_database(candidate)
                self._remove_files(project_id, strict=True)
            return True

    def _backups(self, project_id: str) -> tuple[Path, ...]:
        pattern = f"{project_id}.pre-migration-v*.sqlite3.bak"
        return tuple(sorted(self._locations.projects_dir.glob(pattern)))

    def _remove_files(self, project_id: str, *, strict: bool = False) -> None:
        path = self._path(project_id)
        targets = [
            *self._backups(project_id),
            *(path.with_name(path.name + suffix) for suffix in _SIDECAR_SUFFIXES),
            path,
        ]
        failed = False
        for target in targets:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                failed = True
        if failed and strict:
            raise ProjectStorageError(
                code="delete_failed",
                message=(
                    "The project's data was cleared but its file could not be "
                    "removed. Close other programs using it and delete it again."
                ),
            )
