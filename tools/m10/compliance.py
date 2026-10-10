"""Offline license/source packet assembly; never grants distribution approval."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


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


def verify_packet(root: Path, inventory: dict[str, object]) -> dict[str, object]:
    """Structural integrity is separate from permission to distribute."""
    valid = True
    materials = inventory.get("materials")
    if not isinstance(materials, list) or not materials:
        valid = False
    else:
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


BLOCKERS = [
    "B1: Exact Qt/PySide binary corresponding source, modifications and build recipes "
    "are not established by upstream release archives alone.",
    "B2: opengl32sw software renderer build provenance and compiled Mesa/LLVM "
    "component attribution are unverified.",
    "B3: Microsoft runtime redistribution grant and custom CPython runtime/native "
    "build provenance are not verified.",
    "B4: Static Rust/native and vendored dependency license coverage is not "
    "certified by package-level metadata or source-superset notices.",
    "B5: py3langid embedded model training-corpus redistribution terms remain open.",
]


def installed_notices(name: str, output: Path) -> list[dict[str, str]]:
    distribution = importlib.metadata.distribution(name)
    output.mkdir(parents=True, exist_ok=True)
    notices = []
    for item in distribution.files or ():
        basename = item.name.lower()
        if not (
            "/licenses/" in item.as_posix().lower()
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
    if "msvcp" in name or "vcruntime" in name:
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


def assemble(bundle: Path, source_dir: Path, project: Path) -> dict[str, object]:
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
    for path in (project / "distribution/legal").rglob("*"):
        if path.is_file():
            target = legal / path.relative_to(project / "distribution/legal")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    shutil.copyfile(project / "LICENSE", legal / "STI-LICENSE.txt")
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", legal / "PYTHON-LICENSE.txt")
    names: set[str] = set()
    mapping = importlib.metadata.packages_distributions()
    modules: set[str] = set()
    for executable in ("sti-desktop.exe", "sti-check.exe"):
        archive = CArchiveReader(str(bundle / executable))
        embedded = archive.open_embedded_archive("PYZ.pyz")
        modules.update(embedded.toc)
    unmapped = []
    stdlib = sys.stdlib_module_names | {"social_text_intelligence"}
    for top in sorted({name.split(".")[0] for name in modules}):
        if top == "social_text_intelligence":
            continue
        distributions = mapping.get(top)
        if distributions:
            names.update(distributions)
        elif top not in stdlib:
            unmapped.append(top)
    names.add("PyInstaller")
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
    blockers = list(BLOCKERS)
    native = [
        dict(item, owner=native_owner(str(item["path"])))
        for item in files
        if Path(str(item["path"])).suffix.lower() in {".dll", ".pyd", ".exe"}
    ]
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
        "application_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project, text=True
        ).strip(),
        "modules": sorted(modules),
        "native_components": native,
        "components": components,
        "source_delivery": source_receipts,
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
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            inventory = json.loads((args.bundle / "legal/inventory.json").read_text())
        elif args.source_dir:
            inventory = assemble(
                args.bundle, args.source_dir, Path(__file__).parents[2]
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
