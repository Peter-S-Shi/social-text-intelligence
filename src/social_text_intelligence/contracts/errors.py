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
        "The models folder could not be read or written. Free disk space or "
        "check permissions, then try again."
    ),
    "storage_full": (
        "There is not enough free disk space for the models. Free some disk "
        "space and try again; finished files and a partial download are kept."
    ),
    "source_unreadable": "The chosen folder could not be read.",
    "provisioning_in_progress": (
        "Another model download or import is already running."
    ),
    "provisioning_elsewhere": (
        "Another window of this app is already changing the models folder. "
        "Wait for it to finish there, or close that window, then try again. "
        "Nothing was changed here."
    ),
}


class ModelProvisioningError(SocialTextIntelligenceError):
    """Provisioning failed; the fixed message carries no path, URL, or reply."""

    def __init__(self, code: str) -> None:
        message = _PROVISIONING_MESSAGES[code]
        super().__init__(message)
        self.code = code
        self.message = message


class AnalysisUnavailableError(SocialTextIntelligenceError):
    """Analysis cannot run right now for any input (setup or a session rule).

    A batch re-raises it instead of recording it as a row failure, so nothing is
    committed and the analysis lease is released.
    """


SESSION_BLOCK_MESSAGE = (
    "Analysis is off until you restart the app. A model check found damaged "
    "files after analysis had started in this session, and repairing the files "
    "does not turn analysis back on here. Close and reopen the app to check the "
    "models again and load them fresh."
)


class AnalysisSessionBlockedError(AnalysisUnavailableError):
    """Analysis was requested after a mid-session corruption finding (H2)."""

    def __init__(self) -> None:
        super().__init__(SESSION_BLOCK_MESSAGE)
        self.code = "analysis_session_blocked"
        self.message = SESSION_BLOCK_MESSAGE


class AnalysisSetupError(AnalysisUnavailableError):
    """The model runtime could not be set up (load failure or missing runtime).

    The provider's code and fixed message are kept. As an unavailability it fails a
    whole batch instead of being recorded on every row.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ModelsNotReadyError(AnalysisUnavailableError):
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
