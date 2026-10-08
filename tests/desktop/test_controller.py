"""The provisioning controller: action routing, progress, cancel, and recovery."""

from __future__ import annotations

import threading
from pathlib import Path

from social_text_intelligence.application.model_provisioning import (
    FolderFinding,
    FolderInspection,
    FolderModelFinding,
    ProvisioningOutcome,
    ProvisioningResult,
    Readiness,
)
from social_text_intelligence.contracts.errors import ModelProvisioningError
from social_text_intelligence.desktop.controller import (
    Activity,
    ControllerState,
    ProvisioningController,
)

from .fakes import (
    FakeProvisioning,
    ImmediateRunner,
    ManualRunner,
    ThreadedRunner,
    failed,
    progress,
    status,
)

MISSING = status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
READY = status()
PARTIAL = status(
    Readiness.INCOMPLETE,
    Readiness.NOT_INSTALLED,
    sentiment_args={"resumable": 40, "problems": ("weights.bin",)},
)


def make(
    fake: FakeProvisioning, runner: ManualRunner | ThreadedRunner | None = None
) -> tuple[ProvisioningController, list[ControllerState]]:
    controller = ProvisioningController(fake, runner or ImmediateRunner())
    seen: list[ControllerState] = []
    controller.subscribe(seen.append)
    return controller, seen


def test_refresh_reads_the_quick_status() -> None:
    fake = FakeProvisioning(current=MISSING)
    controller, seen = make(fake)

    controller.refresh()

    assert controller.state.status == MISSING
    assert controller.state.activity is Activity.IDLE
    assert seen[-1].status == MISSING


def test_download_runs_and_ends_with_the_fresh_status() -> None:
    fake = FakeProvisioning(
        current=MISSING,
        next_download=ProvisioningResult(ProvisioningOutcome.COMPLETED, READY),
    )
    controller, seen = make(fake)

    controller.refresh()
    assert controller.download(("sentiment",))

    assert fake.calls[-1] == ("download", ("sentiment",))
    assert controller.state.status == READY
    assert controller.state.activity is Activity.IDLE
    assert controller.state.progress is None
    report = controller.state.report
    assert report is not None and report.outcome is ProvisioningOutcome.COMPLETED
    assert any(state.activity is Activity.DOWNLOADING for state in seen)


def test_a_failure_is_a_result_with_its_code_and_fixed_message() -> None:
    fake = FakeProvisioning(
        current=MISSING, next_download=failed("network_unavailable", PARTIAL)
    )
    controller, _ = make(fake)

    controller.download()

    report = controller.state.report
    assert report is not None
    assert report.outcome is ProvisioningOutcome.FAILED
    assert report.error_code == "network_unavailable"
    assert report.error_message == ModelProvisioningError("network_unavailable").message
    assert controller.state.status == PARTIAL


def test_only_one_operation_runs_at_a_time() -> None:
    fake = FakeProvisioning(current=MISSING)
    runner = ManualRunner()
    controller, _ = make(fake, runner)

    assert controller.download()
    assert not controller.download()
    assert not controller.verify()
    assert not controller.discard()
    assert not controller.inspect_folder(Path("synthetic"))
    assert len(runner.jobs) == 1


def test_stop_sets_the_cancel_flag_and_keeps_what_was_kept() -> None:
    hold = threading.Event()
    fake = FakeProvisioning(current=MISSING, hold=hold)
    runner = ThreadedRunner()
    controller, _ = make(fake, runner)

    try:
        controller.download()
        assert fake.started.wait(5)
        assert controller.can_stop
        controller.stop()
        assert controller.state.stopping
        fake.current = PARTIAL
        runner.drain(lambda: controller.state.activity is Activity.IDLE)
    finally:
        hold.set()  # a failed assertion must never leave a spinning worker behind
        runner.join()

    assert fake.saw_cancel
    report = controller.state.report
    assert report is not None and report.outcome is ProvisioningOutcome.CANCELLED
    assert controller.state.status == PARTIAL
    assert not controller.state.stopping


def test_verify_cannot_be_stopped() -> None:
    fake = FakeProvisioning(current=READY)
    controller, _ = make(fake, ManualRunner())

    controller.verify()
    controller.stop()

    assert not controller.state.stopping
    assert not controller.can_stop


def test_verify_reports_damage_and_tells_observers_before_the_state() -> None:
    damaged = status(Readiness.READY, Readiness.CORRUPT)
    fake = FakeProvisioning(current=READY, next_verify=damaged)
    controller, _ = make(fake)
    order: list[str] = []
    controller.add_verify_observer(lambda found: order.append("observer"))
    controller.subscribe(lambda state: order.append("state"))

    controller.verify()

    assert order[-2:] == ["observer", "state"]
    report = controller.state.report
    assert report is not None and report.found_damage
    assert controller.state.status == damaged


def test_provisioning_errors_from_verify_become_a_report() -> None:
    fake = FakeProvisioning(
        current=READY, next_verify=ModelProvisioningError("storage_failed")
    )
    controller, _ = make(fake)

    controller.verify()

    report = controller.state.report
    assert report is not None and report.error_code == "storage_failed"
    assert report.outcome is ProvisioningOutcome.FAILED
    assert controller.state.activity is Activity.IDLE


def test_discard_runs_and_a_busy_discard_is_reported() -> None:
    kept = status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
    fake = FakeProvisioning(current=PARTIAL, next_discard=kept)
    controller, _ = make(fake)
    controller.discard(("sentiment",))
    assert fake.calls[-1] == ("discard", ("sentiment",))
    assert controller.state.status == kept

    fake.next_discard = ModelProvisioningError("provisioning_in_progress")
    controller.discard()
    report = controller.state.report
    assert report is not None and report.error_code == "provisioning_in_progress"


def test_unexpected_exceptions_never_leak_their_text() -> None:
    fake = FakeProvisioning(
        current=MISSING, next_download=RuntimeError("C:/Users/someone/secret.txt")
    )
    controller, _ = make(fake)

    controller.download()

    report = controller.state.report
    assert report is not None and report.error_code == "unexpected_error"
    assert report.error_message is not None
    assert "secret" not in report.error_message
    assert controller.state.activity is Activity.IDLE


def test_folder_inspect_then_verified_import() -> None:
    inspection = FolderInspection(
        (
            FolderModelFinding("sentiment", FolderFinding.FOUND, ()),
            FolderModelFinding("emotion", FolderFinding.INCOMPLETE, ("weights",)),
        )
    )
    fake = FakeProvisioning(
        current=MISSING,
        next_inspection=inspection,
        next_import=ProvisioningResult(
            ProvisioningOutcome.COMPLETED,
            status(Readiness.READY, Readiness.NOT_INSTALLED),
        ),
    )
    controller, _ = make(fake)
    folder = Path("synthetic-folder")

    assert not controller.import_folder()  # nothing inspected yet
    controller.inspect_folder(folder)
    assert controller.state.folder is not None
    assert controller.state.folder.inspection == inspection
    assert fake.calls[-1] == ("inspect", folder)

    controller.import_folder()

    assert ("import", (folder, ("sentiment",))) in fake.calls
    assert controller.state.status.model("sentiment").ready
    assert controller.state.folder is None  # imported; nothing left to import


def test_only_found_models_can_be_imported() -> None:
    inspection = FolderInspection(
        (FolderModelFinding("sentiment", FolderFinding.MISMATCHED, ("weights",)),)
    )
    fake = FakeProvisioning(current=MISSING, next_inspection=inspection)
    controller, _ = make(fake)
    controller.inspect_folder(Path("synthetic-folder"))

    assert not controller.import_folder()
    assert not any(call[0] == "import" for call in fake.calls)


def test_an_unreadable_folder_is_a_finding_not_a_crash() -> None:
    fake = FakeProvisioning(
        current=MISSING, next_inspection=ModelProvisioningError("source_unreadable")
    )
    controller, _ = make(fake)

    controller.inspect_folder(Path("synthetic-folder"))

    folder = controller.state.folder
    assert folder is not None and folder.inspection is None
    assert folder.error_code == "source_unreadable"
    assert not folder.checking


def test_a_failed_import_keeps_the_folder_for_another_attempt() -> None:
    inspection = FolderInspection(
        (FolderModelFinding("sentiment", FolderFinding.FOUND, ()),)
    )
    fake = FakeProvisioning(
        current=MISSING,
        next_inspection=inspection,
        next_import=failed("checksum_mismatch", MISSING),
    )
    controller, _ = make(fake)
    controller.inspect_folder(Path("synthetic-folder"))

    controller.import_folder()

    report = controller.state.report
    assert report is not None and report.error_code == "checksum_mismatch"
    assert controller.state.folder is not None


def test_retry_repeats_the_last_failed_operation() -> None:
    fake = FakeProvisioning(
        current=MISSING, next_download=failed("storage_failed", MISSING)
    )
    controller, _ = make(fake)
    controller.download(("emotion",))

    fake.next_download = ProvisioningResult(ProvisioningOutcome.COMPLETED, READY)
    assert controller.retry()

    assert [call for call in fake.calls if call[0] == "download"] == [
        ("download", ("emotion",)),
        ("download", ("emotion",)),
    ]
    assert controller.state.status == READY


def test_dismiss_clears_the_report() -> None:
    fake = FakeProvisioning(
        current=MISSING, next_download=failed("download_rejected", MISSING)
    )
    controller, _ = make(fake)
    controller.download()
    controller.dismiss_report()
    assert controller.state.report is None


def test_work_runs_off_the_ui_thread_and_listeners_run_on_it() -> None:
    fake = FakeProvisioning(current=MISSING, emit=[progress(10), progress(80)])
    runner = ThreadedRunner()
    controller, _ = make(fake, runner)
    threads: list[int] = []
    controller.subscribe(lambda state: threads.append(threading.get_ident()))

    controller.download()
    runner.drain(lambda: controller.state.activity is Activity.IDLE)
    runner.join()

    assert threads and set(threads) == {threading.get_ident()}
    assert fake.thread_ids and threading.get_ident() not in fake.thread_ids


def test_progress_updates_are_coalesced_to_the_latest_value() -> None:
    fake = FakeProvisioning(
        current=MISSING, emit=[progress(10), progress(20), progress(30)]
    )
    runner = ManualRunner()
    controller, _ = make(fake, runner)

    controller.download()
    work, deliver = runner.jobs.popleft()
    work()
    assert len(runner.posted) == 1  # three events, one pending UI update
    runner.pump_posts()

    latest = controller.state.progress
    assert latest is not None and latest.overall_bytes_done == 30
    deliver(ProvisioningResult(ProvisioningOutcome.COMPLETED, READY))
    assert controller.state.progress is None


def test_a_late_progress_post_cannot_resurrect_a_finished_operation() -> None:
    fake = FakeProvisioning(current=MISSING, emit=[progress(10)])
    runner = ManualRunner()
    controller, _ = make(fake, runner)
    controller.download()
    work, deliver = runner.jobs.popleft()
    work()
    deliver(ProvisioningResult(ProvisioningOutcome.COMPLETED, READY))

    runner.pump_posts()  # the stale update arrives after completion

    assert controller.state.progress is None
    assert controller.state.activity is Activity.IDLE


def test_when_idle_runs_immediately_or_after_the_operation() -> None:
    fake = FakeProvisioning(current=MISSING)
    runner = ManualRunner()
    controller, _ = make(fake, runner)
    ran: list[str] = []

    controller.when_idle(lambda: ran.append("now"))
    assert ran == ["now"]

    controller.download()
    controller.when_idle(lambda: ran.append("later"))
    assert ran == ["now"]
    runner.run_next()
    assert ran == ["now", "later"]


def test_try_again_still_retries_the_failed_download_after_a_folder_check() -> None:
    inspection = FolderInspection(
        (FolderModelFinding("sentiment", FolderFinding.NOT_FOUND, ()),)
    )
    fake = FakeProvisioning(
        current=MISSING,
        next_download=failed("storage_failed", MISSING),
        next_inspection=inspection,
    )
    controller, _ = make(fake)
    controller.download(("emotion",))
    controller.inspect_folder(Path("synthetic-folder"))  # the report stays visible

    fake.next_download = ProvisioningResult(ProvisioningOutcome.COMPLETED, READY)
    assert controller.retry()

    assert fake.calls[-1] == ("download", ("emotion",))
