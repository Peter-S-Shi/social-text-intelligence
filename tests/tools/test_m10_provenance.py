"""Qt binary provenance is matched to official build SBOMs, never assumed."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import struct
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def load() -> Any:
    path = ROOT / "tools" / "m10" / "compliance.py"
    spec = importlib.util.spec_from_file_location("sti_compliance_provenance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def synthetic_pe(body: bytes, *, signed: bool) -> tuple[bytes, bytes]:
    """Return (signed-or-plain image, the same image as it was before signing)."""
    optional = 0x40 + 24
    image = bytearray(optional + 240)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x40)
    image[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HH", image, 0x44, 0x8664, 0)
    struct.pack_into("<H", image, 0x40 + 20, 240)
    struct.pack_into("<H", image, optional, 0x20B)
    image += body
    original = bytes(image)
    if not signed:
        return original, original
    certificate = b"synthetic certificate table"
    struct.pack_into("<I", image, optional + 64, 0x1234)
    struct.pack_into("<II", image, optional + 112 + 32, len(image), len(certificate))
    return bytes(image + certificate), original


def sbom(path: Path, files: dict[str, bytes], commit: str | None = COMMIT) -> Path:
    location = "git://code.qt.io/qt/qtbase.git" + (f"@{commit}" if commit else "")
    document = {
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-Package-qtbase",
            }
        ],
        "packages": [
            {
                "SPDXID": "SPDXRef-Package-qtbase",
                "name": "qtbase",
                "versionInfo": "synthetic",
                "downloadLocation": location,
            }
        ],
        "files": [
            {
                "fileName": "./" + name,
                "checksums": [
                    {
                        "algorithm": "SHA1",
                        "checksumValue": hashlib.sha1(data).hexdigest(),
                    }
                ],
            }
            for name, data in files.items()
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def source_archive(path: Path, tag: str) -> Path:
    with tarfile.open(path, "w:xz") as archive:
        data = tag.encode() + b"\n"
        entry = tarfile.TarInfo("qtbase-everywhere-src-0.0.0/.tag")
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
    return path


def bundle(tmp_path: Path, files: dict[str, bytes]) -> Path:
    root = tmp_path / "bundle"
    for name, data in files.items():
        target = root / "_internal" / "PySide6" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def test_signature_removal_restores_the_pre_signing_digest() -> None:
    compliance = load()
    signed, original = synthetic_pe(b"synthetic code", signed=True)
    assert compliance.unsigned_sha1(signed) == hashlib.sha1(original).hexdigest()
    plain, _ = synthetic_pe(b"synthetic code", signed=False)
    assert compliance.unsigned_sha1(plain) == hashlib.sha1(plain).hexdigest()


def test_non_pe_or_trailing_data_after_the_signature_is_rejected() -> None:
    compliance = load()
    with pytest.raises(ValueError, match="PE"):
        compliance.unsigned_sha1(b"synthetic, not an executable image" * 4)
    signed, _ = synthetic_pe(b"synthetic code", signed=True)
    with pytest.raises(ValueError, match="final"):
        compliance.unsigned_sha1(signed + b"appended")


def test_matching_binaries_verify_and_uncovered_qt_files_are_reported(
    tmp_path: Path,
) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    plugin, plugin_original = synthetic_pe(b"synthetic plugin", signed=True)
    root = bundle(
        tmp_path,
        {
            "Qt6Core.dll": core,
            "plugins/platforms/qwindows.dll": plugin,
            "pyside6.abi3.dll": b"binding outside the Qt build SBOM",
            "opengl32sw.dll": b"software renderer outside the Qt build SBOM",
        },
    )
    document = sbom(
        tmp_path / "qtbase.spdx.json",
        {
            "bin/Qt6Core.dll": core_original,
            "plugins/platforms/qwindows.dll": plugin_original,
        },
    )
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert [row["status"] for row in receipt["binaries"]] == ["VERIFIED", "VERIFIED"]
    assert receipt["modules"][0]["source_link"] == "COMMIT_MATCH"
    assert receipt["uncovered_qt_binaries"] == ["opengl32sw.dll"]
    assert receipt["qt_libraries_verified"] is False
    assert receipt["distribution_permitted"] is False
    (root / "_internal/PySide6/opengl32sw.dll").unlink()
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert receipt["qt_libraries_verified"] is True
    assert receipt["bindings_covered"] is False


@pytest.mark.parametrize("change", ["binary", "source_tag"])
def test_changed_binary_or_unmatched_source_tag_fails_verification(
    tmp_path: Path, change: str
) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    if change == "binary":
        core, _ = synthetic_pe(b"modified synthetic core", signed=True)
    root = bundle(tmp_path, {"Qt6Core.dll": core})
    document = sbom(tmp_path / "qtbase.spdx.json", {"bin/Qt6Core.dll": core_original})
    tag = "f" * 40 if change == "source_tag" else COMMIT
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", tag)
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    expected = "MISMATCH" if change == "binary" else "SOURCE_MISMATCH"
    assert receipt["binaries"][0]["status"] == expected
    assert receipt["qt_libraries_verified"] is False


def test_sbom_without_a_commit_links_to_source_by_version_only(tmp_path: Path) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    root = bundle(tmp_path, {"Qt6Core.dll": core})
    document = sbom(
        tmp_path / "qtbase.spdx.json", {"bin/Qt6Core.dll": core_original}, commit=None
    )
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert receipt["modules"][0]["source_link"] == "VERSION_ONLY"
    assert receipt["qt_libraries_verified"] is True


def test_blockers_narrow_only_with_evidence_and_never_grant_permission() -> None:
    compliance = load()
    unverified = compliance.distribution_blockers(
        {"qt_libraries_verified": False}, software_renderer=True
    )
    assert unverified[0] == compliance.B1_UNVERIFIED
    assert compliance.B2 in unverified
    verified = compliance.distribution_blockers(
        {"qt_libraries_verified": True}, software_renderer=False
    )
    assert verified[0] == compliance.B1_BINDINGS
    assert compliance.B2 not in verified
    assert [item[:3] for item in verified] == ["B1:", "B3:", "B4:", "B5:"]


def test_spec_keeps_the_binding_layer_replaceable_and_omits_the_renderer() -> None:
    spec = (ROOT / "tools/m10/sti_desktop.spec").read_text(encoding="utf-8")
    assert 'module_collection_mode={"PySide6": "py", "shiboken6": "py"}' in spec
    assert '!= "opengl32sw.dll"' in spec


def test_provenance_manifest_pins_every_official_sbom() -> None:
    definition = json.loads(
        (ROOT / "distribution/qt-binary-provenance.json").read_text(encoding="utf-8")
    )
    names = {item["filename"] for item in definition["documents"]}
    assert names == {
        "qtbase-6.11.2.spdx.json",
        "qtsvg-6.11.2.spdx.json",
        "qtimageformats-6.11.2.spdx.json",
    }
    for item in definition["documents"]:
        assert len(item["sha256"]) == 64
        assert item["url"].startswith("https://download.qt.io/")
    assert definition["bindings_covered"] is False
