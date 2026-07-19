"""Thread-safe lazy construction for reusable local analysis providers."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from ..contracts import AnalysisReport, NormalizedTextInput
from .analysis import AnalysisService


class LazyAnalysisService:
    """Build one analysis service on first use and reuse it for later requests."""

    def __init__(self, factory: Callable[[], AnalysisService]) -> None:
        self._factory = factory
        self._service: AnalysisService | None = None
        self._lock = Lock()

    @property
    def initialized(self) -> bool:
        return self._service is not None

    def _get_service(self) -> AnalysisService:
        service = self._service
        if service is not None:
            return service
        with self._lock:
            service = self._service
            if service is None:
                service = self._factory()
                self._service = service
        return service

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        return self._get_service().analyze(record)
