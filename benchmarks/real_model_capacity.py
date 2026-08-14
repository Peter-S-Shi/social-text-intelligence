"""Opt-in real-model Batch capacity probe for release hardening.

This module is intentionally excluded from ordinary CI execution. It uses the
pinned Cardiff sentiment and SamLowe emotion models already present in the
local Hugging Face cache and emits a privacy-safe JSON report.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import statistics
import sys
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from social_text_intelligence.contracts import NormalizedTextInput, SourceType
from social_text_intelligence.interface.batch_state import (
    BatchWorkspace,
    EphemeralBatchStore,
)
from social_text_intelligence.providers import (
    CardiffSentimentProvider,
    SamLoweEmotionProvider,
)
from social_text_intelligence.providers.cardiff_sentiment import (
    MODEL_ID as SENTIMENT_MODEL_ID,
)
from social_text_intelligence.providers.cardiff_sentiment import (
    MODEL_REVISION as SENTIMENT_MODEL_REVISION,
)
from social_text_intelligence.providers.samlowe_emotion import (
    EMOTION_MODEL_ID,
    EMOTION_MODEL_REVISION,
)
from social_text_intelligence.services import AnalysisService, analyze_batch
from social_text_intelligence.services.batch import (
    DEFAULT_MAX_BATCH_ROWS,
    BatchPreview,
    PreparedBatchRow,
)

PRODUCTION_BATCH_TTL_SECONDS = 30 * 60
PROBE_LEASE_TTL_SECONDS = 1
REQUIRED_COUNTS = (1, 50, DEFAULT_MAX_BATCH_ROWS)
SYNTHETIC_TEXTS = (
    "The local service answered clearly, and the result was useful for my review.",
    "I am disappointed by the delay, but the support instructions are understandable.",
    "The update is interesting, although I still have questions about the next step.",
    "This explanation feels reassuring and gives me a practical action to take today.",
    "The response missed an important detail, so I would like a careful clarification.",
    "I appreciate the transparent notice and the calm way the limitation "
    "was described.",
    "The outcome surprised me, but I can follow the documented recovery path safely.",
    "This is frustrating because the task took longer than expected without a warning.",
)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    current_rss_bytes: int
    process_peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class StageResult:
    name: str
    rows: int
    wall_seconds: float
    rows_per_second: float
    success_count: int
    failure_count: int
    lease_ttl_seconds: int
    elapsed_beyond_probe_ttl: bool
    active_lease_survived: bool
    result_committed: bool
    memory: MemorySnapshot


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = (
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
    )


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = (
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    )


def _windows_memory_snapshot() -> MemorySnapshot:
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    if not ok:
        raise OSError("GetProcessMemoryInfo failed")
    return MemorySnapshot(
        current_rss_bytes=int(counters.WorkingSetSize),
        process_peak_rss_bytes=int(counters.PeakWorkingSetSize),
    )


def _unix_memory_snapshot() -> MemorySnapshot:
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF)
    peak = int(usage.ru_maxrss)
    if sys.platform != "darwin":
        peak *= 1024
    current = peak
    if sys.platform.startswith("linux"):
        with Path("/proc/self/statm").open(encoding="ascii") as handle:
            resident_pages = int(handle.read().split()[1])
        current = resident_pages * int(os.sysconf("SC_PAGE_SIZE"))
    return MemorySnapshot(current_rss_bytes=current, process_peak_rss_bytes=peak)


def memory_snapshot() -> MemorySnapshot:
    if sys.platform == "win32":
        return _windows_memory_snapshot()
    return _unix_memory_snapshot()


def _windows_physical_memory() -> tuple[int, int]:
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(_MemoryStatusEx),)
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return int(status.ullTotalPhys), int(status.ullAvailPhys)


def physical_memory() -> tuple[int | None, int | None]:
    if sys.platform == "win32":
        return _windows_physical_memory()
    if hasattr(os, "sysconf"):
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total = int(os.sysconf("SC_PHYS_PAGES")) * page_size
        available = int(os.sysconf("SC_AVPHYS_PAGES")) * page_size
        return total, available
    return None, None


def cpu_description() -> str:
    if sys.platform == "win32":
        import winreg

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return str(value).strip()
    if sys.platform.startswith("linux"):
        with Path("/proc/cpuinfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.lower().startswith("model name"):
                    return line.split(":", maxsplit=1)[1].strip()
    return platform.processor() or "unavailable"


def synthetic_preview(row_count: int) -> BatchPreview:
    rows: list[PreparedBatchRow] = []
    for index in range(row_count):
        identity = f"capacity-{index + 1:04d}"
        text = SYNTHETIC_TEXTS[index % len(SYNTHETIC_TEXTS)]
        record = NormalizedTextInput.from_text(
            text,
            record_id=identity,
            source_type=SourceType.FILE,
            source_label="synthetic-capacity-probe",
            language="en",
        )
        rows.append(
            PreparedBatchRow(
                row_number=index + 1,
                identity=identity,
                input_values=(
                    ("record_id", identity),
                    ("text", text),
                    ("source_type", SourceType.FILE.value),
                    ("source_label", "synthetic-capacity-probe"),
                    ("language", "en"),
                    ("timestamp", ""),
                    ("topic", ""),
                    ("community", ""),
                    ("parent_record_id", ""),
                    ("notes", ""),
                ),
                record=record,
            )
        )
    return BatchPreview(
        text_column="text",
        headers=("record_id", "text", "source_type", "source_label", "language"),
        ignored_columns=(),
        rows=tuple(rows),
    )


def run_batch_stage(
    *, name: str, row_count: int, service: AnalysisService
) -> StageResult:
    store = EphemeralBatchStore(
        ttl_seconds=PROBE_LEASE_TTL_SECONDS,
        capacity=1,
    )
    preview = synthetic_preview(row_count)
    token = store.create(BatchWorkspace(preview=preview))
    lease = store.begin_analysis(token)
    if lease is None:
        raise RuntimeError("The capacity probe could not acquire its Batch lease.")

    started = time.perf_counter()
    result = analyze_batch(preview, service)
    elapsed = time.perf_counter() - started

    lease_survived = store.get(token) is not None
    committed = store.complete_analysis(
        lease,
        BatchWorkspace(preview=preview, result=result),
    )
    stored = store.get(token)
    result_committed = bool(
        committed and stored is not None and stored.result is result
    )
    store.delete(token)
    return StageResult(
        name=name,
        rows=row_count,
        wall_seconds=elapsed,
        rows_per_second=row_count / elapsed,
        success_count=result.aggregates.analyzed_count,
        failure_count=result.aggregates.failed_count,
        lease_ttl_seconds=PROBE_LEASE_TTL_SECONDS,
        elapsed_beyond_probe_ttl=elapsed > PROBE_LEASE_TTL_SECONDS,
        active_lease_survived=lease_survived,
        result_committed=result_committed,
        memory=memory_snapshot(),
    )


def environment_report() -> dict[str, Any]:
    import torch

    total_memory, available_memory = physical_memory()
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": cpu_description(),
        "logical_cpu_count": os.cpu_count(),
        "total_physical_memory_bytes": total_memory,
        "available_physical_memory_bytes_at_start": available_memory,
        "torch": torch.__version__,
        "cpu_only": not torch.cuda.is_available(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-real-model-run",
        action="store_true",
        help="Required acknowledgement that the opt-in probe may run for minutes.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("model_cache"),
        help="Local Hugging Face cache containing both pinned revisions.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. The report never includes the cache path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Write only to --output; useful for a detached local probe.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm_real_model_run:
        raise SystemExit(
            "Refusing the heavy opt-in probe without --confirm-real-model-run."
        )

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    initial_memory = memory_snapshot()
    environment = environment_report()

    sentiment = CardiffSentimentProvider(cache_dir=args.cache_dir, offline=True)
    emotion = SamLoweEmotionProvider(cache_dir=args.cache_dir, offline=True)
    service = AnalysisService(
        sentiment_provider=sentiment,
        emotion_provider=emotion,
    )
    probe_record = synthetic_preview(1).rows[0].record
    if probe_record is None:
        raise RuntimeError("The synthetic probe record was not prepared.")

    init_started = time.perf_counter()
    sentiment.validate_input(probe_record)
    sentiment_init_seconds = time.perf_counter() - init_started
    init_started = time.perf_counter()
    emotion.validate_input(probe_record)
    emotion_init_seconds = time.perf_counter() - init_started

    first_started = time.perf_counter()
    first_report = service.analyze(probe_record)
    first_inference_seconds = time.perf_counter() - first_started
    cold_start_memory = memory_snapshot()

    stages = tuple(
        run_batch_stage(name=f"warm_{count}_rows", row_count=count, service=service)
        for count in REQUIRED_COUNTS
    )
    final_memory = memory_snapshot()
    text_lengths = tuple(len(text) for text in SYNTHETIC_TEXTS)
    word_counts = tuple(len(text.split()) for text in SYNTHETIC_TEXTS)
    report = {
        "schema_version": 1,
        "started_at_utc": started_at,
        "mode": "offline_local_real_models_cpu",
        "models": {
            "sentiment": {
                "model_id": SENTIMENT_MODEL_ID,
                "revision": SENTIMENT_MODEL_REVISION,
            },
            "emotion": {
                "model_id": EMOTION_MODEL_ID,
                "revision": EMOTION_MODEL_REVISION,
            },
        },
        "environment": environment,
        "fixture": {
            "synthetic": True,
            "language": "en",
            "template_count": len(SYNTHETIC_TEXTS),
            "character_count_min": min(text_lengths),
            "character_count_max": max(text_lengths),
            "character_count_mean": statistics.fmean(text_lengths),
            "word_count_min": min(word_counts),
            "word_count_max": max(word_counts),
            "word_count_mean": statistics.fmean(word_counts),
            "complete_input_validation": "passed_by_both_pinned_providers",
        },
        "cold_start": {
            "sentiment_initialization_seconds": sentiment_init_seconds,
            "emotion_initialization_seconds": emotion_init_seconds,
            "model_initialization_seconds": (
                sentiment_init_seconds + emotion_init_seconds
            ),
            "first_combined_inference_seconds": first_inference_seconds,
            "initialization_to_first_result_seconds": (
                sentiment_init_seconds + emotion_init_seconds + first_inference_seconds
            ),
            "first_sentiment_label": first_report.sentiment.label.value,
            "first_emotion_label": first_report.emotion.dominant_emotion.value,
            "memory": asdict(cold_start_memory),
        },
        "batch_stages": [asdict(stage) for stage in stages],
        "lease_contract": {
            "production_ttl_seconds": PRODUCTION_BATCH_TTL_SECONDS,
            "probe_ttl_seconds": PROBE_LEASE_TTL_SECONDS,
            "all_active_leases_survived": all(
                stage.active_lease_survived for stage in stages
            ),
            "all_results_committed": all(stage.result_committed for stage in stages),
        },
        "process_memory": {
            "initial_rss_bytes": initial_memory.current_rss_bytes,
            "final_rss_bytes": final_memory.current_rss_bytes,
            "peak_rss_bytes": final_memory.process_peak_rss_bytes,
            "rss_growth_bytes": (
                final_memory.current_rss_bytes - initial_memory.current_rss_bytes
            ),
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not args.quiet:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
