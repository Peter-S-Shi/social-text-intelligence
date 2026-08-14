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


class ModelInputTooLongError(ProviderError):
    """The pinned model cannot consume the complete encoded input."""

    def __init__(
        self,
        *,
        provider: str,
        encoded_length: int,
        max_input_tokens: int,
    ) -> None:
        super().__init__(
            provider=provider,
            code="model_input_too_long",
            message=(
                "The complete text exceeds the current model encoded-input limit "
                f"({encoded_length} tokens including special tokens; maximum "
                f"{max_input_tokens}). No truncation or partial analysis was performed."
            ),
        )
        self.encoded_length = encoded_length
        self.max_input_tokens = max_input_tokens


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
