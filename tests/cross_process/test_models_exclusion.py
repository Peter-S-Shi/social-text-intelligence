"""Two application instances on one models folder: scoped, recoverable exclusion."""

from __future__ import annotations

from pathlib import Path

import pytest
from provisioning.fakes import CONTENT, MANIFEST, FakeTransport, write_model

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
)
from social_text_intelligence.contracts.errors import ModelProvisioningError
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import (
    LocalModelProvisioner,
    local_model_provisioner,
)
from social_text_intelligence.infrastructure.process_locks import FileProcessLocks

from .harness import Peer, eventually


def instance(root: Path) -> LocalModelProvisioner:
    locations = AppDataLocations(root)
    return LocalModelProvisioner(
        models_root=locations.models_dir,
        transport=FakeTransport.serving_manifest(),
        manifest=MANIFEST,
        process_locks=FileProcessLocks(locations.locks_dir),
    )


def source_folder(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    for spec in MANIFEST:
        write_model(source, spec)
    return source


def test_a_concurrent_import_is_refused_with_an_actionable_message(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    source = source_folder(tmp_path)
    peer = Peer(
        "import-models", tmp_path / "sig", root=str(root), source=str(source)
    )
    peer.wait_started()
    try:
        refused = instance(root).import_folder(source)
    finally:
        assert peer.finish() == {"outcome": "completed", "error": None}

    assert refused.outcome is ProvisioningOutcome.FAILED
    assert refused.error_code == "provisioning_elsewhere"  # not storage_failed
    assert refused.error_message is not None
    assert "another window" in refused.error_message.lower()
    assert instance(root).status().ready  # the first instance finished cleanly


def test_verify_download_and_discard_are_refused_the_same_way(tmp_path: Path) -> None:
    root = tmp_path / "root"
    source = source_folder(tmp_path)
    peer = Peer(
        "import-models", tmp_path / "sig", root=str(root), source=str(source)
    )
    peer.wait_started()
    mine = instance(root)
    try:
        with pytest.raises(ModelProvisioningError) as verify:
            mine.verify()
        with pytest.raises(ModelProvisioningError) as discard:
            mine.discard_partial_downloads()
        downloaded = mine.download()
        assert mine.status() is not None  # quick status is read-only: never blocked
    finally:
        assert peer.finish()["outcome"] == "completed"

    assert verify.value.code == "provisioning_elsewhere"
    assert discard.value.code == "provisioning_elsewhere"
    assert downloaded.error_code == "provisioning_elsewhere"


def test_a_hard_killed_importer_leaves_a_folder_a_new_import_can_repair(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    source = source_folder(tmp_path)
    peer = Peer(
        "import-models", tmp_path / "sig", root=str(root), source=str(source)
    )
    peer.wait_started()
    assert instance(root).import_folder(source).error_code == "provisioning_elsewhere"

    peer.kill()

    outcome = eventually(
        lambda: instance(root).import_folder(source),
        accept=lambda result: result.error_code != "provisioning_elsewhere",
    )
    assert outcome.outcome is ProvisioningOutcome.COMPLETED
    assert outcome.status.ready
    for spec in MANIFEST:
        installed = (
            root / "models" / f"models--{spec.model_id.replace('/', '--')}"
        ).rglob("*")
        assert {p.name for p in installed if p.is_file()} == set(CONTENT[spec.key])


def test_the_production_wiring_takes_the_cross_process_lock(tmp_path: Path) -> None:
    locations = AppDataLocations(tmp_path / "root")
    held = FileProcessLocks(locations.locks_dir).try_acquire("models")
    assert held is not None
    try:
        with pytest.raises(ModelProvisioningError) as refused:
            local_model_provisioner(locations).discard_partial_downloads()
        assert refused.value.code == "provisioning_elsewhere"
    finally:
        held.release()
    local_model_provisioner(locations).discard_partial_downloads()
