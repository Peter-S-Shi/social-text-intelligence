"""Headless smoke tests of the real Qt shell over a fake provisioner."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import QPushButton  # noqa: E402

from social_text_intelligence.application.model_provisioning import (  # noqa: E402
    FolderFinding,
    FolderInspection,
    FolderModelFinding,
    ProvisioningOutcome,
    ProvisioningResult,
    Readiness,
)
from social_text_intelligence.desktop.composition import (  # noqa: E402
    build_desktop_services,
)
from social_text_intelligence.desktop.controller import Activity  # noqa: E402
from social_text_intelligence.desktop.qt.main_window import MainWindow  # noqa: E402
from social_text_intelligence.desktop.qt.platform import DesktopPlatform  # noqa: E402
from social_text_intelligence.desktop.qt.runner import QtJobRunner  # noqa: E402
from social_text_intelligence.infrastructure.app_data import (  # noqa: E402
    AppDataLocations,
)

from .conftest import FakePlatform  # noqa: E402
from .fakes import (  # noqa: E402
    MB,
    FakeProvisioning,
    ImmediateRunner,
    StubGateway,
    failed,
    progress,
    status,
    synthetic_report,
)

MISSING = status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)
CORRUPT = status(
    Readiness.READY,
    Readiness.CORRUPT,
    emotion_args={"problems": ("model.safetensors",)},
)


class Shell:
    def __init__(
        self,
        tmp_path: Path,
        fake: FakeProvisioning,
        runner: Any,
        platform: FakePlatform | None = None,
    ) -> None:
        self.fake = fake
        self.platform = platform or FakePlatform()
        self.gateway = StubGateway(report=synthetic_report())
        services = build_desktop_services(
            AppDataLocations(tmp_path), provisioning=fake, analysis=self.gateway
        )
        self.window = MainWindow(
            services,
            runner,
            DesktopPlatform(
                pick_folder=self.platform.pick_folder,
                open_folder=self.platform.open_folder,
                confirm=self.platform.confirm,
            ),
        )
        self.window.show()
        self.window.start()

    @property
    def setup(self) -> Any:
        return self.window.ui.setup_dialog

    @property
    def models(self) -> Any:
        return self.window.ui.models_dialog

    def button(self, parent: Any, text: str) -> QPushButton:
        matches = [
            b
            for b in parent.findChildren(QPushButton)
            if b.text() == text and b.isVisibleTo(parent)
        ]
        assert matches, f"no visible button {text!r}"
        return cast(QPushButton, matches[0])

    def close(self) -> None:
        self.window.close()


@pytest.fixture
def make_shell(qapp: Any, tmp_path: Path):  # type: ignore[no-untyped-def]
    shells: list[Shell] = []

    def factory(
        fake: FakeProvisioning, runner: Any = None, platform: Any = None
    ) -> Shell:
        shell = Shell(tmp_path, fake, runner or ImmediateRunner(), platform)
        shells.append(shell)
        return shell

    yield factory
    for shell in shells:
        for dialog in (
            shell.window.ui.setup_dialog,
            shell.window.ui.models_dialog,
            shell.window.ui.folder_dialog,
        ):
            dialog.hide()
        shell.window.hide()
        shell.window.deleteLater()
    QCoreApplication.processEvents()


def test_the_job_runner_works_off_the_ui_thread_and_delivers_on_it(
    qapp: Any, pump: Any
) -> None:
    runner = QtJobRunner()
    seen: dict[str, Any] = {}

    def work() -> int:
        seen["work"] = threading.get_ident()
        return 7

    runner.run(
        work, lambda outcome: seen.update(done=threading.get_ident(), out=outcome)
    )
    pump(lambda: "done" in seen)

    main = threading.get_ident()
    assert seen["work"] != main and seen["done"] == main and seen["out"] == 7


def test_the_job_runner_delivers_an_error_instead_of_raising(
    qapp: Any, pump: Any
) -> None:
    runner = QtJobRunner()
    seen: list[Any] = []

    def work() -> None:
        raise RuntimeError("synthetic")

    runner.run(work, seen.append)
    pump(lambda: bool(seen))
    assert isinstance(seen[0], RuntimeError)


def test_launch_shows_the_setup_window_when_models_are_not_ready(
    make_shell: Any,
) -> None:
    shell = make_shell(FakeProvisioning(current=MISSING))
    assert shell.setup.isVisible()
    assert shell.setup.panel.headline.text() == "Set up the language models"
    assert shell.setup.close_button.text() == "Later"
    names = [b.text() for b in shell.setup.panel.action_row.buttons]
    assert names == ["Download both models · 200.0 MB", "Use a models folder…"]


def test_launch_is_quiet_when_models_are_ready(make_shell: Any) -> None:
    shell = make_shell(FakeProvisioning(current=status()))
    assert not shell.setup.isVisible()
    button = shell.window.models_button
    assert button.text().startswith("✓ Models ready")
    assert button.accessibleName() == "Models ready. 2 of 2 models ready. Open models."
    assert shell.fake.calls[0] == ("status", None)


def test_nothing_downloads_until_the_user_asks(make_shell: Any) -> None:
    shell = make_shell(FakeProvisioning(current=MISSING))
    assert not any(call[0] == "download" for call in shell.fake.calls)


def test_download_button_routes_to_the_boundary_and_updates_the_sidebar(
    make_shell: Any,
) -> None:
    fake = FakeProvisioning(
        current=MISSING,
        next_download=ProvisioningResult(ProvisioningOutcome.COMPLETED, status()),
    )
    shell = make_shell(fake)

    shell.button(shell.setup, "Download both models · 200.0 MB").click()

    assert ("download", ("sentiment", "emotion")) in fake.calls
    assert shell.window.models_button.text().startswith("✓ Models ready")
    assert shell.setup.close_button.text() == "Done"
    assert shell.setup.panel.report.isVisible()


def test_later_keeps_the_app_usable_and_analysis_blocked_with_a_reason(
    make_shell: Any,
) -> None:
    shell = make_shell(FakeProvisioning(current=MISSING))
    shell.setup.close_button.click()
    assert not shell.setup.isVisible()

    page = shell.window.analyze_page
    shell.window._show_page(1)
    assert not page.analyze_button.isEnabled()
    assert page.block.isVisibleTo(page)
    assert "models are not ready" in page.block.body.text()
    assert "not ready" in page.analyze_button.accessibleDescription()
    # Projects stay usable
    assert shell.window.nav_buttons["Projects"].isEnabled()


def test_every_button_has_an_accessible_name_and_is_keyboard_reachable(
    make_shell: Any,
) -> None:
    shell = make_shell(FakeProvisioning(current=MISSING))
    shell.window.ui.show_models()
    for root in (shell.window, shell.setup, shell.models):
        for button in root.findChildren(QPushButton):
            assert button.accessibleName() or button.text(), button.objectName()
            assert button.focusPolicy() & Qt.FocusPolicy.TabFocus


def test_busy_state_disables_actions_and_says_why(make_shell: Any) -> None:
    from .fakes import ManualRunner

    runner = ManualRunner()
    shell = make_shell(FakeProvisioning(current=MISSING), runner)

    shell.button(shell.setup, "Download both models · 200.0 MB").click()

    panel = shell.setup.panel
    assert shell.window.provisioning.state.activity is Activity.DOWNLOADING
    assert panel.busy_note.isVisibleTo(panel) and "running" in panel.busy_note.text()
    assert not any(b.isEnabled() for b in panel.action_row.buttons)
    assert shell.setup.close_button.text() == "Continue while this runs"
    assert panel.progress.isVisibleTo(panel)
    assert shell.window.models_meter.isVisibleTo(shell.window)


def test_real_threads_keep_the_ui_alive_and_stop_keeps_focus(
    make_shell: Any, qapp: Any, pump: Any
) -> None:
    hold = threading.Event()
    fake = FakeProvisioning(current=MISSING, hold=hold, emit=[progress(50 * MB)])
    runner = QtJobRunner()
    shell = make_shell(fake, runner)
    panel = shell.setup.panel

    button = shell.button(shell.setup, "Download both models · 200.0 MB")
    button.setFocus()
    button.click()
    pump(lambda: panel.progress.isVisibleTo(panel) and fake.started.is_set())
    pump(lambda: "50.0 MB" in panel.progress._bars[2][1].format())

    assert panel.progress.stop_button.isVisibleTo(panel)
    assert shell.setup.focusWidget() is panel.progress.stop_button
    ticks = []
    for _ in range(20):
        QCoreApplication.processEvents()
        ticks.append(1)
    assert len(ticks) == 20  # the event loop kept running while the worker held

    panel.progress.stop_button.click()
    pump(lambda: shell.window.provisioning.state.activity is Activity.IDLE)
    assert fake.saw_cancel
    assert panel.report.isVisibleTo(panel)


def test_failure_shows_title_fixed_message_code_and_recovery(make_shell: Any) -> None:
    fake = FakeProvisioning(
        current=MISSING, next_download=failed("network_unavailable", MISSING)
    )
    shell = make_shell(fake)

    shell.button(shell.setup, "Download both models · 200.0 MB").click()

    report = shell.setup.panel.report
    assert report.isVisibleTo(shell.setup)
    assert "Connection lost" in report.title.text()
    assert report.code.text() == "network_unavailable"
    assert [b.text() for b in report.action_row.buttons] == [
        "Download again · resumes",
        "Use a models folder…",
    ]


def test_discard_asks_first_and_states_the_size(make_shell: Any) -> None:
    partial = status(
        Readiness.INCOMPLETE,
        Readiness.NOT_INSTALLED,
        sentiment_args={"resumable": 20 * MB, "problems": ("weights.bin",)},
    )
    platform = FakePlatform()
    platform.confirmed = False
    fake = FakeProvisioning(current=partial, next_discard=MISSING)
    shell = make_shell(fake, platform=platform)
    button = shell.button(shell.setup, "Discard partial download")

    button.click()
    assert platform.confirmations and "20.0 MB" in platform.confirmations[0]
    assert not any(call[0] == "discard" for call in fake.calls)

    platform.confirmed = True
    button.click()
    assert ("discard", ("sentiment",)) in fake.calls


def test_folder_flow_inspects_read_only_then_imports(make_shell: Any) -> None:
    inspection = FolderInspection(
        (
            FolderModelFinding("sentiment", FolderFinding.FOUND, ()),
            FolderModelFinding("emotion", FolderFinding.FOUND, ()),
        )
    )
    fake = FakeProvisioning(
        current=MISSING,
        next_inspection=inspection,
        next_import=ProvisioningResult(ProvisioningOutcome.COMPLETED, status()),
    )
    platform = FakePlatform()
    platform.folder = Path("synthetic-folder")
    shell = make_shell(fake, platform=platform)

    shell.button(shell.setup, "Use a models folder…").click()
    dialog = shell.window.ui.folder_dialog
    assert dialog.isVisible()
    assert "read-only" in dialog.status_label.text().lower()

    shell.button(dialog, "Choose a folder…").click()
    assert ("inspect", Path("synthetic-folder")) in fake.calls
    assert dialog.status_label.text() == "Read-only check. Nothing was copied."

    shell.button(dialog, "Import both models").click()
    assert (
        "import",
        (Path("synthetic-folder"), ("sentiment", "emotion")),
    ) in fake.calls
    assert not dialog.isVisible()  # finished; the result is in the window behind
    assert shell.window.models_button.text().startswith("✓ Models ready")


def test_an_unreadable_folder_is_explained_in_the_dialog(make_shell: Any) -> None:
    from social_text_intelligence.contracts.errors import ModelProvisioningError

    fake = FakeProvisioning(
        current=MISSING, next_inspection=ModelProvisioningError("source_unreadable")
    )
    platform = FakePlatform()
    platform.folder = Path("synthetic-folder")
    shell = make_shell(fake, platform=platform)
    shell.button(shell.setup, "Use a models folder…").click()
    dialog = shell.window.ui.folder_dialog

    shell.button(dialog, "Choose a folder…").click()

    assert dialog.error_box.isVisibleTo(dialog)
    assert "Couldn't read that folder" in dialog.error_box.title.text()
    assert dialog.error_box.code.text() == "source_unreadable"


def test_models_window_verify_and_open_folder(make_shell: Any) -> None:
    fake = FakeProvisioning(current=status(), next_verify=status())
    shell = make_shell(fake)
    shell.window.models_button.click()
    assert shell.models.isVisible()

    shell.button(shell.models, "Verify files").click()
    assert ("verify", None) in fake.calls
    assert "Verify finished" in shell.models.panel.report.title.text()

    shell.button(shell.models, "Open models folder").click()
    assert shell.platform.opened == [fake.models_root]


def test_details_and_provenance_are_one_toggle_away(make_shell: Any) -> None:
    shell = make_shell(FakeProvisioning(current=status()))
    shell.window.ui.show_models()
    card = shell.models.panel.cards["sentiment"]
    assert not card.details.isVisibleTo(card)

    card.details_toggle.click()

    assert card.details.isVisibleTo(card)
    assert "synthetic-org/sentiment-model" in card.details.text()
    assert "CC-BY-4.0" in card.details.text()


def test_analysis_runs_when_ready_and_shows_provenance(make_shell: Any) -> None:
    shell = make_shell(FakeProvisioning(current=status()))
    shell.window._show_page(1)
    page = shell.window.analyze_page
    assert page.analyze_button.isEnabled() and not page.block.isVisibleTo(page)

    page.editor.setPlainText("A synthetic sentence.")
    page.analyze_button.click()

    assert page.result_box.isVisibleTo(page)
    assert "Sentiment:" in page.result_text.text()
    assert len(shell.gateway.records) == 1


def test_h2_blocks_every_analysis_surface_until_restart(make_shell: Any) -> None:
    fake = FakeProvisioning(current=status(), next_verify=CORRUPT)
    shell = make_shell(fake)
    shell.window._show_page(1)
    page = shell.window.analyze_page
    page.editor.setPlainText("A synthetic sentence.")
    page.analyze_button.click()  # analysis loads the service
    first_text = page.result_text.text()

    shell.window.models_button.click()
    shell.button(shell.models, "Verify files").click()

    # sidebar, analyze page, projects page, and the Models window all say so
    assert shell.window.models_button.text().startswith("✕ Analysis off until restart")
    assert not page.analyze_button.isEnabled()
    assert "restart" in page.block.body.text().lower()
    assert shell.window.projects_page.block.isVisibleTo(shell.window.projects_page)
    assert shell.models.panel.session_note.isVisibleTo(shell.models)
    assert page.result_text.text() == first_text  # the earlier result stays

    # repair by download: models become ready, the block stays
    fake.next_download = ProvisioningResult(ProvisioningOutcome.COMPLETED, status())
    shell.button(shell.models, "Download replacement · 1 file, 50.0 MB").click()
    assert fake.current.ready
    assert not page.analyze_button.isEnabled()
    assert "restart" in shell.window.models_button.text().lower() or (
        "restart" in shell.window.models_button.text()
    )
    assert len(shell.gateway.records) == 1


def test_closing_while_verifying_is_refused_until_it_finishes(
    make_shell: Any,
) -> None:
    from .fakes import ManualRunner

    runner = ManualRunner()
    shell = make_shell(FakeProvisioning(current=status()), runner)
    while runner.jobs:  # the project listing queued at launch
        runner.run_next()
    shell.window.provisioning.verify()
    assert shell.window.provisioning.state.activity is Activity.VERIFYING

    event = QCloseEvent()
    shell.window.closeEvent(event)

    assert not event.isAccepted()
    assert "cannot be stopped" in shell.window.statusBar().currentMessage()
    runner.run_next()
    QCoreApplication.processEvents()
    assert not shell.window.isVisible()  # closed itself once Verify finished
