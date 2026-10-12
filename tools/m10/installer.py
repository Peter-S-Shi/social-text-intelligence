"""Build a local internal-use installer from a verified Windows onedir packet."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from build import MICROSOFT_RUNTIME
from compliance import digest, verify_packet

CONFIG = Path(__file__).resolve().parent
INNO_VERSION = "6.7.3"
ISCC_SHA256 = "0a8757031b33777e4c9cbffee40f11a5062b36d25cbe144c1db73b6102b80ad7"
LICENSE_SHA256 = "3df23505b7ec00dc007a1e1e9ba32ee3895e7ce90043bcd1ac1b9b47155921a7"
MARKER = "STI M10-C managed application files v1"
BLOCKER_CODE = re.compile(r"(B[1-6]):")
# Release-readiness facts that the packet does not derive; stated, not inferred.
RELEASE_CONDITIONS = {
    "B6": (
        "closed only on the narrow M10-E2 QtCore-only criterion (M10 S3); a "
        "modified-source rebuild of Gui, Widgets and plugins was not exercised"
    ),
    "clean_machine_validation": "NOT RUN",
    "public_source_hosting": "not operational",
}


def packet_blockers(inventory: dict[str, object]) -> tuple[list[str], list[str]]:
    """The packet's own blocker codes, and any blocker that has no code.

    Fails closed: a packet that permits distribution, or whose blocker list is
    malformed, is refused rather than summarised.
    """
    blockers = inventory.get("blockers")
    if inventory.get("distribution_permitted") is not False:
        raise ValueError(
            "The license packet must record distribution as not permitted."
        )
    if not isinstance(blockers, list) or not all(isinstance(b, str) for b in blockers):
        raise ValueError("The license packet's blocker list is malformed.")
    codes, uncoded = [], []
    for blocker in blockers:
        match = BLOCKER_CODE.match(blocker)
        if match is None:
            uncoded.append(blocker)
        elif match.group(1) not in codes:
            codes.append(match.group(1))
    return codes, uncoded


def ordinary_path(path: Path) -> None:
    for entry in (path, *path.parents):
        if not entry.exists() and not entry.is_symlink():
            continue
        attributes = getattr(entry.lstat(), "st_file_attributes", 0)
        if entry.is_symlink() or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Links/reparse points are not accepted as build paths.")


def quoted(value: str) -> str:
    if any(ord(char) < 32 for char in value):
        raise ValueError("Control characters are not accepted in build paths.")
    return value.replace('"', '""').replace("{", "{{")


def prepare(bundle: Path, output: Path) -> dict[str, object]:
    ordinary_path(bundle)
    ordinary_path(output)
    required = (
        "sti-desktop.exe",
        "sti-check.exe",
        "legal/inventory.json",
        "legal/GNU-LGPL-3.0.txt",
        "legal/GNU-GPL-3.0.txt",
        "legal/SOURCE_ACCESS.md",
        "legal/QT_REPLACEMENT.md",
    )
    if not all((bundle / name).is_file() for name in required):
        raise ValueError(
            "A complete license packet and both frozen entries are required."
        )
    if output.exists() or output.is_symlink():
        raise ValueError(
            "A new output directory is required; existing data is preserved."
        )
    bundle = bundle.resolve()
    output = output.resolve()
    if output.is_relative_to(bundle):
        raise ValueError("Installer output must be outside the original bundle.")
    inventory = json.loads(
        (bundle / "legal/inventory.json").read_text(encoding="utf-8")
    )
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ValueError("A version-1 license inventory object is required.")
    if not verify_packet(bundle, inventory)["materials_valid"]:
        raise ValueError("The complete license packet failed byte/set verification.")
    legal_blockers, other_blockers = packet_blockers(inventory)
    sources = inventory.get("source_delivery", [])
    names = [item["filename"] for item in sources]
    if len(set(names)) != 5 or any(
        not isinstance(name, str)
        or not name.endswith(".tar.xz")
        or any(char in name for char in "/\\:")
        for name in names
    ):
        raise ValueError("Source receipts must name five distinct local archives.")
    if len(sources) != 5 or not all(
        (bundle / "legal/sources" / item["filename"]).is_file() for item in sources
    ):
        raise ValueError("All five accompanying source archives are required.")
    revision = inventory.get("application_revision", "")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("The frozen application revision must be recorded.")
    for path in bundle.rglob("*"):
        ordinary_path(path)
        quoted(str(path))
        if path.is_file() and (
            path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".safetensors"}
            or path.name.lower() in {".env", "pytorch_model.bin"}
        ):
            raise ValueError("Model weights or user data cannot enter the installer.")
        if path.is_file() and MICROSOFT_RUNTIME.fullmatch(path.name):
            raise ValueError(
                "Microsoft Visual C++ runtime files cannot enter the installer; "
                "it requires the system runtime instead."
            )
    if digest(CONFIG / "INNO-LICENSE.txt") != LICENSE_SHA256:
        raise ValueError("The versioned installer license text changed.")
    output.mkdir(parents=True, exist_ok=False)
    payload = output / "payload"
    shutil.copytree(bundle, payload)
    (payload / "installer").mkdir()
    shutil.copyfile(CONFIG / "INNO-LICENSE.txt", payload / "installer/INNO-LICENSE.txt")
    (payload / "installer/managed.txt").write_text(MARKER, encoding="ascii")
    files = sorted(path for path in payload.rglob("*") if path.is_file())
    entries = []
    checks = []
    uninstall_checks = []
    for path in files:
        relative = path.relative_to(payload)
        destination = str(relative).replace("/", "\\")
        parent = str(relative.parent).replace("/", "\\")
        target = "{app}" if parent == "." else "{app}\\" + quoted(parent)
        entries.append(
            f'Source: "{quoted(str(path))}"; DestDir: "{target}"; Flags: ignoreversion'
        )
        pascal_path = destination.replace("{", "{{").replace("'", "''")
        checks.append(
            "  if Collides(ExpandConstant('{app}\\"
            + pascal_path
            + "'), Owned) then begin\n"
            "    Result := 'Existing files are not owned by this installer. '"
            "'Move them manually before installation.'; Exit;\n  end;"
        )
        uninstall_checks.append(
            "  if HasReparse(ExpandConstant('{app}\\" + pascal_path + "')) then Exit;"
        )
    script = (CONFIG / "installer.iss").read_text(encoding="utf-8")
    script = (
        script.replace("@@FILES@@", "\n".join(entries))
        .replace("@@COLLISIONS@@", "\n".join(checks))
        .replace("@@UNINSTALL_CHECKS@@", "\n".join(uninstall_checks))
        .replace("@@OUTPUT@@", quoted(str(output / "compiled")))
    )
    script = script.replace("@@WARNING@@", quoted(str(CONFIG / "INSTALLER_NOTICE.txt")))
    (output / "installer.iss").write_text(script, encoding="utf-8-sig")
    receipt: dict[str, object] = {
        "schema_version": 1,
        "prepared": True,
        "compiled": False,
        "frozen_application_sha": revision,
        "input_inventory_sha256": digest(bundle / "legal/inventory.json"),
        "installer_template_sha256": digest(CONFIG / "installer.iss"),
        "installer_generator_sha256": digest(CONFIG / "installer.py"),
        "installer_notice_sha256": digest(CONFIG / "INSTALLER_NOTICE.txt"),
        "inno_version": INNO_VERSION,
        "inno_license_sha256": LICENSE_SHA256,
        "models_bundled": False,
        "distribution_permitted": False,
        # As derived by the verified packet, not a fixed list.
        "legal_blockers": legal_blockers,
        "other_packet_blockers": other_blockers,
        "release_conditions": RELEASE_CONDITIONS,
        "clean_machine_validation": "NOT RUN",
        "owner_30_minute_smoke": "NOT RUN",
        "payload": [
            {"path": p.relative_to(payload).as_posix(), "sha256": digest(p)}
            for p in files
        ],
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--iscc", type=Path)
    args = parser.parse_args()
    try:
        if args.iscc and (sys.platform != "win32" or digest(args.iscc) != ISCC_SHA256):
            raise ValueError(
                "The verified Windows Inno Setup 6.7.3 compiler is required."
            )
        receipt = prepare(args.bundle, args.output)
        if args.iscc:
            with (args.output / "compiler-private.log").open(
                "w", encoding="utf-8"
            ) as log:
                subprocess.run(
                    [
                        str(args.iscc.resolve()),
                        str((args.output / "installer.iss").resolve()),
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=600,
                )
            for item in receipt["payload"]:
                if digest(args.output / "payload" / item["path"]) != item["sha256"]:
                    raise ValueError("Installer payload changed during compilation.")
            for filename, key in (
                ("installer.iss", "installer_template_sha256"),
                ("installer.py", "installer_generator_sha256"),
                ("INSTALLER_NOTICE.txt", "installer_notice_sha256"),
            ):
                if digest(CONFIG / filename) != receipt[key]:
                    raise ValueError("Installer recipe changed during compilation.")
            installer = args.output / "compiled/STI-0.10.0-internal-x64.exe"
            receipt.update(compiled=True, installer_sha256=digest(installer))
        (args.output / "installer-receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {key: value for key, value in receipt.items() if key != "payload"}
            )
        )
        return 0
    except ValueError as error:
        print(str(error))
        return 2
    except (OSError, KeyError, TypeError, subprocess.SubprocessError):
        print(
            "Installer preparation failed; require a complete license packet, "
            "a new output "
            "directory and verified inputs. Check the local compiler log if present."
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
