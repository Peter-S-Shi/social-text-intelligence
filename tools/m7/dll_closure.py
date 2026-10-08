"""List DLL imports of a frozen onedir that resolve neither inside it nor in System32.

A clean-machine proxy only: it cannot prove a bare Windows install runs the build.
    dll_closure.py DIST_DIR
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pefile  # type: ignore[import-not-found]


def main(root_arg: str) -> int:
    root = Path(root_arg)
    local = {
        p.name.lower() for p in root.rglob("*") if p.suffix.lower() in {".dll", ".pyd"}
    }
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"
    missing: dict[str, set[str]] = {}
    scanned = 0
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".dll", ".pyd", ".exe"}:
            continue
        scanned += 1
        try:
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
            )
        except pefile.PEFormatError:
            continue
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            name = entry.dll.decode().lower()
            if (
                name in local
                or name.startswith("api-ms-win-")
                or (system / name).exists()
            ):
                continue
            missing.setdefault(name, set()).add(path.name)
    print(f"scanned {scanned} binaries")
    for name, users in sorted(missing.items()):
        print(f"UNRESOLVED {name} <- {sorted(users)[:3]}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
