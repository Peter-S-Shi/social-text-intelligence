"""The source hosting record narrows B1 to the installer-page link only."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
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


def load(name: str) -> Any:
    sys.path.insert(0, str(ROOT / "tools" / "m10"))
    try:
        path = ROOT / "tools" / "m10" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"sti_sh_{name}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "tools" / "m10"))


def definition() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (ROOT / "distribution" / "source-manifest.json").read_text(encoding="utf-8")
    )
    return data


def record() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (LEGAL / "SOURCE_HOSTING.json").read_text(encoding="utf-8")
    )
    return data


def packet(tmp_path: Path, data: object | None = None) -> Path:
    """A legal folder holding the replacement guide and a (possibly altered) record."""
    legal = tmp_path / "legal"
    legal.mkdir(parents=True)
    shutil.copyfile(LEGAL / "QT_REPLACEMENT.md", legal / "QT_REPLACEMENT.md")
    (legal / "SOURCE_HOSTING.json").write_text(
        json.dumps(record() if data is None else data), encoding="utf-8"
    )
    return legal


def test_committed_record_matches_the_evidence_and_claims_no_installer_page() -> None:
    compliance = load("compliance")
    status, problems = compliance.source_hosting(LEGAL, ROOT, definition())
    assert problems == []
    assert status["valid"] is True
    data = record()
    assert data["release"]["immutable"] is True
    assert data["release"]["url"].endswith("/releases/tag/sources-qt-6.11.2")
    assert len(data["assets"]) == 13
    assert data["installer_download_page"] == "not live"
    assert data["installer_page_source_link_verified"] is False
    assert data["distribution_permitted"] is False
    # The notices name the same release and say that no installer page is live.
    url = data["release"]["url"]
    for name in ("SOURCE_ACCESS.md", "QT_NOTICE.md"):
        assert url in (LEGAL / name).read_text(encoding="utf-8")
    from social_text_intelligence.desktop.license_notice import qt_notice_text

    assert url in qt_notice_text("6.11.2")


def test_a_valid_record_narrows_b1_to_the_installer_page_link_only() -> None:
    compliance = load("compliance")
    common: dict[str, Any] = dict(b1_record_problems=[], decision_problems=[])
    hosted = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, **common, hosting_problems=[]
    )
    assert hosted == [compliance.B1_HOSTED]
    assert "same-page link must be verified" in hosted[0]
    assert "no such page is live" in hosted[0]
    # Without a record check the earlier wording stays.
    unchecked = compliance.distribution_blockers(VERIFIED, **EVIDENCE, **common)
    assert unchecked == [compliance.B1_ASSESSED]
    rejected = compliance.distribution_blockers(
        VERIFIED, **EVIDENCE, **common, hosting_problems=["x differs"]
    )
    assert rejected[0].startswith(compliance.B1_ASSESSED)
    assert "Source hosting record rejected: x differs" in rejected[0]
    # The hosting record cannot stand in for the decisions or the owner record.
    others: list[dict[str, Any]] = [
        dict(b1_record_problems=None, decision_problems=[]),
        dict(b1_record_problems=["missing"], decision_problems=[]),
        dict(b1_record_problems=[], decision_problems=["missing"]),
        dict(b1_record_problems=[], decision_problems=None),
    ]
    for other in others:
        blockers = compliance.distribution_blockers(
            VERIFIED, **EVIDENCE, **other, hosting_problems=[]
        )
        assert blockers[0] != compliance.B1_HOSTED
        assert blockers[0].startswith("B1:")
    unverified = compliance.distribution_blockers(
        {"qt_libraries_verified": False}, **EVIDENCE, **common, hosting_problems=[]
    )
    assert unverified[0] == compliance.B1_UNVERIFIED


def test_missing_or_malformed_records_fail_closed(tmp_path: Path) -> None:
    compliance = load("compliance")
    assert compliance.source_hosting(tmp_path, ROOT, definition())[1] == [
        "the source hosting record is missing"
    ]
    legal = packet(tmp_path)
    (legal / "SOURCE_HOSTING.json").write_text("{not json", encoding="utf-8")
    status, malformed = compliance.source_hosting(legal, ROOT, definition())
    assert status["valid"] is False
    assert malformed == ["the source hosting record is malformed"]
    (legal / "SOURCE_HOSTING.json").write_text(json.dumps([1]), encoding="utf-8")
    assert compliance.source_hosting(legal, ROOT, definition())[1] == [
        "the source hosting record is not schema version 1"
    ]


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
        (mutate(("installer_download_page",), "live"), "installer_download_page"),
        (
            mutate(("installer_page_source_link_verified",), True),
            "installer_page_source_link_verified",
        ),
        (mutate(("release", "immutable"), False), "release"),
        (mutate(("release", "tag"), "v1.0.0"), "release"),
        (mutate(("release", "target_commit"), "0" * 40), "release"),
        (mutate(("release", "url"), "https://example.invalid/sources"), "release"),
        (
            mutate(("assets", "qtbase-everywhere-src-6.11.2.tar.xz"), "0" * 64),
            "assets",
        ),
        (mutate(("assets", "extra.bin"), "0" * 64), "assets"),
        (mutate(("extra",), True), "extra"),
    ],
)
def test_inconsistent_records_are_rejected(
    tmp_path: Path, change: Callable[[dict[str, Any]], None], expected: str
) -> None:
    compliance = load("compliance")
    data = copy.deepcopy(record())
    change(data)
    status, problems = compliance.source_hosting(
        packet(tmp_path, data), ROOT, definition()
    )
    assert status["valid"] is False
    assert any(expected in problem for problem in problems), problems


def test_hosted_assets_must_be_the_evidence_the_packet_carries(tmp_path: Path) -> None:
    compliance = load("compliance")
    # A source manifest naming another archive hash is not what was hosted.
    other = copy.deepcopy(definition())
    other["archives"][0]["sha256"] = "0" * 64
    problems = compliance.source_hosting(packet(tmp_path), ROOT, other)[1]
    assert any("differs from the packet's evidence" in item for item in problems)
    # Nor is a replacement guide whose bytes changed.
    legal = packet(tmp_path / "second")
    (legal / "QT_REPLACEMENT.md").write_text("changed\n", encoding="utf-8")
    problems = compliance.source_hosting(legal, ROOT, definition())[1]
    assert (
        "hosted asset QT_REPLACEMENT.md differs from the packet's evidence" in problems
    )


def inventory_with(compliance: Any, legal: Path) -> dict[str, Any]:
    status, problems = compliance.source_hosting(legal, ROOT, definition())
    return {"source_hosting": dict(status, problems=problems)}


def test_the_installer_rederives_the_hosting_condition(tmp_path: Path) -> None:
    installer = load("installer")
    comp = load("compliance")
    bundle = tmp_path / "bundle"
    legal = packet(bundle)
    inventory = inventory_with(comp, legal)
    # No claim, or an invalid one, leaves the condition at "not operational".
    assert installer.public_source_hosting(bundle, {}) == "not operational"
    invalid = {"source_hosting": {"valid": False}}
    assert installer.public_source_hosting(bundle, invalid) == "not operational"
    hosted = installer.public_source_hosting(bundle, inventory)
    assert hosted == installer.HOSTED_CONDITION
    assert "does not link to it yet" in hosted
    assert "not verified" in hosted


@pytest.mark.parametrize(
    "forgery", ["altered-record", "stale-hash", "claimed-problems"]
)
def test_a_forged_hosting_claim_refuses_the_installer(
    tmp_path: Path, forgery: str
) -> None:
    installer = load("installer")
    comp = load("compliance")
    bundle = tmp_path / "bundle"
    legal = packet(bundle)
    inventory = inventory_with(comp, legal)
    if forgery == "altered-record":
        data = record()
        data["installer_page_source_link_verified"] = True
        (legal / "SOURCE_HOSTING.json").write_text(json.dumps(data), encoding="utf-8")
        inventory["source_hosting"]["record_sha256"] = comp.digest(
            legal / "SOURCE_HOSTING.json"
        )
    if forgery == "stale-hash":
        inventory["source_hosting"]["record_sha256"] = "0" * 64
    if forgery == "claimed-problems":
        inventory["source_hosting"]["problems"] = ["x"]
    with pytest.raises(ValueError):
        installer.public_source_hosting(bundle, inventory)
