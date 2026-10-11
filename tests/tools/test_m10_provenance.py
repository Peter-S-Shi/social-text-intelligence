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


def synthetic_pe(
    body: bytes, *, signed: bool, pe32: bool = False, checksum: int = 0
) -> tuple[bytes, bytes]:
    """Return (signed-or-plain image, the same image as it was before signing)."""
    optional = 0x40 + 24
    directories = optional + (96 if pe32 else 112)
    image = bytearray(directories + 16 * 8)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x40)
    image[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HH", image, 0x44, 0x8664, 0)
    struct.pack_into("<H", image, 0x40 + 20, len(image) - optional)
    struct.pack_into("<H", image, optional, 0x10B if pe32 else 0x20B)
    struct.pack_into("<I", image, optional + 64, checksum)
    struct.pack_into("<I", image, directories - 4, 16)
    image += body
    original = bytes(image)
    if not signed:
        return original, original
    certificate = b"synthetic certificate table"
    struct.pack_into("<I", image, optional + 64, 0x1234)
    struct.pack_into("<II", image, directories + 32, len(image), len(certificate))
    return bytes(image + certificate), original


def sbom(
    path: Path,
    files: dict[str, bytes],
    commit: str | None = COMMIT,
    version: str = "0.0.0",
    described: int = 1,
) -> Path:
    location = "git://code.qt.io/qt/qtbase.git" + (f"@{commit}" if commit else "")
    document = {
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": f"SPDXRef-Package-qtbase-{index}",
            }
            for index in range(described)
        ],
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-qtbase-{index}",
                "name": "qtbase",
                "versionInfo": version,
                "downloadLocation": location,
            }
            for index in range(described)
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


@pytest.mark.parametrize("pe32", [False, True])
def test_signature_removal_restores_the_pre_signing_digest(pe32: bool) -> None:
    compliance = load()
    signed, original = synthetic_pe(b"synthetic code", signed=True, pe32=pe32)
    assert compliance.unsigned_sha1(signed) == hashlib.sha1(original).hexdigest()


def test_an_unsigned_image_is_hashed_unchanged_including_its_checksum() -> None:
    compliance = load()
    plain, _ = synthetic_pe(b"synthetic code", signed=False, checksum=0x5678)
    assert compliance.unsigned_sha1(plain) == hashlib.sha1(plain).hexdigest()


def test_non_pe_truncated_or_trailing_data_after_the_signature_is_rejected() -> None:
    compliance = load()
    with pytest.raises(ValueError, match="PE"):
        compliance.unsigned_sha1(b"synthetic, not an executable image" * 4)
    image, _ = synthetic_pe(b"", signed=False)
    with pytest.raises(ValueError, match="PE"):
        compliance.unsigned_sha1(image[:0x50])
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


def test_version_only_sbom_must_match_the_delivered_release_version(
    tmp_path: Path,
) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    root = bundle(tmp_path, {"Qt6Core.dll": core})
    document = sbom(
        tmp_path / "qtbase.spdx.json",
        {"bin/Qt6Core.dll": core_original},
        commit=None,
        version="9.9.9",
    )
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert receipt["modules"][0]["source_link"] == "VERSION_MISMATCH"
    assert receipt["binaries"][0]["status"] == "SOURCE_MISMATCH"
    receipt = compliance.verify_qt_provenance(root, [document], [])
    assert receipt["modules"][0]["source_link"] == "NO_SOURCE_ARCHIVE"
    assert receipt["qt_libraries_verified"] is False


def test_a_bundle_without_qt_binaries_is_not_verified(tmp_path: Path) -> None:
    compliance = load()
    root = bundle(tmp_path, {"pyside6.abi3.dll": b"binding only"})
    document = sbom(tmp_path / "qtbase.spdx.json", {})
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert receipt["binaries"] == []
    assert receipt["qt_libraries_verified"] is False


def test_ambiguous_sboms_are_rejected(tmp_path: Path) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    root = bundle(tmp_path, {"Qt6Core.dll": core})
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    two_modules = sbom(tmp_path / "two.spdx.json", {}, described=2)
    with pytest.raises(ValueError, match="exactly one"):
        compliance.verify_qt_provenance(root, [two_modules], [archive])
    first = sbom(tmp_path / "a.spdx.json", {"bin/Qt6Core.dll": core_original})
    duplicate = sbom(tmp_path / "b.spdx.json", {"bin/Qt6Core.dll": core_original})
    receipt = compliance.verify_qt_provenance(root, [first, duplicate], [archive])
    assert receipt["qt_libraries_verified"] is True
    conflicting = sbom(tmp_path / "c.spdx.json", {"bin/Qt6Core.dll": b"other"})
    with pytest.raises(ValueError, match="conflict"):
        compliance.verify_qt_provenance(root, [first, conflicting], [archive])


def test_translations_are_verified_by_plain_digest(tmp_path: Path) -> None:
    compliance = load()
    core, core_original = synthetic_pe(b"synthetic core", signed=True)
    translation = b"synthetic compiled translation catalogue"
    root = bundle(
        tmp_path, {"Qt6Core.dll": core, "translations/qtbase_xx.qm": translation}
    )
    archive = source_archive(tmp_path / "qtbase-everywhere-src-0.0.0.tar.xz", COMMIT)
    document = sbom(
        tmp_path / "qtbase.spdx.json",
        {"bin/Qt6Core.dll": core_original, "translations/qtbase_xx.qm": translation},
    )
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert [row["status"] for row in receipt["binaries"]] == ["VERIFIED", "VERIFIED"]
    (root / "_internal/PySide6/translations/qtbase_yy.qm").write_bytes(b"unlisted")
    receipt = compliance.verify_qt_provenance(root, [document], [archive])
    assert receipt["uncovered_qt_binaries"] == ["translations/qtbase_yy.qm"]
    assert receipt["qt_libraries_verified"] is False


def test_blockers_narrow_only_with_evidence_and_never_grant_permission() -> None:
    compliance = load()
    unverified = compliance.distribution_blockers(
        {"qt_libraries_verified": False}, software_renderer=True
    )
    assert unverified[0] == compliance.B1_UNVERIFIED
    assert compliance.B2 in unverified
    assert compliance.B3_MICROSOFT in unverified
    assert compliance.B3_PYTHON in unverified
    verified = compliance.distribution_blockers(
        {"qt_libraries_verified": True},
        software_renderer=False,
        microsoft_runtime=False,
        python_runtime_verified=True,
    )
    assert verified[0] == compliance.B1_BINDINGS
    assert [item[:3] for item in verified] == ["B1:", "B4:", "B5:"]


def test_bundled_cpython_must_be_the_pinned_official_runtime(tmp_path: Path) -> None:
    compliance = load()
    base = tmp_path / "official"
    base.mkdir()
    (base / "LICENSE.txt").write_text("synthetic licence")
    internal = tmp_path / "bundle" / "_internal"
    internal.mkdir(parents=True)
    (internal / "python313.dll").write_bytes(b"synthetic runtime")
    (internal / "_ssl.pyd").write_bytes(b"synthetic extension")
    manifest = {
        "version": "0.0.0",
        "files": {
            "python313.dll": hashlib.sha256(b"synthetic runtime").hexdigest(),
            "DLLs/_ssl.pyd": hashlib.sha256(b"synthetic extension").hexdigest(),
            "LICENSE.txt": hashlib.sha256(b"synthetic licence").hexdigest(),
        },
    }
    receipt = compliance.verify_python_runtime(tmp_path / "bundle", manifest, base)
    assert receipt["verified"] is True
    (internal / "_ssl.pyd").write_bytes(b"rebuilt extension")
    assert (
        compliance.verify_python_runtime(tmp_path / "bundle", manifest, base)[
            "verified"
        ]
        is False
    )
    (internal / "_ssl.pyd").write_bytes(b"synthetic extension")
    (internal / "_unpinned.pyd").write_bytes(b"extra")
    receipt = compliance.verify_python_runtime(tmp_path / "bundle", manifest, base)
    assert receipt["unpinned_cpython_files"] == ["_unpinned.pyd"]
    assert receipt["verified"] is False


def test_spec_keeps_the_binding_layer_replaceable_and_omits_redistributables() -> None:
    spec = (ROOT / "tools/m10/sti_desktop.spec").read_text(encoding="utf-8")
    assert 'module_collection_mode={"PySide6": "py", "shiboken6": "py"}' in spec
    for omitted in (
        r'r"opengl32sw\.dll|protoc\.exe"',
        r'r"|(msvcp140|vcruntime140|concrt140|vccorlib140)([_-][0-9a-z_]+)?\.dll"',
        '"hf_xet"]',
    ):
        assert omitted in spec


def test_provenance_manifest_pins_every_official_sbom() -> None:
    definition = json.loads(
        (ROOT / "distribution/qt-binary-provenance.json").read_text(encoding="utf-8")
    )
    names = {item["filename"] for item in definition["documents"]}
    assert names == {
        "qtbase-6.11.2.spdx.json",
        "qtsvg-6.11.2.spdx.json",
        "qtimageformats-6.11.2.spdx.json",
        "qttranslations-6.11.2.spdx.json",
    }
    for item in definition["documents"]:
        assert len(item["sha256"]) == 64
        assert item["url"].startswith("https://download.qt.io/")
    assert definition["bindings_covered"] is False
