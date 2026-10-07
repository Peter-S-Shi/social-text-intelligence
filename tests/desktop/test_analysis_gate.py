"""H2: a confirmed corruption after analysis loaded blocks analysis until restart."""

from __future__ import annotations

import pytest

from social_text_intelligence.application.model_provisioning import Readiness
from social_text_intelligence.contracts import AnalysisReport, NormalizedTextInput
from social_text_intelligence.desktop.gate import (
    AnalysisAvailability,
    AnalysisGate,
    AnalysisSessionBlockedError,
)

from .fakes import StubGateway, status, synthetic_report


def record() -> NormalizedTextInput:
    return NormalizedTextInput.from_text(
        "A synthetic sentence.", language="en", max_text_length=1000
    )


def loaded_gate() -> tuple[AnalysisGate, StubGateway]:
    inner = StubGateway(report=synthetic_report())
    gate = AnalysisGate(inner)
    gate.analyze(record())  # the first analysis builds the service
    assert inner.initialized
    return gate, inner


def test_available_only_when_both_models_are_ready() -> None:
    gate = AnalysisGate(StubGateway())
    assert gate.availability(status()) is AnalysisAvailability.AVAILABLE
    assert (
        gate.availability(status(emotion=Readiness.INCOMPLETE))
        is AnalysisAvailability.MODELS_NOT_READY
    )


def test_corruption_before_the_service_loads_is_not_a_session_block() -> None:
    gate = AnalysisGate(StubGateway())
    gate.note_verify_result(status(sentiment=Readiness.CORRUPT))
    assert not gate.session_blocked
    # readiness alone decides, so repairing makes analysis available again
    assert gate.availability(status()) is AnalysisAvailability.AVAILABLE


def test_corruption_after_the_service_loaded_blocks_the_rest_of_the_session() -> None:
    gate, inner = loaded_gate()

    gate.note_verify_result(status(emotion=Readiness.CORRUPT))

    assert gate.session_blocked
    assert gate.availability(status()) is AnalysisAvailability.SESSION_BLOCKED
    with pytest.raises(AnalysisSessionBlockedError) as blocked:
        gate.analyze(record())
    assert blocked.value.code == "analysis_session_blocked"
    assert len(inner.records) == 1  # nothing reached the loaded service again


def test_repair_never_lifts_the_block_in_this_process() -> None:
    gate, inner = loaded_gate()
    gate.note_verify_result(status(sentiment=Readiness.CORRUPT))

    gate.note_verify_result(status())  # a later Verify finds everything fine

    assert gate.session_blocked
    assert gate.availability(status()) is AnalysisAvailability.SESSION_BLOCKED
    with pytest.raises(AnalysisSessionBlockedError):
        gate.analyze(record())
    assert len(inner.records) == 1


def test_a_clean_verify_after_loading_does_not_block() -> None:
    gate, _ = loaded_gate()
    gate.note_verify_result(status())
    assert not gate.session_blocked
    assert gate.availability(status()) is AnalysisAvailability.AVAILABLE


def test_the_block_message_says_repair_needs_a_restart() -> None:
    message = AnalysisSessionBlockedError().message
    assert "restart" in message.lower() or "reopen" in message.lower()
    assert "repair" in message.lower()


def test_damage_confirmed_while_the_first_analysis_is_still_loading_blocks() -> None:
    gate_box: list[AnalysisGate] = []

    class VerifyDuringLoad(StubGateway):
        def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
            # the service is not built yet, but this analysis is already loading
            gate_box[0].note_verify_result(status(emotion=Readiness.CORRUPT))
            return super().analyze(record)

    gate = AnalysisGate(VerifyDuringLoad(report=object()))  # type: ignore[arg-type]
    gate_box.append(gate)

    gate.analyze(record())

    assert gate.session_blocked
