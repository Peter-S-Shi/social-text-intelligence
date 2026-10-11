"""Repeatable Windows onedir build; always writes a new output, never deletes one."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import vc_runtime

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent
# Visual C++ runtime DLLs are Microsoft redistributables. Route R1 relies on the
# system runtime (M10-E2, blocker B3); route R2 ships only the pinned copies from
# a licensed Visual Studio VC\Redist folder in _internal, beside python313.dll
# (M10-E3).
MICROSOFT_RUNTIME = re.compile(
    r"(msvcp140|vcruntime140|concrt140|vccorlib140)([_-][0-9a-z_]+)?\.dll", re.I
)
APP_LOCAL_DIRECTORY = "_internal"
VENDORED_RUNTIME = re.compile(r"msvcp140-[0-9a-f]{32}\.dll", re.I)


def prepare_output(output: Path) -> Path:
    if output.exists() or output.is_symlink():
        raise ValueError(
            "A new output directory is required; existing data is preserved."
        )
    if len(str(output.resolve())) > 60:
        raise ValueError("Use a short output directory (60 characters maximum).")
    output.mkdir(parents=True, exist_ok=False)
    return output.resolve()


def audit_bundle(root: Path) -> dict[str, int]:
    files = [path for path in root.rglob("*") if path.is_file()]
    if not files:
        raise ValueError("Empty packaging output.")
    for path in files:
        if path.suffix.lower() in {".safetensors", ".db", ".sqlite", ".sqlite3"} or (
            path.name.lower() in {"pytorch_model.bin", ".env"}
        ):
            raise ValueError("Packaging output contains forbidden model or user data.")
    for name in ("sti-desktop.exe", "sti-check.exe"):
        if not (root / name).is_file():
            raise ValueError("Required packaging entry is absent.")
    return {"files": len(files), "bytes": sum(path.stat().st_size for path in files)}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


IMPORT_DIRECTORY, DELAY_IMPORT_DIRECTORY = 1, 13


@dataclass(frozen=True)
class PeImage:
    """Minimal read-only view of a PE image's headers and section mapping."""

    data: bytes
    wide: bool
    image_base: int
    directory_count: int
    directories: int
    sections: tuple[tuple[int, int, int, int], ...]

    @classmethod
    def parse(cls, data: bytes) -> PeImage:
        try:
            header = struct.unpack_from("<I", data, 0x3C)[0]
            if data[:2] != b"MZ" or data[header : header + 4] != b"PE\0\0":
                raise ValueError("Not a PE image.")
            count, optional_size = struct.unpack_from("<H12xH", data, header + 6)
            optional = header + 24
            wide = struct.unpack_from("<H", data, optional)[0] == 0x20B
            image_base = struct.unpack_from(
                "<Q" if wide else "<I", data, optional + (24 if wide else 28)
            )[0]
            directories = optional + (112 if wide else 96)
            directory_count = struct.unpack_from("<I", data, directories - 4)[0]
            sections = tuple(
                struct.unpack_from("<8xIIII", data, optional + optional_size + 40 * i)
                for i in range(count)
            )
        except struct.error as error:
            raise ValueError("Not a PE image.") from error
        return cls(data, wide, image_base, directory_count, directories, sections)

    def directory(self, index: int) -> int:
        """RVA of a data directory, or 0 when the image has none."""
        if index >= self.directory_count:
            return 0
        return int(struct.unpack_from("<I", self.data, self.directories + 8 * index)[0])

    def offset(self, rva: int) -> int:
        # Only file-backed bytes can be read; virtual-only tails are not mapped.
        for _, address, raw_size, raw in self.sections:
            if address <= rva < address + raw_size:
                return raw + rva - address
        raise ValueError("RVA outside every section.")

    def string(self, at: int) -> str:
        return self.data[at : self.data.index(b"\0", at)].decode("ascii")


def import_names(data: bytes) -> list[tuple[int, str]]:
    """(file offset, DLL name) of every ordinary and delay-loaded import."""
    try:
        image = PeImage.parse(data)
        names = []
        rva = image.directory(IMPORT_DIRECTORY)
        descriptor = image.offset(rva) if rva else -1
        while rva and any(struct.unpack_from("<5I", data, descriptor)):
            at = image.offset(struct.unpack_from("<I", data, descriptor + 12)[0])
            names.append((at, image.string(at)))
            descriptor += 20
        rva = image.directory(DELAY_IMPORT_DIRECTORY)
        descriptor = image.offset(rva) if rva else -1
        while rva and any(struct.unpack_from("<8I", data, descriptor)):
            attributes, name = struct.unpack_from("<II", data, descriptor)
            # Old-style descriptors hold virtual addresses instead of RVAs.
            at = image.offset(name if attributes & 1 else name - image.image_base)
            names.append((at, image.string(at)))
            descriptor += 32
        return names
    except (struct.error, UnicodeDecodeError) as error:
        raise ValueError("Unreadable PE import directory.") from error


def relink_vendored_runtime(bundle: Path) -> list[dict[str, str]]:
    """Point delvewheel-renamed msvcp140 imports back at the shared msvcp140.dll.

    That is the system runtime (R1) or the pinned app-local copy (R2). The rename is
    the same in-place import-name edit delvewheel made; the vendored Microsoft copy
    itself is not shipped. Every edit is returned as a receipt.
    """
    receipts = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".pyd", ".dll"}:
            continue
        data = bytearray(path.read_bytes())
        names = [
            item
            for item in import_names(bytes(data))
            if VENDORED_RUNTIME.fullmatch(item[1])
        ]
        if not names:
            continue
        before = hashlib.sha256(data).hexdigest()
        for at, name in names:
            data[at : at + len(name)] = b"msvcp140.dll".ljust(len(name), b"\0")
        path.write_bytes(data)
        receipts.append(
            {
                "path": path.relative_to(bundle).as_posix(),
                "replaced_imports": ", ".join(name for _, name in names),
                "before_sha256": before,
                "after_sha256": digest(path),
            }
        )
    return receipts


def verify_no_microsoft_runtime(
    bundle: Path, app_local: dict[str, str] | None = None
) -> None:
    """No runtime file at all (R1), or exactly the pinned ones in _internal (R2)."""
    pinned = {name.lower(): sha for name, sha in (app_local or {}).items()}
    for path in bundle.rglob("*"):
        if (
            path.is_file()
            and MICROSOFT_RUNTIME.fullmatch(path.name)
            and (
                path.parent != bundle / APP_LOCAL_DIRECTORY
                or pinned.get(path.name.lower()) != digest(path)
            )
        ):
            raise ValueError("A Microsoft Visual C++ runtime file was bundled.")
        if (
            path.is_file()
            and path.suffix.lower() in {".pyd", ".dll", ".exe"}
            and any(
                VENDORED_RUNTIME.fullmatch(name)
                for _, name in import_names(path.read_bytes())
            )
        ):
            raise ValueError("A binary still imports a vendored runtime copy.")


def runtime_imports(bundle: Path) -> dict[str, int]:
    """Microsoft runtime DLL names the bundle's native files import, with counts."""
    counts: dict[str, int] = {}
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".pyd", ".dll", ".exe"}:
            for name in {n.lower() for _, n in import_names(path.read_bytes())}:
                if MICROSOFT_RUNTIME.fullmatch(name):
                    counts[name] = counts.get(name, 0) + 1
    return counts


def stage_app_local_runtime(
    bundle: Path, folder: Path, manifest: dict[str, object]
) -> list[dict[str, str]]:
    """Copy the verified pinned runtime into _internal (route R2).

    The bootloader loads _internal/python313.dll with LOAD_WITH_ALTERED_SEARCH_PATH,
    which searches that DLL's own folder instead of the executable's folder. Later
    loads reuse the already-loaded modules or find _internal, the bootloader's DLL
    directory. runtime_origins.ps1 measures where each module really came from.
    """
    receipts = vc_runtime.verify_source(folder, manifest)
    imported = set(runtime_imports(bundle))
    required = {name.lower() for name in vc_runtime.required_files(manifest)}
    if not imported <= required:
        raise ValueError("The bundle imports a runtime file outside the pinned set.")
    for item in receipts:
        target = bundle / APP_LOCAL_DIRECTORY / item["file"]
        if target.exists():
            raise ValueError("A runtime file already exists in the bundle.")
        target.write_bytes((folder / item["file"]).read_bytes())
        if digest(target) != item["sha256"]:
            raise ValueError("A staged runtime file differs from its pin.")
    return receipts


def runtime_mismatches(base: Path, manifest: dict[str, object]) -> list[str]:
    """Files of the build interpreter that differ from the pinned official runtime."""
    files = manifest["files"]
    assert isinstance(files, dict)
    mismatched = []
    for relative, expected in sorted(files.items()):
        path = base / relative
        if not path.is_file() or digest(path) != expected:
            mismatched.append(relative)
    return mismatched


def verify_build_environment() -> None:
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError("The production build requires Windows x64.")
    if sys.version_info[:2] != (3, 13):
        raise ValueError("The production build requires Python 3.13.")
    manifest = json.loads((ROOT / "distribution/python-runtime.json").read_text())
    if runtime_mismatches(Path(sys.base_prefix), manifest):
        raise ValueError(
            "The build interpreter must be the pinned official CPython runtime."
        )
    for line in (CONFIG / "requirements-build.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        if importlib.metadata.version(name) != expected:
            raise ValueError(
                "Build dependency versions must match the pinned manifest."
            )


def source_revision(root: Path = ROOT) -> str:
    paths = (
        "src",
        "tools/m10",
        "distribution",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
    )
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=root,
        text=True,
    )
    if status.strip():
        raise ValueError("Packaging inputs must be committed before building.")
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def build_environment(output: Path) -> dict[str, str]:
    """Keep unrelated host native tools and caches out of dependency analysis."""
    environment = dict(os.environ)
    system = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
    environment["PATH"] = os.pathsep.join(
        str(path)
        for path in (
            Path(sys.executable).parent,
            Path(sys.base_prefix),
            system / "System32",
            system,
        )
    )
    for name in ("QT_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        environment.pop(name, None)
    environment.update(
        PYTHONPATH=str(ROOT / "src"),
        PYTHONNOUSERSITE="1",
        HF_HOME=str(output / "build-hub-cache"),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    return environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--runtime-route",
        choices=("r1", "r2"),
        default="r1",
        help="r1: system Visual C++ runtime; r2: pinned app-local runtime",
    )
    parser.add_argument(
        "--vs-install",
        type=Path,
        help="r2 only: the licensed Visual Studio installation to copy from",
    )
    args = parser.parse_args()
    try:
        if (args.runtime_route == "r2") != (args.vs_install is not None):
            raise ValueError("--vs-install is required for, and only for, route r2.")
        app_local: dict[str, str] | None = None
        if args.runtime_route == "r2":
            vc_manifest = vc_runtime.load_manifest()
            version, folder = vc_runtime.redist_directory(args.vs_install)
            if vc_manifest["redist_version"] is None:
                raise ValueError("The app-local runtime is not pinned yet (run --pin).")
            if version != vc_manifest["redist_version"]:
                raise ValueError("The installed redistributable is not the pinned one.")
            vc_runtime.verify_source(folder, vc_manifest)
        verify_build_environment()
        sha = source_revision()
        output = prepare_output(args.output)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--distpath",
                str(output / "dist"),
                "--workpath",
                str(output / "work"),
                str(CONFIG / "sti_desktop.spec"),
            ],
            cwd=ROOT,
            check=True,
            env=build_environment(output),
        )
        bundle = output / "dist" / "sti-desktop"
        relinked = relink_vendored_runtime(bundle)
        verify_no_microsoft_runtime(bundle)
        imported = runtime_imports(bundle)
        staged: list[dict[str, str]] = []
        if args.runtime_route == "r2":
            staged = stage_app_local_runtime(bundle, folder, vc_manifest)
            app_local = {item["file"]: item["sha256"] for item in staged}
            verify_no_microsoft_runtime(bundle, app_local)
        subprocess.run(
            [
                sys.executable,
                str(CONFIG / "compliance.py"),
                "--bundle",
                str(bundle),
                "--source-dir",
                str(args.source_dir),
                "--application-sha",
                sha,
            ],
            cwd=ROOT,
            check=True,
            env=build_environment(output),
        )
        layout = audit_bundle(bundle)
        if source_revision() != sha:
            raise ValueError("Packaging inputs changed during the build.")
        evidence = {
            "schema_version": 1,
            "application_sha": sha,
            "python": platform.python_version(),
            "platform": "windows-x64",
            "spec_sha256": hashlib.sha256(
                (CONFIG / "sti_desktop.spec").read_bytes()
            ).hexdigest(),
            "requirements_sha256": hashlib.sha256(
                (CONFIG / "requirements-build.txt").read_bytes()
            ).hexdigest(),
            "layout": layout,
            "python_runtime": json.loads(
                (ROOT / "distribution/python-runtime.json").read_text()
            )["build"],
            "microsoft_runtime_route": args.runtime_route.upper(),
            "microsoft_runtime_redistributed": bool(staged),
            "microsoft_runtime_imports": imported,
            "app_local_runtime": staged,
            "relinked_runtime_imports": relinked,
            "models_bundled": False,
            "release_ready": False,
        }
        (output / "build-evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
        print("Windows onedir build complete; distribution gates remain open.")
        return 0
    except ValueError as error:
        print(str(error))
        return 2
    except (
        OSError,
        subprocess.SubprocessError,
        importlib.metadata.PackageNotFoundError,
    ):
        print("Build failed; check pinned dependencies and the private build log.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
