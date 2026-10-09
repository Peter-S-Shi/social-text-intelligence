"""M8 Track A5 probe: memory limit behaviour and UI responsiveness during model load.

Windows only, real models, disposable root:

  prepare   import the two pinned models into --root from --models-src (first)
  limit     run one cold analysis in a child process inside a Windows job object
            with a per-process committed-memory limit for each --limits-mb value
  ui        real Qt event loop (platform from QT_QPA_PLATFORM) with a heartbeat
            timer while the real job runner loads both models on a worker thread

    python tools/m8/probe_memory_ui.py prepare --root DIR --models-src DIR
    python tools/m8/probe_memory_ui.py limit --root DIR --limits-mb 3072,2304,1792
    python tools/m8/probe_memory_ui.py ui --root DIR

A job-object limit emulates a smaller committed-memory budget. It is NOT a smaller
physical RAM (no paging pressure, no other programs competing); the ledger says so.
Synthetic text only.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve()
TEXT = "I really love how smooth this update feels, great work everyone!"


class _Counters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def memory_mb() -> dict[str, float]:
    counters = _Counters()
    counters.cb = ctypes.sizeof(_Counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_Counters),
        wintypes.DWORD,
    ]
    ctypes.windll.psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), counters.cb
    )
    mb = 1024 * 1024
    return {
        "peak_working_set_mb": round(counters.PeakWorkingSetSize / mb),
        "peak_commit_mb": round(counters.PeakPagefileUsage / mb),
        "private_mb": round(counters.PrivateUsage / mb),
    }


# --- job object ---------------------------------------------------------------------


class _BasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ("a", "b", "c", "d", "e", "f")]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimit),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def run_limited(root: str, limit_mb: int | None) -> dict[str, object]:
    command = [sys.executable, str(HERE), "child-load", "--root", root]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if limit_mb is not None:
        info = _ExtendedLimit()
        info.BasicLimitInformation.LimitFlags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = limit_mb * 1024 * 1024
        ok = kernel32.SetInformationJobObject(
            wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")
    started = time.perf_counter()
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if limit_mb is not None:
        kernel32.AssignProcessToJobObject(
            wintypes.HANDLE(job), wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]
        )
    out, err = process.communicate(timeout=900)
    seconds = round(time.perf_counter() - started, 1)
    kernel32.CloseHandle(wintypes.HANDLE(job))
    result: dict[str, object] = {"limit_mb": limit_mb, "returncode": process.returncode}
    for line in out.splitlines():
        if line.startswith("RESULT "):
            result.update(json.loads(line[7:]))
    result["seconds"] = seconds
    if "outcome" not in result:
        result["stderr_tail"] = err[-300:]
    return result


# --- workers ------------------------------------------------------------------------


def services(root: str):  # type: ignore[no-untyped-def]
    from social_text_intelligence.desktop.composition import build_desktop_services
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    return build_desktop_services(AppDataLocations(Path(root)))


def child_load(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    result: dict[str, object] = {}
    try:
        svc = services(args.root)
        svc.gate.note_verify_result(svc.provisioning.status())
        report = svc.use_cases.analyze_text(TEXT, max_text_length=1000)
        result["outcome"] = "analysed"
        result["sentiment"] = report.sentiment.label.value
    except MemoryError:
        result["outcome"] = "MemoryError (raw, not translated by the app)"
    except BaseException as error:  # noqa: BLE001 - the probe reports
        result["outcome"] = f"{type(error).__name__}"
        result["code"] = getattr(error, "code", None)
        result["message"] = getattr(error, "message", None)
    result["load_seconds"] = round(time.perf_counter() - started, 1)
    result["memory"] = memory_mb()
    print("RESULT " + json.dumps(result, default=str), flush=True)
    return 0


def ui_probe(args: argparse.Namespace) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from social_text_intelligence.desktop.qt.app import build_window
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    app = QApplication.instance() or QApplication(sys.argv[:1])
    locations = AppDataLocations(Path(args.root))
    window, runner = build_window(locations)
    window.show()
    app.processEvents()
    svc = window._services if hasattr(window, "_services") else services(args.root)  # noqa: SLF001
    svc.gate.note_verify_result(svc.provisioning.status())

    beats: list[float] = [time.perf_counter()]
    gaps: list[tuple[float, float]] = []

    def beat() -> None:
        now = time.perf_counter()
        gaps.append((round(now - T_START[0], 2), round((now - beats[-1]) * 1000)))
        beats.append(now)

    T_START = [time.perf_counter()]
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(beat)
    timer.start()
    done: dict[str, object] = {}

    def deliver(outcome: object) -> None:
        done["finished_at"] = round(time.perf_counter() - T_START[0], 2)
        done["outcome"] = (
            type(outcome).__name__
            if isinstance(outcome, BaseException)
            else "analysed"
        )
        QTimer.singleShot(300, app.quit)

    T_START[0] = time.perf_counter()
    runner.run(
        lambda: svc.use_cases.analyze_text(TEXT, max_text_length=1000), deliver
    )
    app.exec()
    timer.stop()
    stalls = [gap for gap in gaps if gap[1] > 100]
    result = {
        "platform": app.platformName(),
        "load_and_first_analysis_seconds": done.get("finished_at"),
        "outcome": done.get("outcome"),
        "heartbeats": len(gaps),
        "expected_heartbeats_at_10ms": int(float(str(done.get("finished_at"))) * 100),
        "max_gap_ms": max((gap[1] for gap in gaps), default=None),
        "gaps_over_100ms": len(stalls),
        "gaps_over_500ms": len([g for g in gaps if g[1] > 500]),
        "worst_gaps_ms": sorted((g[1] for g in gaps), reverse=True)[:8],
        "first_stalls_at_s": [g[0] for g in stalls[:8]],
        "memory": memory_mb(),
    }
    print("RESULT " + json.dumps(result), flush=True)
    return 0


def prepare(args: argparse.Namespace) -> int:
    svc = services(args.root)
    outcome = svc.provisioning.import_folder(Path(args.models_src))
    status = svc.provisioning.verify()
    print(json.dumps({"import": outcome.outcome.value, "ready": status.ready}))
    return 0


def limit(args: argparse.Namespace) -> int:
    limits: list[int | None] = [
        int(item) for item in args.limits_mb.split(",") if item
    ]
    results = [run_limited(args.root, value) for value in [None, *limits]]
    print(json.dumps(results, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "limit", "ui", "child-load"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--models-src", default="")
    parser.add_argument("--limits-mb", default="3072,2560,2304,2048,1792,1536")
    args = parser.parse_args()
    handlers = {
        "prepare": prepare,
        "limit": limit,
        "ui": ui_probe,
        "child-load": child_load,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
