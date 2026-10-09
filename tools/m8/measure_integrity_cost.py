"""M8 Track A3: what does re-checking the model weights cost on this machine?

Imports the two pinned models from a local Hugging Face cache into a DISPOSABLE
root with the application's own provisioner, then times (all with a warm file
cache, which is what a second launch sees; a cold cache needs privileges this
tool does not use):

  * the full SHA-256 Verify the app already offers,
  * a size-and-modified-time fingerprint check of the installed files,
  * raw SHA-256 throughput of the largest weights file.

It also flips one byte of a copy-installed weights file to show which check sees it.

    python tools/m8/measure_integrity_cost.py --root DIR --models-src DIR [--runs 3]

``--root`` is rewritten, so give it a disposable path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import time
from pathlib import Path

from social_text_intelligence.application.model_provisioning import APPROVED_MODELS
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import (
    LocalModelProvisioner,
    snapshots_dir,
)


def fingerprint(root: Path) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for spec in APPROVED_MODELS:
        base = snapshots_dir(root, spec) / spec.revision
        for item in spec.files:
            stat = (base / item.name).stat()
            result[f"{spec.key}/{item.name}"] = (stat.st_size, stat.st_mtime_ns)
    return result


def uncached_verify_seconds(paths: list[Path]) -> float | None:
    """SHA-256 every file reading straight from disk (Windows, no admin needed).

    ``FILE_FLAG_NO_BUFFERING`` bypasses the file cache, so this approximates a
    first-launch (cold cache) Verify: disk throughput plus hashing. None elsewhere."""

    if os.name != "nt":
        return None
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.ReadFile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
    ]
    chunk = 4 * 1024 * 1024
    raw = ctypes.create_string_buffer(chunk + 4096)
    address = (ctypes.addressof(raw) + 4095) & ~4095  # sector-aligned buffer
    start = time.perf_counter()
    for path in paths:
        handle = kernel32.CreateFileW(
            str(path), 0x80000000, 1, None, 3, 0x20000000 | 0x08000000, None
        )
        if handle in (None, ctypes.c_void_p(-1).value):
            raise OSError(ctypes.get_last_error(), "unbuffered open failed")
        digest = hashlib.sha256()
        try:
            while True:
                read = ctypes.c_uint32(0)
                ok = kernel32.ReadFile(handle, address, chunk, ctypes.byref(read), None)
                if not ok or read.value == 0:
                    break
                digest.update(ctypes.string_at(address, read.value))
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
    return time.perf_counter() - start


def timed(action):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    value = action()
    return value, time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--models-src", required=True)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    source = Path(args.models_src).resolve()
    if root == source or source in root.parents or root in source.parents:
        parser.error("--root and --models-src must not contain one another")
    shutil.rmtree(root, ignore_errors=True)

    locations = AppDataLocations(root)
    from social_text_intelligence.infrastructure.model_download import (
        UrllibDownloadTransport,
    )

    provisioner = LocalModelProvisioner(
        models_root=locations.models_dir, transport=UrllibDownloadTransport()
    )
    report: dict[str, object] = {}
    imported, seconds = timed(lambda: provisioner.import_folder(source))
    report["import_seconds"] = round(seconds, 2)
    report["import_outcome"] = imported.outcome.value
    total = sum(spec.total_bytes for spec in APPROVED_MODELS)
    report["total_bytes"] = total

    verifies = [timed(provisioner.verify)[1] for _ in range(args.runs)]
    report["full_verify_seconds"] = [round(v, 2) for v in verifies]
    report["full_verify_median_seconds"] = round(statistics.median(verifies), 2)

    base = fingerprint(locations.models_dir)
    checks = []
    for _ in range(200):
        _, seconds = timed(lambda: fingerprint(locations.models_dir) == base)
        checks.append(seconds)
    report["fingerprint_check_median_ms"] = round(statistics.median(checks) * 1000, 3)
    report["fingerprint_files"] = len(base)

    biggest = max(
        (
            snapshots_dir(locations.models_dir, spec) / spec.revision / item.name
            for spec in APPROVED_MODELS
            for item in spec.files
        ),
        key=lambda path: path.stat().st_size,
    )
    start = time.perf_counter()
    digest = hashlib.sha256()
    with biggest.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    elapsed = time.perf_counter() - start
    report["sha256_mib_per_second"] = round(biggest.stat().st_size / 2**20 / elapsed)

    installed = [
        snapshots_dir(locations.models_dir, spec) / spec.revision / item.name
        for spec in APPROVED_MODELS
        for item in spec.files
    ]
    uncached = [uncached_verify_seconds(installed) for _ in range(2)]
    report["uncached_read_and_hash_seconds"] = [
        None if value is None else round(value, 2) for value in uncached
    ]

    # One flipped byte in an installed weights file (the M7 "corruption window").
    with biggest.open("r+b") as handle:
        handle.seek(1024)
        byte = handle.read(1)
        handle.seek(1024)
        handle.write(bytes([byte[0] ^ 0xFF]))
    after_flip = fingerprint(locations.models_dir)
    status_after = provisioner.status().model(
        "emotion" if "emotions" in str(biggest) else "sentiment"
    )
    report["after_one_byte_flip"] = {
        "quick_status": status_after.readiness.value,
        "size_mtime_fingerprint_detects": after_flip != base,
        "full_verify": provisioner.verify().not_ready_keys,
    }
    report["python_pid"] = os.getpid()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
