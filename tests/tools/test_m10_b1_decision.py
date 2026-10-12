"""The B1 owner-decision record narrows B1's wording only; it never removes B1."""

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
VERSIONS = {"pyside6_essentials": "6.11.2", "shiboken6": "6.11.2"}
VERIFIED = {"qt_libraries_verified": True}
EVIDENCE = dict(
    software_renderer=False,
    microsoft_runtime=False,
    python_runtime_verified=True,
    language_model_bundled=False,
    b4_remaining=["Intel item"],
)


def load() -> Any:
    path = ROOT / "tools" / "m10" / "compliance.py"
    spec = importlib.util.spec_from_file_location("sti_b1_compliance", path)
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
        (LEGAL / "B1_OWNER_DECISION.json").read_text(encoding="utf-8")
    )
    return data


def write(legal: Path, data: object) -> Path:
    legal.mkdir(parents=True, exist_ok=True)
    (legal / "B1_OWNER_DECISION.json").write_text(json.dumps(data), encoding="utf-8")
    return legal


def test_committed_record_is_consistent_and_records_no_legal_approval() -> None:
    compliance = load()
    status, problems = compliance.b1_owner_decision(LEGAL, definition(), VERSIONS)
    assert problems == []
    assert status["valid"] is True
    assert status["decisions"] == {
        "D1": "approved_engineering_direction",
        "D2": "approved_engineering_direction",
        "D3": "approved_engineering_direction",
        "D4": "unresolved",
    }
    assert status["legal_confirmation"] == "pending"
    assert status["b1_effect"] == "remains_open"
    assert record()["distribution_permitted"] is False


def test_a_valid_record_narrows_b1_but_never_removes_it() -> None:
    compliance = load()
    decided = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=[]
    )
    assert decided[0] == compliance.B1_DECIDED
    assert "Legal confirmation is pending" in decided[0]
    assert [item[:3] for item in decided] == ["B1:", "B4:"]
    unchecked = compliance.distribution_blockers(VERIFIED, **EVIDENCE)
    assert unchecked[0] == compliance.B1_BINDINGS
    # A record cannot stand in for unverified Qt binaries.
    unverified = compliance.distribution_blockers(
        {"qt_libraries_verified": False}, **EVIDENCE, b1_record_problems=[]
    )
    assert unverified[0] == compliance.B1_UNVERIFIED


def test_missing_or_malformed_records_fail_closed(tmp_path: Path) -> None:
    compliance = load()
    _, missing = compliance.b1_owner_decision(tmp_path, definition(), VERSIONS)
    assert missing == ["the owner decision record is missing"]
    (tmp_path / "B1_OWNER_DECISION.json").write_text("{not json", encoding="utf-8")
    status, malformed = compliance.b1_owner_decision(tmp_path, definition(), VERSIONS)
    assert status["valid"] is False
    assert malformed == ["the owner decision record is malformed"]
    write(tmp_path, [record()])
    assert compliance.b1_owner_decision(tmp_path, definition(), VERSIONS)[1]
    write(tmp_path, dict(record(), extra="field"))
    assert compliance.b1_owner_decision(tmp_path, definition(), VERSIONS)[1] == [
        "extra differs from the approved schema 1 content"
    ]
    blockers = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=missing
    )
    assert blockers[0].startswith(compliance.B1_BINDINGS)
    assert "Owner decision record rejected" in blockers[0]


def mutate(path: tuple[str, ...], value: object) -> Callable[[dict[str, Any]], None]:
    def apply(data: dict[str, Any]) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return apply


def delete(path: tuple[str, ...]) -> Callable[[dict[str, Any]], None]:
    def apply(data: dict[str, Any]) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return apply


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (mutate(("legal_confirmation",), "confirmed"), "legal_confirmation"),
        (mutate(("b1_effect",), "closed"), "b1_effect"),
        (mutate(("distribution_permitted",), True), "distribution_permitted"),
        (mutate(("distribution_permitted",), 0), "distribution_permitted"),
        (mutate(("schema_version",), True), "not schema version 1"),
        (mutate(("schema_version",), 2), "not schema version 1"),
        (
            mutate(("binding_producer_source_correspondence",), "proven"),
            "binding_producer_source_correspondence",
        ),
        (mutate(("public_source_hosting",), "operational"), "public_source_hosting"),
        # Record identity and metadata, with their types.
        (mutate(("record",), "M10 S4 B1 legal clearance"), "record"),
        (mutate(("decided",), 20261011), "decided"),
        (mutate(("decided",), "2026-10-12"), "decided"),
        (mutate(("basis",), "docs/OTHER.md"), "basis"),
        (mutate(("extra",), "field"), "extra"),
        (delete(("basis",)), "basis"),
        # Decision content, not only status.
        (mutate(("decisions", "D1", "status"), "approved"), "decisions"),
        (
            mutate(("decisions", "D1", "summary"), "Legal sufficiency is confirmed."),
            "decisions",
        ),
        (mutate(("decisions", "D3", "summary"), ""), "decisions"),
        (mutate(("decisions", "D2", "note"), "unreviewed"), "decisions"),
        (mutate(("decisions", "D4", "status"), "resolved"), "decisions"),
        (mutate(("decisions", "D4", "linked_blocker"), "B1"), "decisions"),
        (delete(("decisions", "D4", "summary")), "decisions"),
        (delete(("decisions", "D3")), "decisions"),
        # The exact two-package binding scope and the source manifest.
        (mutate(("scope", "qt_version"), "6.11.1"), "scope"),
        (
            mutate(
                ("scope", "source_archives", "qtbase-everywhere-src-6.11.2.tar.xz"),
                "0" * 64,
            ),
            "scope",
        ),
        (
            delete(("scope", "source_archives", "qtsvg-everywhere-src-6.11.2.tar.xz")),
            "scope",
        ),
        (mutate(("scope", "components", "shiboken6"), "6.11.1"), "scope"),
        (delete(("scope", "components", "shiboken6")), "scope"),
        (mutate(("scope", "components", "PySide6_Addons"), "6.11.2"), "scope"),
        (mutate(("scope", "components"), {}), "scope"),
        (mutate(("scope", "extra"), True), "scope"),
    ],
)
def test_inconsistent_records_are_rejected(
    tmp_path: Path, change: Callable[[dict[str, Any]], None], expected: str
) -> None:
    compliance = load()
    data = copy.deepcopy(record())
    change(data)
    status, problems = compliance.b1_owner_decision(
        write(tmp_path, data), definition(), VERSIONS
    )
    assert status["valid"] is False
    assert any(expected in problem for problem in problems), problems
    blockers = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, b1_record_problems=problems
    )
    assert blockers[0].startswith("B1:")
    assert blockers[0] != compliance.B1_DECIDED


def test_missing_decision_keys_are_rejected(tmp_path: Path) -> None:
    compliance = load()
    data = copy.deepcopy(record())
    del data["decisions"]["D3"]
    problems = compliance.b1_owner_decision(
        write(tmp_path, data), definition(), VERSIONS
    )[1]
    assert "decisions differs from the approved schema 1 content" in problems


def test_bundle_versions_must_match_the_record(tmp_path: Path) -> None:
    compliance = load()
    problems = compliance.b1_owner_decision(
        LEGAL, definition(), {**VERSIONS, "pyside6_essentials": "6.12.0"}
    )[1]
    assert problems == [
        "the bundled binding versions differ from the record: PySide6_Essentials"
    ]
