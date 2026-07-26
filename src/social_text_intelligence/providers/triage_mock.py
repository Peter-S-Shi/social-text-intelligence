"""Deterministic fixture-backed support triage suggestions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts.errors import ProviderError
from ..contracts.triage import MockTriageSuggestion, SupportTicket

EXPECTED_MOCK_PROVIDER_ID = "sti-fixture-support-triage-mock"
EXPECTED_MOCK_PROVIDER_VERSION = "1.0.0"


@runtime_checkable
class TriageSuggestionProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def version(self) -> str: ...

    def suggest(self, ticket: SupportTicket) -> MockTriageSuggestion | None: ...


class FixtureTriageSuggestionProvider:
    """Return a ticket's frozen synthetic suggestion without inference."""

    @property
    def provider_id(self) -> str:
        return EXPECTED_MOCK_PROVIDER_ID

    @property
    def version(self) -> str:
        return EXPECTED_MOCK_PROVIDER_VERSION

    def suggest(self, ticket: SupportTicket) -> MockTriageSuggestion | None:
        suggestion = ticket.mock_suggestion
        if suggestion is None:
            return None
        if (
            suggestion.provider_id != self.provider_id
            or suggestion.provider_version != self.version
        ):
            raise ProviderError(
                provider=self.provider_id,
                code="mock_provider_mismatch",
                message=(
                    "The ticket mock does not match the configured fixture "
                    "provider."
                ),
            )
        return suggestion
