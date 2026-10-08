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
from ..contracts.errors import (
    SESSION_BLOCK_MESSAGE,
    AnalysisSessionBlockedError,
    AnalysisSetupError,
    ProviderError,
)

# A provider that cannot load its model fails every row alike: a whole-run failure.
_SETUP_CODES = frozenset({"model_load_failed", "missing_model_dependencies"})


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
        self._loading = 0  # analyses in flight; the first one builds the service

    @property
    def initialized(self) -> bool:
        """Part of the ``AnalysisGateway`` protocol this gate stands in for."""

        return self._inner.initialized

    @property
    def session_blocked(self) -> bool:
        return self._session_blocked

    def note_verify_result(self, status: ModelsStatus) -> None:
        """Latch the block when Verify confirms damage after the service loaded."""

        damaged = any(item.readiness is Readiness.CORRUPT for item in status.models)
        if damaged and (self._inner.initialized or self._loading):
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
        with self._lock:
            self._loading += 1
        try:
            return self._inner.analyze(record)
        except ProviderError as error:
            if error.code in _SETUP_CODES:
                raise AnalysisSetupError(error.code, error.message) from None
            raise
        finally:
            with self._lock:
                self._loading -= 1


__all__ = [
    "SESSION_BLOCK_MESSAGE",
    "AnalysisAvailability",
    "AnalysisGate",
    "AnalysisSessionBlockedError",
]
