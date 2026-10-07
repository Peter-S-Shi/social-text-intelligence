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


class ProjectStorageError(SocialTextIntelligenceError):
    """Durable project storage failed; the message never echoes project content."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_PROVISIONING_MESSAGES = {
    "network_unavailable": (
        "The model source could not be reached. Check the connection and "
        "download again; finished and partial files are kept."
    ),
    "download_rejected": (
        "The model source returned an unexpected response. Try again later "
        "or use a models folder."
    ),
    "checksum_mismatch": (
        "A model file did not match its approved checksum and was discarded. "
        "Download again or choose a different models folder."
    ),
    "storage_failed": (
        "The models folder could not be written. Free disk space or check "
        "permissions, then try again."
    ),
    "source_unreadable": "The chosen folder could not be read.",
    "provisioning_in_progress": (
        "Another model download or import is already running."
    ),
}


class ModelProvisioningError(SocialTextIntelligenceError):
    """Provisioning failed; the fixed message carries no path, URL, or reply."""

    def __init__(self, code: str) -> None:
        message = _PROVISIONING_MESSAGES[code]
        super().__init__(message)
        self.code = code
        self.message = message


class ModelsNotReadyError(SocialTextIntelligenceError):
    """Analysis was requested while a required local model is not ready."""

    def __init__(self, not_ready: tuple[str, ...]) -> None:
        message = (
            "The required local models are not ready. Download them or use a "
            "models folder before analysing."
        )
        super().__init__(message)
        self.code = "models_not_ready"
        self.message = message
        self.not_ready = not_ready


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
