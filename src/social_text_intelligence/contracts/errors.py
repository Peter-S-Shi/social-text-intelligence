"""Explicit error contracts shared across the application core."""

from __future__ import annotations


class SocialTextIntelligenceError(Exception):
    """Base class for expected application errors."""


class ValidationError(SocialTextIntelligenceError):
    """A typed input or result contract failed validation."""

    def __init__(self, *, field: str, code: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message


class ProviderError(SocialTextIntelligenceError):
    """A model provider could not produce a valid application result."""

    def __init__(self, *, provider: str, code: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.message = message


class UnsupportedLanguageError(ProviderError):
    """The selected provider does not support the input language."""

    def __init__(self, *, provider: str, language: str) -> None:
        super().__init__(
            provider=provider,
            code="unsupported_language",
            message=f"Provider does not support language: {language}",
        )
        self.language = language


class InvalidProviderOutputError(ProviderError):
    """A provider returned data that violates the normalized result contract."""

    def __init__(self, *, provider: str, message: str) -> None:
        super().__init__(
            provider=provider,
            code="invalid_provider_output",
            message=message,
        )
