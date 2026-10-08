"""M7 end-to-end probe (experiment, not a product feature).

Runs the real desktop service wiring against a disposable application-data root:
model import from a models folder, full Verify, one direct analysis (cold then warm),
a synthetic CSV project (import, choose column, batch analysis, results), and a window
construction with a screenshot. It works unfrozen (``python tools/m7/probe_e2e.py``)
and frozen (the same module is the entry of ``sti-probe.exe``).

    probe_e2e.py --root DIR --models-src DIR --out report.json [--rows N] [--shot PNG]

Only synthetic text is used. Nothing is written outside ``--root``/``--out``/``--shot``.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

T0 = time.perf_counter()


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
        "working_set": round(counters.WorkingSetSize / mb, 1),
        "peak_working_set": round(counters.PeakWorkingSetSize / mb, 1),
        "private": round(counters.PrivateUsage / mb, 1),
    }


SAMPLES = (
    "I really love how smooth this update feels, great work everyone!",
    "This is the third time the app crashed today and I am furious.",
    "The meeting is moved to Thursday at noon.",
    "Thanks so much for the quick help, that was a pleasant surprise.",
    "I am worried the results will not be ready before the deadline.",
    "Honestly the new layout is confusing and a bit disappointing.",
    "What a lovely afternoon, the whole team was laughing together.",
    "Nothing special to report, the report arrived as scheduled.",
)


def synthetic_csv(rows: int) -> bytes:
    lines = ["id,text"]
    for index in range(rows):
        text = SAMPLES[index % len(SAMPLES)] + f" (item {index})"
        lines.append(f'{index},"{text}"')
    lines.append(f"{rows},")  # one empty row so the validation path is exercised
    return ("\n".join(lines) + "\n").encode("utf-8")


def network_probe() -> dict[str, object]:
    """One tiny pinned file through the app's own transport (frozen TLS check)."""

    from social_text_intelligence.infrastructure.model_download import (
        UrllibDownloadTransport,
        pinned_file_url,
    )

    url = pinned_file_url(
        "SamLowe/roberta-base-go_emotions",
        "d75048347613a25d77de8cf6412eaae9fa7b26be",
        "config.json",
    )
    try:
        with UrllibDownloadTransport().open(url, start=0) as stream:
            size = sum(len(chunk) for chunk in stream.chunks)
        return {"ok": True, "bytes": size}
    except Exception as error:  # noqa: BLE001 - reported, not hidden
        return {"ok": False, "error": f"{type(error).__name__}: {error}"}


def recovery_probe(services, provisioning, models_src: Path) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Flip one byte of an installed weight file, then repair it by re-import."""

    out: dict[str, object] = {}
    target = next(
        provisioning.models_root.glob(
            "models--SamLowe--*/snapshots/*/model.safetensors"
        )
    )
    with target.open("r+b") as handle:
        handle.seek(1024)
        original = handle.read(1)
        handle.seek(1024)
        handle.write(bytes([original[0] ^ 0xFF]))
    out["quick_status_after_flip"] = [
        (m.key, m.readiness.value) for m in provisioning.status().models
    ]
    verified = provisioning.verify()
    services.gate.note_verify_result(verified)
    out["verify_after_flip"] = [(m.key, m.readiness.value) for m in verified.models]
    try:
        services.use_cases.analyze_text("Blocked?", max_text_length=1000)
        out["analysis_while_corrupt"] = "ran"
    except Exception as error:  # noqa: BLE001
        out["analysis_while_corrupt"] = f"{type(error).__name__}"
    repaired = provisioning.import_folder(models_src, ("emotion",))
    out["import_repair_outcome"] = repaired.outcome.value
    again = provisioning.verify()
    services.gate.note_verify_result(again)
    out["verify_after_repair"] = [(m.key, m.readiness.value) for m in again.models]
    try:
        services.use_cases.analyze_text("Works again.", max_text_length=1000)
        out["analysis_after_repair"] = "ran"
    except Exception as error:  # noqa: BLE001
        out["analysis_after_repair"] = f"{type(error).__name__}: {error}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--models-src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rows", type=int, default=200)
    parser.add_argument("--shot")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--net", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {"frozen": bool(getattr(sys, "frozen", False))}
    steps: dict[str, float] = {}
    mem: dict[str, dict[str, float]] = {}

    def mark(name: str, since: float) -> float:
        now = time.perf_counter()
        steps[name] = round(now - since, 3)
        mem[name] = memory_mb()
        return now

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    mark("imports_qt", T0)
    report["torch_loaded_before_analysis"] = "torch" in sys.modules

    from social_text_intelligence.desktop.composition import build_desktop_services
    from social_text_intelligence.desktop.qt.app import build_window
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    locations = AppDataLocations(Path(args.root))
    started = time.perf_counter()
    window, runner = build_window(locations)
    window.show()
    app.processEvents()
    mark("window_shown", started)
    report["torch_loaded_after_window"] = "torch" in sys.modules
    report["flask_loaded"] = "flask" in sys.modules
    report["qt_modules"] = sorted(
        name for name in sys.modules if name.startswith("PySide6.Qt")
    )

    services = build_desktop_services(locations)
    provisioning = services.provisioning
    started = time.perf_counter()
    report["status_before"] = [
        (m.key, m.readiness.value) for m in provisioning.status().models
    ]
    inspection = provisioning.inspect_folder(Path(args.models_src))
    report["inspect"] = [(m.key, m.finding.value) for m in inspection.models]
    started = mark("inspect", started)
    result = provisioning.import_folder(Path(args.models_src))
    report["import_outcome"] = result.outcome.value
    started = mark("import_folder", started)
    verified = provisioning.verify()
    report["verify_ready"] = verified.ready
    started = mark("verify_hash_all", started)
    services.gate.note_verify_result(verified)

    limit = services.settings.max_text_length
    direct = services.use_cases.analyze_text(SAMPLES[0], max_text_length=limit)
    started = mark("direct_first_cold", started)
    report["torch_loaded_after_analysis"] = "torch" in sys.modules
    services.use_cases.analyze_text(SAMPLES[1], max_text_length=limit)
    started = mark("direct_second_warm", started)
    report["direct_sentiment"] = (
        str(direct.sentiment.label) if direct.sentiment else None
    )

    details = services.workflow.import_csv(synthetic_csv(args.rows), name="m7-probe")
    started = mark("csv_import", started)
    report["csv"] = {
        "phase": details.phase.value,
        "rows": details.row_count,
        "valid": details.valid_rows,
        "invalid": details.invalid_rows,
    }
    project_id = details.summary.project_id
    if details.phase.value == "needs_column":
        details = services.workflow.choose_column(project_id, "text")
    report["csv"]["phase_after_column"] = details.phase.value  # type: ignore[index]
    started = mark("choose_column", started)
    run = services.workflow.analyze(project_id)
    mark("batch_analyze", started)
    final = services.workflow.open_project(project_id)
    report["batch"] = {
        "run": run.value,
        "analyzed": final.analyzed_rows,
        "failed": final.failed_rows,
        "sentiment_counts": final.sentiment_counts,
        "language": repr(final.language),
    }
    if args.net:
        report["net"] = network_probe()
        started = mark("net_config_fetch", started)
    if args.recovery:
        report["recovery"] = recovery_probe(
            services, provisioning, Path(args.models_src)
        )
        started = mark("recovery", started)
    if args.shot:
        window.grab().save(args.shot)
    report["steps_s"] = steps
    report["memory_mb"] = mem
    report["total_s"] = round(time.perf_counter() - T0, 3)
    Path(args.out).write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    runner.wait_idle(5)
    window.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
