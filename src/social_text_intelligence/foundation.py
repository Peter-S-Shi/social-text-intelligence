"""Stable project status without model, persistence, or UI dependencies."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectStatus:
    """Machine-readable status used by diagnostics and future interfaces."""

    name: str
    milestone: int
    local_first: bool
    analysis_contracts_available: bool
    model_inference_available: bool


PROJECT_STATUS = ProjectStatus(
    name="Social Text Intelligence",
    milestone=8,
    local_first=True,
    analysis_contracts_available=True,
    model_inference_available=True,
)
