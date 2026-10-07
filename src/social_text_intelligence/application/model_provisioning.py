"""UI-neutral model provisioning contract: approved models, typed state, and port.

The behavior these types describe is fixed by docs/MODEL_PROVISIONING.md. Hugging
Face, filesystem, and network details live in ``infrastructure``; a desktop UI
depends only on this module.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ..contracts.errors import ModelsNotReadyError
from ..providers import (
    EMOTION_MODEL_ID,
    EMOTION_MODEL_REVISION,
    MODEL_ID,
    MODEL_REVISION,
)
from ..services import AnalysisService, LazyAnalysisService
from .settings import AnalysisGateway, AppSettings, pinned_analysis_service


@dataclass(frozen=True, slots=True)
class ModelFile:
    name: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """One approved model at its immutable revision, with every required file."""

    key: str
    model_id: str
    revision: str
    license: str
    files: tuple[ModelFile, ...]

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)


APPROVED_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="sentiment",
        model_id=MODEL_ID,
        revision=MODEL_REVISION,
        license="CC-BY-4.0",
        files=(
            ModelFile(
                "config.json",
                929,
                "d2fba19997da698157196ba16f5fcb30a97a7551cef6845a0f3d743ee19c6129",
            ),
            ModelFile(
                "merges.txt",
                456_318,
                "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
            ),
            ModelFile(
                "pytorch_model.bin",
                501_045_531,
                "4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae",
            ),
            ModelFile(
                "special_tokens_map.json",
                239,
                "378eb3bf733eb16e65792d7e3fda5b8a4631387ca04d2015199c4d4f22ae554d",
            ),
            ModelFile(
                "vocab.json",
                898_822,
                "06b4d46c8e752d410213d9548eb27a54db70fda0319b6271fb8d59dead5e1cab",
            ),
        ),
    ),
    ModelSpec(
        key="emotion",
        model_id=EMOTION_MODEL_ID,
        revision=EMOTION_MODEL_REVISION,
        license="MIT",
        files=(
            ModelFile(
                "config.json",
                1_924,
                "3d4ef8e1465958e169761e2eb09d6e2c8d8806216973691ac40e405c97339d5c",
            ),
            ModelFile(
                "merges.txt",
                456_356,
                "fe36cab26d4f4421ed725e10a2e9ddb7f799449c603a96e7f29b5a3c82a95862",
            ),
            ModelFile(
                "model.safetensors",
                498_697_004,
                "84d6d338b4cf63f0ed3c990a0ce748d32d1d2965c072f4645accaa71af3888c0",
            ),
            ModelFile(
                "special_tokens_map.json",
                280,
                "06e405a36dfe4b9604f484f6a1e619af1a7f7d09e34a8555eb0b77b66318067f",
            ),
            ModelFile(
                "tokenizer.json",
                2_108_856,
                "90e2336a1cdacffe5d4328ab323aa9e5c33889026e4e4881323bebdeeb0e179d",
            ),
            ModelFile(
                "tokenizer_config.json",
                380,
                "6735f2f38dc5399eb76a2c20dcba3ef27a9b2fbba0d05b6e2966038f28aefcf9",
            ),
            ModelFile(
                "vocab.json",
                798_293,
                "ed19656ea1707df69134c4af35c8ceda2cc9860bf2c3495026153a133670ab5e",
            ),
        ),
    ),
)


class Readiness(StrEnum):
    READY = "ready"
    NOT_INSTALLED = "not_installed"
    INCOMPLETE = "incomplete"
    CORRUPT = "corrupt"
    WRONG_REVISION = "wrong_revision"


@dataclass(frozen=True, slots=True)
class ModelStatus:
    key: str
    model_id: str
    revision: str
    license: str
    readiness: Readiness
    total_bytes: int
    installed_bytes: int
    resumable_bytes: int
    problem_files: tuple[str, ...]
    other_revisions: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.readiness is Readiness.READY


@dataclass(frozen=True, slots=True)
class ModelsStatus:
    models: tuple[ModelStatus, ...]

    @property
    def ready(self) -> bool:
        return all(model.ready for model in self.models)

    @property
    def not_ready_keys(self) -> tuple[str, ...]:
        return tuple(model.key for model in self.models if not model.ready)

    def model(self, key: str) -> ModelStatus:
        for model in self.models:
            if model.key == key:
                return model
        raise KeyError(key)


class ProvisioningPhase(StrEnum):
    VERIFYING = "verifying"
    DOWNLOADING = "downloading"
    COPYING = "copying"


@dataclass(frozen=True, slots=True)
class ProvisioningProgress:
    phase: ProvisioningPhase
    model_key: str
    file_name: str
    file_bytes_done: int
    file_bytes_total: int
    model_bytes_done: int
    model_bytes_total: int
    overall_bytes_done: int
    overall_bytes_total: int


class ProvisioningOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProvisioningResult:
    """Every operation ends with the fresh status so the next action is known."""

    outcome: ProvisioningOutcome
    status: ModelsStatus
    error_code: str | None = None
    error_message: str | None = None


class FolderFinding(StrEnum):
    FOUND = "found"
    INCOMPLETE = "incomplete"
    MISMATCHED = "mismatched"
    WRONG_REVISION = "wrong_revision"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class FolderModelFinding:
    key: str
    finding: FolderFinding
    problem_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FolderInspection:
    """Read-only findings for a user-chosen models folder."""

    models: tuple[FolderModelFinding, ...]

    @property
    def supported(self) -> bool:
        return any(m.finding is not FolderFinding.NOT_FOUND for m in self.models)

    @property
    def importable_keys(self) -> tuple[str, ...]:
        return tuple(
            m.key for m in self.models if m.finding is FolderFinding.FOUND
        )


ProgressCallback = Callable[[ProvisioningProgress], None]
CancelCheck = Callable[[], bool]


class ModelProvisioning(Protocol):
    """The provisioning port a desktop UI calls; see the contract, section 10."""

    @property
    def models_root(self) -> Path: ...

    def status(self) -> ModelsStatus:
        """Quick and read-only: presence, exact size, and recorded Verify findings."""
        ...

    def verify(
        self, *, on_progress: ProgressCallback | None = None
    ) -> ModelsStatus:
        """Hash every installed file; a ``corrupt`` finding persists until repaired."""
        ...

    def download(
        self,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: CancelCheck | None = None,
    ) -> ProvisioningResult: ...

    def discard_partial_downloads(
        self, keys: tuple[str, ...] | None = None
    ) -> ModelsStatus: ...

    def inspect_folder(self, folder: Path) -> FolderInspection: ...

    def import_folder(
        self,
        folder: Path,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: CancelCheck | None = None,
    ) -> ProvisioningResult: ...


def provisioned_analysis_settings(settings: AppSettings, models_root: Path) -> (
    AppSettings
):
    """Point the pinned loaders at the managed folder with network loading off."""

    return replace(settings, cache_dir=models_root, offline=True)


def build_provisioned_analysis_service(
    settings: AppSettings, provisioning: ModelProvisioning
) -> AnalysisGateway:
    """Desktop composition: analysis requires ready models and never downloads."""

    def build() -> AnalysisService:
        status = provisioning.status()
        if not status.ready:
            raise ModelsNotReadyError(status.not_ready_keys)
        return pinned_analysis_service(
            provisioned_analysis_settings(settings, provisioning.models_root)
        )

    return LazyAnalysisService(build)
