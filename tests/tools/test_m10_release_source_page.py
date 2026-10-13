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


def test_the_page_stays_unpublished_and_invents_no_location() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert "It is **not published**." in text
    for placeholder in (
        "{{SOURCE_LOCATION}}",
        "{{RELEASE_TAG}}",
        "{{RELEASE_VERSION}}",
    ):
        assert placeholder in text
    # No hosting exists, so the page names no URL at all.
    assert "http://" not in text and "https://" not in text
    # It is a release step, not a packet file.
    assert not (ROOT / "distribution/legal" / PAGE.name).exists()
