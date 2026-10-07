"""Compatibility imports for the V1 workspace mutation interface."""

from ..application.workspace_mutation import (
    StoredWorkspace,
    WorkspaceMutationConflict,
    apply_atomic_mutation,
)

__all__ = ["StoredWorkspace", "WorkspaceMutationConflict", "apply_atomic_mutation"]
