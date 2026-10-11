"""Count Qt imports in a bundle that its own Qt DLLs do not export (M10-E4 helper)."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from build import import_names


def export_names(data: bytes) -> set[str]:
    header = struct.unpack_from("<I", data, 0x3C)[0]
    sections, optional_size = struct.unpack_from("<H12xH", data, header + 6)
    optional = header + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    directories = optional + (112 if magic == 0x20B else 96)
    exports = struct.unpack_from("<I", data, directories)[0]
    table = [
        struct.unpack_from("<8xIIII", data, optional + optional_size + 40 * index)
        for index in range(sections)
    ]

    def offset(rva: int) -> int:
        for size, address, raw_size, raw in table:
            if address <= rva < address + max(size, raw_size):
                return raw + rva - address
        raise ValueError("Export RVA outside every section.")

    if not exports:
        return set()
    count, _, names = struct.unpack_from("<III", data, offset(exports) + 24)
    result = set()
    for index in range(count):
        at = offset(struct.unpack_from("<I", data, offset(names) + 4 * index)[0])
        result.add(data[at : data.index(b"\0", at)].decode("ascii"))
    return result


def imported_symbols(data: bytes, dll: str) -> list[str]:
    """Named imports from one DLL (ordinal imports are skipped)."""
    header = struct.unpack_from("<I", data, 0x3C)[0]
    sections, optional_size = struct.unpack_from("<H12xH", data, header + 6)
    optional = header + 24
    wide = struct.unpack_from("<H", data, optional)[0] == 0x20B
    directories = optional + (112 if wide else 96)
    table = [
        struct.unpack_from("<8xIIII", data, optional + optional_size + 40 * index)
        for index in range(sections)
    ]

    def offset(rva: int) -> int:
        for size, address, raw_size, raw in table:
            if address <= rva < address + max(size, raw_size):
                return raw + rva - address
        raise ValueError("Import RVA outside every section.")

    descriptor = offset(struct.unpack_from("<I", data, directories + 8)[0])
    symbols = []
    while any(struct.unpack_from("<5I", data, descriptor)):
        lookup, _, _, name_rva, first = struct.unpack_from("<5I", data, descriptor)
        at = offset(name_rva)
        if data[at : data.index(b"\0", at)].decode("ascii").lower() == dll:
            thunk = offset(lookup or first)
            step, flag = (8, 1 << 63) if wide else (4, 1 << 31)
            while value := struct.unpack_from("<Q" if wide else "<I", data, thunk)[0]:
                if not value & flag:
                    hint = offset(value & 0x7FFFFFFF) + 2
                    symbols.append(data[hint : data.index(b"\0", hint)].decode("ascii"))
                thunk += step
        descriptor += 20
    return symbols


def main(internal: Path) -> int:
    binaries = [p for p in internal.rglob("*") if p.suffix.lower() in {".dll", ".pyd"}]
    qt = {p.name.lower(): p for p in binaries if p.name.lower().startswith("qt6")}
    exports = {name: export_names(path.read_bytes()) for name, path in qt.items()}
    unresolved = 0
    for path in binaries:
        data = path.read_bytes()
        for _, dll in import_names(data):
            if dll.lower() in exports:
                unresolved += sum(
                    symbol not in exports[dll.lower()]
                    for symbol in imported_symbols(data, dll.lower())
                )
    print(json.dumps({"unresolved": unresolved}))
    return 0 if unresolved == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
