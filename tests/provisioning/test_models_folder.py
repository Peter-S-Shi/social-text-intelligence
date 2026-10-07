"""Offline / pre-provisioned models folder: read-only inspection, verified import."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_text_intelligence.application.model_provisioning import (
    FolderFinding,
    ProvisioningOutcome,
    ProvisioningPhase,
    ProvisioningProgress,
)
from social_text_intelligence.contracts.errors import ModelProvisioningError
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import CONTENT, EMOTION, MANIFEST, SENTIMENT, FakeTransport, write_model


def make_provisioner(root: Path) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root, transport=FakeTransport(), manifest=MANIFEST
    )


def write_flat(folder: Path, key: str, overrides: dict[str, bytes] | None = None) -> (
    Path
):
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in CONTENT[key].items():
        (folder / name).write_bytes((overrides or {}).get(name, data))
    return folder


def snapshot_of(folder: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(folder)): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def findings(provisioner: LocalModelProvisioner, folder: Path) -> dict[str, str]:
    inspection = provisioner.inspect_folder(folder)
    return {model.key: model.finding.value for model in inspection.models}


def test_a_hugging_face_cache_folder_is_found_without_being_changed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "existing-cache"
    write_model(source, SENTIMENT)
    write_model(source, EMOTION)
    before = snapshot_of(source)

    inspection = make_provisioner(tmp_path / "models").inspect_folder(source)

    assert inspection.supported
    assert inspection.importable_keys == ("sentiment", "emotion")
    assert snapshot_of(source) == before
    assert not (tmp_path / "models").exists()


def test_flat_model_folders_are_recognised_directly_or_one_level_down(
    tmp_path: Path,
) -> None:
    provisioner = make_provisioner(tmp_path / "models")
    single = write_flat(tmp_path / "emotion-files", "emotion")
    parent = tmp_path / "model-pack"
    write_flat(parent / "sentiment", "sentiment")
    write_flat(parent / "emotion", "emotion")

    assert findings(provisioner, single) == {
        "sentiment": "not_found",
        "emotion": "found",
    }
    assert findings(provisioner, parent) == {"sentiment": "found", "emotion": "found"}


def test_inspection_names_wrong_revision_incomplete_and_mismatched_material(
    tmp_path: Path,
) -> None:
    provisioner = make_provisioner(tmp_path / "models")
    other_revision = tmp_path / "other-revision-cache"
    write_model(other_revision, SENTIMENT, revision="c" * 40)
    write_model(other_revision, EMOTION, only=("config.json", "model.safetensors"))
    mismatched = write_flat(
        tmp_path / "damaged", "sentiment", overrides={"weights.bin": b"short"}
    )

    assert findings(provisioner, other_revision) == {
        "sentiment": "wrong_revision",
        "emotion": "incomplete",
    }
    inspection = provisioner.inspect_folder(mismatched)
    sentiment = inspection.models[0]
    assert sentiment.finding is FolderFinding.MISMATCHED
    assert sentiment.problem_files == ("weights.bin",)
    assert inspection.importable_keys == ()


def test_an_unrelated_folder_is_unsupported_and_a_missing_one_is_unreadable(
    tmp_path: Path,
) -> None:
    provisioner = make_provisioner(tmp_path / "models")
    unrelated = tmp_path / "holiday-photos"
    unrelated.mkdir()
    (unrelated / "notes.txt").write_text("synthetic", encoding="utf-8")

    assert not provisioner.inspect_folder(unrelated).supported
    with pytest.raises(ModelProvisioningError) as raised:
        provisioner.inspect_folder(tmp_path / "does-not-exist")
    assert raised.value.code == "source_unreadable"
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


def test_import_copies_verified_files_and_leaves_the_source_unchanged(
    tmp_path: Path,
) -> None:
    source = tmp_path / "existing-cache"
    write_model(source, SENTIMENT)
    write_model(source, EMOTION)
    before = snapshot_of(source)
    events: list[ProvisioningProgress] = []
    provisioner = make_provisioner(tmp_path / "models")

    result = provisioner.import_folder(source, on_progress=events.append)

    assert result.outcome is ProvisioningOutcome.COMPLETED
    assert result.status.ready
    assert snapshot_of(source) == before
    copying = [e for e in events if e.phase is ProvisioningPhase.COPYING]
    assert copying[-1].overall_bytes_done == copying[-1].overall_bytes_total
    assert not list((tmp_path / "models" / ".sti-staging").rglob("*.*"))


def test_import_rejects_same_size_tampering_and_installs_nothing_for_that_file(
    tmp_path: Path,
) -> None:
    tampered = bytes(len(CONTENT["emotion"]["model.safetensors"]))
    source = write_flat(
        tmp_path / "emotion-files", "emotion", {"model.safetensors": tampered}
    )
    provisioner = make_provisioner(tmp_path / "models")
    assert provisioner.inspect_folder(source).importable_keys == ("emotion",)

    result = provisioner.import_folder(source)

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "checksum_mismatch"
    emotion = result.status.model("emotion")
    assert not emotion.ready
    assert "model.safetensors" in emotion.problem_files
    assert emotion.resumable_bytes == 0
    assert not list((tmp_path / "models" / ".sti-staging").rglob("*.*"))


def test_a_cancelled_import_removes_its_partial_copies(tmp_path: Path) -> None:
    source = write_flat(tmp_path / "sentiment-files", "sentiment")
    provisioner = make_provisioner(tmp_path / "models")
    calls: list[int] = []

    def cancel_on_second_check() -> bool:
        calls.append(1)
        return len(calls) >= 2

    result = provisioner.import_folder(source, cancelled=cancel_on_second_check)

    assert result.outcome is ProvisioningOutcome.CANCELLED
    assert not result.status.model("sentiment").ready
    assert result.status.model("sentiment").resumable_bytes == 0
    assert not list((tmp_path / "models" / ".sti-staging").rglob("*.*"))
