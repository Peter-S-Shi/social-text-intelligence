"""The release gate separates draft readiness from public B1 operational closure."""

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
BODY_TAG = "v9.9.9-test"
VERSION = "9.9.9"
NAME = f"STI-{VERSION}-x64-setup.exe"
SHA = "a" * 40


def load(name: str) -> Any:
    sys.path.insert(0, str(ROOT / "tools" / "m10"))
    try:
        path = ROOT / "tools" / "m10" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"sti_gate_{name}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "tools" / "m10"))


def make_receipt(installer: Path, **changes: object) -> dict[str, Any]:
    data = installer.read_bytes()
    receipt: dict[str, Any] = {
        "release_candidate": True,
        "profile": "candidate",
        "compiled": True,
        "published": False,
        "distribution_permitted": False,
        "legal_blockers": ["B1"],
        "other_packet_blockers": [],
        "installer_filename": installer.name,
        "version": VERSION,
        "installer_bytes": len(data),
        "installer_sha256": hashlib.sha256(data).hexdigest(),
        "frozen_application_sha": SHA,
        "input_inventory_sha256": "b" * 64,
    }
    receipt.update(changes)
    return receipt


@pytest.fixture
def manifest(tmp_path: Path) -> dict[str, Any]:
    gate = load("release_gate")
    installer = tmp_path / NAME
    installer.write_bytes(b"synthetic installer bytes")
    data: dict[str, Any] = gate.candidate_manifest(make_receipt(installer), installer)
    return data


def draft_api(gate: Any, manifest: dict[str, Any], **changes: Any) -> dict[str, Any]:
    body = gate.render_body(manifest, VERSION, BODY_TAG)
    installer = manifest["installer"]
    api: dict[str, Any] = {
        "draft": True,
        "prerelease": False,
        "immutable": False,
        "tag_name": BODY_TAG,
        "target_commitish": SHA,
        "body": body,
        "assets": [
            {
                "name": installer["filename"],
                "size": installer["bytes"],
                "digest": "sha256:" + installer["sha256"],
            }
        ],
    }
    api.update(changes)
    return api


def source_api(gate: Any) -> dict[str, Any]:
    release = gate.SH_SCHEMA_1["release"]
    return {
        "draft": False,
        "prerelease": False,
        "immutable": True,
        "tag_name": release["tag"],
        "target_commitish": release["target_commit"],
        "body": "source",
        "assets": [
            {"name": n, "size": 1, "digest": "sha256:" + h}
            for n, h in gate.SH_SCHEMA_1["assets"].items()
        ],
    }


def run(gate: Any, manifest: dict[str, Any], phase: str, api: Any, **kw: Any) -> Any:
    html = kw.pop("html", f"<a href='{gate.SH_RELEASE_URL}'>source</a>")
    return gate.verify(
        manifest,
        VERSION,
        BODY_TAG,
        phase,
        lambda: copy.deepcopy(api),
        kw.pop("source", lambda: source_api(gate)),
        lambda: html,
    )


def test_the_candidate_manifest_is_sanitized_and_awaits_the_owner(
    manifest: dict[str, Any], tmp_path: Path
) -> None:
    assert manifest["status"] == "awaiting-owner-decisions"
    assert manifest["owner_decisions_pending"] == [
        "application version",
        "application tag",
    ]
    assert manifest["distribution_permitted"] is False
    assert manifest["published"] is False
    assert str(tmp_path) not in json.dumps(manifest)
    assert len(manifest["source_release"]["assets"]) == 13


@pytest.mark.parametrize(
    "change",
    [
        {"profile": "internal"},
        {"release_candidate": False},
        {"compiled": False},
        {"published": True},
        {"distribution_permitted": True},
        {"legal_blockers": ["B1", "B4"]},
        {"other_packet_blockers": ["x"]},
        {"installer_sha256": "0" * 64},
        {"installer_bytes": 1},
        {"installer_filename": "other.exe"},
        {"version": "1.0.0"},
        {"frozen_application_sha": "short"},
    ],
)
def test_the_manifest_refuses_inconsistent_receipts(
    tmp_path: Path, change: dict[str, object]
) -> None:
    gate = load("release_gate")
    installer = tmp_path / NAME
    installer.write_bytes(b"synthetic installer bytes")
    with pytest.raises(ValueError):
        gate.candidate_manifest(make_receipt(installer, **change), installer)


def test_the_body_needs_the_owners_decisions_and_a_complete_template(
    manifest: dict[str, Any],
) -> None:
    gate = load("release_gate")
    body = gate.render_body(manifest, VERSION, BODY_TAG)
    assert "{{" not in body and manifest["installer"]["sha256"] in body
    assert gate.SH_RELEASE_URL in body and BODY_TAG in body
    assert "internal" not in body.lower()
    for version, tag in (
        ("1.0.0", BODY_TAG),
        (VERSION, ""),
        (VERSION, "bad tag"),
        (VERSION, gate.SOURCE_TAG),
        (VERSION, "sources-other"),
    ):
        with pytest.raises(ValueError):
            gate.render_body(manifest, version, tag)


def test_an_unfilled_template_is_refused(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load("release_gate")
    page = tmp_path / "page.md"
    page.write_text("x\n## Page content\n> {{UNKNOWN_FIELD}}\n", encoding="utf-8")
    monkeypatch.setattr(gate, "TEMPLATE", page)
    with pytest.raises(ValueError, match="unfilled"):
        gate.render_body(manifest, VERSION, BODY_TAG)


def test_a_correct_draft_is_ready_for_approval_but_never_a_closure(
    manifest: dict[str, Any],
) -> None:
    gate = load("release_gate")
    result = run(gate, manifest, "draft", draft_api(gate, manifest))
    assert result["all_checks_passed"] and result["ready_for_owner_approval"]
    assert result["b1_operational_closure"] is False
    assert result["distribution_permitted"] is False
    assert "immutable" not in result["checks"]


@pytest.mark.parametrize(
    ("change", "failing"),
    [
        ({"tag_name": "v0.0.1"}, "tag"),
        ({"target_commitish": "main"}, "target_is_candidate_revision"),
        ({"prerelease": True}, "not_prerelease"),
        ({"body": "no link"}, "body_links_source_release"),
        ({"body": "x"}, "body_is_planned_body"),
        ({"draft": False}, "state_matches_phase"),
        ({"assets": []}, "only_planned_assets"),
        (
            {"assets": [{"name": NAME, "size": 25, "digest": "sha256:" + "0" * 64}]},
            "asset_digests",
        ),
        (
            {"assets": [{"name": NAME, "size": 1, "digest": "sha256:x"}]},
            "asset_digests",
        ),
    ],
)
def test_a_wrong_draft_fails_the_named_check(
    manifest: dict[str, Any], change: dict[str, Any], failing: str
) -> None:
    gate = load("release_gate")
    result = run(gate, manifest, "draft", draft_api(gate, manifest, **change))
    assert result["checks"][failing] is False
    assert result["all_checks_passed"] is False
    assert result["ready_for_owner_approval"] is False


def test_an_extra_asset_is_refused(manifest: dict[str, Any]) -> None:
    gate = load("release_gate")
    api = draft_api(gate, manifest)
    api["assets"].append(
        {"name": "extra.bin", "size": 1, "digest": "sha256:" + "1" * 64}
    )
    assert run(gate, manifest, "draft", api)["checks"]["only_planned_assets"] is False


def public(gate: Any, manifest: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return draft_api(gate, manifest, **{"draft": False, "immutable": True, **changes})


def test_only_a_verified_public_page_closes_b1_operationally(
    manifest: dict[str, Any],
) -> None:
    gate = load("release_gate")
    result = run(gate, manifest, "public", public(gate, manifest))
    assert result["all_checks_passed"] and result["b1_operational_closure"]
    assert result["ready_for_owner_approval"] is False
    assert result["distribution_permitted"] is False
    assert set(result["response_digests"]) == {
        "release_api_sha256",
        "source_release_api_sha256",
        "page_sha256",
    }
    # A draft-shaped response cannot pass the public phase.
    for api in (draft_api(gate, manifest), public(gate, manifest, immutable=False)):
        rejected = run(gate, manifest, "public", api)
        assert rejected["b1_operational_closure"] is False


def test_the_public_page_must_link_the_untouched_source_release(
    manifest: dict[str, Any],
) -> None:
    gate = load("release_gate")
    api = public(gate, manifest)
    no_link = run(gate, manifest, "public", api, html="<html>no link</html>")
    assert no_link["checks"]["page_links_source_release"] is False
    assert no_link["b1_operational_closure"] is False
    altered = source_api(gate)
    altered["assets"][0]["digest"] = "sha256:" + "0" * 64
    swapped = run(gate, manifest, "public", api, source=lambda: altered)
    assert swapped["checks"]["source_release_assets"] is False
    mutable = source_api(gate)
    mutable["immutable"] = False
    unlocked = run(gate, manifest, "public", api, source=lambda: mutable)
    assert unlocked["checks"]["source_release_immutable"] is False
    assert unlocked["b1_operational_closure"] is False


def test_the_public_phase_needs_the_source_release_and_the_page(
    manifest: dict[str, Any],
) -> None:
    gate = load("release_gate")
    with pytest.raises(ValueError):
        gate.verify(
            manifest, VERSION, BODY_TAG, "public", lambda: public(gate, manifest)
        )
    with pytest.raises(ValueError):
        gate.verify(manifest, VERSION, BODY_TAG, "other", lambda: {})
