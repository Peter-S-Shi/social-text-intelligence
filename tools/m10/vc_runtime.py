"""Pin and stage app-local Visual C++ runtime DLLs (M10-E3, runtime route R2).

The files come only from a licensed Visual Studio installation's official
VC\\Redist directory, unmodified. They are copied next to the two STI executables,
the application directory that every loader path searches. Nothing here
downloads, installs or elevates anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "distribution/vc-runtime.json"
SIGNER = "O=Microsoft Corporation"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("A version-1 Visual C++ runtime manifest is required.")
    return manifest


def required_files(manifest: dict[str, object]) -> list[str]:
    names = manifest["required_files"]
    assert isinstance(names, list)
    return [str(name) for name in names]


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def redist_directory(vs_install: Path) -> tuple[str, Path]:
    """The default redistributable version and its x64 CRT folder."""
    marker = vs_install / "VC/Auxiliary/Build/Microsoft.VCRedistVersion.default.txt"
    version = marker.read_text(encoding="utf-8").strip()
    if not version or any(part not in "0123456789." for part in version):
        raise ValueError("The Visual Studio redistributable version is unreadable.")
    # Microsoft.VC143.CRT for Visual Studio 2022; later toolsets bump the number.
    folders = sorted(
        (vs_install / "VC/Redist/MSVC" / version / "x64").glob("Microsoft.VC*.CRT")
    )
    if len(folders) != 1 or not folders[0].is_dir():
        raise ValueError("The official VC\\Redist x64 CRT folder is absent.")
    return version, folders[0]


def file_facts(paths: list[Path]) -> list[dict[str, str]]:
    """Authenticode status, signer and file version as Windows reports them."""
    script = (
        "$ErrorActionPreference='Stop';"
        "$env:STI_VC_FILES -split '\\|' | ForEach-Object {"
        "$s=Get-AuthenticodeSignature -LiteralPath $_;"
        "[pscustomobject]@{path=$_;status=[string]$s.Status;"
        "signer=[string]$s.SignerCertificate.Subject;"
        "version=(Get-Item -LiteralPath $_).VersionInfo.FileVersionRaw.ToString()}"
        "} | ConvertTo-Json -Compress"
    )
    environment = dict(os.environ, STI_VC_FILES="|".join(str(p) for p in paths))
    output = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=environment,
        text=True,
        timeout=120,
    )
    facts = json.loads(output)
    return facts if isinstance(facts, list) else [facts]


def check_files(
    folder: Path, manifest: dict[str, object], facts: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Every required file present, Microsoft-signed and at the minimum version."""
    minimum = version_tuple(str(manifest["minimum_version"]))
    by_name = {Path(item["path"]).name.lower(): item for item in facts}
    receipts = []
    for name in required_files(manifest):
        item = by_name.get(name.lower())
        if item is None or not (folder / name).is_file():
            raise ValueError("A required Visual C++ runtime file is absent.")
        subject = [part.strip() for part in item["signer"].split(",")]
        if item["status"] != "Valid" or SIGNER not in subject:
            raise ValueError("A runtime file lacks a valid Microsoft signature.")
        if version_tuple(item["version"])[: len(minimum)] < minimum:
            raise ValueError("A runtime file is older than the minimum version.")
        receipts.append(
            {
                "file": name,
                "sha256": digest(folder / name),
                "file_version": item["version"],
            }
        )
    return receipts


def pin(vs_install: Path, manifest_path: Path = MANIFEST) -> dict[str, object]:
    """Record the exact files of the owner's licensed installation."""
    manifest = load_manifest(manifest_path)
    version, folder = redist_directory(vs_install)
    paths = [folder / name for name in required_files(manifest)]
    receipts = check_files(folder, manifest, file_facts(paths))
    manifest.update(
        redist_version=version,
        files={item["file"]: item["sha256"] for item in receipts},
        file_versions={item["file"]: item["file_version"] for item in receipts},
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_source(folder: Path, manifest: dict[str, object]) -> list[dict[str, str]]:
    """The staging folder must hold exactly the pinned, still-signed bytes."""
    pinned = manifest.get("files")
    if not isinstance(pinned, dict) or not pinned:
        raise ValueError("The app-local runtime is not pinned yet (run --pin).")
    if sorted(pinned) != sorted(required_files(manifest)):
        raise ValueError("The runtime pin does not cover the required file set.")
    paths = [folder / name for name in required_files(manifest)]
    receipts = check_files(folder, manifest, file_facts(paths))
    if any(pinned[item["file"]] != item["sha256"] for item in receipts):
        raise ValueError("A runtime file differs from the pinned bytes.")
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vs-install", type=Path, required=True)
    parser.add_argument("--pin", action="store_true")
    args = parser.parse_args()
    try:
        if sys.platform != "win32":
            raise ValueError("Pinning reads Windows signatures; use Windows.")
        if args.pin:
            manifest = pin(args.vs_install)
        else:
            manifest = load_manifest()
            verify_source(redist_directory(args.vs_install)[1], manifest)
        result = {"redist_version": manifest["redist_version"], "verified": True}
        print(json.dumps(result))
        return 0
    except ValueError as error:
        print(str(error))
        return 2
    except (OSError, KeyError, subprocess.SubprocessError, json.JSONDecodeError):
        print("Runtime pinning failed; check the Visual Studio installation path.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
