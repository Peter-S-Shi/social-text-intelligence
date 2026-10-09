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

from ..application.exclusion import ProcessLock, ProcessLocks, project_scope
from ..application.projects import (
    BatchAnalysisLease,
    BatchWorkspace,
    ProjectBusy,
    ProjectBusyElsewhere,
    ProjectStatus,
    ProjectSummary,
)
from ..application.workspace_mutation import StoredWorkspace, apply_atomic_mutation
from ..contracts.errors import ProjectStorageError, ValidationError
from . import project_schema as schema
from . import sqlite_support as support
from . import workspace_store as store
from .app_data import AppDataLocations
from .process_locks import FileProcessLocks

DEFAULT_PROJECT_NAME = "Untitled project"
MAX_PROJECT_NAME_LENGTH = 120


@dataclass(slots=True)
class _Lease:
    analysis_id: str
    revision: int
    # Cross-process hold on the project: released with the lease, or by the OS if
    # this process dies, so a killed analysis never blocks a project.
    hold: ProcessLock


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
        process_locks: ProcessLocks | None = None,
    ) -> None:
        self._locations = locations
        self._clock = clock
        self._process_locks: ProcessLocks = process_locks or FileProcessLocks(
            locations.locks_dir
        )
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
        # A symlink with a managed name is never opened: it could lead to a
        # project (or any database) outside the projects directory.
        if support.touches_symlink(path) or not path.is_file():
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

    def _managed_files(self) -> list[tuple[str, Path]]:
        directory = self._locations.projects_dir
        if not directory.is_dir():
            return []
        return [
            (project_id, path)
            for path in sorted(directory.iterdir())
            if (project_id := support.managed_project_id(path.name)) is not None
            and (path.is_file() or path.is_symlink())
        ]

    def _artifacts(self, project_id: str) -> tuple[Path, ...]:
        """Every managed file for a project id: database, sidecars, and backups.

        Found by id, not through the main database, so a retry still discovers
        residue after an earlier partial deletion removed the main file. Only the
        file names this store creates qualify; anything else is left alone.
        """

        return tuple(
            path for found, path in self._managed_files() if found == project_id
        )

    @staticmethod
    def _delete_failed() -> ProjectStorageError:
        return ProjectStorageError(
            code="delete_failed",
            message=(
                "Some of this project's files could not be removed. Close "
                "other programs using them and delete the project again."
            ),
        )

    def _remove_files(self, project_id: str, *, strict: bool = False) -> None:
        failed = False
        for target in self._artifacts(project_id):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                failed = True
        if failed and strict:
            raise self._delete_failed()

    # --- cross-process exclusion --------------------------------------------------

    def _hold_project(self, project_id: str, action: str) -> ProcessLock:
        """Take the project's cross-process hold, or say another window has it."""

        hold = self._process_locks.try_acquire(project_scope(project_id))
        if hold is None:
            raise ProjectBusyElsewhere(
                f"This project is in use in another window of the app. Wait for "
                f"it to finish there, or close that window, then {action}. "
                "Nothing was changed."
            )
        return hold

    def _drop_lease(self, project_id: str) -> None:
        lease = self._leases.pop(project_id, None)
        if lease is not None:
            lease.hold.release()

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
        project_ids = sorted({found for found, _ in self._managed_files()})
        summaries = [self._list_entry(project_id) for project_id in project_ids]
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

    def _list_entry(self, project_id: str) -> ProjectSummary:
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
                raise ProjectBusy(
                    "This project is already being analyzed. Wait for the "
                    "active analysis to finish before trying again."
                )
            hold = self._hold_project(project_id, "analyse it")
            try:
                with self._open(project_id) as connection:
                    if connection is None:
                        hold.discard()
                        return None
                    with support.transaction(connection, write=False):
                        workspace, revision = store.load_workspace(connection)
            except BaseException:
                hold.release()
                raise
            analysis_id = secrets.token_urlsafe(24)
            self._leases[project_id] = _Lease(analysis_id, revision, hold)
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
                    self._drop_lease(lease.token)
                    return False
                with support.transaction(connection, write=True):
                    current, revision = store.load_workspace(connection)
                    if revision != held.revision:
                        self._drop_lease(lease.token)
                        return False
                    store.write_workspace(connection, current, workspace, encoded)
                    store.record_commit(
                        connection,
                        revision=revision,
                        committed_at=self._clock().isoformat(),
                        workspace=workspace,
                    )
                support.checkpoint(connection)
            self._drop_lease(lease.token)
            return True

    def cancel_analysis(self, lease: BatchAnalysisLease) -> bool:
        """Release a lease after analysis fails without changing the project."""

        with self._lock:
            held = self._leases.get(lease.token)
            if held is None or held.analysis_id != lease.analysis_id:
                return False
            self._drop_lease(lease.token)
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
                raise ProjectBusy(
                    "This project is being analyzed and cannot be deleted "
                    "until the active analysis finishes."
                )
            hold = self._hold_project(project_id, "delete it")
            try:
                removed = self._delete_held(project_id)
            except BaseException:
                hold.release()
                raise
            hold.discard()  # the project is gone: forget its lock file too
            return removed

    def _delete_held(self, project_id: str) -> bool:
        artifacts = self._artifacts(project_id)
        if not artifacts:
            return False
        for link in artifacts:
            if link.is_symlink():  # remove links first; never purge through them
                try:
                    link.unlink()
                except OSError:
                    # Stop before touching the real files so a retry can still
                    # purge them; they cannot be purged while a link remains.
                    raise self._delete_failed() from None
        for candidate in self._artifacts(project_id):
            if candidate.suffix in {".sqlite3", ".bak"}:
                support.purge_database(candidate)
        self._remove_files(project_id, strict=True)
        return True
