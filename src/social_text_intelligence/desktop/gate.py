"""The single analysis gate for the desktop session (owner decision H2).

If the analysis service has already loaded its models and an explicit Verify then
confirms damage, every later analysis is blocked for the rest of the process.
Repairing the files does not re-enable it: a restart re-checks readiness and loads
the verified models fresh. Nothing is unloaded or reloaded in-process.
"""

from __future__ import annotations

from enum import StrEnum
from threading import Lock

from ..application.model_provisioning import ModelsStatus, Readiness
from ..application.settings import AnalysisGateway
from ..contracts import AnalysisReport, NormalizedTextInput
from ..contracts.errors import SocialTextIntelligenceError

SESSION_BLOCK_MESSAGE = (
    "Analysis is off until you restart the app. A model check found damaged "
    "files after analysis had started in this session, and repairing the files "
    "does not turn analysis back on here. Close and reopen the app to check the "
    "models again and load them fresh."
)


class AnalysisSessionBlockedError(SocialTextIntelligenceError):
    """Analysis was requested after a mid-session corruption finding."""

    def __init__(self) -> None:
        super().__init__(SESSION_BLOCK_MESSAGE)
        self.code = "analysis_session_blocked"
        self.message = SESSION_BLOCK_MESSAGE


class AnalysisAvailability(StrEnum):
    AVAILABLE = "available"
    MODELS_NOT_READY = "models_not_ready"
    SESSION_BLOCKED = "session_blocked"


class AnalysisGate:
    """Wraps the analysis gateway; every analysis entry point goes through it."""

    def __init__(self, inner: AnalysisGateway) -> None:
        self._inner = inner
        self._lock = Lock()
        self._session_blocked = False

    @property
    def initialized(self) -> bool:
        return self._inner.initialized

    @property
    def session_blocked(self) -> bool:
        return self._session_blocked

    def note_verify_result(self, status: ModelsStatus) -> None:
        """Latch the block when Verify confirms damage after the service loaded."""

        damaged = any(item.readiness is Readiness.CORRUPT for item in status.models)
        if damaged and self._inner.initialized:
            with self._lock:
                self._session_blocked = True

    def availability(self, status: ModelsStatus) -> AnalysisAvailability:
        if self._session_blocked:
            return AnalysisAvailability.SESSION_BLOCKED
        if not status.ready:
            return AnalysisAvailability.MODELS_NOT_READY
        return AnalysisAvailability.AVAILABLE

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if self._session_blocked:
            raise AnalysisSessionBlockedError
        return self._inner.analyze(record)
