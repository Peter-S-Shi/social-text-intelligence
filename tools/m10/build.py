"""Repeatable Windows onedir build; always writes a new output, never deletes one."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent


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


def verify_build_environment() -> None:
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError("The production build requires Windows x64.")
    if sys.version_info[:2] != (3, 12):
        raise ValueError("The production build requires Python 3.12.")
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
    args = parser.parse_args()
    try:
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
