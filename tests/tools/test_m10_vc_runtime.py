"""App-local Visual C++ runtime pinning accepts only signed, pinned VC\\Redist files."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[2]
SIGNER = "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, C=US"


def load() -> ModuleType:
    path = ROOT / "tools/m10/vc_runtime.py"
    spec = importlib.util.spec_from_file_location("m10_vc_runtime", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def installation(root: Path, version: str = "14.44.35208") -> Path:
    marker = root / "VC/Auxiliary/Build/Microsoft.VCRedistVersion.default.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text(version + "\n", encoding="utf-8")
    folder = root / "VC/Redist/MSVC" / version / "x64/Microsoft.VC143.CRT"
    folder.mkdir(parents=True)
    for name in ("msvcp140.dll", "vcruntime140.dll"):
        (folder / name).write_bytes(b"synthetic " + name.encode())
    return folder


def manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "minimum_version": "14.44",
                "required_files": ["msvcp140.dll", "vcruntime140.dll"],
                "redist_version": None,
                "files": {},
                "file_versions": {},
                "owner_licence_confirmation": None,
            }
        ),
        encoding="utf-8",
    )
    return path


def facts(folder: Path, **override: str) -> list[dict[str, str]]:
    row = {"status": "Valid", "signer": SIGNER, "version": "14.44.35208.0"}
    return [
        {**row, **override, "path": str(folder / name)}
        for name in ("msvcp140.dll", "vcruntime140.dll")
    ]


def test_pin_records_the_default_redist_files_and_keeps_confirmation_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vc = load()
    folder = installation(tmp_path / "vs")
    monkeypatch.setattr(vc, "file_facts", lambda paths: facts(folder))
    path = manifest(tmp_path / "vc-runtime.json")
    pinned = vc.pin(tmp_path / "vs", path)
    assert pinned["redist_version"] == "14.44.35208"
    assert (
        pinned["files"]["vcruntime140.dll"]
        == hashlib.sha256(b"synthetic vcruntime140.dll").hexdigest()
    )
    assert pinned["owner_licence_confirmation"] is None
    assert json.loads(path.read_text(encoding="utf-8")) == pinned
    assert vc.verify_source(folder, pinned)[0]["file"] == "msvcp140.dll"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"status": "HashMismatch"}, "signature"),
        ({"signer": "CN=Synthetic Publisher, O=Synthetic"}, "signature"),
        ({"signer": "CN=Synthetic, O=Microsoft Corporation Lookalike"}, "signature"),
        ({"version": "14.38.33135.0"}, "older"),
    ],
)
def test_unsigned_foreign_or_old_files_are_never_pinned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: dict[str, str],
    message: str,
) -> None:
    vc = load()
    folder = installation(tmp_path / "vs")
    monkeypatch.setattr(vc, "file_facts", lambda paths: facts(folder, **override))
    path = manifest(tmp_path / "vc-runtime.json")
    before = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        vc.pin(tmp_path / "vs", path)
    assert path.read_text(encoding="utf-8") == before


def test_a_missing_required_file_or_changed_bytes_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vc = load()
    folder = installation(tmp_path / "vs")
    monkeypatch.setattr(vc, "file_facts", lambda paths: facts(folder))
    pinned = vc.pin(tmp_path / "vs", manifest(tmp_path / "vc-runtime.json"))
    (folder / "msvcp140.dll").write_bytes(b"synthetic modified runtime")
    with pytest.raises(ValueError, match="differs from the pinned"):
        vc.verify_source(folder, pinned)
    (folder / "msvcp140.dll").unlink()
    with pytest.raises(ValueError, match="absent"):
        vc.verify_source(folder, pinned)


def test_an_unpinned_manifest_cannot_stage_anything(tmp_path: Path) -> None:
    vc = load()
    folder = installation(tmp_path / "vs")
    unpinned = json.loads(manifest(tmp_path / "vc-runtime.json").read_text())
    with pytest.raises(ValueError, match="not pinned"):
        vc.verify_source(folder, unpinned)


def test_an_absent_redist_folder_is_reported(tmp_path: Path) -> None:
    vc = load()
    marker = tmp_path / "VC/Auxiliary/Build/Microsoft.VCRedistVersion.default.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("14.44.35208", encoding="utf-8")
    with pytest.raises(ValueError, match="absent"):
        vc.redist_directory(tmp_path)


def test_the_committed_manifest_covers_the_measured_import_closure() -> None:
    """M10-E3 measured these six names across all 87 native files of the bundle."""
    committed = json.loads((ROOT / "distribution/vc-runtime.json").read_text())
    assert committed["required_files"] == [
        "msvcp140.dll",
        "msvcp140_1.dll",
        "msvcp140_2.dll",
        "msvcp140_atomic_wait.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
    ]
    assert committed["minimum_version"] == "14.44"
    # Not pinned and not confirmed until the owner's licensed installation exists.
    assert committed["files"] == {}
    assert committed["owner_licence_confirmation"] is None
