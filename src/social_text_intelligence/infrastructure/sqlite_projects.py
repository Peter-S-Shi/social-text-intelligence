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
    ProjectStatus,
    ProjectSummary,
)
from ..application.workspace_mutation import StoredWorkspace, apply_atomic_mutation
from ..contracts.errors import ProjectStorageError, ValidationError
from . import project_schema as schema
from . import sqlite_support as support
from . import workspace_store as store
from .app_data import AppDataLocations

DEFAULT_PROJECT_NAME = "Untitled project"
MAX_PROJECT_NAME_LENGTH = 120


@dataclass(slots=True)
class _Lease:
    analysis_id: str
    revision: int


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


def _summary(connection: sqlite3.Connection) -> ProjectSummary:
    project_id, name, created_at, updated_at = connection.execute(
        "SELECT project_id, name, created_at, updated_at FROM project"
    ).fetchone()
    return ProjectSummary(
        project_id=project_id,
        status=ProjectStatus.OK,
        name=name,
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )


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

    # --- files --------------------------------------------------------------------

    def _path(self, project_id: str) -> Path:
        return self._locations.projects_dir / f"{project_id}.sqlite3"

    @contextmanager
    def _open(
        self, project_id: str, *, migrate: bool = True
    ) -> Iterator[sqlite3.Connection | None]:
        """Yield a checked connection, or None when the project does not exist.

        Listing opens with ``migrate=False``: migrations are additive, so an older
        file stays readable and listing never writes a backup.
        """

        path = self._path(project_id)
        if not path.is_file():
            yield None
            return
        connection = support.connect(path)
        try:
            if migrate:
                schema.ensure_current(connection, path)
            else:
                schema.check_identity(connection)
            yield connection
        finally:
            connection.close()

    def _backups(self, project_id: str) -> tuple[Path, ...]:
        pattern = f"{project_id}.pre-migration-v*.sqlite3.bak"
        return tuple(sorted(self._locations.projects_dir.glob(pattern)))

    def _remove_files(self, project_id: str, *, strict: bool = False) -> None:
        path = self._path(project_id)
        targets = [
            *self._backups(project_id),
            *(path.with_name(path.name + s) for s in support.SIDECAR_SUFFIXES),
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

    # --- create / list ------------------------------------------------------------

    def create(self, workspace: BatchWorkspace) -> str:
        return self.create_project(workspace, name=DEFAULT_PROJECT_NAME).project_id

    @support.storage_guarded
    def create_project(self, workspace: BatchWorkspace, *, name: str) -> ProjectSummary:
        cleaned = _clean_name(name)
        encoded = store.encode_workspace(workspace)
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
            connection = support.connect(path)
            try:
                connection.execute("PRAGMA journal_mode = WAL")
                now = self._clock().isoformat()
                with support.transaction(connection, write=True):
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
                    store.write_workspace(
                        connection, BatchWorkspace(), workspace, encoded
                    )
                return _summary(connection)
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
            if support.PROJECT_ID_PATTERN.fullmatch(path.stem)
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
            return self._read_summary(project_id)
        except ProjectStorageError as error:
            status = (
                ProjectStatus.UNSUPPORTED_VERSION
                if error.code == "unsupported_schema_version"
                else ProjectStatus.UNREADABLE
            )
        except (ValueError, TypeError):
            status = ProjectStatus.UNREADABLE
        return ProjectSummary(project_id, status)

    @support.storage_guarded
    def _read_summary(self, project_id: str) -> ProjectSummary:
        with self._open(project_id, migrate=False) as connection:
            if connection is None:
                return ProjectSummary(project_id, ProjectStatus.UNREADABLE)
            with support.transaction(connection, write=False):
                return _summary(connection)

    # --- workspace access ---------------------------------------------------------

    @support.storage_guarded
    def get(self, token: str) -> BatchWorkspace | None:
        project_id = support.valid_project_id(token)
        if project_id is None:
            return None
        with self._open(project_id) as connection:
            if connection is None:
                return None
            with support.transaction(connection, write=False):
                return store.load_workspace(connection)[0]

    @support.storage_guarded
    def mutate(
        self,
        token: str,
        mutation: Callable[[BatchWorkspace], BatchWorkspace],
    ) -> BatchWorkspace | None:
        """Apply one current-state mutation atomically; never accept stale state."""

        project_id = support.valid_project_id(token)
        if project_id is None:
            return None
        with self._lock, self._open(project_id) as connection:
            if connection is None:
                return None
            with support.transaction(connection, write=True):
                current, revision = store.load_workspace(connection)
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
                changed = updated != current
                if changed:
                    store.write_workspace(
                        connection, current, updated, store.encode_workspace(updated)
                    )
                    store.record_commit(
                        connection,
                        revision=revision,
                        committed_at=self._clock().isoformat(),
                        workspace=updated,
                    )
            if changed:
                support.checkpoint(connection)
            return updated

    # --- analysis leases ----------------------------------------------------------

    @support.storage_guarded
    def begin_analysis(self, token: str) -> BatchAnalysisLease | None:
        """Reserve a project so another analysis or mutation cannot interleave."""

        project_id = support.valid_project_id(token)
        if project_id is None:
            return None
        with self._lock:
            if project_id in self._leases:
                raise RuntimeError(
                    "This project is already being analyzed. Wait for the "
                    "active analysis to finish before trying again."
                )
            with self._open(project_id) as connection:
                if connection is None:
                    return None
                with support.transaction(connection, write=False):
                    workspace, revision = store.load_workspace(connection)
            analysis_id = secrets.token_urlsafe(24)
            self._leases[project_id] = _Lease(analysis_id, revision)
            return BatchAnalysisLease(
                token=project_id, analysis_id=analysis_id, workspace=workspace
            )

    @support.storage_guarded
    def complete_analysis(
        self, lease: BatchAnalysisLease, workspace: BatchWorkspace
    ) -> bool:
        """Commit an analysis in one transaction only if its lease is still current."""

        with self._lock:
            held = self._leases.get(lease.token)
            if held is None or held.analysis_id != lease.analysis_id:
                return False
            encoded = store.encode_workspace(workspace)
            with self._open(lease.token) as connection:
                if connection is None:
                    del self._leases[lease.token]
                    return False
                with support.transaction(connection, write=True):
                    current, revision = store.load_workspace(connection)
                    if revision != held.revision:
                        del self._leases[lease.token]
                        return False
                    store.write_workspace(connection, current, workspace, encoded)
                    store.record_commit(
                        connection,
                        revision=revision,
                        committed_at=self._clock().isoformat(),
                        workspace=workspace,
                    )
                support.checkpoint(connection)
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

    @support.storage_guarded
    def delete(self, token: str) -> bool:
        """Remove a project from the application's data files; not forensic erasure."""

        project_id = support.valid_project_id(token)
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
            for candidate in (path, *self._backups(project_id)):
                support.purge_database(candidate)
            self._remove_files(project_id, strict=True)
            return True
