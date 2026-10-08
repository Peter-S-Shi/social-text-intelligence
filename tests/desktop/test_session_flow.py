"""Controller + gate + analysis page together, at the composition seam."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import pytest

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
    ProvisioningResult,
    Readiness,
)
from social_text_intelligence.contracts import ProviderError
from social_text_intelligence.contracts.errors import ModelsNotReadyError
from social_text_intelligence.desktop.analysis import (
    AnalysisPageController,
    analysis_error,
)
from social_text_intelligence.desktop.composition import (
    DesktopServices,
    build_analysis_controller,
    build_desktop_services,
    build_provisioning_controller,
)
from social_text_intelligence.desktop.controller import ProvisioningController
from social_text_intelligence.desktop.gate import (
    AnalysisAvailability,
    AnalysisSessionBlockedError,
)
from social_text_intelligence.desktop.panel import build_panel
from social_text_intelligence.infrastructure.app_data import AppDataLocations

from .fakes import (
    FakeProvisioning,
    ImmediateRunner,
    StubGateway,
    status,
    synthetic_report,
)

Parts: TypeAlias = tuple[
    DesktopServices,
    FakeProvisioning,
    StubGateway,
    ProvisioningController,
    AnalysisPageController,
]

CORRUPT = status(Readiness.READY, Readiness.CORRUPT)


@pytest.fixture
def parts(tmp_path: Path) -> Parts:
    fake = FakeProvisioning(current=status())
    gateway = StubGateway(report=synthetic_report())
    services = build_desktop_services(
        AppDataLocations(tmp_path), provisioning=fake, analysis=gateway
    )
    runner = ImmediateRunner()
    controller = build_provisioning_controller(services, runner)
    analysis = build_analysis_controller(services, runner)
    controller.refresh()
    return services, fake, gateway, controller, analysis


def availability(
    services: DesktopServices, controller: ProvisioningController
) -> AnalysisAvailability:
    return services.gate.availability(controller.state.status)


def test_analysis_runs_when_models_are_ready_and_shows_a_result(parts: Parts) -> None:
    services, _, gateway, controller, analysis = parts
    assert availability(services, controller) is AnalysisAvailability.AVAILABLE

    analysis.submit("A synthetic sentence.")

    result = analysis.state.result
    assert result is not None and analysis.state.error is None
    assert result.sentiment and result.emotion
    assert len(gateway.records) == 1 and gateway.initialized


def test_h2_verify_damage_after_analysis_blocks_every_later_entry_point(
    parts: Parts,
) -> None:
    services, fake, gateway, controller, analysis = parts
    analysis.submit("A synthetic sentence.")  # the service is now loaded
    first = analysis.state.result

    fake.next_verify = CORRUPT
    controller.verify()

    assert availability(services, controller) is AnalysisAvailability.SESSION_BLOCKED
    analysis.submit("Another synthetic sentence.")
    error = analysis.state.error
    assert error is not None and error.code == "analysis_session_blocked"
    assert error.offers_models
    assert len(gateway.records) == 1  # the loaded service was not called again
    assert analysis.state.result == first  # the earlier result stays as it was
    # the direct use-case entry point is gated too
    with pytest.raises(AnalysisSessionBlockedError):
        services.use_cases.analyze_text("x y z", max_text_length=1000)


def test_h2_repair_by_download_does_not_unblock_until_restart(parts: Parts) -> None:
    services, fake, gateway, controller, analysis = parts
    analysis.submit("A synthetic sentence.")
    fake.next_verify = CORRUPT
    controller.verify()

    fake.next_download = ProvisioningResult(ProvisioningOutcome.COMPLETED, status())
    controller.download(("emotion",))

    assert controller.state.status.ready  # models repaired on disk
    assert availability(services, controller) is AnalysisAvailability.SESSION_BLOCKED
    panel = build_panel(
        controller.state, availability(services, controller), window="models"
    )
    assert panel.report is not None
    assert "Analysis stays off in this session" in panel.report.body

    analysis.submit("Still blocked.")
    assert analysis.state.error is not None
    assert analysis.state.error.code == "analysis_session_blocked"

    fake.next_verify = status()  # a clean Verify does not lift it either
    controller.verify()
    assert availability(services, controller) is AnalysisAvailability.SESSION_BLOCKED
    assert len(gateway.records) == 1

    # "restart": a fresh process builds a fresh gate over the repaired models
    restarted = build_desktop_services(
        AppDataLocations(services.locations.root),
        provisioning=fake,
        analysis=StubGateway(report=synthetic_report()),
    )
    assert restarted.gate.availability(fake.status()) is AnalysisAvailability.AVAILABLE


def test_damage_found_before_analysis_ever_loaded_is_not_an_h2_block(
    parts: Parts,
) -> None:
    services, fake, _, controller, _ = parts
    fake.next_verify = CORRUPT
    controller.verify()
    assert availability(services, controller) is AnalysisAvailability.MODELS_NOT_READY

    fake.next_download = ProvisioningResult(ProvisioningOutcome.COMPLETED, status())
    controller.download(("emotion",))
    assert availability(services, controller) is AnalysisAvailability.AVAILABLE


def test_models_not_ready_is_an_error_with_a_route_to_models() -> None:
    error = analysis_error(ModelsNotReadyError(("emotion",)))
    assert error.code == "models_not_ready" and error.offers_models


def test_model_load_failure_offers_verify_and_not_the_v1_offline_text() -> None:
    error = analysis_error(
        ProviderError(provider="p", code="model_load_failed", message="V1 offline mode")
    )
    assert error.offers_verify and error.offers_models
    assert "offline mode" not in error.body
    assert "Verify" in error.body


def test_unexpected_analysis_errors_do_not_leak_text() -> None:
    error = analysis_error(RuntimeError("C:/Users/someone/private.txt"))
    assert "private" not in error.body and "private" not in error.title


def test_blank_input_is_a_validation_message_not_a_crash(parts: Parts) -> None:
    _, _, gateway, _, analysis = parts
    analysis.submit("   ")
    assert analysis.state.error is not None
    assert gateway.records == []


def test_only_one_analysis_runs_at_a_time() -> None:
    from .fakes import ManualRunner

    runner = ManualRunner()
    page = AnalysisPageController(lambda text: synthetic_report(), runner)
    assert page.submit("a b c")
    assert not page.submit("d e f")
    assert page.state.running
    runner.run_next()
    assert not page.state.running and page.state.result is not None
