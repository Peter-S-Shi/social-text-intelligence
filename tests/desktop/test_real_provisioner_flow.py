"""The controller over the real M5.0 provisioner (synthetic manifest, no network)."""

from __future__ import annotations

import threading
from pathlib import Path

from provisioning.fakes import (
    CONTENT,
    MANIFEST,
    FakeTransport,
    snapshot_dir,
    write_model,
)

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
    Readiness,
)
from social_text_intelligence.desktop.controller import (
    Activity,
    ProvisioningController,
)
from social_text_intelligence.desktop.gate import (
    AnalysisAvailability,
    AnalysisGate,
)
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import StubGateway, ThreadedRunner, synthetic_report


def real(root: Path, transport: FakeTransport | None = None) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root,
        transport=transport or FakeTransport.serving_manifest(),
        manifest=MANIFEST,
    )


def run(controller: ProvisioningController, runner: ThreadedRunner) -> None:
    runner.drain(lambda: controller.state.activity is Activity.IDLE)
    runner.join()


def test_download_through_real_threads_installs_both_models(tmp_path: Path) -> None:
    runner = ThreadedRunner()
    controller = ProvisioningController(real(tmp_path), runner)
    seen: list[int] = []
    controller.subscribe(
        lambda state: (
            seen.append(state.progress.overall_bytes_done) if state.progress else None
        )
    )
    controller.refresh()
    assert controller.state.status.not_ready_keys == ("sentiment", "emotion")

    controller.download(("sentiment", "emotion"))
    run(controller, runner)

    assert controller.state.status.ready
    report = controller.state.report
    assert report is not None and report.outcome is ProvisioningOutcome.COMPLETED
    assert seen == sorted(seen)  # overall progress never moves backwards


def test_stop_then_download_again_resumes_the_partial_file(tmp_path: Path) -> None:
    started, proceed = threading.Event(), threading.Event()
    transport = FakeTransport.serving_manifest()
    transport.chunk_size = 512

    chunks_seen = {"weights": 0}

    def pause_on_first_chunk(url: str) -> None:
        # pause inside the large weights file so a real partial is left behind
        if url.endswith("weights.bin") and not started.is_set():
            chunks_seen["weights"] += 1
            if chunks_seen["weights"] == 3:
                started.set()
                proceed.wait(5)

    transport.on_chunk = pause_on_first_chunk
    runner = ThreadedRunner()
    controller = ProvisioningController(real(tmp_path, transport), runner)
    controller.refresh()

    controller.download(("sentiment",))
    runner.drain(started.is_set)
    controller.stop()
    proceed.set()
    run(controller, runner)

    report = controller.state.report
    assert report is not None and report.outcome is ProvisioningOutcome.CANCELLED
    model = controller.state.status.model("sentiment")
    assert model.readiness is Readiness.INCOMPLETE and model.resumable_bytes > 0

    transport.on_chunk = None
    transport.requests.clear()
    controller.download(("sentiment",))
    run(controller, runner)

    assert controller.state.status.model("sentiment").ready
    assert any(start > 0 for _, start in transport.requests)  # resumed with a range


def test_folder_inspect_and_verified_import(tmp_path: Path) -> None:
    source = tmp_path / "source"
    for spec in MANIFEST:
        write_model(source, spec)
    runner = ThreadedRunner()
    controller = ProvisioningController(real(tmp_path / "managed"), runner)
    controller.refresh()

    controller.inspect_folder(source)
    run(controller, runner)
    folder = controller.state.folder
    assert folder is not None and folder.inspection is not None
    assert folder.inspection.importable_keys == ("sentiment", "emotion")

    controller.import_folder()
    run(controller, runner)

    assert controller.state.status.ready
    assert controller.state.folder is None
    assert snapshot_dir(source, MANIFEST[0]).is_dir()  # the source is untouched


def test_h2_session_block_survives_repair_until_a_fresh_process(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    for spec in MANIFEST:
        write_model(root, spec)
    gateway = StubGateway(report=synthetic_report())
    gate = AnalysisGate(gateway)
    runner = ThreadedRunner()
    controller = ProvisioningController(real(root), runner)
    controller.add_verify_observer(gate.note_verify_result)
    controller.refresh()
    assert gate.availability(controller.state.status) is AnalysisAvailability.AVAILABLE

    gate.analyze(synthetic_report().record)  # analysis loads its models

    # silent same-size damage that only a hash check can see
    damaged = snapshot_dir(root, MANIFEST[1]) / "model.safetensors"
    original = damaged.read_bytes()
    damaged.write_bytes(bytes(len(original)))
    controller.refresh()
    assert controller.state.status.ready  # the quick status cannot see it

    controller.verify()
    run(controller, runner)

    assert controller.state.status.model("emotion").readiness is Readiness.CORRUPT
    availability = gate.availability(controller.state.status)
    assert availability is AnalysisAvailability.SESSION_BLOCKED

    # the finding is durable: a brand-new provisioner over the same folder sees it
    assert real(root).status().model("emotion").readiness is Readiness.CORRUPT

    # repair by download replaces only the bad file
    controller.download(("emotion",))
    run(controller, runner)
    assert controller.state.status.ready
    assert (
        gate.availability(controller.state.status)
        is AnalysisAvailability.SESSION_BLOCKED
    )
    assert (snapshot_dir(root, MANIFEST[1]) / "model.safetensors").read_bytes() == (
        CONTENT["emotion"]["model.safetensors"]
    )

    # restart: a fresh gate over the repaired folder is available again
    fresh = AnalysisGate(StubGateway(report=synthetic_report()))
    assert fresh.availability(real(root).status()) is AnalysisAvailability.AVAILABLE
