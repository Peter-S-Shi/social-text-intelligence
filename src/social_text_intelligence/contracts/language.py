"""Detected-language evidence, kept apart from the language a file supplies.

A person may supply a language tag for a record (trusted, imported metadata that the
Insights Language grouping uses unchanged). Separately, STI can run a local language
detector over the text. The two can disagree and both stay true: "supplied: en" and
"detected: fr" coexist. This module only describes the detector's evidence and what
it means for the approved models; it never rewrites the supplied value, never changes
a label, and never says anything about the writer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .errors import ValidationError


class LanguageStatus(StrEnum):
    SUPPORTED = "supported"  # detected, and the approved models cover it
    UNSUPPORTED = "unsupported"  # detected, and the approved models do not cover it
    UNDETERMINED = "undetermined"  # the detector would not commit to a language
    NOT_ASSESSED = "not_assessed"  # no detection result exists for this text


class LanguageReason(StrEnum):
    NOT_RUN = "not_run"  # no check was part of this analysis (e.g. an older project)
    DETECTOR_UNAVAILABLE = "detector_unavailable"
    DETECTOR_FAILED = "detector_failed"
    LOW_SCORE = "low_score"
    NO_LANGUAGE_CONTENT = "no_language_content"


_UNDETERMINED_REASONS = {LanguageReason.LOW_SCORE, LanguageReason.NO_LANGUAGE_CONTENT}
_NOT_ASSESSED_REASONS = {
    LanguageReason.NOT_RUN,
    LanguageReason.DETECTOR_UNAVAILABLE,
    LanguageReason.DETECTOR_FAILED,
}


def _invalid(field: str, message: str) -> ValidationError:
    return ValidationError(
        field=field, code="invalid_language_assessment", message=message
    )


@dataclass(frozen=True, slots=True)
class DetectorInfo:
    """Enough to audit which detector produced a result, and how it abstains."""

    name: str
    version: str
    model: str
    min_score: float

    def __post_init__(self) -> None:
        for field in ("name", "version", "model"):
            if not getattr(self, field).strip():
                raise _invalid(field, f"Detector {field} must not be empty.")
        if not math.isfinite(self.min_score) or not 0.0 <= self.min_score <= 1.0:
            raise _invalid("min_score", "Detector min_score must be between 0 and 1.")

    @property
    def label(self) -> str:
        return f"{self.name} {self.version} ({self.model})"


@dataclass(frozen=True, slots=True)
class LanguageAssessment:
    """What the language check concluded for one analysed text.

    ``score`` is the detector's own score for ``detected_language``. It is not a
    calibrated probability and is never presented as one.
    """

    status: LanguageStatus
    detected_language: str | None = None
    score: float | None = None
    supported_languages: tuple[str, ...] = ()
    detector: DetectorInfo | None = None
    reason: LanguageReason | None = None

    def __post_init__(self) -> None:
        status = self.status
        languages = tuple(item.strip().lower() for item in self.supported_languages)
        object.__setattr__(self, "supported_languages", languages)
        if status in (LanguageStatus.SUPPORTED, LanguageStatus.UNSUPPORTED):
            detected = (self.detected_language or "").strip().lower()
            if not detected:
                raise _invalid("detected_language", "A detected language is required.")
            object.__setattr__(self, "detected_language", detected)
            if (
                self.score is None
                or not math.isfinite(self.score)
                or not 0.0 <= self.score <= 1.0
            ):
                raise _invalid("score", "A detector score between 0 and 1 is required.")
            if self.detector is None or self.reason is not None:
                raise _invalid("detector", "A detected language names its detector.")
            if (detected in languages) is not (status is LanguageStatus.SUPPORTED):
                raise _invalid(
                    "status", "Status must follow the models' supported languages."
                )
            return
        if self.detected_language is not None or self.score is not None:
            raise _invalid("detected_language", "No language was detected.")
        allowed = (
            _UNDETERMINED_REASONS
            if status is LanguageStatus.UNDETERMINED
            else _NOT_ASSESSED_REASONS
        )
        if self.reason not in allowed:
            raise _invalid("reason", "The reason does not fit this status.")
        if status is LanguageStatus.UNDETERMINED and self.detector is None:
            raise _invalid("detector", "An undetermined result names its detector.")

    @classmethod
    def not_assessed(
        cls,
        reason: LanguageReason = LanguageReason.NOT_RUN,
        *,
        supported_languages: tuple[str, ...] = (),
        detector: DetectorInfo | None = None,
    ) -> LanguageAssessment:
        return cls(
            status=LanguageStatus.NOT_ASSESSED,
            supported_languages=supported_languages,
            detector=detector,
            reason=reason,
        )

    @property
    def check_failed(self) -> bool:
        """The check was attempted but could not give an answer."""

        return self.status is LanguageStatus.NOT_ASSESSED and (
            self.reason is not LanguageReason.NOT_RUN
        )

    @property
    def needs_attention(self) -> bool:
        """Whether a person reading the model's labels should be warned first."""

        if self.status is LanguageStatus.NOT_ASSESSED:
            return self.check_failed
        return self.status is not LanguageStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class Detection:
    """One detector's raw answer: a language and its score, or an honest abstention."""

    language: str | None
    score: float | None = None
    reason: LanguageReason | None = None

    def __post_init__(self) -> None:
        if self.language is None:
            if self.score is not None or self.reason not in _UNDETERMINED_REASONS:
                raise _invalid("language", "An abstention names why, and has no score.")
        elif self.score is None or self.reason is not None:
            raise _invalid("score", "A detected language has a score and no reason.")


class LanguageDetectorUnavailable(Exception):
    """The detector cannot run here (for example, its package is not installed)."""
