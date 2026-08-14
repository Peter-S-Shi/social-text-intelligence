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
        "| Current lifecycle phase | **Full Regression and Manual Acceptance** |"
        in status
    )
    assert "| Manual Acceptance status | Not started |" in status
    assert "| Release Candidate status | Not started |" in status
    assert "| Release readiness | **No** |" in status

    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "**Current phase: Full Regression and Manual Acceptance**" in roadmap
    assert "**Status: Completed.**" in roadmap
    assert "**Status: Complete.**" in roadmap
    assert "**Status: PASS.**" in roadmap
    assert roadmap.count("**Status: Not started.**") == 1


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
