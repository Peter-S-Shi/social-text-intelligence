"""M8 Track A4 probe: how the project store reports real file-level faults (Windows).

Runs against a disposable root and prints one line per scenario:
what operation was tried, what happened to the file, and the error code/message the
application would show. REAL here means the fault is produced by the operating
system on a real file; EMULATED means it is injected (see the ledger).

    python tools/m8/probe_storage_faults.py --root DIR

Synthetic text only. Windows only for the lock scenarios (they skip elsewhere).
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import os
import stat
import sys
from collections.abc import Iterator
from pathlib import Path


def csv_bytes() -> bytes:
    rows = [f'{n},"Synthetic sentence {n} is rather nice."' for n in range(5)]
    return ("id,text\n" + "\n".join(rows) + "\n").encode()


@contextlib.contextmanager
def exclusive_handle(path: Path, share: int) -> Iterator[None]:
    """Hold ``path`` open with the given Win32 share mode (0 = no sharing)."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = ctypes.c_void_p
    generic_read_write = 0xC0000000
    open_existing = 3
    handle = kernel32.CreateFileW(
        str(path), generic_read_write, share, None, open_existing, 0x80, None
    )
    if handle in (None, ctypes.c_void_p(-1).value):
        raise OSError(ctypes.get_last_error(), "could not open for the probe")
    try:
        yield
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def attempt(label: str, action: object) -> None:
    try:
        result = action()  # type: ignore[operator]
        print(f"{label}: ok -> {result!r}")
    except Exception as error:  # noqa: BLE001 - the probe reports
        code = getattr(error, "code", "")
        print(f"{label}: {type(error).__name__} code={code!r} :: {error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    from social_text_intelligence.application.project_workflow import (
        CsvLimits,
        ProjectWorkflow,
    )
    from social_text_intelligence.infrastructure.app_data import AppDataLocations
    from social_text_intelligence.infrastructure.sqlite_projects import (
        SqliteProjectRepository,
    )
    from social_text_intelligence.providers import (
        DeterministicEmotionProvider,
        DeterministicSentimentProvider,
    )
    from social_text_intelligence.services import AnalysisService

    service = AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(),
        emotion_provider=DeterministicEmotionProvider(),
    )

    class Gateway:
        initialized = True

        def analyze(self, record):  # type: ignore[no-untyped-def]
            return service.analyze(record)

    root = Path(args.root)
    flow = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(root)),
        Gateway(),
        CsvLimits(2_000_000, 1000, 2000),
    )

    def new_project() -> tuple[str, Path]:
        pid = flow.import_csv(csv_bytes(), name="probe").summary.project_id
        return pid, root / "projects" / f"{pid}.sqlite3"

    def try_all(tag: str, pid: str) -> None:
        attempt(f"{tag}: list", flow.list_projects)
        attempt(f"{tag}: open", lambda: flow.open_project(pid).phase)
        attempt(f"{tag}: analyse", lambda: flow.analyze(pid))
        attempt(f"{tag}: delete", lambda: flow.delete_project(pid))

    if sys.platform == "win32":
        for share, name in ((0, "no sharing"), (1, "share read only")):
            pid, path = new_project()
            with exclusive_handle(path, share):
                try_all(f"[REAL] file held, {name}", pid)
            attempt(
                "[REAL] after release: open",
                lambda pid=pid: flow.open_project(pid).phase,
            )

    pid, path = new_project()
    os.chmod(path, stat.S_IREAD)
    try_all("[REAL] read-only attribute", pid)
    with contextlib.suppress(OSError):
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    attempt("[REAL] attribute cleared: open", lambda: flow.open_project(pid).phase)

    blocker = root / "blocked"
    blocker.write_text("a file where a folder is needed")
    blocked = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(blocker)),
        Gateway(),
        CsvLimits(2_000_000, 1000, 2000),
    )
    attempt(
        "[REAL] data root is a file: import",
        lambda: blocked.import_csv(csv_bytes(), name="x"),
    )
    attempt("[REAL] data root is a file: list", blocked.list_projects)
    return 0


if __name__ == "__main__":
    sys.exit(main())
