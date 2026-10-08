"""Regression checks for canonical lifecycle state and tracked documentation."""

from __future__ import annotations

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


def test_current_surfaces_share_one_lifecycle_truth() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CURRENT_SURFACES)
    for phrase in STALE_CURRENT_PHRASES:
        assert phrase not in combined

    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "| Current version | `0.10.0` |" in status
    assert "| Feature milestone status | Milestones 1–10 complete |" in status
    assert "| Feature Complete Review status | **Completed** |" in status
    assert "| Feature Freeze status | **PASS" in status
    assert (
        "| Current lifecycle phase | **V2 Pre-Release Feasibility (M7, "
        "CONDITIONAL, PR #49 open)** after **V2 Native UI Integration** — "
        in status
    )
    assert "| V2 UI/IA Gate | **PASS — 2026-10-07.**" in status
    assert (
        "**M5.0 — Model Provisioner Function Contract & Foundation, M5.1 — "
        "Model Provisioning UI/UX Design, M5.2 — Native Desktop Shell + Model "
        "Provisioning UI, M5.3 — Native Project Workflow, M5.4 — Native Human "
        "Review and Reviewed Export, M5.5 — Native Insights, Context Notes, "
        "and Representative Cases, and M5.6 — Language Detection and "
        "Unsupported-Language Warning are complete on `main`; the M5 "
        "Functional Exit is PASS; M6 — Full UI Integration / Polish is "
        "complete on `main`.**"
        in status
    )
    assert (
        "| M5.0 — Model Provisioner Function Contract & Foundation | **COMPLETE"
        in status
    )
    assert (
        "| M5.6 — Language Detection and Unsupported-Language Warning (V2-3) | "
        "**COMPLETE"
        in status
    )
    assert "| M5 Functional Exit audit | **PASS (2026-10-08)**" in status
    assert (
        "| M6 — Full UI Integration / Polish | **COMPLETE"
        in status
    )
    assert (
        "| M7 — Pre-Release Feasibility & Risk Gate | **CONDITIONAL" in status
    )
    assert (
        "| Next required action | External verification of PR #49 and the "
        "owner's decision on the M7 CONDITIONAL exit"
        in status
    )
    assert (
        "| M5.5 — Native Insights, Context Notes, and Representative Cases | "
        "**COMPLETE"
        in status
    )
    assert (
        "| M5.4 — Native Human Review and Reviewed Export | **COMPLETE"
        in status
    )
    assert (
        "| M5.3 — Native Project Workflow | **COMPLETE"
        in status
    )
    assert (
        "| M5.2 — Native Desktop Shell + Model Provisioning UI | **COMPLETE"
        in status
    )
    assert (
        "| M5.1 — Model Provisioning UI/UX Design | **COMPLETE — Human Gate PASS"
        in status
    )
    assert (
        "| First V2 Persistent Project Foundation milestone (M4) | **COMPLETE"
        in status
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
    assert (
        "**Current phase: V2 Native UI Integration (M6) is complete; M7 — "
        "Pre-Release Feasibility & Risk Gate is recorded as CONDITIONAL in "
        "open PR #49, and the next action is the owner's decision on that "
        "exit.**" in roadmap
    )
    assert "**V1 final phase: Public Portfolio Delivery**" in roadmap
    assert "**Status: Completed.**" in roadmap
    assert "**Status: Complete.**" in roadmap
    assert "**Status: PASS.**" in roadmap
    assert roadmap.count("**Status: PASS — 2026-08-14.**") == 2
    assert roadmap.count("**Status: Not started.**") == 0

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert (
        "> **Current lifecycle phase: V2 Native UI Integration — M6 complete**"
        in readme
    )
    assert (
        "integration and polish) is complete on `main`; the next action is to scope"
        in readme
    )


def test_source_of_truth_responsibilities_are_explicit() -> None:
    charter = (ROOT / "PROJECT_CHARTER.md").read_text(encoding="utf-8")
    development = (ROOT / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "The Charter does not\nrecord the live phase" in charter
    assert "maintained only in\n[PROJECT_STATUS.md](PROJECT_STATUS.md)" in charter
    assert "`PROJECT_STATUS.md` is the only live execution ledger" in development
    readme_status_pointer = (
        "Detailed live execution state is maintained only in\n[Project Status]"
    )
    assert readme_status_pointer in readme


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
                failures.append(
                    f"{document.relative_to(ROOT)} -> {target}"
                )
    assert failures == []
