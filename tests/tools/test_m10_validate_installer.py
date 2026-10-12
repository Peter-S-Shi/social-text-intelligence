"""The clean-machine harness checks (M10 S5-A, H1-H3), without installing anything.

The PowerShell checks run through Windows PowerShell or pwsh when one is present;
the registry is replaced by synthetic values. The harness is never executed.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

M10 = Path(__file__).parents[2] / "tools/m10"
HARNESS = M10 / "validate_installer.ps1"
LIB = M10 / "validate_installer_lib.ps1"
SHELL = shutil.which("pwsh") or (
    shutil.which("powershell") if sys.platform == "win32" else None
)
needs_powershell = pytest.mark.skipif(SHELL is None, reason="needs PowerShell")

DRIVER = r"""
param([string]$Lib, [string]$Case, [string]$DataPath)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. $Lib
$data = Get-Content -LiteralPath $DataPath -Raw | ConvertFrom-Json
try {
    if ($Case -eq 'receipt') {
        $out = @{ ok = $true; result = (Test-StiReceipt $data.receipt) }
    } elseif ($Case -eq 'runtime') {
        $values = $null
        if ($null -ne $data.registry) {
            $values = @{}
            foreach ($p in $data.registry.PSObject.Properties) {
                $value = $p.Value
                if ($value -is [long]) { $value = [int]$value }
                $values[$p.Name] = $value
            }
        }
        $state = Get-StiVCRuntimeState { $values }.GetNewClosure()
        Assert-StiRuntimeExpectation $state $data.expectation
        $out = @{ ok = $true; result = $state }
    } else {
        $facts = Test-StiReceipt $data.receipt
        $state = Get-StiVCRuntimeState { $null }
        $automated = [ordered]@{ install_refused_without_runtime = 'PASS' }
        $observed = New-StiObservations $data.receipt $facts $state `
            'DisposableVM' 'Missing' $automated
        $out = @{ ok = $true; result = $observed }
    }
} catch {
    $out = @{ ok = $false; error = $_.Exception.Message }
}
$out | ConvertTo-Json -Depth 8 -Compress
"""

RECEIPT: dict[str, Any] = {
    "schema_version": 1,
    "prepared": True,
    "compiled": True,
    "frozen_application_sha": "a" * 40,
    "models_bundled": False,
    "distribution_permitted": False,
    "legal_blockers": ["B1", "B4"],
    "other_packet_blockers": [],
    "release_conditions": {
        "B6": "closed only on the narrow QtCore-only criterion",
        "clean_machine_validation": "NOT RUN",
        "public_source_hosting": "not operational",
    },
    "clean_machine_validation": "NOT RUN",
    "owner_30_minute_smoke": "NOT RUN",
    "payload": [{"path": "sti-desktop.exe", "sha256": "b" * 64}],
    "installer_sha256": "c" * 64,
}


def run(case: str, data: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    assert SHELL is not None
    driver = tmp_path / "driver.ps1"
    driver.write_text(DRIVER, encoding="utf-8")
    payload = tmp_path / "data.json"
    payload.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [
            SHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(driver),
            "-Lib",
            str(LIB),
            "-Case",
            case,
            "-DataPath",
            str(payload),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return dict(json.loads(result.stdout))


def receipt(**changes: Any) -> dict[str, Any]:
    value = copy.deepcopy(RECEIPT)
    for key, new in changes.items():
        if new is None:
            value.pop(key)
        else:
            value[key] = new
    return value


@needs_powershell
def test_blockers_come_from_the_receipt_not_a_fixed_list(tmp_path: Path) -> None:
    other = "A synthetic uncoded packet blocker."
    checked = run(
        "receipt",
        {"receipt": receipt(legal_blockers=["B1"], other_packet_blockers=[other])},
        tmp_path,
    )
    assert checked["ok"], checked
    assert checked["result"]["legal_blockers"] in (["B1"], "B1")
    assert checked["result"]["other_packet_blockers"] in ([other], other)
    assert checked["result"]["release_conditions"] == RECEIPT["release_conditions"]


# Each unsafe receipt and the refusal it must produce.
UNSAFE = {
    "distribution permitted": (receipt(distribution_permitted=True), "not permitted"),
    "distribution flag not boolean": (
        receipt(distribution_permitted="false"),
        "not permitted",
    ),
    "models bundled": (receipt(models_bundled=True), "no models are bundled"),
    "not compiled": (receipt(compiled=False), "Compiled installer receipt"),
    "other schema": (receipt(schema_version=2), "schema version 1"),
    "no blockers": (receipt(legal_blockers=[]), "must name its blockers"),
    "B1 omitted": (receipt(legal_blockers=["B4"]), "omits B1"),
    "malformed code": (receipt(legal_blockers=["B1", "B7"]), "malformed"),
    "lower-case code": (receipt(legal_blockers=["b1"]), "malformed"),
    "repeated code": (receipt(legal_blockers=["B1", "B1"]), "repeated"),
    "blockers not a list": (receipt(legal_blockers="B1"), "must be a list"),
    "uncoded blocker not text": (receipt(other_packet_blockers=[3]), "malformed"),
    "uncoded blockers missing": (
        receipt(other_packet_blockers=None),
        "'other_packet_blockers' is missing",
    ),
    "release conditions missing": (
        receipt(release_conditions=None),
        "'release_conditions' is missing",
    ),
    "B6 condition missing": (
        receipt(
            release_conditions={
                "clean_machine_validation": "NOT RUN",
                "public_source_hosting": "not operational",
            }
        ),
        "release_conditions.B6 is missing",
    ),
    "clean machine claimed in conditions": (
        receipt(
            release_conditions=dict(
                RECEIPT["release_conditions"], clean_machine_validation="PASS"
            )
        ),
        "clean-machine result",
    ),
    "clean machine claimed at top level": (
        receipt(clean_machine_validation="PASS"),
        "clean-machine result",
    ),
    "installer hash missing": (receipt(installer_sha256=None), "'installer_sha256'"),
    "empty payload": (receipt(payload=[]), "installed payload"),
}


@needs_powershell
@pytest.mark.parametrize("case", sorted(UNSAFE))
def test_an_inconsistent_or_unsafe_receipt_is_refused(
    case: str, tmp_path: Path
) -> None:
    unsafe, reason = UNSAFE[case]
    checked = run("receipt", {"receipt": unsafe}, tmp_path)
    assert not checked["ok"], case
    assert reason in checked["error"], checked


@needs_powershell
@pytest.mark.parametrize(
    ("registry", "meets"),
    [
        (None, False),
        ({"Installed": 1, "Major": 14, "Minor": 43, "Bld": 34808}, False),
        ({"Installed": 1, "Major": 14, "Minor": 44, "Bld": 35208}, True),
        ({"Installed": 1, "Major": 14, "Minor": 51, "Bld": 36247}, True),
        ({"Installed": 1, "Major": 15, "Minor": 0, "Bld": 1}, True),
        ({"Installed": 0, "Major": 14, "Minor": 51, "Bld": 36247}, False),
        ({"Installed": 1, "Major": "14", "Minor": "51", "Bld": 36247}, False),
    ],
)
def test_runtime_modes_follow_the_registry_and_the_14_44_threshold(
    registry: dict[str, Any] | None, meets: bool, tmp_path: Path
) -> None:
    matching = "Present" if meets else "Missing"
    other = "Missing" if meets else "Present"

    accepted = run("runtime", {"registry": registry, "expectation": matching}, tmp_path)
    refused = run("runtime", {"registry": registry, "expectation": other}, tmp_path)

    assert accepted["ok"], accepted
    assert accepted["result"]["meets_requirement"] is meets
    assert accepted["result"]["present"] is (registry is not None)
    assert not refused["ok"]
    assert "RuntimeExpectation" in refused["error"]


@needs_powershell
def test_observations_never_claim_clean_machine_acceptance(tmp_path: Path) -> None:
    checked = run("observations", {"receipt": receipt()}, tmp_path)
    assert checked["ok"], checked
    observed = checked["result"]

    assert observed["clean_machine_acceptance"] == "NOT DETERMINED BY THIS HARNESS"
    assert "not proof of a clean baseline" in observed["environment_marker"]
    assert observed["clean_baseline_proof"].startswith("NOT PROVIDED")
    assert observed["owner_witness"].startswith("NOT RECORDED")
    assert observed["distribution_permitted"] is False
    assert observed["legal_blockers"] == ["B1", "B4"]
    assert observed["automated_checks"] == {"install_refused_without_runtime": "PASS"}
    assert "PASS" not in json.dumps(
        {k: v for k, v in observed.items() if k != "automated_checks"}
    )


@needs_powershell
def test_the_harness_parses(tmp_path: Path) -> None:
    script = (
        "$t=$null; $e=$null; [void][System.Management.Automation.Language.Parser]"
        f"::ParseFile('{HARNESS}', [ref]$t, [ref]$e); $e.Count"
    )
    assert SHELL is not None
    result = subprocess.run(
        [SHELL, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.stdout.strip() == "0", result.stdout + result.stderr


def test_the_harness_has_no_fixed_blocker_list_or_self_acceptance() -> None:
    harness = HARNESS.read_text(encoding="utf-8")

    assert re.search(r"'B[1-6]'", harness) is None
    assert "clean_machine_acceptance" not in harness
    assert ". (Join-Path $PSScriptRoot 'validate_installer_lib.ps1')" in harness
    assert "[Parameter(Mandatory=$true)][ValidateSet('Missing','Present')]" in harness
    assert "$facts = Test-StiReceipt $manifest" in harness
    assert "Assert-StiRuntimeExpectation $runtime $RuntimeExpectation" in harness


def test_the_harness_keeps_its_data_protection_guards() -> None:
    harness = HARNESS.read_text(encoding="utf-8")
    for guard in (
        "Validation output must be new.",
        "Existing installation/data is preserved; use a fresh Windows profile.",
        "Existing project/model data is preserved; use a fresh Windows profile.",
        "Receipt path escapes install directory.",
        "Installer checksum differs from receipt.",
        "Uninstaller accepted a redirected material directory.",
        "Unexpected link: stop and inspect manually.",
        "Synthetic preservation sentinel changed.",
        "Disposable VM marker is required.",
        "Run only against a new application/profile namespace. No recursive cleanup.",
    ):
        assert guard in harness, guard
    assert "-Recurse" not in harness


def test_the_runtime_threshold_matches_the_installer() -> None:
    script = (M10 / "installer.iss").read_text(encoding="utf-8")
    lib = LIB.read_text(encoding="utf-8")

    assert "((Major > 14) or ((Major = 14) and (Minor >= 44)))" in script
    assert "$StiVCRuntimeMinimum = @{ Major = 14; Minor = 44 }" in lib
    assert "'SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64'" in lib
    assert (
        "VCRuntimeKey = 'SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64'"
        in script
    )
