"""Bounded, expiring in-memory state for the active local batch workflow."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from ..services.batch import BatchPreview, BatchResult, PendingBatchUpload
from ..services.review import ReviewState


@dataclass(frozen=True, slots=True)
class BatchWorkspace:
    pending: PendingBatchUpload | None = None
    preview: BatchPreview | None = None
    result: BatchResult | None = None
    reviews: ReviewState | None = None


@dataclass(slots=True)
class _StoredWorkspace:
    workspace: BatchWorkspace
    expires_at: float


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
            token for token, item in self._items.items() if item.expires_at <= now
        ]
        for token in expired:
            del self._items[token]

    def create(self, workspace: BatchWorkspace) -> str:
        with self._lock:
            now = self._clock()
            self._purge(now)
            while len(self._items) >= self._capacity:
                oldest = min(
                    self._items,
                    key=lambda token: self._items[token].expires_at,
                )
                del self._items[oldest]
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
            if stored is None:
                return False
            stored.workspace = workspace
            stored.expires_at = now + self._ttl_seconds
            return True

    def delete(self, token: str) -> None:
        with self._lock:
            self._items.pop(token, None)
