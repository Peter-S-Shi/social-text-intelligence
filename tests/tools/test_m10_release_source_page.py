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
    assert f"> Source location: <{url}>" in text
    # The installer page is a template: its release-specific parts stay unfilled,
    # and the page does not claim that it is live.
    for placeholder in (
        "{{INSTALLER_FILENAME}}",
        "{{RELEASE_TAG}}",
        "{{RELEASE_VERSION}}",
    ):
        assert placeholder in text
    assert "does not exist yet" in text
    assert "Verify that same-page link" in text
    # Every URL on the page is the source release; no other hosting is invented.
    assert set(re.findall(r"https?://[^\s>)]+", text)) == {url}
    # It is a release step, not a packet file.
    assert not (ROOT / "distribution/legal" / PAGE.name).exists()
