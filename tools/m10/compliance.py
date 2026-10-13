"""Offline license/source packet assembly; never grants distribution approval."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import re
import shutil
import struct
import sys
import tarfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class SourceArchive:
    component: str
    filename: str
    sha256: str
    url: str


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage_sources(
    source: Path, destination: Path, manifest: Sequence[SourceArchive]
) -> list[dict[str, str]]:
    for entry in manifest:
        if (
            not entry.filename
            or entry.filename in {".", ".."}
            or any(character in entry.filename for character in "/\\:")
        ):
            raise ValueError("Source filename must be a plain archive basename.")
        path = source / entry.filename
        if path.is_symlink() or not path.is_file() or digest(path) != entry.sha256:
            raise ValueError(
                "Required source archive is missing or has a checksum mismatch."
            )
    destination.mkdir(parents=True, exist_ok=False)
    for entry in manifest:
        shutil.copyfile(source / entry.filename, destination / entry.filename)
    return [
        {
            "component": entry.component,
            "filename": entry.filename,
            "sha256": entry.sha256,
            "upstream": entry.url,
        }
        for entry in manifest
    ]


def collect_source_notices(
    archives: Sequence[Path], destination: Path
) -> list[dict[str, str]]:
    """Read notices without extracting archive paths or following links."""
    destination.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    gnu: dict[str, bytes] = {}
    for path in archives:
        with tarfile.open(path, "r:xz") as archive:
            for member in archive:
                basename = member.name.rsplit("/", 1)[-1]
                if not member.isfile() or not (
                    "/LICENSES/" in member.name
                    or basename.lower().startswith(("license", "copying", "copyright"))
                    or basename.lower()
                    in {"notice", "notice.txt", "qt_attribution.json"}
                ):
                    continue
                if member.size > 4 * 1024 * 1024:
                    raise ValueError("Oversized upstream license entry.")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("Unreadable upstream license entry.")
                data = stream.read()
                checksum = hashlib.sha256(data).hexdigest()
                target = checksum + ".txt"
                (destination / target).write_bytes(data)
                records.append(
                    {
                        "archive": path.name,
                        "upstream_path": member.name,
                        "file": target,
                        "sha256": checksum,
                    }
                )
                if basename in {"LGPL-3.0-only.txt", "GPL-3.0-only.txt"}:
                    gnu[basename] = data
    if len(gnu) != 2:
        raise ValueError("Full GNU LGPL v3 and GPL v3 texts are required.")
    for source, target in (
        ("LGPL-3.0-only.txt", "GNU-LGPL-3.0.txt"),
        ("GPL-3.0-only.txt", "GNU-GPL-3.0.txt"),
    ):
        (destination.parent / target).write_bytes(gnu[source])
    return records


def unsigned_sha1(data: bytes) -> str:
    """SHA-1 of a PE image before Authenticode signing, as Qt build SBOMs record it.

    Signing appends the certificate table and sets the security directory and
    header checksum. Qt's signed release images were built with a zero checksum,
    so for a signed image removing exactly those restores the pre-signing bytes;
    an unsigned image is hashed unchanged.
    """
    try:
        if data[:2] != b"MZ":
            raise ValueError("Not a PE image.")
        header = struct.unpack_from("<I", data, 0x3C)[0]
        if data[header : header + 4] != b"PE\0\0":
            raise ValueError("Not a PE image.")
        optional = header + 24
        magic = struct.unpack_from("<H", data, optional)[0]
        if magic not in {0x10B, 0x20B}:
            raise ValueError("Unsupported PE optional header.")
        directories = optional + (112 if magic == 0x20B else 96)
        if struct.unpack_from("<I", data, directories - 4)[0] < 5:
            raise ValueError("PE image has no security directory slot.")
        security = directories + 4 * 8
        offset, size = struct.unpack_from("<II", data, security)
    except struct.error as error:
        raise ValueError("Not a PE image.") from error
    if not size:
        return hashlib.sha1(data).hexdigest()
    if offset + size != len(data):
        raise ValueError("Certificate table is not the final part of the image.")
    image = bytearray(data[:offset])
    struct.pack_into("<I", image, optional + 64, 0)
    struct.pack_into("<II", image, security, 0, 0)
    return hashlib.sha1(image).hexdigest()


@dataclass(frozen=True)
class ReleaseSource:
    """Identity of one delivered Qt release source archive."""

    version: str
    tag: str | None


def release_sources(archives: Sequence[Path]) -> dict[str, ReleaseSource]:
    """Read each Qt release archive's version (file name) and upstream .tag commit."""
    sources: dict[str, ReleaseSource] = {}
    for path in archives:
        repository, _, rest = path.name.partition("-everywhere-src-")
        tag = None
        with tarfile.open(path, "r:xz") as archive:
            for member in archive:
                parts = member.name.removeprefix("./").split("/")
                if member.isfile() and len(parts) == 2 and parts[1] == ".tag":
                    stream = archive.extractfile(member)
                    if stream is not None:
                        tag = stream.read().decode().strip()
                    break
        sources[repository] = ReleaseSource(rest.removesuffix(".tar.xz"), tag)
    return sources


@dataclass(frozen=True)
class SbomEntry:
    sha1: str
    module: str


def source_link(
    commit: str | None, version: str | None, source: ReleaseSource | None
) -> str:
    """How an SBOM's built module is tied to the delivered source archive."""
    if source is None:
        return "NO_SOURCE_ARCHIVE"
    if commit:
        return "COMMIT_MATCH" if commit == source.tag else "COMMIT_MISMATCH"
    return "VERSION_ONLY" if version == source.version else "VERSION_MISMATCH"


def read_build_sbom(
    path: Path, sources: dict[str, ReleaseSource], entries: dict[str, SbomEntry]
) -> dict[str, object]:
    """Record one SBOM's module identity and add its file checksums to entries."""
    document = json.loads(path.read_text(encoding="utf-8"))
    described = {
        item["relatedSpdxElement"]
        for item in document.get("relationships", [])
        if item.get("spdxElementId") == "SPDXRef-DOCUMENT"
        and item.get("relationshipType") == "DESCRIBES"
    }
    packages = [
        item for item in document.get("packages", []) if item["SPDXID"] in described
    ]
    if len(packages) != 1:
        raise ValueError("A Qt build SBOM must describe exactly one module.")
    module = packages[0]["name"]
    match = re.fullmatch(
        r"git://code\.qt\.io/qt/[a-z0-9-]+\.git(?:@([0-9a-f]{40}))?",
        packages[0].get("downloadLocation", ""),
    )
    commit = match.group(1) if match else None
    version = packages[0].get("versionInfo")
    source = sources.get(module)
    for item in document.get("files", []):
        name = item.get("fileName", "").removeprefix("./").lower()
        for checksum in item.get("checksums", []):
            if checksum.get("algorithm") == "SHA1":
                entry = SbomEntry(checksum["checksumValue"].lower(), module)
                # An SBOM may list one file twice; only a conflicting entry is
                # ambiguous.
                if entries.get(name, entry) != entry:
                    raise ValueError("Two Qt build SBOM entries conflict for a file.")
                entries[name] = entry
    return {
        "module": module,
        "version": version,
        "sbom": path.name,
        "sbom_sha256": digest(path),
        "built_commit": commit,
        "source_archive_tag": source.tag if source else None,
        "source_link": source_link(commit, version, source),
    }


def verify_qt_provenance(
    bundle: Path, documents: Sequence[Path], archives: Sequence[Path]
) -> dict[str, object]:
    """Match every shipped Qt library binary and translation to an official SBOM.

    PySide6/shiboken6 binding binaries and runtime DLLs have no Qt build SBOM and
    stay outside this check; any other uncovered Qt-tree binary is reported.
    """
    sources = release_sources(archives)
    entries: dict[str, SbomEntry] = {}
    modules = [read_build_sbom(path, sources, entries) for path in documents]
    links = {item["module"]: item["source_link"] for item in modules}
    qt = bundle / "_internal" / "PySide6"
    rows = []
    uncovered = []
    for path in sorted(qt.rglob("*")):
        relative = path.relative_to(qt).as_posix()
        key = relative.lower()
        translation = key.startswith("translations/") and key.endswith(".qm")
        if not path.is_file() or not (translation or key.endswith(".dll")):
            continue
        if key.startswith(("pyside6.", "msvcp", "vcruntime")):
            continue
        entry = entries.get(
            key if key.startswith(("plugins/", "translations/")) else "bin/" + key
        )
        if entry is None:
            uncovered.append(relative)
            continue
        data = path.read_bytes()
        observed = (
            hashlib.sha1(data).hexdigest() if translation else unsigned_sha1(data)
        )
        status = "VERIFIED" if observed == entry.sha1 else "MISMATCH"
        if status == "VERIFIED" and links[entry.module] not in {
            "COMMIT_MATCH",
            "VERSION_ONLY",
        }:
            status = "SOURCE_MISMATCH"
        rows.append(
            {
                "path": "_internal/PySide6/" + relative,
                "module": entry.module,
                "unsigned_sha1": observed,
                "status": status,
            }
        )
    verified = bool(rows) and all(row["status"] == "VERIFIED" for row in rows)
    return {
        "schema_version": 1,
        "modules": modules,
        "binaries": rows,
        "uncovered_qt_binaries": uncovered,
        "qt_libraries_verified": verified and not uncovered,
        "bindings_covered": False,
        "distribution_permitted": False,
    }


def verify_packet(root: Path, inventory: dict[str, object]) -> dict[str, object]:
    """Structural integrity is separate from permission to distribute."""
    valid = True
    materials = inventory.get("materials")
    if not isinstance(materials, list) or not materials:
        valid = False
    else:
        expected_paths = {
            str(entry.get("path", "")) for entry in materials if isinstance(entry, dict)
        }
        actual_paths = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and path.relative_to(root).as_posix() != "legal/inventory.json"
        }
        if actual_paths != expected_paths or len(expected_paths) != len(materials):
            valid = False
        for entry in materials:
            if not isinstance(entry, dict):
                valid = False
                continue
            relative = entry.get("path", "")
            path = root / str(relative)
            if (
                not isinstance(relative, str)
                or "\\" in relative
                or ":" in relative
                or not path.resolve().is_relative_to(root.resolve())
                or path.is_symlink()
                or not path.is_file()
                or digest(path) != entry.get("sha256")
            ):
                valid = False
    return {
        "materials_valid": valid,
        "distribution_permitted": False,
        "blockers": inventory.get("blockers", []),
    }


B1_UNVERIFIED = (
    "B1: Exact Qt/PySide binary corresponding source, modifications and build recipes "
    "are not established by upstream release archives alone."
)
B1_BINDINGS = (
    "B1: Qt library binaries and translations match the official Qt build SBOMs, "
    "linked to the delivered source archives by commit or, where an SBOM names "
    "none, by release version only; PySide6/shiboken6 binding binaries have no "
    "producer build record, and the release source-delivery route needs "
    "owner/legal confirmation."
)
B2 = (
    "B2: opengl32sw software renderer build provenance and compiled Mesa/LLVM "
    "component attribution are unverified."
)
B3_MICROSOFT = (
    "B3: Microsoft Visual C++ runtime files are bundled without a recorded "
    "redistribution licence route."
)
B3_PYTHON = (
    "B3: Bundled CPython runtime files do not match the pinned official runtime."
)
B4 = (
    "B4: Static Rust/native and vendored dependency license coverage is not "
    "certified by package-level metadata or source-superset notices."
)
B4_INTEL = (
    "Intel OpenMP (libiomp5md/libiompstubs5md) redistribution from Intel's "
    "author-signed NuGet package under the Intel Simplified Software License "
    "needs legal confirmation (channel, notice content, D4 scope, high-risk-use "
    "clause)"
)
INTEL_LICENSE = "Intel Simplified Software License (Version October 2022)"
B5 = "B5: py3langid embedded model training-corpus redistribution terms remain open."
INTEL_FILES = ("libiomp5md.dll", "libiompstubs5md.dll")


B1_DECIDED = (
    "B1: Qt library binaries and translations match the official Qt build SBOMs; "
    "the owner approved keeping the unmodified official Qt/PySide6/shiboken6 "
    "binaries with upstream release-source delivery (D1-D3) as an engineering "
    "direction only. Legal confirmation is pending, exact binding producer-source "
    "correspondence is unproven, public source hosting is not operational, and D4 "
    "is unresolved with B4."
)
B1_RECORD = "B1_OWNER_DECISION.json"
B1_APPROVED = "approved_engineering_direction"
# The owner-approved content of schema version 1, exactly. Version 1 can express
# only an engineering direction: legal confirmation pending and B1 open. A
# confirmation, a B1 closure or other content needs a reviewed new version,
# added here beside it.
B1_SCHEMA_1: dict[str, object] = {
    "schema_version": 1,
    "record": "M10 S4 B1 owner decision (engineering direction)",
    "decided": "2026-10-11",
    "basis": "docs/V2_M10_S4_B1_DECISION_MEMO.md",
    "decisions": {
        "D1": {
            "status": B1_APPROVED,
            "summary": "Keep the official, unmodified Qt/PySide6/shiboken6 6.11.2 "
            "binaries and deliver the hash-pinned upstream release sources and "
            "build scripts as their source.",
        },
        "D2": {
            "status": B1_APPROVED,
            "summary": "Plan in-package source archives plus GPLv3 section 6(d) "
            "equivalent access, with same-download-page hosting as the preferred "
            "policy.",
        },
        "D3": {
            "status": B1_APPROVED,
            "summary": "Keep the Qt libraries replaceable with no signature or "
            "integrity lock for standalone software distribution.",
        },
        "D4": {
            "status": "unresolved",
            "linked_blocker": "B4",
            "summary": "Whether an Intel-only anti-reverse-engineering term is "
            "compatible with LGPLv3 section 4.",
        },
    },
    "legal_confirmation": "pending",
    "binding_producer_source_correspondence": "unproven",
    "public_source_hosting": "not operational",
    "b1_effect": "remains_open",
    "distribution_permitted": False,
}
B1_SCHEMA_1_COMPONENTS = {"PySide6_Essentials": "6.11.2", "shiboken6": "6.11.2"}

B1_ASSESSED = (
    "B1: the owner assessed the unmodified official Qt/PySide6/shiboken6 binaries "
    "with upstream release-source delivery as compliant (LD1-LD3 in "
    "LICENSE_DECISIONS.json; not external legal certification), accepting the "
    "unproven binding producer-source correspondence as a disclosed residual "
    "risk. Public source access under GPLv3 section 6(d) is prepared but not "
    "operational."
)
LD_RECORD = "LICENSE_DECISIONS.json"
LD_ASSESSED = "owner_assessed"
INTEL_PACKAGE = {
    "id": "intelopenmp.redist.win",
    "version": "2026.1.0.239",
    "sha256": "2a0f9fcdb51d8ac9fa535b67f013fd9341338355679261a39b946ef5e3f399fe",
}
# The owner-approved content of the licence decision record, schema version 1,
# exactly. It answers legal questions only. It cannot record public source
# hosting as operational or permit distribution; that needs a reviewed new
# version and a separate Owner Release Gate.
LD_SCHEMA_1: dict[str, object] = {
    "schema_version": 1,
    "record": "STI V2 Release-2 owner-assessed licence decisions LD1-LD6",
    "decided": "2026-10-13",
    "basis": "docs/V2_R2_LICENSE_DECISIONS.md",
    "assessment": "Owner-assessed internal compliance decisions with disclosed "
    "residual risks. Not an external legal certification and not a special "
    "permission from any rights holder.",
    "supplements": B1_RECORD,
    "decisions": {
        "LD1": {
            "status": LD_ASSESSED,
            "blocker": "B1",
            "decision": "The hash-pinned upstream Qt 6.11.2 and pyside-setup "
            "6.11.2 release sources and build scripts are delivered as the "
            "Corresponding Source of the unmodified official binaries (D1).",
            "residual_risk": "Exact binding producer-source correspondence is "
            "unproven; the binding wheels carry no producer build record.",
        },
        "LD2": {
            "status": LD_ASSESSED,
            "blocker": "B1",
            "decision": "In-package source archives plus GPLv3 section 6(d) "
            "equivalent access from the download location are the delivery "
            "route (D2). Download-only distribution to users' own PCs does not "
            "trigger Installation Information (D3).",
            "residual_risk": "The equivalent public access is not operational "
            "until it is published with a release.",
        },
        "LD3": {
            "status": LD_ASSESSED,
            "blocker": "B1, B4",
            "decision": "Intel's no-reverse-engineering term, scoped in writing "
            "to libiomp5md.dll and libiompstubs5md.dll, is compatible with "
            "LGPLv3 section 4 for the Qt libraries (D4).",
            "residual_risk": "The scope rests on the written notices; Intel has "
            "not confirmed it.",
        },
        "LD4": {
            "status": LD_ASSESSED,
            "blocker": "B4",
            "decision": "The two DLLs taken from Intel's pinned, author-signed "
            "NuGet package are redistributed under the Intel Simplified "
            "Software License (Version October 2022).",
            "residual_risk": "Byte-identical copies also reach the build through "
            "PyTorch under the Developer Tools EULA; certificate revocation was "
            "not checked.",
        },
        "LD5": {
            "status": LD_ASSESSED,
            "blocker": "B4",
            "decision": "intel-openmp/NOTICE.md with the package's copyright "
            "line, the full licence text and third-party-programs.txt satisfies "
            "the licence's notice condition.",
            "residual_risk": "The licence text itself carries no copyright line.",
        },
        "LD6": {
            "status": LD_ASSESSED,
            "blocker": "B4",
            "decision": "The owner accepts the licence's high-risk-use "
            "disclaimer. The oneTBB third-party file that "
            "third-party-programs.txt refers to is not required.",
            "residual_risk": "The oneTBB finding rests on the upstream oneTBB "
            "2022.3.0 build definition, not on Intel's internal build.",
        },
    },
    "b1_effect": "legal_subitems_closed_remains_open_for_public_source_access",
    "b4_effect": "intel_item_closed_for_the_pinned_package_only",
    "public_source_hosting": "not operational",
    "release_gate": "separate owner release gate required",
    "distribution_permitted": False,
}


def canonical(value: object) -> str:
    """JSON text that keeps types apart (true is not 1), for exact comparison."""
    return json.dumps(value, sort_keys=True)


def b1_owner_decision(
    legal: Path, definition: dict[str, object], versions: dict[str, str]
) -> tuple[dict[str, object], list[str]]:
    """Validate the shipped owner-decision record against the packet's evidence.

    Schema 1 must equal the approved content exactly, with a scope of the source
    manifest's Qt version and archives and exactly the two bundled binding
    packages. A valid record only narrows B1's wording; it never removes B1,
    because owner engineering approval is not legal approval.
    """
    path = legal / B1_RECORD
    if not path.is_file():
        return {"present": False}, ["the owner decision record is missing"]
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"present": True, "valid": False}, [
            "the owner decision record is malformed"
        ]
    if not isinstance(record, dict) or canonical(record.get("schema_version")) != "1":
        return {"present": True, "valid": False}, [
            "the owner decision record is not schema version 1"
        ]
    archives = {
        item["filename"]: item["sha256"]
        for item in definition["archives"]  # type: ignore[union-attr]
    }
    expected = dict(
        B1_SCHEMA_1,
        scope={
            "qt_version": definition["version"],
            "components": B1_SCHEMA_1_COMPONENTS,
            "source_archives": archives,
        },
    )
    problems = sorted(
        f"{key} differs from the approved schema 1 content"
        for key in set(expected) | set(record)
        if key not in record
        or key not in expected
        or canonical(record[key]) != canonical(expected[key])
    )
    mismatched = sorted(
        name
        for name, version in B1_SCHEMA_1_COMPONENTS.items()
        if versions.get(name.lower()) != version
    )
    if mismatched:
        problems.append(
            "the bundled binding versions differ from the record: "
            + ", ".join(mismatched)
        )
    decisions = record.get("decisions")
    return {
        "present": True,
        "valid": not problems,
        "schema_version": 1,
        "record_sha256": digest(path),
        "decided": record.get("decided"),
        "decisions": {
            key: value.get("status") if isinstance(value, dict) else None
            for key, value in (decisions.items() if isinstance(decisions, dict) else ())
        },
        "legal_confirmation": record.get("legal_confirmation"),
        "b1_effect": record.get("b1_effect"),
    }, problems


def license_decisions(
    legal: Path, definition: dict[str, object]
) -> tuple[dict[str, object], list[str]]:
    """Validate the shipped licence decision record (LD1-LD6) against its pins.

    Schema 1 must equal the approved content exactly, scoped to the source
    manifest's Qt version and archives, the two binding packages and the pinned
    Intel package. A valid record closes legal subitems only; it never removes
    B1 and never permits distribution.
    """
    path = legal / LD_RECORD
    if not path.is_file():
        return {"present": False}, ["the licence decision record is missing"]
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"present": True, "valid": False}, [
            "the licence decision record is malformed"
        ]
    if not isinstance(record, dict) or canonical(record.get("schema_version")) != "1":
        return {"present": True, "valid": False}, [
            "the licence decision record is not schema version 1"
        ]
    expected = dict(
        LD_SCHEMA_1,
        scope={
            "qt_version": definition["version"],
            "components": B1_SCHEMA_1_COMPONENTS,
            "source_archives": {
                item["filename"]: item["sha256"]
                for item in definition["archives"]  # type: ignore[union-attr]
            },
            "intel_openmp_package": INTEL_PACKAGE,
        },
    )
    problems = sorted(
        f"{key} differs from the approved schema 1 content"
        for key in set(expected) | set(record)
        if key not in record
        or key not in expected
        or canonical(record[key]) != canonical(expected[key])
    )
    decisions = record.get("decisions")
    return {
        "present": True,
        "valid": not problems,
        "schema_version": 1,
        "record_sha256": digest(path),
        "decided": record.get("decided"),
        "decisions": {
            key: value.get("status") if isinstance(value, dict) else None
            for key, value in (decisions.items() if isinstance(decisions, dict) else ())
        },
        "public_source_hosting": record.get("public_source_hosting"),
    }, problems


def distribution_blockers(
    provenance: dict[str, object],
    software_renderer: bool,
    microsoft_runtime: bool = True,
    python_runtime_verified: bool = False,
    language_model_bundled: bool = True,
    b4_remaining: Sequence[str] | None = None,
    b1_record_problems: Sequence[str] | None = None,
    decision_problems: Sequence[str] | None = None,
) -> list[str]:
    """Each blocker stays until its own evidence closes it; none grants permission.

    B4 fails closed: without a coverage check (`b4_remaining` is None) it keeps its
    general wording; with one, it names what is still open. B1 is always derived.
    A valid owner-decision record (`b1_record_problems == []`) only narrows its
    wording; a missing or invalid one is named and never narrows it. A valid
    licence decision record (`decision_problems == []`) narrows it further to
    the public source access still missing; it never removes B1.
    """
    if not provenance["qt_libraries_verified"]:
        b1 = B1_UNVERIFIED
    elif b1_record_problems is None:
        b1 = B1_BINDINGS
    elif b1_record_problems:
        b1 = (
            B1_BINDINGS
            + " Owner decision record rejected: "
            + "; ".join(b1_record_problems)
            + "."
        )
    elif decision_problems is None:
        b1 = B1_DECIDED
    elif decision_problems:
        b1 = (
            B1_DECIDED
            + " Licence decision record rejected: "
            + "; ".join(decision_problems)
            + "."
        )
    else:
        b1 = B1_ASSESSED
    blockers = [b1]
    if software_renderer:
        blockers.append(B2)
    if microsoft_runtime:
        blockers.append(B3_MICROSOFT)
    if not python_runtime_verified:
        blockers.append(B3_PYTHON)
    if b4_remaining is None:
        blockers.append(B4)
    elif b4_remaining:
        blockers.append("B4: " + "; ".join(b4_remaining) + ".")
    # B5 concerns redistributing the model; a bundle without it does not ship it.
    return blockers + ([B5] if language_model_bundled else [])


def rust_notice_coverage(
    legal: Path, versions: dict[str, str]
) -> tuple[dict[str, object], list[str]]:
    """Licence texts for every crate in the pinned source superset (B4).

    `versions` are the frozen tokenizers/safetensors versions; the index only
    covers the versions it was collected for.
    """
    index_path = legal / "rust-crates" / "index.json"
    if not index_path.is_file():
        return {"present": False}, ["Rust crate licence texts are not in the packet"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    gaps = []
    for name, version in index["binaries"].items():
        if versions.get(name) != version:
            gaps.append(
                f"the Rust crate index covers {name} {version}, not the bundled one"
            )
    missing_texts = sorted(
        {
            notice["sha256"]
            for crate in index["crates"]
            for notice in crate["notices"]
            if not (legal / "rust-crates/texts" / f"{notice['sha256']}.txt").is_file()
            or digest(legal / "rust-crates/texts" / f"{notice['sha256']}.txt")
            != notice["sha256"]
        }
    )
    uncovered = sorted(
        f"{crate['name']}@{crate['version']}"
        for crate in index["crates"]
        if not crate["notices"] and "not_linked_on_windows" not in crate
    )
    if missing_texts:
        gaps.append(
            f"{len(missing_texts)} indexed Rust licence texts are missing or changed"
        )
    if uncovered:
        gaps.append("Rust crates without a licence text: " + ", ".join(uncovered))
    summary = {
        "present": True,
        "crates": len(index["crates"]),
        "texts": len({n["sha256"] for c in index["crates"] for n in c["notices"]}),
        "not_linked_on_windows": sorted(
            c["name"] for c in index["crates"] if "not_linked_on_windows" in c
        ),
        "complete": not gaps,
    }
    return summary, gaps


def intel_package_entries(package: Path, source: dict[str, object]) -> dict[str, bytes]:
    """The pinned entries of Intel's NuGet package, or an error; nothing is guessed."""
    if package.is_symlink() or not package.is_file():
        raise ValueError("The pinned Intel OpenMP NuGet package is missing.")
    if package.stat().st_size != source["bytes"]:
        raise ValueError("The Intel OpenMP NuGet package does not match its pin.")
    data = package.read_bytes()
    sha512 = base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    if (
        len(data) != source["bytes"]
        or hashlib.sha256(data).hexdigest() != source["sha256"]
        or sha512 != source["sha512_base64"]
    ):
        raise ValueError("The Intel OpenMP NuGet package does not match its pin.")
    entries = source["entries"]
    assert isinstance(entries, dict)
    found: dict[str, bytes] = {}
    # Parse the very bytes that were hashed, not the file a second time.
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [info.filename for info in archive.infolist()]
        for name, expected in entries.items():
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or names.count(name) != 1:
                raise ValueError("A pinned Intel package entry is absent or ambiguous.")
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("A pinned Intel package entry has changed.")
            found[name] = content
    return found


def intel_openmp_status(
    bundle: Path, legal: Path, decided: bool = False
) -> tuple[dict[str, object], list[str]]:
    """The shipped Intel OpenMP DLLs must be the ones whose terms are recorded.

    The B4 Intel item closes only when `decided` (a valid licence decision
    record) and the shipped bytes, texts, notice and NuGet source all match the
    package that record names. Any other state keeps it.
    """
    record_path = legal / "intel-openmp" / "provenance.json"
    shipped = {
        name: bundle / "_internal/torch/lib" / name
        for name in INTEL_FILES
        if (bundle / "_internal/torch/lib" / name).is_file()
    }
    if not shipped:
        return {"bundled": False}, []
    if not record_path.is_file():
        return {"bundled": True, "recorded": False}, [
            "Intel OpenMP has no recorded provenance or licence text"
        ]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    expected = {
        Path(path).name: item["sha256"] for path, item in record["files"].items()
    }
    matches = all(expected.get(name) == digest(path) for name, path in shipped.items())
    licence = record["license"]
    texts = all(
        (legal / "intel-openmp" / licence[key]).is_file()
        and digest(legal / "intel-openmp" / licence[key]) == licence[key + "_sha256"]
        for key in ("text", "third_party_notices")
    )
    source = record.get("source", {})
    entries = source.get("entries", {})
    # The licence on record must be the one carried by the pinned NuGet package.
    nuget = (
        record.get("schema_version") == 2
        and source.get("channel") == "nuget"
        and licence["name"] == INTEL_LICENSE
        and entries.get("license.txt") == licence["text_sha256"]
        and licence["third_party_notices_sha256"] in entries.values()
        and all(
            entries.get(item["package_entry"]) == item["sha256"]
            for item in record["files"].values()
        )
    )
    gaps = []
    if not matches:
        gaps.append("the bundled Intel OpenMP DLLs differ from the recorded provenance")
    if not texts:
        gaps.append("the Intel OpenMP licence texts are missing or changed")
    if not nuget:
        gaps.append("the Intel OpenMP record does not name the pinned NuGet source")
    notice = (legal / "intel-openmp" / licence.get("notice", "NOTICE.md")).is_file()
    if not notice:
        gaps.append("the Intel OpenMP notice is missing")
    package = {
        "id": source.get("package_id"),
        "version": source.get("version"),
        "sha256": source.get("sha256"),
    }
    # Engineering evidence cannot settle the licence's redistribution conditions;
    # only the owner's decisions on this exact package can (LD3-LD6).
    assessed = decided and package == INTEL_PACKAGE and not gaps
    if not assessed:
        gaps.append(B4_INTEL)
    return {
        "bundled": True,
        "recorded": True,
        "matches_provenance": matches,
        "nuget_source_recorded": nuget,
        "source_package": f"{source.get('package_id')} {source.get('version')}",
        "license": licence["name"],
        "texts_present": texts,
        "notice_present": notice,
        "owner_assessed": assessed,
        "redistribution": record["redistribution"]["status"],
    }, gaps


def verify_intel_source(bundle: Path, source_dir: Path, legal: Path) -> None:
    """Bundled Intel DLLs must be the bytes of the pinned, verified NuGet package."""
    shipped = [bundle / "_internal/torch/lib" / name for name in INTEL_FILES]
    if not any(path.is_file() for path in shipped):
        return
    record = json.loads(
        (legal / "intel-openmp/provenance.json").read_text(encoding="utf-8")
    )
    entries = intel_package_entries(
        source_dir / record["source"]["filename"], record["source"]
    )
    for path, item in record["files"].items():
        if (bundle / path).read_bytes() != entries[item["package_entry"]]:
            raise ValueError("A bundled Intel DLL is not the NuGet package's copy.")


def verify_python_runtime(
    bundle: Path, manifest: dict[str, object]
) -> dict[str, object]:
    """Bundled CPython natives and the shipped licence must be the pinned files."""
    files = manifest["files"]
    assert isinstance(files, dict)
    expected = {Path(name).name.lower(): sha for name, sha in files.items()}
    internal = bundle / "_internal"
    rows, unpinned = [], []
    for path in sorted(internal.iterdir()) if internal.is_dir() else []:
        if not path.is_file() or path.suffix.lower() not in {".pyd", ".dll"}:
            continue
        if native_owner("_internal/" + path.name).startswith("CPython"):
            pinned = expected.get(path.name.lower())
            if pinned is None:
                unpinned.append(path.name)
            else:
                rows.append({"file": path.name, "matches": digest(path) == pinned})
    licence = bundle / "legal" / "PYTHON-LICENSE.txt"
    licence_matches = licence.is_file() and digest(licence) == files.get("LICENSE.txt")
    return {
        "version": manifest.get("version"),
        "build": manifest.get("build"),
        "checked": rows,
        "unpinned_cpython_files": unpinned,
        "licence_matches": licence_matches,
        "verified": bool(rows)
        and all(row["matches"] for row in rows)
        and not unpinned
        and licence_matches,
    }


def language_model_status(bundle: Path) -> dict[str, object]:
    """Whether py3langid's statistical model is redistributed in this bundle.

    Only the redistribution question is answered here. The training-corpus terms
    stay unverified either way (M10-E2 section 2.5).
    """
    stray = sorted(
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("model.npz.xz")
        if path.is_file()
    )
    bundled = bool(stray)
    return {
        "bundled": bundled,
        "files": stray,
        "distribution": (
            "redistributed in this bundle"
            if bundled
            else "not redistributed; the user may install it from upstream "
            "(adbar/py3langid at the v0.4.0 commit, SHA-256 pinned)"
        ),
        "training_corpus_terms": "not verified",
    }


def installed_notices(name: str, output: Path) -> list[dict[str, str]]:
    distribution = importlib.metadata.distribution(name)
    output.mkdir(parents=True, exist_ok=True)
    notices = []
    for item in distribution.files or ():
        basename = item.name.lower()
        if not (
            "/licenses/" in item.as_posix().lower()
            # Wheel-embedded CycloneDX SBOMs list compiled Rust dependencies.
            or "/sboms/" in item.as_posix().lower()
            or basename.startswith(("license", "copying", "copyright"))
            or basename in {"notice", "notice.txt"}
        ):
            continue
        path = Path(distribution.locate_file(item))
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        target = checksum + ".txt"
        (output / target).write_bytes(data)
        notices.append(
            {"upstream_path": item.as_posix(), "file": target, "sha256": checksum}
        )
    return notices


def native_owner(relative: str) -> str:
    path = relative.lower()
    name = path.rsplit("/", 1)[-1]
    if "pyside6/" in path:
        return "Software renderer (B2)" if name == "opengl32sw.dll" else "Qt/PySide6"
    if "shiboken6/" in path:
        return "shiboken6"
    if name.startswith(("msvcp", "vcruntime", "concrt", "vccorlib")):
        return "Microsoft runtime (B3)"
    for prefix, owner in (
        ("numpy", "NumPy/OpenBLAS"),
        ("torch/", "PyTorch/native dependencies (B4)"),
        ("hf_xet/", "hf-xet/Rust dependencies (B4)"),
        ("tokenizers/", "tokenizers/Rust dependencies (B4)"),
        ("safetensors/", "safetensors/Rust dependencies (B4)"),
        ("markupsafe/", "MarkupSafe"),
        ("yaml/", "PyYAML"),
        ("regex/", "regex"),
    ):
        if path.removeprefix("_internal/").startswith(prefix):
            return owner
    if name.startswith(("python", "libcrypto", "libssl", "libffi", "sqlite")):
        return "CPython/runtime bundled dependencies (B3)"
    if name.endswith(".pyd") and path.count("/") == 1:
        return "CPython standard-library extensions (B3)"
    if name in {"sti-check.exe", "sti-desktop.exe"}:
        return "STI/PyInstaller bootloader"
    return "UNRESOLVED native ownership"


def loose_python_packages(bundle: Path) -> set[str]:
    """Top-level names of Python sources shipped as files rather than in the PYZ.

    `module_collection_mode="py"`/`"pyc"` (PySide6/shiboken6) and hook-collected
    sources leave no PYZ entry; their owners still need a version-matched audit.
    """
    internal = bundle / "_internal"
    return {
        path.relative_to(internal).parts[0].removesuffix(path.suffix)
        for path in internal.rglob("*")
        if path.is_file() and path.suffix.lower() in {".py", ".pyc"}
    }


def python_owners(
    bundle: Path, pyz_modules: set[str], mapping: dict[str, list[str]], stdlib: set[str]
) -> tuple[set[str], list[str], set[str]]:
    """Owners of every delivered Python module, in the PYZ or as loose files.

    Fails closed: an owner without a version-matched register entry stops packet
    assembly, and a loose name with no owner becomes an unmapped-owner blocker.
    """
    loose = loose_python_packages(bundle)
    owners, unknown = module_owners(pyz_modules | loose, mapping, stdlib)
    return owners, unknown, loose


def module_owners(
    modules: set[str], mapping: dict[str, list[str]], stdlib: set[str]
) -> tuple[set[str], list[str]]:
    """Resolve module ownership, including PyInstaller's installed fake module."""
    owners: set[str] = {"PyInstaller"}
    unknown = []
    for top in sorted({name.split(".")[0] for name in modules}):
        if top == "_pyi_rth_utils":
            # PyInstaller/fake-modules/_pyi_rth_utils; Apache-2.0 in COPYING.txt.
            owners.add("PyInstaller")
        elif top in mapping:
            owners.update(mapping[top])
        elif top not in stdlib:
            unknown.append(top)
    return owners, unknown


def assemble(
    bundle: Path, source_dir: Path, project: Path, application_revision: str
) -> dict[str, object]:
    """Inventory actual frozen modules, binaries, installed notices and sources."""
    from PyInstaller.archive.readers import CArchiveReader

    definition = json.loads((project / "distribution/source-manifest.json").read_text())
    archives = [
        SourceArchive(item["component"], item["filename"], item["sha256"], item["url"])
        for item in definition["archives"]
    ]
    legal = bundle / "legal"
    if legal.exists():
        raise ValueError("Existing legal packet is preserved; use a fresh build.")
    source_receipts = stage_sources(source_dir, legal / "sources", archives)
    source_notices = collect_source_notices(
        [legal / "sources" / entry.filename for entry in archives], legal / "qt-notices"
    )
    provenance_definition = json.loads(
        (project / "distribution/qt-binary-provenance.json").read_text()
    )
    sboms = [
        SourceArchive(item["component"], item["filename"], item["sha256"], item["url"])
        for item in provenance_definition["documents"]
    ]
    sbom_receipts = stage_sources(source_dir, legal / "qt-sbom", sboms)
    provenance = verify_qt_provenance(
        bundle,
        [legal / "qt-sbom" / entry.filename for entry in sboms],
        [legal / "sources" / entry.filename for entry in archives],
    )
    for path in (project / "distribution/legal").rglob("*"):
        if path.is_file():
            target = legal / path.relative_to(project / "distribution/legal")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    verify_intel_source(bundle, source_dir, legal)
    shutil.copyfile(project / "LICENSE", legal / "STI-LICENSE.txt")
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", legal / "PYTHON-LICENSE.txt")
    mapping = importlib.metadata.packages_distributions()
    modules: set[str] = set()
    for executable in ("sti-desktop.exe", "sti-check.exe"):
        archive = CArchiveReader(str(bundle / executable))
        embedded = archive.open_embedded_archive("PYZ.pyz")
        modules.update(embedded.toc)
    stdlib = sys.stdlib_module_names | {"social_text_intelligence"}
    mapping.pop("social_text_intelligence", None)
    names, unmapped, loose = python_owners(bundle, modules, dict(mapping), stdlib)
    register = json.loads(
        (project / "distribution/component-register.json").read_text()
    )
    approved = {
        item["name"].lower().replace("_", "-"): item for item in register["components"]
    }
    components = []
    for name in sorted(names, key=str.lower):
        dist = importlib.metadata.distribution(name)
        metadata = dist.metadata
        safe_name = re.sub(r"[^a-z0-9.-]", "-", name.lower())
        notices = installed_notices(name, legal / "packages" / safe_name)
        audit = approved.get(name.lower().replace("_", "-"))
        if audit is None or audit["version"] != dist.version:
            raise ValueError("Frozen component has no version-matched license audit.")
        components.append(
            {
                "name": metadata["Name"],
                "version": dist.version,
                "license_expression": metadata.get("License-Expression"),
                "license_metadata": metadata.get("License"),
                "license_notices": notices,
                "audit": audit,
            }
        )
    files = [
        {
            "path": path.relative_to(bundle).as_posix(),
            "sha256": digest(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    ]
    native = [
        dict(item, owner=native_owner(str(item["path"])))
        for item in files
        if Path(str(item["path"])).suffix.lower() in {".dll", ".pyd", ".exe"}
    ]
    python_runtime = verify_python_runtime(
        bundle,
        json.loads((project / "distribution/python-runtime.json").read_text()),
    )
    language_model = language_model_status(bundle)
    versions = {str(item["name"]).lower(): str(item["version"]) for item in components}
    rust_notices, rust_gaps = rust_notice_coverage(legal, versions)
    decisions, decision_problems = license_decisions(legal, definition)
    decisions["problems"] = decision_problems
    intel_openmp, intel_gaps = intel_openmp_status(
        bundle, legal, decided=not decision_problems
    )
    b1_decision, b1_problems = b1_owner_decision(legal, definition, versions)
    b1_decision["problems"] = b1_problems
    torch_notices = next(
        (
            len(item["license_notices"])
            for item in components
            if item["name"] == "torch"
        ),
        0,
    )
    torch_gaps = (
        []
        if torch_notices
        else ["PyTorch's upstream third_party licence files are missing"]
    )
    b4_remaining = rust_gaps + intel_gaps + torch_gaps
    b4 = {
        "rust_crates": rust_notices,
        "intel_openmp": intel_openmp,
        # Plan revision 2 section 5 keeps PyTorch's static content at this level.
        "pytorch_static_third_party": {
            "coverage": "upstream third_party licence superset from the torch wheel",
            "notice_files": torch_notices,
        },
        "remaining": b4_remaining,
    }
    blockers = distribution_blockers(
        provenance,
        (bundle / "_internal/PySide6/opengl32sw.dll").exists(),
        microsoft_runtime=any(
            item["owner"] == "Microsoft runtime (B3)" for item in native
        ),
        python_runtime_verified=bool(python_runtime["verified"]),
        language_model_bundled=bool(language_model["bundled"]),
        b4_remaining=b4_remaining,
        b1_record_problems=b1_problems,
        decision_problems=decision_problems,
    )
    if any(item["owner"] == "UNRESOLVED native ownership" for item in native):
        blockers.append(
            "Unresolved native ownership exists; inspect native_components."
        )
    if unmapped:
        blockers.append("Unmapped frozen module owners: " + ", ".join(unmapped))
    for item in components:
        if not item["license_notices"] and item["name"] != "tokenizers":
            blockers.append("Missing installed license text: " + str(item["name"]))
    inventory: dict[str, object] = {
        "schema_version": 1,
        "distribution_permitted": False,
        "blockers": blockers,
        "python_version": sys.version.split()[0],
        "qt_version": definition["version"],
        "application_revision": application_revision,
        "modules": sorted(modules),
        "loose_python_packages": sorted(loose),
        "native_components": native,
        "components": components,
        "source_delivery": source_receipts,
        "qt_build_sboms": sbom_receipts,
        "qt_binary_provenance": provenance,
        "python_runtime": python_runtime,
        "language_model": language_model,
        "b4_coverage": b4,
        "b1_owner_decision": b1_decision,
        "license_decisions": decisions,
        "qt_source_notices": source_notices,
        "notice_scope": "source superset; not a compiled static-link SBOM",
        "materials": files,
    }
    (legal / "inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--application-sha")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            inventory = json.loads((args.bundle / "legal/inventory.json").read_text())
        elif args.source_dir:
            if not args.application_sha or not re.fullmatch(
                r"[0-9a-f]{40}", args.application_sha
            ):
                print("Application revision must be a 40-character Git SHA.")
                return 2
            inventory = assemble(
                args.bundle,
                args.source_dir,
                Path(__file__).parents[2],
                args.application_sha,
            )
        else:
            raise ValueError("A verified local source directory is required.")
        result = verify_packet(args.bundle, inventory)
        print(json.dumps(result))
        return 0 if result["materials_valid"] else 2
    except (OSError, ValueError, KeyError):
        print(
            "License/source material validation failed; distribution remains blocked."
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
