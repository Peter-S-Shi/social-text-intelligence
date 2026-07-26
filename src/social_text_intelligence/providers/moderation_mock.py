"""Deterministic fixture-backed mock moderation recommendations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import (
    MockModerationRecommendation,
    ModerationTrainingCase,
)
from ..contracts.errors import ProviderError


@runtime_checkable
class ModerationRecommendationProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def version(self) -> str: ...

    def recommend(
        self, case: ModerationTrainingCase
    ) -> MockModerationRecommendation | None: ...


class FixtureModerationRecommendationProvider:
    """Return the independently authored mock recommendation frozen in a case."""

    def __init__(
        self,
        *,
        provider_id: str = "sti-fixture-moderation-mock",
        version: str = "1.0.0",
    ) -> None:
        self._provider_id = provider_id
        self._version = version

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def version(self) -> str:
        return self._version

    def recommend(
        self, case: ModerationTrainingCase
    ) -> MockModerationRecommendation | None:
        recommendation = case.mock_recommendation
        if recommendation is None:
            return None
        if (
            recommendation.provider_id != self.provider_id
            or recommendation.provider_version != self.version
        ):
            raise ProviderError(
                provider=self.provider_id,
                code="mock_provider_mismatch",
                message=(
                    "The case mock recommendation does not match the configured "
                    "synthetic provider."
                ),
            )
        return recommendation
