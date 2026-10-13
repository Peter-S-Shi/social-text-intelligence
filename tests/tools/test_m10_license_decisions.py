"""The licence decision record closes legal subitems only; never B1 or permission."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGAL = ROOT / "distribution" / "legal"
VERIFIED = {"qt_libraries_verified": True}
EVIDENCE = dict(
    software_renderer=False,
    microsoft_runtime=False,
    python_runtime_verified=True,
    language_model_bundled=False,
    b4_remaining=[],
)


def load() -> Any:
    path = ROOT / "tools" / "m10" / "compliance.py"
    spec = importlib.util.spec_from_file_location("sti_ld_compliance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def definition() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (ROOT / "distribution" / "source-manifest.json").read_text(encoding="utf-8")
    )
    return data


def record() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (LEGAL / "LICENSE_DECISIONS.json").read_text(encoding="utf-8")
    )
    return data


def write(legal: Path, data: object) -> Path:
    legal.mkdir(parents=True, exist_ok=True)
    (legal / "LICENSE_DECISIONS.json").write_text(json.dumps(data), encoding="utf-8")
    return legal


def test_committed_record_is_valid_and_permits_nothing() -> None:
    compliance = load()
    status, problems = compliance.license_decisions(LEGAL, definition())
    assert problems == []
    assert status["decisions"] == {f"LD{n}": "owner_assessed" for n in range(1, 7)}
    assert status["public_source_hosting"] == "not operational"
    data = record()
    assert data["distribution_permitted"] is False
    assert "Not an external legal certification" in data["assessment"]
    for item in data["decisions"].values():
        assert item["residual_risk"]
    intel = json.loads((LEGAL / "intel-openmp/provenance.json").read_text())
    assert data["scope"]["intel_openmp_package"] == {
        "id": intel["source"]["package_id"],
        "version": intel["source"]["version"],
        "sha256": intel["source"]["sha256"],
    }


def test_a_valid_record_narrows_b1_to_public_source_access_but_keeps_it() -> None:
    compliance = load()
    assessed = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=[], decision_problems=[]
    )
    assert assessed == [compliance.B1_ASSESSED]
    assert "prepared but not operational" in assessed[0]
    assert "not external legal certification" in assessed[0]
    # Without a valid B1 engineering record, the decisions narrow nothing.
    for b1_problems in (None, ["the owner decision record is missing"]):
        blockers = compliance.distribution_blockers(
            VERIFIED, **EVIDENCE, b1_record_problems=b1_problems, decision_problems=[]
        )
        assert blockers[0].startswith(compliance.B1_BINDINGS)
    # Nor can they stand in for unverified Qt binaries.
    unverified = compliance.distribution_blockers(
        {"qt_libraries_verified": False},
        **EVIDENCE,
        b1_record_problems=[],
        decision_problems=[],
    )
    assert unverified[0] == compliance.B1_UNVERIFIED


def test_missing_or_malformed_records_fail_closed(tmp_path: Path) -> None:
    compliance = load()
    _, missing = compliance.license_decisions(tmp_path, definition())
    assert missing == ["the licence decision record is missing"]
    (tmp_path / "LICENSE_DECISIONS.json").write_text("{not json", encoding="utf-8")
    status, malformed = compliance.license_decisions(tmp_path, definition())
    assert status["valid"] is False
    assert malformed == ["the licence decision record is malformed"]
    write(tmp_path, [record()])
    assert compliance.license_decisions(tmp_path, definition())[1] == [
        "the licence decision record is not schema version 1"
    ]
    blockers = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=[], decision_problems=missing
    )
    assert blockers[0].startswith(compliance.B1_DECIDED)
    assert "Licence decision record rejected" in blockers[0]


def mutate(path: tuple[str, ...], value: object) -> Callable[[dict[str, Any]], None]:
    def apply(data: dict[str, Any]) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return apply


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (mutate(("distribution_permitted",), True), "distribution_permitted"),
        (mutate(("public_source_hosting",), "operational"), "public_source_hosting"),
        (mutate(("release_gate",), "passed"), "release_gate"),
        (mutate(("b1_effect",), "closed"), "b1_effect"),
        (mutate(("decisions", "LD2", "status"), "closed"), "decisions"),
        (mutate(("decisions", "LD7"), {"status": "owner_assessed"}), "decisions"),
        (mutate(("decisions", "LD6", "residual_risk"), ""), "decisions"),
        (mutate(("assessment",), "External legal certification."), "assessment"),
        (mutate(("scope", "intel_openmp_package", "version"), "2027.0.0"), "scope"),
        (mutate(("scope", "qt_version"), "6.12.0"), "scope"),
        (mutate(("extra",), True), "extra"),
    ],
)
def test_inconsistent_records_are_rejected(
    tmp_path: Path, change: Callable[[dict[str, Any]], None], expected: str
) -> None:
    compliance = load()
    data = copy.deepcopy(record())
    change(data)
    status, problems = compliance.license_decisions(write(tmp_path, data), definition())
    assert status["valid"] is False
    assert any(expected in problem for problem in problems), problems
    blockers = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=[], decision_problems=problems
    )
    assert blockers[0] != compliance.B1_ASSESSED
    assert blockers[0].startswith("B1:")
