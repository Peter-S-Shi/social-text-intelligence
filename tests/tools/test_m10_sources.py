"""Source delivery verifies upstream bytes and never overwrites local data."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest


def load() -> Any:
    path = Path(__file__).resolve().parents[2] / "tools" / "m10" / "compliance.py"
    spec = importlib.util.spec_from_file_location("sti_compliance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_archive(path: Path) -> str:
    with tarfile.open(path, "w:xz") as archive:
        text = b"Synthetic test license text; not an actual upstream license.\n"
        entry = tarfile.TarInfo("synthetic-1.0/LICENSES/example.txt")
        entry.size = len(text)
        archive.addfile(entry, io.BytesIO(text))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_delivery_rejects_modified_bytes_before_creating_output(
    tmp_path: Path,
) -> None:
    compliance = load()

    source = tmp_path / "source"
    source.mkdir()
    path = source / "synthetic.tar.xz"
    digest = source_archive(path)
    manifest = [
        compliance.SourceArchive(
            "synthetic", path.name, digest, "https://example.invalid"
        )
    ]
    path.write_bytes(path.read_bytes() + b"modified")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="checksum"):
        compliance.stage_sources(source, output, manifest)
    assert not output.exists()


def test_source_delivery_copies_verified_archive_and_preserves_existing_data(
    tmp_path: Path,
) -> None:
    compliance = load()
    source = tmp_path / "source"
    source.mkdir()
    archive = source / "synthetic.tar.xz"
    checksum = source_archive(archive)
    manifest = [
        compliance.SourceArchive(
            "synthetic", archive.name, checksum, "https://example.invalid"
        )
    ]
    output = tmp_path / "output"
    receipt = compliance.stage_sources(source, output, manifest)
    assert (output / archive.name).read_bytes() == archive.read_bytes()
    assert receipt[0]["sha256"] == checksum
    with pytest.raises(FileExistsError):
        compliance.stage_sources(source, output, manifest)
    assert (output / archive.name).read_bytes() == archive.read_bytes()


def test_license_packet_requires_full_gnu_texts(tmp_path: Path) -> None:
    compliance = load()
    archive = tmp_path / "synthetic.tar.xz"
    source_archive(archive)
    with pytest.raises(ValueError, match="GNU"):
        compliance.collect_source_notices([archive], tmp_path / "legal")


def test_packet_verification_detects_missing_or_modified_material(
    tmp_path: Path,
) -> None:
    compliance = load()
    material = tmp_path / "GNU-LGPL-3.0.txt"
    material.write_text("synthetic material")
    manifest = {
        "materials": [{"path": material.name, "sha256": compliance.digest(material)}],
        "distribution_permitted": False,
        "blockers": ["synthetic unresolved obligation"],
    }
    assert compliance.verify_packet(tmp_path, manifest)["materials_valid"] is True
    material.write_text("modified")
    assert compliance.verify_packet(tmp_path, manifest)["materials_valid"] is False
    material.unlink()
    assert compliance.verify_packet(tmp_path, manifest)["materials_valid"] is False


def test_source_delivery_rejects_parent_paths(tmp_path: Path) -> None:
    compliance = load()
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "synthetic.tar.xz"
    checksum = source_archive(path)
    manifest = [
        compliance.SourceArchive(
            "synthetic", "../synthetic.tar.xz", checksum, "https://example.invalid"
        )
    ]
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="filename"):
        compliance.stage_sources(source, output, manifest)
    assert not output.exists()


def test_packet_verification_rejects_an_uninventoried_dll(tmp_path: Path) -> None:
    compliance = load()
    notice = tmp_path / "notice.txt"
    notice.write_text("synthetic notice")
    inventory = {
        "materials": [{"path": notice.name, "sha256": compliance.digest(notice)}]
    }
    assert compliance.verify_packet(tmp_path, inventory)["materials_valid"] is True
    (tmp_path / "unreviewed.dll").write_bytes(b"synthetic unreviewed binary")
    assert compliance.verify_packet(tmp_path, inventory)["materials_valid"] is False


def test_packet_verification_rejects_duplicate_receipts(tmp_path: Path) -> None:
    compliance = load()
    notice = tmp_path / "notice.txt"
    notice.write_text("synthetic notice")
    entry = {"path": notice.name, "sha256": compliance.digest(notice)}
    assert compliance.verify_packet(tmp_path, {"materials": [entry, entry]})[
        "materials_valid"
    ] is False
