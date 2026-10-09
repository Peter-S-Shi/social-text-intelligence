"""Cross-process mutual exclusion port.

Several instances of the application can run against one data folder. A few
operations must not overlap across them (analysing or committing the same project,
changing the shared models folder). Each is guarded by a named scope. A lock is
tried, never waited on, so a refused caller can say so at once, and it must be
released by the operating system when its holder dies, so a crash never leaves a
stale lock. Adapters live in ``infrastructure``.
"""

from __future__ import annotations

from typing import Protocol

MODELS_SCOPE = "models"


def project_scope(project_id: str) -> str:
    return f"project-{project_id}"


class ProcessLock(Protocol):
    """A held scope. Release is idempotent."""

    def release(self) -> None: ...

    def discard(self) -> None:
        """Release and, best effort, forget the scope's backing file."""


class ProcessLocks(Protocol):
    def try_acquire(self, scope: str) -> ProcessLock | None:
        """Return the held lock, or None if another holder has the scope."""


__all__ = ["MODELS_SCOPE", "ProcessLock", "ProcessLocks", "project_scope"]
