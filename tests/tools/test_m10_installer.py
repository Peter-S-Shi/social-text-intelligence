"""Installer build boundary rejects unsafe inputs before creating output."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/m10/installer.py"


def invoke(bundle: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bundle",
            str(bundle),
            "--output",
            str(output),
            "--prepare-only",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_incomplete_license_packet_is_rejected_without_output(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "sti-desktop.exe").write_bytes(b"synthetic")
    output = tmp_path / "new-output"
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert "complete license packet" in result.stdout
    assert not output.exists()


def packet(root: Path, *extra: str, runtime: dict[str, object] | None = None) -> Path:
    root.mkdir()
    files = [
        "sti-desktop.exe",
        "sti-check.exe",
        "legal/GNU-LGPL-3.0.txt",
        "legal/GNU-GPL-3.0.txt",
        "legal/SOURCE_ACCESS.md",
        "legal/QT_REPLACEMENT.md",
        *extra,
    ]
    sources = []
    for index in range(5):
        name = f"synthetic-{index}.tar.xz"
        files.append(f"legal/sources/{name}")
        sources.append({"filename": name})
    receipts = []
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"Synthetic infrastructure fixture, not actual license/source."
        )
        receipts.append(
            {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    (root / "legal/inventory.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "application_revision": "a" * 40,
                "materials": receipts,
                "source_delivery": sources,
                "distribution_permitted": False,
                "blockers": ["Synthetic unresolved gate"],
                **({"microsoft_runtime": runtime} if runtime else {}),
            }
        )
    )
    return root


def test_existing_output_and_unrelated_data_are_preserved(tmp_path: Path) -> None:
    bundle = packet(tmp_path / "bundle")
    output = tmp_path / "existing"
    output.mkdir()
    (output / "unrelated.txt").write_text("keep")
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert "new output" in result.stdout
    assert (output / "unrelated.txt").read_text() == "keep"


def test_prepare_stages_verified_packet_without_claiming_installation(
    tmp_path: Path,
) -> None:
    bundle = packet(tmp_path / "bundle")
    output = tmp_path / "prepared"
    result = invoke(bundle, output)
    assert result.returncode == 0, result.stdout
    observed = json.loads(result.stdout)
    assert observed["prepared"] is True
    assert observed["compiled"] is False
    assert observed["distribution_permitted"] is False
    assert observed["clean_machine_validation"] == "NOT RUN"
    assert (output / "payload/legal/inventory.json").read_bytes() == (
        bundle / "legal/inventory.json"
    ).read_bytes()
    assert (output / "payload/installer/INNO-LICENSE.txt").is_file()


@pytest.mark.parametrize(
    "runtime", ["_internal/vcruntime140.dll", "_internal/PySide6/MSVCP140_2.dll"]
)
def test_microsoft_runtime_files_never_enter_the_installer(
    tmp_path: Path, runtime: str
) -> None:
    bundle = packet(tmp_path / "bundle", runtime)
    output = tmp_path / "untouched"
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert "Microsoft Visual C++ runtime" in result.stdout
    assert not output.exists()


def test_installer_requires_the_system_runtime_without_elevating(
    tmp_path: Path,
) -> None:
    bundle = packet(tmp_path / "bundle")
    output = tmp_path / "prepared"
    assert invoke(bundle, output).returncode == 0
    script = (output / "installer.iss").read_text(encoding="utf-8-sig")
    assert "PrivilegesRequired=lowest" in script
    assert "function InitializeSetup(): Boolean;" in script
    assert "RequireSystemRuntime = True;" in script
    assert "LicenseFile=" not in script
    assert "Result := (not RequireSystemRuntime) or VCRuntimeInstalled();" in script
    assert "(Major = 14) and (Minor >= 44)" in script
    # The Microsoft installer is linked, never bundled or launched elevated.
    assert "vc_redist.x64.exe" not in script.lower()
    assert "runascurrentuser" not in script.lower()


def test_source_receipt_cannot_escape_archive_directory(tmp_path: Path) -> None:
    bundle = packet(tmp_path / "bundle")
    path = bundle / "legal/inventory.json"
    inventory = json.loads(path.read_text())
    inventory["source_delivery"][0]["filename"] = "../GNU-LGPL-3.0.txt"
    path.write_text(json.dumps(inventory))
    output = tmp_path / "untouched"
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert not output.exists()


def test_generated_uninstaller_guards_reparse_paths(tmp_path: Path) -> None:
    bundle = packet(tmp_path / "bundle")
    output = tmp_path / "prepared"
    assert invoke(bundle, output).returncode == 0
    script = (output / "installer.iss").read_text(encoding="utf-8-sig")
    assert "function InitializeUninstall(): Boolean;" in script
    assert (
        "if HasReparse(ExpandConstant('{app}\\sti-desktop.exe')) then Exit;" in script
    )
    assert "[UninstallDelete]" not in script


@pytest.mark.parametrize("text", ["[]", "null", "{"])
def test_malformed_inventory_fails_without_traceback_or_writes(
    tmp_path: Path, text: str
) -> None:
    bundle = packet(tmp_path / "bundle")
    (bundle / "legal/inventory.json").write_text(text)
    output = tmp_path / "untouched"
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert result.stderr == ""
    assert not output.exists()


APP_LOCAL = ["msvcp140.dll", "vcruntime140.dll"]


def test_pinned_app_local_runtime_needs_no_prerequisite(tmp_path: Path) -> None:
    runtime = {"route": "R2", "shipped": APP_LOCAL, "matches_pin": True}
    bundle = packet(tmp_path / "bundle", *APP_LOCAL, runtime=runtime)
    output = tmp_path / "prepared"
    result = invoke(bundle, output)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["microsoft_runtime_route"] == "R2"
    script = (output / "installer.iss").read_text(encoding="utf-8-sig")
    assert "RequireSystemRuntime = False;" in script
    assert "R2_END_USER_TERMS.txt" in script
    assert "PrivilegesRequired=lowest" in script
    assert (output / "payload/vcruntime140.dll").is_file()


@pytest.mark.parametrize(
    ("runtime", "extra"),
    [
        ({"route": "R2", "shipped": APP_LOCAL, "matches_pin": False}, APP_LOCAL),
        (
            {"route": "R2", "shipped": APP_LOCAL, "matches_pin": True},
            [*APP_LOCAL, "_internal/msvcp140_2.dll"],
        ),
    ],
)
def test_unpinned_or_extra_runtime_files_are_refused(
    tmp_path: Path, runtime: dict[str, object], extra: list[str]
) -> None:
    bundle = packet(tmp_path / "bundle", *extra, runtime=runtime)
    output = tmp_path / "untouched"
    result = invoke(bundle, output)
    assert result.returncode == 2
    assert "runtime" in result.stdout
    assert not output.exists()
