"""A second application instance for cross-process tests (run as a script).

Each scenario signals ``started`` once it holds its resource, waits for a
``release`` file (or is killed by the test), and prints one ``RESULT {json}`` line.
Synthetic data and fake gateways/transports only; no real models.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS))

WAIT_SECONDS = 60.0


def wait_for_release(signal: Path) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not (signal / "release").exists():
        if time.monotonic() > deadline:
            raise SystemExit(3)
        time.sleep(0.02)


def started(signal: Path) -> None:
    (signal / "started").write_text("1")


def scenario_hold(args: argparse.Namespace) -> dict[str, object]:
    from social_text_intelligence.infrastructure.process_locks import FileProcessLocks

    lock = FileProcessLocks(Path(args.root) / "locks").try_acquire(args.scope)
    if lock is None:
        return {"held": False}
    started(Path(args.signal))
    wait_for_release(Path(args.signal))
    lock.release()
    return {"held": True}


def scenario_analyze(args: argparse.Namespace) -> dict[str, object]:
    from persistence.workflow_samples import ScriptedGateway

    from social_text_intelligence.application.project_workflow import (
        CsvLimits,
        ProjectWorkflow,
    )
    from social_text_intelligence.infrastructure.app_data import AppDataLocations
    from social_text_intelligence.infrastructure.sqlite_projects import (
        SqliteProjectRepository,
    )

    signal = Path(args.signal)

    def hold_first_row(call: int) -> None:
        if call == 1:
            started(signal)
            wait_for_release(signal)

    flow = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(Path(args.root))),
        ScriptedGateway(hold_first_row),
        CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500),
    )
    return {"run": flow.analyze(args.project).value}


def scenario_import_models(args: argparse.Namespace) -> dict[str, object]:
    from provisioning.fakes import MANIFEST, FakeTransport

    from social_text_intelligence.application.model_provisioning import (
        ProvisioningProgress,
    )
    from social_text_intelligence.infrastructure.app_data import AppDataLocations
    from social_text_intelligence.infrastructure.model_store import (
        LocalModelProvisioner,
    )
    from social_text_intelligence.infrastructure.process_locks import FileProcessLocks

    locations = AppDataLocations(Path(args.root))
    signal = Path(args.signal)
    first = True

    def hold_first_event(_: ProvisioningProgress) -> None:
        nonlocal first
        if first:
            first = False
            started(signal)
            wait_for_release(signal)

    provisioner = LocalModelProvisioner(
        models_root=locations.models_dir,
        transport=FakeTransport(),
        manifest=MANIFEST,
        process_locks=FileProcessLocks(locations.locks_dir),
    )
    outcome = provisioner.import_folder(
        Path(args.source), on_progress=hold_first_event
    )
    return {"outcome": outcome.outcome.value, "error": outcome.error_code}


SCENARIOS = {
    "hold": scenario_hold,
    "analyze": scenario_analyze,
    "import-models": scenario_import_models,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--root", required=True)
    parser.add_argument("--signal", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("--scope", default="models")
    parser.add_argument("--source", default="")
    args = parser.parse_args()
    try:
        result = SCENARIOS[args.scenario](args)
    except Exception as error:  # noqa: BLE001 - the test reads the report
        result = {"exception": type(error).__name__}
    print("RESULT " + json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
