"""Bounded, expiring in-memory state for the active local batch workflow."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from threading import Lock
from typing import Protocol

from ..services.batch import BatchPreview, BatchResult, PendingBatchUpload
from ..services.insights import InsightState
from ..services.review import ReviewState
from .workspace_mutation import (
    StoredWorkspace,
    WorkspaceMutationConflict,
    apply_atomic_mutation,
)


class ProjectBusy(RuntimeError):
    """The project is held by a running analysis (still a ``RuntimeError``)."""


class ProjectBusyElsewhere(ProjectBusy):
    """Another instance of the application (another process) holds the project."""


@dataclass(frozen=True, slots=True)
class BatchWorkspace:
    pending: PendingBatchUpload | None = None
    preview: BatchPreview | None = None
    result: BatchResult | None = None
    reviews: ReviewState | None = None
    insights: InsightState | None = None


@dataclass(frozen=True, slots=True)
class BatchAnalysisLease:
    """Exclusive lease that keeps one batch alive while analysis is running."""

    token: str
    analysis_id: str
    workspace: BatchWorkspace


class ProjectRepository(Protocol):
    """Workspace operations shared by application use cases and adapters."""

    def create(self, workspace: BatchWorkspace) -> str: ...
    def get(self, token: str) -> BatchWorkspace | None: ...
    def mutate(
        self, token: str, mutation: Callable[[BatchWorkspace], BatchWorkspace]
    ) -> BatchWorkspace | None: ...
    def begin_analysis(self, token: str) -> BatchAnalysisLease | None: ...
    def complete_analysis(
        self, lease: BatchAnalysisLease, workspace: BatchWorkspace
    ) -> bool: ...
    def cancel_analysis(self, lease: BatchAnalysisLease) -> bool: ...
    def delete(self, token: str) -> bool: ...


class ProjectStatus(StrEnum):
    """Whether a project file can be opened by this version of the application."""

    OK = "ok"
    UNSUPPORTED_VERSION = "unsupported_version"
    UNREADABLE = "unreadable"


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    """Listing entry; the project id doubles as the repository token."""

    project_id: str
    status: ProjectStatus
    name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Read-time counts for the project list (``None`` where the repository keeps
    # none). They are counted from stored rows when listing, never persisted, and
    # never read from any text column.
    row_count: int | None = None  # every data row of the imported CSV
    rejected_rows: int | None = None  # rows the CSV preparation rejected
    analysed_rows: int | None = None  # rows with an AI result
    attempted_rows: int | None = None  # rows an analysis ran on (ok or failed)
    reviewed_rows: int | None = None  # rows judged in both dimensions
    corrected_rows: int | None = None  # rows where the human corrected the AI


class PersistentProjectRepository(ProjectRepository, Protocol):
    """Durable projects: identity and listing on top of the base port.

    ``get`` opens a project and ``delete`` removes it from the application's data
    files; neither promises forensic erasure.
    """

    def create_project(
        self, workspace: BatchWorkspace, *, name: str
    ) -> ProjectSummary: ...
    def list_projects(self) -> tuple[ProjectSummary, ...]: ...


class InMemoryProjectRepository:
    """Keep a small number of active batches in memory; never write to disk."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 30 * 60,
        capacity: int = 8,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds < 1 or capacity < 1:
            raise ValueError("ttl_seconds and capacity must be positive")
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._clock = clock
        self._items: dict[str, StoredWorkspace[BatchWorkspace]] = {}
        self._lock = Lock()

    def _purge(self, now: float) -> None:
        expired = [
            token
            for token, item in self._items.items()
            if item.expires_at <= now and item.active_operation_id is None
        ]
        for token in expired:
            del self._items[token]

    def create(self, workspace: BatchWorkspace) -> str:
        with self._lock:
            now = self._clock()
            self._purge(now)
            if len(self._items) >= self._capacity:
                raise RuntimeError(
                    "Batch workspace capacity reached; clear an existing "
                    "workspace or wait for expiry. Existing work was not removed."
                )
            token = secrets.token_urlsafe(24)
            self._items[token] = StoredWorkspace(
                workspace=workspace,
                expires_at=now + self._ttl_seconds,
            )
            return token

    def get(self, token: str) -> BatchWorkspace | None:
        with self._lock:
            now = self._clock()
            self._purge(now)
            stored = self._items.get(token)
            if stored is None:
                return None
            stored.expires_at = now + self._ttl_seconds
            return stored.workspace

    def mutate(
        self,
        token: str,
        mutation: Callable[[BatchWorkspace], BatchWorkspace],
    ) -> BatchWorkspace | None:
        """Apply one current-state mutation atomically; never accept stale state."""

        with self._lock:
            now = self._clock()
            self._purge(now)
            stored = self._items.get(token)
            if stored is None:
                return None
            return apply_atomic_mutation(
                stored,
                mutation,
                expires_at=now + self._ttl_seconds,
                blocked_message=(
                    "This temporary batch is being analyzed. Retry the mutation "
                    "after analysis finishes."
                ),
            )

    def begin_analysis(self, token: str) -> BatchAnalysisLease | None:
        """Reserve a workspace so expiry or another analysis cannot remove it."""

        with self._lock:
            now = self._clock()
            self._purge(now)
            stored = self._items.get(token)
            if stored is None:
                return None
            if stored.active_operation_id is not None:
                raise ProjectBusy(
                    "This temporary batch is already being analyzed. Wait for the "
                    "active analysis to finish before trying again."
                )
            analysis_id = secrets.token_urlsafe(24)
            stored.active_operation_id = analysis_id
            stored.expires_at = now + self._ttl_seconds
            return BatchAnalysisLease(
                token=token,
                analysis_id=analysis_id,
                workspace=stored.workspace,
            )

    def complete_analysis(
        self, lease: BatchAnalysisLease, workspace: BatchWorkspace
    ) -> bool:
        """Commit an analysis only when its exclusive lease is still current."""

        with self._lock:
            stored = self._items.get(lease.token)
            if stored is None or stored.active_operation_id != lease.analysis_id:
                return False
            stored.workspace = workspace
            stored.active_operation_id = None
            stored.expires_at = self._clock() + self._ttl_seconds
            return True

    def cancel_analysis(self, lease: BatchAnalysisLease) -> bool:
        """Release a lease after analysis fails without changing the workspace."""

        with self._lock:
            stored = self._items.get(lease.token)
            if stored is None or stored.active_operation_id != lease.analysis_id:
                return False
            stored.active_operation_id = None
            stored.expires_at = self._clock() + self._ttl_seconds
            return True

    def delete(self, token: str) -> bool:
        with self._lock:
            stored = self._items.get(token)
            if stored is not None and stored.active_operation_id is not None:
                raise ProjectBusy(
                    "This temporary batch is being analyzed and cannot be cleared "
                    "until the active analysis finishes."
                )
            return self._items.pop(token, None) is not None


EphemeralBatchStore = InMemoryProjectRepository

__all__ = [
    "BatchAnalysisLease",
    "BatchWorkspace",
    "EphemeralBatchStore",
    "InMemoryProjectRepository",
    "PersistentProjectRepository",
    "ProjectBusy",
    "ProjectBusyElsewhere",
    "ProjectRepository",
    "ProjectStatus",
    "ProjectSummary",
    "WorkspaceMutationConflict",
]
