"""The candidate installer profile adds gates; the internal profile is unchanged."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40


def load(name: str) -> Any:
    sys.path.insert(0, str(ROOT / "tools" / "m10"))
    try:
        path = ROOT / "tools" / "m10" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"sti_cand_{name}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "tools" / "m10"))


def inventory() -> dict[str, Any]:
    return {
        "application_revision": SHA,
        "license_decisions": {"valid": True, "problems": []},
        "source_hosting": {"valid": True, "problems": []},
        "b4_coverage": {"remaining": []},
    }


@pytest.fixture
def installer(monkeypatch: pytest.MonkeyPatch) -> Any:
    module = load("installer")
    monkeypatch.setattr(module, "source_revision", lambda: SHA)
    return module


def test_the_profiles_differ_only_in_name_and_notice() -> None:
    module = load("installer")
    assert module.PROFILES["internal"]["suffix"] == "internal-x64"
    assert module.PROFILES["internal"]["notice"] == "INSTALLER_NOTICE.txt"
    assert module.PROFILES["candidate"]["suffix"] == "x64-setup"
    assert module.application_version() == "0.10.0"
    internal = (ROOT / "tools/m10/INSTALLER_NOTICE.txt").read_text(encoding="utf-8")
    assert "NOT APPROVED FOR DISTRIBUTION" in internal
    release = (ROOT / "tools/m10/RELEASE_NOTICE.txt").read_text(encoding="utf-8")
    # The release notice states licence facts and invents no approval or status.
    for forbidden in ("internal", "approved", "distribution", "blocker", "B1"):
        assert forbidden.lower() not in release.lower(), forbidden
    assert "never installs or bundles" in " ".join(release.split())


def test_a_ready_packet_passes_the_candidate_gate(installer: Any) -> None:
    installer.candidate_gate(inventory(), ["B1"], [])


@pytest.mark.parametrize(
    ("blockers", "other", "change"),
    [
        (["B1", "B4"], [], {}),
        (["B1"], ["Unmapped frozen module owners: x"], {}),
        ([], [], {}),
        (["B1"], [], {"license_decisions": {"valid": False}}),
        (["B1"], [], {"license_decisions": None}),
        (["B1"], [], {"source_hosting": {"valid": False}}),
        (["B1"], [], {"source_hosting": {}}),
        (["B1"], [], {"b4_coverage": {"remaining": ["x"]}}),
        (["B1"], [], {"b4_coverage": {}}),
        (["B1"], [], {"application_revision": "b" * 40}),
    ],
)
def test_the_candidate_gate_fails_closed(
    installer: Any, blockers: list[str], other: list[str], change: dict[str, Any]
) -> None:
    data = copy.deepcopy(inventory())
    data.update(change)
    with pytest.raises(ValueError):
        installer.candidate_gate(data, blockers, other)


def test_an_uncommitted_tree_refuses_the_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load("installer")

    def dirty() -> str:
        raise ValueError("Packaging inputs must be committed before building.")

    monkeypatch.setattr(module, "source_revision", dirty)
    with pytest.raises(ValueError, match="committed"):
        module.candidate_gate(inventory(), ["B1"], [])


def test_the_cli_refuses_a_candidate_from_an_unready_packet(tmp_path: Path) -> None:
    import subprocess

    bundle = tmp_path / "bundle"
    for name in (
        "sti-desktop.exe",
        "sti-check.exe",
        "legal/GNU-LGPL-3.0.txt",
        "legal/GNU-GPL-3.0.txt",
        "legal/SOURCE_ACCESS.md",
        "legal/QT_REPLACEMENT.md",
        *(f"legal/sources/s{i}.tar.xz" for i in range(5)),
    ):
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic")
    materials = [
        {
            "path": p.relative_to(bundle).as_posix(),
            "sha256": hashlib.sha256(b"synthetic").hexdigest(),
        }
        for p in bundle.rglob("*")
        if p.is_file()
    ]
    (bundle / "legal/inventory.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "application_revision": SHA,
                "materials": materials,
                "source_delivery": [{"filename": f"s{i}.tar.xz"} for i in range(5)],
                "distribution_permitted": False,
                "blockers": ["B1: synthetic."],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/m10/installer.py"),
            "--bundle",
            str(bundle),
            "--output",
            str(output),
            "--profile",
            "candidate",
            "--prepare-only",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert not output.exists()
