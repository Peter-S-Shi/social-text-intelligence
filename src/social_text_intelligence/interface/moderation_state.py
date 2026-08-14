"""Bounded expiring process-memory state for moderation training."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from threading import Lock

from ..services import ModerationWorkspace
from .workspace_mutation import StoredWorkspace, apply_atomic_mutation


class EphemeralModerationStore:
    """Retain a bounded set of local training workspaces without persistence."""

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
        self._items: dict[str, StoredWorkspace[ModerationWorkspace]] = {}
        self._lock = Lock()

    def _purge(self, now: float) -> None:
        expired = [
            token
            for token, item in self._items.items()
            if item.expires_at <= now
        ]
        for token in expired:
            del self._items[token]

    def create(self, workspace: ModerationWorkspace) -> str:
        with self._lock:
            now = self._clock()
            self._purge(now)
            if len(self._items) >= self._capacity:
                raise RuntimeError(
                    "Moderation workspace capacity reached; clear an existing "
                    "workspace or wait for expiry."
                )
            token = secrets.token_urlsafe(24)
            self._items[token] = StoredWorkspace(
                workspace=workspace,
                expires_at=now + self._ttl_seconds,
            )
            return token

    def get(self, token: str) -> ModerationWorkspace | None:
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
        mutation: Callable[[ModerationWorkspace], ModerationWorkspace],
    ) -> ModerationWorkspace | None:
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
            )

    def delete(self, token: str) -> None:
        with self._lock:
            self._items.pop(token, None)
