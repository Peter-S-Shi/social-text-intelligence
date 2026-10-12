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

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent
# Visual C++ runtime DLLs are Microsoft redistributables; the bundle relies on the
# system runtime instead (M10-E2, blocker B3).
MICROSOFT_RUNTIME = re.compile(
    r"(msvcp140|vcruntime140|concrt140|vccorlib140)([_-][0-9a-z_]+)?\.dll", re.I
)
VENDORED_RUNTIME = re.compile(r"msvcp140-[0-9a-f]{32}\.dll", re.I)
EXECUTABLES = ("sti-desktop.exe", "sti-check.exe")
# truststore verifies every model download (M10 S5-NET-001). Install it with
# requirements-truststore.txt, which hash-locks the reviewed PyPI wheel; each
# installed file below must still match that wheel byte for byte.
TRUSTSTORE_FILES = {
    "truststore/__init__.py": (
        "06eee4aa49a9ba784bb23e710aef204ffdb992da0f5dc4a7c1ef151e4d46989a"
    ),
    "truststore/_api.py": (
        "0910c84046483677663181b1c1b9f5db1ce5baddf89b4e9ed94248d8846a232e"
    ),
    "truststore/_macos.py": (
        "9d994b90e9accd413483aaf2470055198e423b33f2b9d72c889b4359aacce4b4"
    ),
    "truststore/_openssl.py": (
        "cc1f9242f272764b3bb50d32230acfe860f77d035249a3e2abbcf0e321794f8d"
    ),
    "truststore/_ssl_constants.py": (
        "3540f87d529d483d36ae2efe75bd2d9ced15a8b3fd687bb3992b5c5bbb40974f"
    ),
    "truststore/_windows.py": (
        "ac01f22980fc33bb7e6d77c6f1580e55add3a5f85585bb78ad94253b8e58b8ff"
    ),
    "truststore-0.10.4.dist-info/licenses/LICENSE": (
        "33be7b7e8fa4fd19b1760e1a8ed8a668bdab852c91b692dd41424bcb725a9fca"
    ),
}


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
    for name in EXECUTABLES:
        if not (root / name).is_file():
            raise ValueError("Required packaging entry is absent.")
    return {"files": len(files), "bytes": sum(path.stat().st_size for path in files)}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


IMPORT_DIRECTORY, DELAY_IMPORT_DIRECTORY, RESOURCE_DIRECTORY = 1, 13, 2
RT_ICON = 3
# The approved application icon (M10 S5-UI-001) and the sizes it must carry.
APPLICATION_ICON = ROOT / "src/social_text_intelligence/desktop/qt/resources/sti.ico"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 256)


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


def ico_images(data: bytes) -> list[tuple[int, bytes]]:
    """(pixel size, image bytes) of every ICO entry; 256 is stored as 0."""
    try:
        reserved, kind, count = struct.unpack_from("<HHH", data)
        if (reserved, kind) != (0, 1) or count == 0:
            raise ValueError("Not an icon file.")
        images = []
        for index in range(count):
            width, height, _, _, _, _, size, offset = struct.unpack_from(
                "<BBBBHHII", data, 6 + 16 * index
            )
            if width != height or offset + size > len(data):
                raise ValueError("Malformed icon entry.")
            images.append((width or 256, data[offset : offset + size]))
        return images
    except struct.error as error:
        raise ValueError("Not an icon file.") from error


def verify_icon_file(path: Path = APPLICATION_ICON) -> list[bytes]:
    """The approved icon, with exactly the required sizes; otherwise the build fails."""
    if not path.is_file():
        raise ValueError("The application icon is missing; the build is refused.")
    images = ico_images(path.read_bytes())
    if sorted(size for size, _ in images) != sorted(ICON_SIZES):
        raise ValueError("The application icon lacks or adds a required size.")
    return [image for _, image in images]


def icon_resources(data: bytes) -> list[bytes]:
    """The RT_ICON images embedded in a PE image."""

    def entries(at: int) -> list[tuple[int, int]]:
        named, numbered = struct.unpack_from("<12xHH", data, at)
        return [
            struct.unpack_from("<II", data, at + 16 + 8 * i)
            for i in range(named + numbered)
        ]

    try:
        image = PeImage.parse(data)
        rva = image.directory(RESOURCE_DIRECTORY)
        if not rva:
            return []
        root = image.offset(rva)
        images = []
        for kind, types in entries(root):
            if kind != RT_ICON or not types & 0x80000000:
                continue
            for _, names in entries(root + (types & 0x7FFFFFFF)):
                for _, leaf in entries(root + (names & 0x7FFFFFFF)):
                    at, size = struct.unpack_from("<II", data, root + leaf)
                    start = image.offset(at)
                    images.append(data[start : start + size])
        return images
    except struct.error as error:
        raise ValueError("Unreadable PE resource directory.") from error


def verify_executable_icons(bundle: Path, path: Path = APPLICATION_ICON) -> None:
    """Both executables must embed exactly the approved icon's images."""
    expected = sorted(verify_icon_file(path))
    for name in EXECUTABLES:
        if sorted(icon_resources((bundle / name).read_bytes())) != expected:
            raise ValueError(f"{name} does not embed the approved application icon.")
    shipped = bundle / "_internal/social_text_intelligence/desktop/qt/resources"
    if digest(shipped / "sti.ico") != digest(path):
        raise ValueError("The bundle does not ship the approved application icon.")


def relink_vendored_runtime(bundle: Path) -> list[dict[str, str]]:
    """Point delvewheel-renamed msvcp140 imports back at the system runtime.

    The rename is the same in-place import-name edit delvewheel made; the vendored
    Microsoft copy itself is not shipped. Every edit is returned as a receipt.
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


def verify_no_microsoft_runtime(bundle: Path) -> None:
    for path in bundle.rglob("*"):
        if path.is_file() and MICROSOFT_RUNTIME.fullmatch(path.name):
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


def installed_mismatches(name: str, pinned: dict[str, str]) -> list[str]:
    """Pinned files of an installed distribution whose bytes differ or are absent."""
    distribution = importlib.metadata.distribution(name)
    actual = {
        item.as_posix(): hashlib.sha256(
            Path(distribution.locate_file(item)).read_bytes()
        ).hexdigest()
        for item in distribution.files or ()
        if item.as_posix() in pinned
    }
    return sorted(path for path, digest in pinned.items() if actual.get(path) != digest)


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
    if installed_mismatches("truststore", TRUSTSTORE_FILES):
        raise ValueError("truststore must be installed from the reviewed wheel.")


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
    args = parser.parse_args()
    try:
        verify_build_environment()
        verify_icon_file()
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
        verify_executable_icons(bundle)
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
            "application_icon_sha256": digest(APPLICATION_ICON),
            "layout": layout,
            "python_runtime": json.loads(
                (ROOT / "distribution/python-runtime.json").read_text()
            )["build"],
            "microsoft_runtime_redistributed": False,
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
        subprocess.CalledProcessError,
        importlib.metadata.PackageNotFoundError,
    ):
        print("Build failed; check pinned dependencies and the private build log.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
