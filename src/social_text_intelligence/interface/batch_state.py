"""Bounded, expiring in-memory state for the active local batch workflow."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from ..services.batch import BatchPreview, BatchResult, PendingBatchUpload
from ..services.insights import InsightState
from ..services.review import ReviewState


@dataclass(frozen=True, slots=True)
class BatchWorkspace:
    pending: PendingBatchUpload | None = None
    preview: BatchPreview | None = None
    result: BatchResult | None = None
    reviews: ReviewState | None = None
    insights: InsightState | None = None


@dataclass(slots=True)
class _StoredWorkspace:
    workspace: BatchWorkspace
    expires_at: float
    active_analysis_id: str | None = None


@dataclass(frozen=True, slots=True)
class BatchAnalysisLease:
    """Exclusive lease that keeps one batch alive while analysis is running."""

    token: str
    analysis_id: str
    workspace: BatchWorkspace


class EphemeralBatchStore:
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
        self._items: dict[str, _StoredWorkspace] = {}
        self._lock = Lock()

    def _purge(self, now: float) -> None:
        expired = [
            token
            for token, item in self._items.items()
            if item.expires_at <= now and item.active_analysis_id is None
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
            self._items[token] = _StoredWorkspace(
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

    def replace(self, token: str, workspace: BatchWorkspace) -> bool:
        with self._lock:
            now = self._clock()
            self._purge(now)
            stored = self._items.get(token)
            if stored is None or stored.active_analysis_id is not None:
                return False
            stored.workspace = workspace
            stored.expires_at = now + self._ttl_seconds
            return True

    def begin_analysis(self, token: str) -> BatchAnalysisLease | None:
        """Reserve a workspace so expiry or another analysis cannot remove it."""

        with self._lock:
            now = self._clock()
            self._purge(now)
            stored = self._items.get(token)
            if stored is None:
                return None
            if stored.active_analysis_id is not None:
                raise RuntimeError(
                    "This temporary batch is already being analyzed. Wait for the "
                    "active analysis to finish before trying again."
                )
            analysis_id = secrets.token_urlsafe(24)
            stored.active_analysis_id = analysis_id
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
            if (
                stored is None
                or stored.active_analysis_id != lease.analysis_id
            ):
                return False
            stored.workspace = workspace
            stored.active_analysis_id = None
            stored.expires_at = self._clock() + self._ttl_seconds
            return True

    def cancel_analysis(self, lease: BatchAnalysisLease) -> bool:
        """Release a lease after analysis fails without changing the workspace."""

        with self._lock:
            stored = self._items.get(lease.token)
            if (
                stored is None
                or stored.active_analysis_id != lease.analysis_id
            ):
                return False
            stored.active_analysis_id = None
            stored.expires_at = self._clock() + self._ttl_seconds
            return True

    def delete(self, token: str) -> bool:
        with self._lock:
            stored = self._items.get(token)
            if stored is not None and stored.active_analysis_id is not None:
                raise RuntimeError(
                    "This temporary batch is being analyzed and cannot be cleared "
                    "until the active analysis finishes."
                )
            return self._items.pop(token, None) is not None
