"""M7 concurrency probe (experiment): two application instances on one data root.

Drives the real service wiring (real models) from separate OS processes against a
disposable root that already holds provisioned models (see probe_e2e.py). Scenarios:

  A  two instances analyse the same project at the same time
  B  one instance deletes a project while another is analysing it
  C  an instance is killed (hard) mid-analysis, then a new one opens the project
  E  two instances import the same models folder into the same models directory

    probe_concurrency.py --root DIR --models-src DIR --out report.json

Only synthetic text is used; ``--root`` is rewritten, so give it a disposable path.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()


def csv_bytes(rows: int) -> bytes:
    lines = ["id,text,alt"]
    for index in range(rows):
        lines.append(
            f'{index},"Synthetic sentence {index} is rather nice.","Other {index}."'
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def services(root: str):  # type: ignore[no-untyped-def]
    from social_text_intelligence.desktop.composition import build_desktop_services
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    return build_desktop_services(AppDataLocations(Path(root)))


def worker(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    result: dict[str, object] = {"role": args.role}
    try:
        svc = services(args.root)
        if args.role == "setup":
            details = svc.workflow.import_csv(
                csv_bytes(args.rows), name="m7-concurrency"
            )
            if details.phase.value == "needs_column":
                svc.workflow.choose_column(details.summary.project_id, "text")
            result["project_id"] = details.summary.project_id
        elif args.role == "analyze":
            svc.gate.note_verify_result(svc.provisioning.verify())
            result["run"] = svc.workflow.analyze(args.project).value
        elif args.role == "delete":
            result["deleted"] = svc.workflow.delete_project(args.project)
        elif args.role == "rechoose":
            details = svc.workflow.choose_column(args.project, "alt")
            result["phase"] = details.phase.value
            result["column"] = details.text_column
        elif args.role == "state":
            details = svc.workflow.open_project(args.project)
            result.update(
                phase=details.phase.value,
                column=details.text_column,
                analyzed=details.analyzed_rows,
                rows=details.row_count,
            )
        elif args.role == "import":
            outcome = svc.provisioning.import_folder(Path(args.models_src))
            result["outcome"] = outcome.outcome.value
            result["error"] = outcome.error_code
            result["ready_after"] = outcome.status.ready
    except Exception as error:  # noqa: BLE001 - the probe reports, never hides
        result["exception"] = f"{type(error).__name__}: {error}"
    result["seconds"] = round(time.perf_counter() - started, 2)
    print("RESULT " + json.dumps(result, default=str), flush=True)
    return 0


def spawn(args: argparse.Namespace, role: str, **extra: str) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        str(HERE),
        "--worker",
        "--role",
        role,
        "--root",
        args.root,
        "--models-src",
        args.models_src,
    ]
    for key, value in extra.items():
        command += [f"--{key}", value]
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )


def finish(process: subprocess.Popen[str]) -> dict[str, object]:
    out, _ = process.communicate()
    for line in out.splitlines():
        if line.startswith("RESULT "):
            return dict(json.loads(line[7:]))
    return {"exception": "no result", "returncode": process.returncode}


def run_one(args: argparse.Namespace, role: str, **extra: str) -> dict[str, object]:
    return finish(spawn(args, role, **extra))


def project_files(root: str) -> list[str]:
    folder = Path(root) / "projects"
    if not folder.is_dir():
        return []
    return sorted(
        f"{p.name[:6]}..{p.name[-18:]}:{p.stat().st_size}" for p in folder.glob("*")
    )


def orchestrate(args: argparse.Namespace) -> int:
    report: dict[str, object] = {}
    models = Path(args.root) / "models"

    # preparation: a models folder imported once by a single instance
    shutil.rmtree(Path(args.root) / "projects", ignore_errors=True)
    if not models.is_dir():
        report["prepare_import"] = run_one(args, "import")

    def want(name: str) -> bool:
        return not args.only or name in args.only.split(",")

    def new_project() -> str:
        shutil.rmtree(Path(args.root) / "projects", ignore_errors=True)
        return str(run_one(args, "setup", rows=str(args.rows))["project_id"])

    def lap(label: str, **steps: object) -> None:
        report[label] = steps

    if want("A"):  # simultaneous analysis of the same project
        pid = new_project()
        first = spawn(args, "analyze", project=pid)
        time.sleep(3)
        second = spawn(args, "analyze", project=pid)
        lap(
            "A_two_analyses",
            first=finish(first),
            second=finish(second),
            files=project_files(args.root),
            final=run_one(args, "state", project=pid),
        )

    if want("B"):  # delete while another instance analyses
        pid = new_project()
        busy = spawn(args, "analyze", project=pid)
        time.sleep(8)
        deleted = run_one(args, "delete", project=pid)
        files_after_delete = project_files(args.root)
        analyser = finish(busy)
        lap(
            "B_delete_during_analysis",
            delete=deleted,
            files_after_delete=files_after_delete,
            analyser=analyser,
            files_after_analyser=project_files(args.root),
            reopen=run_one(args, "state", project=pid),
        )

    if want("C"):  # hard kill mid-analysis, then reopen
        pid = new_project()
        doomed = spawn(args, "analyze", project=pid)
        time.sleep(8)
        doomed.kill()
        doomed.communicate()
        lap(
            "C_kill_mid_analysis",
            files_after_kill=project_files(args.root),
            reopen=run_one(args, "state", project=pid),
            reanalyse=run_one(args, "analyze", project=pid),
            final=run_one(args, "state", project=pid),
            files_final=project_files(args.root),
        )

    if want("E"):  # two instances import the same models folder into one directory
        shutil.rmtree(models, ignore_errors=True)
        one = spawn(args, "import")
        two = spawn(args, "import")
        lap("E_concurrent_model_import", first=finish(one), second=finish(two))
        report["E_after"] = run_one(args, "import")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--role", default="")
    parser.add_argument("--root", required=True)
    parser.add_argument("--models-src", required=True)
    parser.add_argument("--out", default="concurrency.json")
    parser.add_argument("--project", default="")
    parser.add_argument("--only", default="")
    parser.add_argument("--rows", type=int, default=300)
    args = parser.parse_args()
    root, source = Path(args.root).resolve(), Path(args.models_src).resolve()
    if root == source or source in root.parents or root in source.parents:
        parser.error("--root and --models-src must not contain one another")
    return worker(args) if args.worker else orchestrate(args)


if __name__ == "__main__":
    sys.exit(main())
