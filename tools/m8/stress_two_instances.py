"""M8 Track A2 stress: two application instances analysing one persisted project.

Repeats the M7 "two instances, same project" scenario many times against one
persisted, accumulating data root (nothing is deleted or overwritten between rounds),
with a third observer process that continuously lists and opens the project, and
optionally with CPU burner processes. Any anomaly is captured with the project
file state (names, sizes, mtimes), the exceptions, and a byte-exact copy of the
project's files.

    python tools/m8/stress_two_instances.py --root DIR --rounds 30 [--load] \
        [--rows 300] [--row-ms 15] [--src DIR]

Synthetic text and deterministic providers only; ``--root`` must be disposable.
``--src`` points child processes at another copy of the package sources (for
example a checkout of the pre-hardening baseline).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
LIMITS = (2_000_000, 1000, 2000)


def csv_bytes(rows: int) -> bytes:
    lines = ["id,text"]
    lines += [f'{n},"Synthetic sentence {n} is rather nice."' for n in range(rows)]
    return ("\n".join(lines) + "\n").encode()


def snapshot(root: Path) -> list[str]:
    folder = root / "projects"
    if not folder.is_dir():
        return ["<projects dir missing>"]
    entries = []
    for path in sorted(folder.iterdir()):
        try:
            stat = path.stat()
            entries.append(f"{path.name} size={stat.st_size} mtime={stat.st_mtime:.3f}")
        except OSError as error:
            entries.append(f"{path.name} <stat failed: {type(error).__name__}>")
    return entries


def workflow(root: str, row_ms: float) -> Any:
    from social_text_intelligence.application.project_workflow import (
        CsvLimits,
        ProjectWorkflow,
    )
    from social_text_intelligence.contracts import AnalysisReport, NormalizedTextInput
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

        def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
            time.sleep(row_ms / 1000)
            return service.analyze(record)

    repository = SqliteProjectRepository(AppDataLocations(Path(root)))
    return ProjectWorkflow(repository, Gateway(), CsvLimits(*LIMITS))


def worker(args: argparse.Namespace) -> int:
    root = Path(args.root)
    flow = workflow(args.root, args.row_ms)
    result: dict[str, Any] = {"role": args.role}
    started = time.perf_counter()
    try:
        if args.role == "setup":
            details = flow.import_csv(csv_bytes(args.rows), name="stress")
            result["project_id"] = details.summary.project_id
        elif args.role == "analyze":
            result["run"] = flow.analyze(args.project).value
        elif args.role == "state":
            details = flow.open_project(args.project)
            result.update(phase=details.phase.value, analyzed=details.analyzed_rows)
        elif args.role == "observe":
            stop = Path(args.stop)
            loops, anomalies = 0, []
            while not stop.exists():
                loops += 1
                problem = None
                try:
                    listed = [
                        s for s in flow.list_projects() if s.project_id == args.project
                    ]
                    if not listed:
                        problem = "listing missed the project"
                    elif listed[0].status.value != "ok":
                        problem = f"listing status {listed[0].status.value}"
                    flow.open_project(args.project)
                except Exception as error:  # noqa: BLE001 - the probe reports
                    problem = f"{type(error).__name__}: {error}"
                if problem and len(anomalies) < 25:
                    anomalies.append(
                        {
                            "t": round(time.perf_counter() - started, 3),
                            "problem": problem,
                            "files": snapshot(root),
                        }
                    )
                time.sleep(args.poll_ms / 1000)
            result.update(loops=loops, anomalies=anomalies)
    except Exception as error:  # noqa: BLE001
        result["exception"] = f"{type(error).__name__}: {error}"
    result["seconds"] = round(time.perf_counter() - started, 2)
    print("RESULT " + json.dumps(result, default=str), flush=True)
    return 0


def spawn(args: argparse.Namespace, role: str, **extra: str) -> subprocess.Popen[str]:
    command = [sys.executable, str(HERE), "--worker", "--role", role]
    command += ["--root", args.root, "--rows", str(args.rows)]
    command += ["--row-ms", str(args.row_ms), "--poll-ms", str(args.poll_ms)]
    for key, value in extra.items():
        command += [f"--{key}", value]
    env = dict(os.environ)
    if args.src:
        env["PYTHONPATH"] = str(Path(args.src).resolve())
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
    )


def finish(process: subprocess.Popen[str]) -> dict[str, Any]:
    out, err = process.communicate()
    for line in out.splitlines():
        if line.startswith("RESULT "):
            return dict(json.loads(line[7:]))
    return {"exception": "no result", "rc": process.returncode, "stderr": err[-400:]}


def start_load(count: int) -> list[subprocess.Popen[bytes]]:
    code = "while True: pass"
    return [
        subprocess.Popen([sys.executable, "-c", code], stderr=subprocess.DEVNULL)
        for _ in range(count)
    ]


def orchestrate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    burners = start_load(os.cpu_count() or 4) if args.load else []
    rng = random.Random(args.seed)
    totals = {"rounds": 0, "anomalies": 0}
    outcomes: dict[str, int] = {}
    try:
        with (out / "rounds.jsonl").open("a", encoding="utf-8") as log:
            for number in range(1, args.rounds + 1):
                project = str(finish(spawn(args, "setup"))["project_id"])
                stop = out / f"stop-{number}"
                stop.unlink(missing_ok=True)
                observer = spawn(args, "observe", project=project, stop=str(stop))
                offset = rng.choice([0.0, 0.0, 0.05, 0.3, 1.0, 2.0])
                first = spawn(args, "analyze", project=project)
                time.sleep(offset)
                second = spawn(args, "analyze", project=project)
                runs = [finish(first), finish(second)]
                stop.write_text("1")
                watch = finish(observer)
                final = finish(spawn(args, "state", project=project))
                kinds = sorted(str(r.get("run") or r.get("exception")) for r in runs)
                key = "+".join(kinds)
                outcomes[key] = outcomes.get(key, 0) + 1
                committed = kinds.count("committed")
                anomaly = (
                    committed != 1
                    or final.get("phase") != "analyzed"
                    or bool(watch.get("anomalies"))
                    or "exception" in watch
                )
                record = {
                    "round": number,
                    "project": project,
                    "offset": offset,
                    "runs": runs,
                    "observer": {
                        k: watch.get(k) for k in ("loops", "exception", "seconds")
                    },
                    "observer_anomalies": watch.get("anomalies", []),
                    "final": final,
                    "anomaly": anomaly,
                }
                if anomaly:
                    totals["anomalies"] += 1
                    record["files"] = snapshot(root)
                    keep = out / "artifacts" / f"round-{number}"
                    keep.mkdir(parents=True, exist_ok=True)
                    for path in (root / "projects").glob(f"{project}*"):
                        shutil.copy2(path, keep / path.name)
                log.write(json.dumps(record) + "\n")
                log.flush()
                totals["rounds"] += 1
    finally:
        for burner in burners:
            burner.kill()
    summary = {**totals, "outcomes": outcomes, "load": args.load}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--role", default="")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--stop", default="")
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--rows", type=int, default=300)
    parser.add_argument("--row-ms", type=float, default=15.0)
    parser.add_argument("--poll-ms", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=8)
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--src", default="")
    args = parser.parse_args()
    if not args.worker and not args.out:
        parser.error("--out is required")
    return worker(args) if args.worker else orchestrate(args)


if __name__ == "__main__":
    sys.exit(main())
