"""Thread-safe coalescing of progress updates onto the UI thread."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class CoalescedUpdates(Generic[T]):
    """Keep only the latest value and post at most one pending UI update.

    ``push`` may be called from any thread. ``apply`` always runs on the UI thread
    (through ``post``) with the newest value, so a fast worker cannot flood the
    event queue.
    """

    def __init__(
        self, post: Callable[[Callable[[], None]], None], apply: Callable[[T], None]
    ) -> None:
        self._post = post
        self._apply = apply
        self._lock = threading.Lock()
        self._latest: T | None = None
        self._pending = False

    def push(self, value: T) -> None:
        with self._lock:
            self._latest = value
            if self._pending:
                return
            self._pending = True
        self._post(self._drain)

    def reset(self) -> None:
        """Forget anything not yet applied (UI thread, between operations)."""

        with self._lock:
            self._latest = None
            self._pending = False

    def _drain(self) -> None:
        with self._lock:
            value = self._latest
            self._pending = False
        if value is not None:
            self._apply(value)
