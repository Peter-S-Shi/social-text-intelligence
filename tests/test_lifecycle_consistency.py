"""Regression checks for canonical lifecycle state and tracked documentation."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
STALE_CURRENT_PHRASES = (
    "Feature Complete Review is now in progress",
    "Current phase: Feature Complete Review",
    "Current lifecycle phase: Feature Complete Review",
    "not yet feature-frozen",
    "feature freeze and release review pending",
    "Current phase: Product Hardening",
    "Current lifecycle phase: Product Hardening",
    "| Current lifecycle phase | **Product Hardening** |",
    "Current phase: Full Regression and Manual Acceptance",
    "Current lifecycle phase: Full Regression and Manual Acceptance",
    "| Current lifecycle phase | **Full Regression and Manual Acceptance** |",
    "Current phase: Release Candidate",
    "Current lifecycle phase: Release Candidate",
    "| Current lifecycle phase | **Release Candidate**",
    "| Release readiness | **No** |",
    "Current phase: Public Portfolio Delivery",
    "Current lifecycle phase: Public Portfolio Delivery",
    "| Current lifecycle phase | **Public Portfolio Delivery**",
    "Current phase: V2 Product Discovery",
    "Current lifecycle phase: V2 Product Discovery",
    "| Current lifecycle phase | **V2 Product Discovery**",
    "awaiting the Product Scope human gate",
    "Current phase: V2 Desktop Architecture Exploration",
    "Current lifecycle phase: V2 Desktop Architecture Exploration",
    "| Current lifecycle phase | **V2 Desktop Architecture Exploration**",
    "the Architecture Gate itself is pending",
    "Current phase: V2 Application Foundation",
    "Current lifecycle phase: V2 Application Foundation",
    "| Current lifecycle phase | **V2 Application Foundation**",
    "is the next mainline milestone and has not started",
    "Persistent Project Foundation is the next" + chr(10) + "mainline milestone",
    "Define the boundary and acceptance checks of M4",
    "No SQLite persistence, model provisioner",
    "persistent local projects are approved but not yet implemented",
    "Current phase: V2 Persistent Project Foundation",
    "Current lifecycle phase: V2 Persistent Project Foundation",
    "| Current lifecycle phase | **V2 Persistent Project Foundation**",
    "the next V2 milestone has not been scoped",
    "The next V2 milestone has not been scoped",
    "M6 — Full UI Integration / Polish is the next lifecycle phase",
    "M6 — Full UI Integration / Polish is the next lifecycle phase and has not begun",
    "### M6 — Full UI Integration / Polish (next, not begun)",
    "M8 is IN PROGRESS",
    "M8 is in progress",
    "M8 as a whole is not complete",
    "owner visual review and exploratory trial PENDING OWNER",
    "Review, insights, and exports are not in the desktop yet.",
)
CURRENT_SURFACES = (
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "PROJECT_CHARTER.md",
    ROOT / "PROJECT_STATUS.md",
    ROOT / "docs" / "DEVELOPMENT.md",
)


def _tracked_markdown_files() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(ROOT / item for item in completed.stdout.splitlines() if item)


def test_m10c_engineering_does_not_close_acceptance_or_distribution_gates() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    record = (ROOT / "docs/V2_M10_C_WINDOWS_INSTALLER.md").read_text(encoding="utf-8")
    for name in ("README.md", "PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        for stale in (
            "no installer, binary distribution",
            "no installer or distributed build exists",
            "no installer exists",
            "Next scope is a later M10 engineering gate",
        ):
            assert stale not in surface
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "M10-C installer engineering established" in roadmap
    assert "| M10-C clean-machine acceptance | **Evidence reviewed" in status
    assert "B1–B6 remain BLOCKED" in record
    assert "B2 and B3 are closed and B1 and\nB4–B6 remain BLOCKED" in record
    assert "M9.2–M9.4 remain DEFERRED" in record
    assert "clean-machine acceptance remains NOT RUN" in record
    assert "Actual missing-model analysis UI" in record


def test_current_surfaces_share_one_lifecycle_truth() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CURRENT_SURFACES)
    for phrase in STALE_CURRENT_PHRASES:
        assert phrase not in combined

    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "| Current version | 2.0.0 — **PUBLISHED (2026-10-13)**" in status
    assert "v2.0.0` is planned and not created" not in status
    assert "releases/tag/v2.0.0" in status
    assert "819e048c399799ed78da83c5711ed3b40d5c4caf" in status
    assert "da7d5d6f8b098250dca2ab35fd9c79bc5a8688a085648e28836b1dd12b914dca" in status
    assert "| Feature milestone status | Milestones 1–10 complete |" in status
    assert "| Feature Complete Review status | **Completed** |" in status
    assert "| Feature Freeze status | **PASS" in status
    assert "| Current lifecycle phase | **PP — Portfolio Packaging" in status
    assert "**conditional career-portfolio release**" in status
    assert "STI_PP4_CURRENT_STATE_2026_10_13" in status
    assert "Public Gate 17/17 PASS" in status
    assert "B1 **operational source-access prerequisite**" in status
    assert "sources-qt-6.11.2" in status
    assert "unsigned/SmartScreen risk" in status
    assert "formal Windows UAT and accessibility remain unverified" in status
    assert "M9.2 representative-domain evaluation" in status
    assert "are **not complete**" in status
    assert "Two S5 icon evidence gaps" in status
    assert "`distribution_permitted=false` remains unchanged" in status
    assert "| V2 UI/IA Gate | **PASS — 2026-10-07.**" in status
    assert (
        "| M5.0 — Model Provisioner Function Contract & Foundation | **COMPLETE"
        in status
    )
    assert (
        "| M5.6 — Language Detection and Unsupported-Language Warning (V2-3) | "
        "**COMPLETE" in status
    )
    assert "| M5 Functional Exit audit | **PASS (2026-10-08)**" in status
    assert "| M6 — Full UI Integration / Polish | **COMPLETE" in status
    assert (
        "| M7 — Pre-Release Feasibility & Risk Gate | **COMPLETE on `main` "
        "with a formally accepted CONDITIONAL exit" in status
    )
    assert (
        "| M8 — Product Hardening & UI Fidelity (shared status) | "
        "**COMPLETE on `main` — owner overall PASS (2026-10-10).**" in status
    )
    assert (
        "| Next required action | Formal owner release decision on the M10-D dossier "
        "remains pending. Owner/legal decisions recorded by M10-E2" in status
    )
    assert "clean-machine matrix" in status
    assert "planned NOT RUN" in status
    assert (
        "| M5.5 — Native Insights, Context Notes, and Representative Cases | "
        "**COMPLETE" in status
    )
    assert "| M5.4 — Native Human Review and Reviewed Export | **COMPLETE" in status
    assert "| M5.3 — Native Project Workflow | **COMPLETE" in status
    assert (
        "| M5.2 — Native Desktop Shell + Model Provisioning UI | **COMPLETE" in status
    )
    assert (
        "| M5.1 — Model Provisioning UI/UX Design | **COMPLETE — Human Gate PASS"
        in status
    )
    assert (
        "| First V2 Persistent Project Foundation milestone (M4) | **COMPLETE" in status
    )
    assert (
        "| V1 final lifecycle phase (historical, immutable) | "
        "**Public Portfolio Delivery** — "
        "Release Candidate Gate is **PASS**; the repository owner's "
        "Version / Delivery Decision approved public portfolio delivery "
        "of `0.10.0` |" in status
    )
    assert "| V2 Product Scope gate | **PASS — 2026-10-06.**" in status
    assert "| V2 Architecture Gate | **PASS — 2026-10-06.**" in status
    assert (
        "| Manual Acceptance status | **PASS — 2026-08-14, 20/20 required "
        "items, 0 blocking defects** |" in status
    )
    assert "| Release Candidate status | **PASS — 2026-08-14** |" in status
    assert (
        "| Public portfolio delivery | **Yes — approved by the "
        "repository owner, 2026-08-15.**" in status
    )

    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "<!-- STI_PP4_CURRENT_STATE_2026_10_13 -->" in roadmap
    assert "V2 development COMPLETE" in roadmap
    assert "CONDITIONAL PORTFOLIO RELEASE PUBLISHED" in roadmap
    assert "PP delivery COMPLETE" in roadmap
    assert "17 release-gate checks passing" in roadmap
    assert "two S5 icon-evidence gaps" in roadmap
    assert (
        "**Historical milestone snapshot (pre-Release-5B/5C): "
        "M10 engineering priority" in roadmap
    )
    assert "**Current phase: M10 engineering priority" not in roadmap
    assert "M9.2–M9.4 are deferred by owner" in roadmap
    assert "M7 CONDITIONAL risks are preserved" in roadmap
    assert "**V1 final phase: Public Portfolio Delivery**" in roadmap
    assert "**Status: Completed.**" in roadmap
    assert "**Status: Complete.**" in roadmap
    assert "**Status: PASS.**" in roadmap
    assert roadmap.count("**Status: PASS — 2026-08-14.**") == 2
    assert roadmap.count("**Status: Not started.**") == 0

    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    assert "Current lifecycle phase: V2 M10 engineering priority" not in readme
    assert "releases/download/v2.0.0/STI-2.0.0-x64-setup.exe" in readme
    assert "releases/tag/v2.0.0" in readme
    assert "releases/tag/sources-qt-6.11.2" in readme
    assert "da7d5d6f8b098250dca2ab35fd9c79bc5a8688a085648e28836b1dd12b914dca" in readme
    assert "conditional career-portfolio release" in readme
    assert "**unsigned**" in readme
    assert "SmartScreen" in readme
    assert "synthetic" in readme
    assert "two remaining icon-observation evidence gaps" in readme
    assert "[Project Status](PROJECT_STATUS.md)" in readme

    track_a = (ROOT / "docs" / "V2_M8_TRACK_A_LEDGER.md").read_text(encoding="utf-8")
    track_b = (ROOT / "docs" / "V2_M8_TRACK_B_FIDELITY.md").read_text(encoding="utf-8")
    walkthrough = (ROOT / "manual-qa" / "owner-trial" / "WALKTHROUGH.md").read_text(
        encoding="utf-8"
    )
    friction_log = (ROOT / "manual-qa" / "owner-trial" / "FRICTION_LOG.md").read_text(
        encoding="utf-8"
    )
    assert "OWNER DECISION or NOT VERIFIED items" in track_a
    assert "M8 overall manual acceptance: PASS (2026-10-10)" in track_b
    assert "This is not formal accessibility" in track_b
    assert "no item-level" in walkthrough.lower()
    assert "empty log does not mean zero friction" in friction_log


def test_m9_owner_gate_pass_does_not_imply_evaluation_or_uat() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert (
        "| M9.0 — Evidence Design Gate | **PASS — owner-approved 2026-10-10.**"
        in status
    )
    assert (
        "No acquisition, labels, model runs, formal UAT or V2 release "
        "readiness is implied" in status
    )
    assert "M9.1 infrastructure is complete; M9.2–M9.4 are deferred by owner" in status
    assert "all initially NOT RUN" in status
    # PP-4 replaced the live lifecycle row; the limitation stays enforced.
    assert "M9.3 formal UAT/accessibility" in status
    assert "M9.4 consolidated formal acceptance" in status
    assert "formal Windows UAT and accessibility remain unverified" in status
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "M9.1–M9.4 and M10 have not started" not in readme
    for name in (
        "V2_M9_EVIDENCE_CONTRACT.md",
        "V2_M9_EVALUATION_PROTOCOL.md",
        "V2_M9_UAT_PROTOCOL.md",
        "V2_M9_EXIT_GATE.md",
    ):
        assert (ROOT / "docs" / name).is_file()
        assert f"docs/{name}" in status


def test_source_of_truth_responsibilities_are_explicit() -> None:
    charter = (ROOT / "PROJECT_CHARTER.md").read_text(encoding="utf-8")
    development = (ROOT / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "The Charter does not\nrecord the live phase" in charter
    assert "maintained only in\n[PROJECT_STATUS.md](PROJECT_STATUS.md)" in charter
    assert "`PROJECT_STATUS.md` is the only live execution ledger" in development
    # The recruiter README points to the ledgers; it is not a ledger itself.
    assert "[Project Status](PROJECT_STATUS.md)" in readme
    assert "[Roadmap](ROADMAP.md)" in readme
    assert (
        "historical milestone records should be read in their own time context"
        in readme
    )


def test_canonical_manual_qa_path_is_used() -> None:
    canonical = ROOT / "manual-qa" / "manual_review_questionnaire.html"
    assert canonical.is_file()
    assert not (ROOT / "manual_review_questionnaire.html").exists()

    current_docs = (
        ROOT / "README.md",
        ROOT / "ROADMAP.md",
        ROOT / "PROJECT_STATUS.md",
        ROOT / "docs" / "DEVELOPMENT.md",
        ROOT / "docs" / "FEATURE_COMPLETE_MANUAL_AUDIT.md",
    )
    for path in current_docs:
        text = path.read_text(encoding="utf-8")
        assert "](manual_review_questionnaire.html)" not in text


def test_all_tracked_relative_markdown_links_resolve() -> None:
    failures: list[str] = []
    for document in _tracked_markdown_files():
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(maxsplit=1)[0]
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0])
            if not relative:
                continue
            resolved = (document.parent / relative).resolve()
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
    assert failures == []


def test_m10_foundation_does_not_waive_acceptance_or_distribution_gates() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "Q5 representative-domain evidence remains required" in status
    assert "Optional owner packaged-app smoke" in status
    assert "30-minute owner smoke: NOT RUN" in status
    assert "no distribution, LGPL compliance or release readiness" in status
    assert "DEFERRED, not accepted or waived" in status


def test_m10e1_narrows_blockers_without_granting_distribution() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    record = (ROOT / "docs/V2_M10_E1_DISTRIBUTION_UNBLOCKING.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "M10-E1 distribution unblocking" in roadmap
    assert "| M10-E1 — Practical Binary Distribution Unblocking |" in status
    for row in (
        "| B1 | **OPEN",
        "| B2 | **RESOLVED by removal",
        "| B3 | **OPEN — owner decision required**",
        "| B4 | **OPEN",
        "| B5 | **OWNER/LEGAL DECISION**",
        "| B6 | **OPEN",
    ):
        assert row in record
    assert "until E4 passes" in record
    assert "distribution_permitted" in record
    for evidence in (
        "replacement-evidence.json",
        "qt-provenance-m10b-bundle.json",
        "rust-compiled-crates.json",
        "e1-packet-correction-receipt.json",
    ):
        assert (ROOT / "docs/evidence/m10-e1" / evidence).is_file()
        data = json.loads(
            (ROOT / "docs/evidence/m10-e1" / evidence).read_text(encoding="utf-8")
        )
        assert data["distribution_permitted"] is False


def test_m10e2_closes_only_evidenced_blockers_and_keeps_gates() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    record = (ROOT / "docs/V2_M10_E2_BLOCKER_CLOSURE.md").read_text(encoding="utf-8")
    for name in ("README.md", "PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        assert "B1 and B3–B6 remain BLOCKED" not in surface
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "M10-E2 blocker closure engineering" in roadmap
    assert "| M10-E2 — Distribution Blocker Closure Engineering |" in status
    for row in (
        "| B1 | **OPEN",
        "| B2 | **CLOSED**",
        "| B3 | **CLOSED**",
        "| B4 | **OPEN",
        "| B5 | **OPEN — owner/legal decision**",
        "| B6 | **OPEN**",
    ):
        assert row in record
    assert "owner risk acceptance is not legal clearance" in record
    receipt = json.loads(
        (ROOT / "docs/evidence/m10-e2/e2-build-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item[:3] for item in receipt["blockers"]] == ["B1:", "B4:", "B5:"]
    assert receipt["python_runtime"]["verified"] is True
    assert all(receipt["absent_by_design"].values())
    for evidence in sorted((ROOT / "docs/evidence/m10-e2").glob("*.json")):
        data = json.loads(evidence.read_text(encoding="utf-8"))
        assert data["distribution_permitted"] is False


def test_m10_s1_record_keeps_the_b5_claim_narrow() -> None:
    record = (ROOT / "docs/V2_M10_S1_OPTIONAL_LANGUAGE_MODEL.md").read_text(
        encoding="utf-8"
    )
    receipt = json.loads(
        (ROOT / "docs/evidence/m10-s1/s1-frozen-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert "Nothing here establishes that the training-corpus terms are" in record
    assert receipt["frozen"]["model_files_in_bundle"] == []
    assert receipt["frozen"]["packet_blockers"] == ["B1:", "B4:"]
    assert receipt["frozen"]["packet_language_model"]["training_corpus_terms"] == (
        "not verified"
    )
    assert receipt["installer"]["payload_model_files"] == []
    assert receipt["distribution_permitted"] is False


def test_m10d_dossier_stratifies_readiness_and_leaves_release_pending() -> None:
    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    dossier = (ROOT / "docs" / "V2_M10_D_RELEASE_DOSSIER.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "M10-D release readiness dossier" in roadmap
    assert "| M10-D — Release Readiness Dossier and Decision Gate |" in status
    assert "RECOMMENDATION IS NO-GO" in dossier
    assert "RECOMMENDATION IS GO" in dossier
    assert "PENDING OWNER DECISION" in dossier
    assert "B1–B6" in dossier
    assert "Public Source-Code Portfolio Presentation" in dossier
    assert "Non-Distributable Product Demonstrations" in dossier
    assert "Downloadable Binary Distribution" in dossier
    assert (ROOT / "docs" / "V2_M10_D_RELEASE_DOSSIER.md").is_file()


def table_rows(text: str, *ids: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        for row_id in ids:
            if line.startswith(f"| {row_id} |"):
                rows[row_id] = line
    return rows


def test_m10_s5_record_keeps_its_evidence_boundaries() -> None:
    record = (ROOT / "docs/V2_M10_S5_COMPLETION_RECORD.md").read_text(encoding="utf-8")
    # Reviewed PASS needs the exported hash chains to have been recomputed.
    assert "`EVIDENCE-SHA256.txt` entries recomputed and equal" in record
    # C07 keeps its limited definition and only the owner's reported witness.
    assert "No Cancel interaction is claimed." in record
    rows = table_rows(record, "C07", "C15", "C16", "Icons")
    assert "Owner-reported" in rows["C07"]
    # A formal icon place without visual evidence keeps the icon row from PASS.
    # The same gap keeps the Release-1 gate from an unconditional PASS.
    formal = [line for line in record.splitlines() if "| Formal (" in line]
    assert len(formal) == 4
    gate = table_rows(record, "Release-1 gate decision")["Release-1 gate decision"]
    if any("NOT DETERMINED" in line for line in formal):
        assert "| PASS" not in rows["Icons"]
        assert "PASS" not in gate
    # Gates that no evidence here can open.
    assert "**BLOCKED**" in rows["C15"]
    assert "| PASS" not in rows["C16"]
    assert "`distribution_permitted` stays false" in record
    assert "permits no product release" in record


def test_release_one_does_not_imply_distribution() -> None:
    for name in ("README.md", "PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        assert "distribution_permitted=true" not in surface, name
        assert "`distribution_permitted` true" not in surface, name


def test_release_one_gate_wording_is_preserved_in_the_roadmap() -> None:
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "distribution gate BLOCKED" in roadmap


def test_release_two_decisions_keep_b1_and_permit_nothing() -> None:
    record = (ROOT / "docs/V2_R2_COMPLIANCE_CLOSURE.md").read_text(encoding="utf-8")
    text = (ROOT / "docs/V2_R2_LICENSE_DECISIONS.md").read_text(encoding="utf-8")
    decisions = " ".join(text.split())
    receipt = json.loads(
        (ROOT / "docs/evidence/r2/r2-intel-nuget-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    check = json.loads(
        (ROOT / "docs/evidence/r2/r2-license-decisions-packet-check.json").read_text(
            encoding="utf-8"
        )
    )
    for decision in ("| LD1 |", "| LD2 |", "| LD3 |", "| LD4 |", "| LD5 |", "| LD6 |"):
        assert decision in record and decision in decisions
    assert "LD1–LD6 OWNER-ASSESSED" in decisions
    assert "not an external legal certification" in decisions
    assert "B1 stays OPEN for one operational prerequisite" in decisions
    assert "`distribution_permitted` stays false" in decisions
    # The Release-2 installer predates the decisions; its record stays as built.
    assert receipt["installer"]["distribution_permitted"] is False
    assert receipt["installer"]["published"] is False
    assert receipt["frozen_build"]["packet"]["blockers"] == ["B1", "B4"]
    assert check["result"]["blocker_codes"] == ["B1"]
    assert check["result"]["distribution_permitted"] is False
    assert check["result"]["license_decisions"]["public_source_hosting"] == (
        "not operational"
    )


def test_release_four_a_narrows_b1_without_closing_it() -> None:
    text = (ROOT / "docs/V2_R4A_PUBLIC_SOURCE_ACCESS.md").read_text(encoding="utf-8")
    record = " ".join(text.split())
    assert "B1 stays OPEN" in record
    assert "B1 is never removed" in record
    assert "`distribution_permitted` stays false" in record
    release = json.loads(
        (ROOT / "docs/evidence/r3/r3-source-release-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert release["immutable"] is True and release["asset_count"] == 13
    assert "B1 closure" in release["not_claimed"]
    check = json.loads(
        (ROOT / "docs/evidence/r4a/r4a-packet-check.json").read_text(encoding="utf-8")
    )
    assert check["result"]["blocker_codes"] == ["B1"]
    assert check["result"]["distribution_permitted"] is False
    assert check["result"]["source_hosting"]["installer_download_page"] == "not live"
    assert "B1 closure" in check["not_claimed"]
    for name in ("PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        assert "installer-page source link" in surface, name


def test_release_four_b_keeps_publication_and_decisions_with_the_owner() -> None:
    record = " ".join(
        (ROOT / "docs/V2_R4B_RELEASE_GATE.md").read_text(encoding="utf-8").split()
    )
    assert "B1 stays OPEN" in record
    assert "`distribution_permitted` stays false" in record
    assert "No application tag, GitHub Release" in record
    assert "Owner decisions (surfaced, not made)" in record
    assert "only the public phase" in record.lower() or "Yes**, and only for" in record
    receipt = json.loads(
        (ROOT / "docs/evidence/r4b/r4b-candidate-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["published"] is False
    assert receipt["private_storage_only"] is True
    assert receipt["distribution_permitted"] is False
    assert receipt["candidate"]["legal_blockers"] == ["B1"]
    assert receipt["owner_decisions_pending"] == [
        "application version",
        "application tag",
    ]
    assert "B1 operational closure" in " ".join(receipt["not_claimed"])
    for name in ("PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        assert "two-phase publication gate" in surface, name


def test_release_five_a1_freezes_the_version_without_a_tag_or_release() -> None:
    record = " ".join(
        (ROOT / "docs/V2_R5A1_VERSION_FREEZE.md").read_text(encoding="utf-8").split()
    )
    assert "planned and not created" in record
    assert "not the release installer" in record
    assert "built fresh from the resulting `main` commit" in record
    assert "`distribution_permitted` stays false" in record
    receipt = json.loads(
        (ROOT / "docs/evidence/r5a1/r5a1-preliminary-candidate-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["version"] == "2.0.0" and receipt["planned_tag"] == "v2.0.0"
    assert receipt["planned_tag_created"] is False
    assert receipt["github_release_or_draft_created"] is False
    assert receipt["published"] is False and receipt["distribution_permitted"] is False
    assert receipt["must_be_rebuilt_from_main"] is True
    assert receipt["candidate"]["legal_blockers"] == ["B1"]
    assert receipt["candidate"]["installer_filename"] == "STI-2.0.0-x64-setup.exe"
    for name in ("PROJECT_STATUS.md", "ROADMAP.md"):
        surface = (ROOT / name).read_text(encoding="utf-8")
        assert "Release-5A-1" in surface, name
        assert "undecided Owner decisions" not in surface, name
