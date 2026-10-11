"""Count Qt imports in a bundle that its own Qt DLLs do not export (M10-E4 helper).

Ordinary and delay-loaded imports by name are both checked; an import by ordinal
cannot be matched to an export name and is counted as unresolved (fail closed).
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from build import DELAY_IMPORT_DIRECTORY, IMPORT_DIRECTORY, PeImage

EXPORT_DIRECTORY = 0


def export_names(data: bytes) -> set[str]:
    image = PeImage.parse(data)
    rva = image.directory(EXPORT_DIRECTORY)
    if not rva:
        return set()
    count, _, names = struct.unpack_from("<III", data, image.offset(rva) + 24)
    table = image.offset(names)
    return {
        image.string(image.offset(struct.unpack_from("<I", data, table + 4 * i)[0]))
        for i in range(count)
    }


def imported_symbols(data: bytes) -> dict[str, list[str | None]]:
    """Imported names per DLL (lower-case); None marks an import by ordinal."""
    image = PeImage.parse(data)
    step, flag, fmt = (8, 1 << 63, "<Q") if image.wide else (4, 1 << 31, "<I")
    result: dict[str, list[str | None]] = {}

    def thunks(dll: str, lookup: int) -> None:
        symbols = result.setdefault(dll.lower(), [])
        at = image.offset(lookup)
        while value := struct.unpack_from(fmt, data, at)[0]:
            symbols.append(
                None
                if value & flag
                else image.string(image.offset(value & 0x7FFFFFFF) + 2)
            )
            at += step

    rva = image.directory(IMPORT_DIRECTORY)
    descriptor = image.offset(rva) if rva else -1
    while rva and any(struct.unpack_from("<5I", data, descriptor)):
        lookup, _, _, name, first = struct.unpack_from("<5I", data, descriptor)
        thunks(image.string(image.offset(name)), lookup or first)
        descriptor += 20
    rva = image.directory(DELAY_IMPORT_DIRECTORY)
    descriptor = image.offset(rva) if rva else -1
    while rva and any(struct.unpack_from("<8I", data, descriptor)):
        attributes, name, _, _, lookup = struct.unpack_from("<5I", data, descriptor)
        base = 0 if attributes & 1 else image.image_base
        thunks(image.string(image.offset(name - base)), lookup - base)
        descriptor += 32
    return result


def main(internal: Path) -> int:
    binaries = [p for p in internal.rglob("*") if p.suffix.lower() in {".dll", ".pyd"}]
    qt = [p for p in binaries if p.name.lower().startswith("qt6")]
    exports: dict[str, set[str]] = {}
    for path in qt:
        if path.name.lower() in exports:
            raise ValueError("Two Qt libraries share one file name.")
        exports[path.name.lower()] = export_names(path.read_bytes())
    unresolved = 0
    for path in binaries:
        for dll, symbols in imported_symbols(path.read_bytes()).items():
            if dll in exports:
                unresolved += sum(
                    symbol is None or symbol not in exports[dll] for symbol in symbols
                )
    print(json.dumps({"unresolved": unresolved}))
    return 0 if unresolved == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
