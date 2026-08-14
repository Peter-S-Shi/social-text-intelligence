"""Shared atomic mutation primitive for ephemeral process-memory workspaces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

WorkspaceT = TypeVar("WorkspaceT")


class WorkspaceMutationConflict(RuntimeError):
    """A current exclusive operation prevents a safe workspace mutation."""


@dataclass(slots=True)
class StoredWorkspace(Generic[WorkspaceT]):
    """Mutable store cell; callers must access it only while holding a store lock."""

    workspace: WorkspaceT
    expires_at: float
    active_operation_id: str | None = None


def apply_atomic_mutation(
    stored: StoredWorkspace[WorkspaceT],
    mutation: Callable[[WorkspaceT], WorkspaceT],
    *,
    expires_at: float,
    blocked_message: str | None = None,
) -> WorkspaceT:
    """Derive and commit one replacement from the current state under its lock."""

    if stored.active_operation_id is not None:
        raise WorkspaceMutationConflict(
            blocked_message
            or "The workspace has an active operation; retry after it finishes."
        )
    stored.expires_at = expires_at
    updated = mutation(stored.workspace)
    stored.workspace = updated
    return updated
