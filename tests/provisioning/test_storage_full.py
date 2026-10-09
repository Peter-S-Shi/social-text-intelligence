"""A full disk during download or import is named, and nothing existing is harmed.

ENOSPC is injected at the write seams (a real full disk is not available to the
suite); everything else is the real provisioner over synthetic models.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
    Readiness,
)
from social_text_intelligence.contracts.errors import ModelProvisioningError
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import (
    EMOTION,
    MANIFEST,
    SENTIMENT,
    FakeTransport,
    snapshot_dir,
    write_model,
)


def provisioner(root: Path) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root, transport=FakeTransport.serving_manifest(), manifest=MANIFEST
    )


class _FullAfter:
    """A file that accepts ``budget`` bytes and then reports a full disk."""

    def __init__(self, inner: Any, budget: int) -> None:
        self._inner = inner
        self._budget = budget

    def __enter__(self) -> _FullAfter:
        self._inner.__enter__()
        return self

    def __exit__(self, *exc: Any) -> Any:
        return self._inner.__exit__(*exc)

    def write(self, data: Any) -> int:
        if len(data) > self._budget:
            raise OSError(errno.ENOSPC, "No space left on device")
        self._budget -= len(data)
        return int(self._inner.write(data))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@contextmanager
def disk_full_for(suffix: str, budget: int) -> Iterator[None]:
    """Files whose name ends in ``suffix`` run out of space after ``budget`` bytes."""

    real_open = Path.open

    def opening(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        handle = real_open(self, mode, *args, **kwargs)
        writing = "w" in mode or "a" in mode
        if writing and str(self).endswith(suffix):
            return _FullAfter(handle, budget)
        return handle

    Path.open = opening  # type: ignore[method-assign]
    try:
        yield
    finally:
        Path.open = real_open  # type: ignore[method-assign]


def test_a_full_disk_during_download_is_named_and_the_partial_file_resumes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    write_model(root, EMOTION)  # an already installed, working model
    installed = snapshot_dir(root, EMOTION) / "model.safetensors"
    before = installed.read_bytes()

    with disk_full_for(".part", 3000):
        result = provisioner(root).download(("sentiment",))

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "storage_full"
    assert "disk space" in (result.error_message or "").lower()
    assert result.status.model("emotion").readiness is Readiness.READY
    assert installed.read_bytes() == before  # existing data untouched

    retry = provisioner(root).download(("sentiment",))  # space freed: it resumes
    assert retry.outcome is ProvisioningOutcome.COMPLETED
    assert retry.status.ready


def test_a_full_disk_during_import_leaves_nothing_partial_and_no_damage(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    source = tmp_path / "source"
    for spec in MANIFEST:
        write_model(source, spec)
    write_model(root, EMOTION)

    with disk_full_for(".import", 2000):
        result = provisioner(root).import_folder(source, ("sentiment",))

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "storage_full"
    assert not list(root.rglob("*.import"))  # no staged leftovers
    assert result.status.model("emotion").readiness is Readiness.READY
    assert result.status.model("sentiment").readiness is not Readiness.CORRUPT

    retry = provisioner(root).import_folder(source, ("sentiment",))
    assert retry.outcome is ProvisioningOutcome.COMPLETED
    assert retry.status.ready


def test_a_full_disk_while_installing_is_named_and_keeps_the_verified_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "models"
    real_replace = os.replace

    def replace(src: Any, dst: Any) -> None:
        if str(dst).endswith("weights.bin"):
            raise OSError(errno.ENOSPC, "No space left on device")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    result = provisioner(root).download(("sentiment",))

    assert result.error_code == "storage_full"
    assert not (snapshot_dir(root, SENTIMENT) / "weights.bin").exists()  # not partial
    monkeypatch.setattr(os, "replace", real_replace)
    assert provisioner(root).download().status.ready  # space freed: it completes


def test_the_other_storage_failures_keep_their_existing_code(tmp_path: Path) -> None:
    blocked = tmp_path / "models"
    blocked.write_bytes(b"not a folder")

    assert provisioner(blocked).download().error_code == "storage_failed"
    assert ModelProvisioningError("storage_full").code == "storage_full"
