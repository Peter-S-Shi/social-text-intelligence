"""The prepared GPLv3 section 6(d) source page matches the pinned sources."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "distribution" / "release-source-page.md"


def rows(text: str) -> dict[str, str]:
    """Filename -> SHA-256 for every table row of the page content."""
    return dict(
        re.findall(r"^> \| `([^`]+)` \| [\d,]+ \| `([0-9a-f]{64})` \|$", text, re.M)
    )


def test_every_pinned_source_and_sbom_is_listed_with_its_hash() -> None:
    listed = rows(PAGE.read_text(encoding="utf-8"))
    sources = json.loads(
        (ROOT / "distribution/source-manifest.json").read_text(encoding="utf-8")
    )
    sboms = json.loads(
        (ROOT / "distribution/qt-binary-provenance.json").read_text(encoding="utf-8")
    )
    expected = {item["filename"]: item["sha256"] for item in sources["archives"]}
    expected |= {item["filename"]: item["sha256"] for item in sboms["documents"]}
    assert listed == expected


def test_the_page_names_only_the_published_source_release() -> None:
    text = PAGE.read_text(encoding="utf-8")
    hosting = json.loads(
        (ROOT / "distribution/legal/SOURCE_HOSTING.json").read_text(encoding="utf-8")
    )
    url = hosting["release"]["url"]
    content = text.split("## Page content", 1)[1]
    assert f"<{url}>" in content
    # The page is a template: every release-specific part stays a placeholder,
    # and it asserts nothing about a page being live or its link verified.
    assert set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", content)) == {
        "RELEASE_VERSION",
        "INSTALLER_FILENAME",
        "INSTALLER_BYTES",
        "INSTALLER_SHA256",
        "RELEASE_TAG",
    }
    assert "refuses" in text and "placeholder is unfilled" in " ".join(text.split())
    # Every URL on the page is the source release; no other hosting is invented.
    assert set(re.findall(r"https?://[^\s>)]+", text)) == {url}
    # It is a release step, not a packet file.
    assert not (ROOT / "distribution/legal" / PAGE.name).exists()
