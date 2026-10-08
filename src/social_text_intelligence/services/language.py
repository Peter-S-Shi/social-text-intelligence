"""Turn a language detection into evidence and into words a person can trust.

The approved sentiment and emotion models are English models. Whether a text is in a
language they support is decided here from the models' own capability metadata and a
local detector's answer about the text, never from a CSV language field. An
unsupported or undetermined language is a warning, not a reclassification: the text
is still analysed and its labels are left exactly as the models produced them.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..contracts.language import (
    LanguageAssessment,
    LanguageDetectorUnavailable,
    LanguageReason,
    LanguageStatus,
)
from ..providers.base import LanguageDetector

if TYPE_CHECKING:
    from .batch import BatchResult

# Only a display aid: an unknown code is shown as the code itself.
LANGUAGE_NAMES = {
    "af": "Afrikaans", "ar": "Arabic", "bg": "Bulgarian", "bn": "Bengali",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish", "de": "German",
    "el": "Greek", "en": "English", "es": "Spanish", "et": "Estonian",
    "fa": "Persian", "fi": "Finnish", "fr": "French", "ga": "Irish", "gu": "Gujarati",
    "he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
    "ja": "Japanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "lt": "Lithuanian", "lv": "Latvian",
    "mk": "Macedonian", "ml": "Malayalam", "mr": "Marathi", "ms": "Malay",
    "my": "Burmese", "ne": "Nepali", "nl": "Dutch", "no": "Norwegian",
    "pa": "Punjabi", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian",
    "ru": "Russian", "sk": "Slovak", "sl": "Slovenian", "sq": "Albanian",
    "sr": "Serbian", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil", "te": "Telugu",
    "th": "Thai", "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "vi": "Vietnamese", "zh": "Chinese", "yue": "Cantonese",
}  # fmt: skip


def language_name(code: str) -> str:
    name = LANGUAGE_NAMES.get(code.lower())
    return f"{name} ({code})" if name else code


def assess_language(
    detector: LanguageDetector | None,
    text: str,
    supported: Sequence[str],
) -> LanguageAssessment:
    """Assess one text. This never raises: a detector problem is a result."""

    languages = tuple(item.lower() for item in supported)
    if detector is None:
        # A fresh analysis with no detector configured is a check that could not
        # run, never a silent pass. ("Not run" is only for results stored earlier.)
        return LanguageAssessment.not_assessed(
            LanguageReason.DETECTOR_UNAVAILABLE, supported_languages=languages
        )
    try:
        detection = detector.detect(text)
        info = detector.info
        if detection.language is None:
            return LanguageAssessment(
                status=LanguageStatus.UNDETERMINED,
                supported_languages=languages,
                detector=info,
                reason=detection.reason,
            )
        detected = detection.language.lower()
        return LanguageAssessment(
            status=(
                LanguageStatus.SUPPORTED
                if detected in languages
                else LanguageStatus.UNSUPPORTED
            ),
            detected_language=detected,
            score=detection.score,
            supported_languages=languages,
            detector=info,
        )
    except LanguageDetectorUnavailable:
        return LanguageAssessment.not_assessed(
            LanguageReason.DETECTOR_UNAVAILABLE, supported_languages=languages
        )
    except Exception:
        # The failure text may contain the record's text, so it is not kept; an
        # answer that breaks the evidence contract is a failed check too.
        return LanguageAssessment.not_assessed(
            LanguageReason.DETECTOR_FAILED, supported_languages=languages
        )


@dataclass(frozen=True, slots=True)
class LanguageNotice:
    """The wording for one assessment, shared by every surface that shows it."""

    headline: str
    detail: str
    warns: bool

    @property
    def text(self) -> str:
        """The headline for a surface that has no icon: a warning says so in words."""

        return f"Warning: {self.headline}" if self.warns else self.headline


def _models(languages: Sequence[str]) -> str:
    """What the approved models cover, from their capability metadata."""

    if not languages:
        return "The approved models' supported languages are not recorded"
    names = ", ".join(language_name(code) for code in sorted(languages))
    return f"The approved models support only {names}"


_UNCHANGED = "The text was still analysed and its labels have not been changed."


def describe_language(assessment: LanguageAssessment) -> LanguageNotice:
    status = assessment.status
    models = _models(assessment.supported_languages)
    detected = language_name(assessment.detected_language or "")
    if status is LanguageStatus.SUPPORTED:
        return LanguageNotice(
            headline=f"Detected language: {detected}",
            detail=(
                "A language the approved models support. Detected automatically on "
                "this device; the detector's score is not a probability."
            ),
            warns=False,
        )
    if status is LanguageStatus.UNSUPPORTED:
        return LanguageNotice(
            headline=(
                f"Detected language: {detected}, not supported by the approved models"
            ),
            detail=(
                f"{models}, so these results may be unreliable. {_UNCHANGED} "
                "This describes the wording of the text only."
            ),
            warns=True,
        )
    if status is LanguageStatus.UNDETERMINED:
        return LanguageNotice(
            headline="Detected language: not confidently determined",
            detail=(
                "There was too little language to tell (for example a very short "
                f"text, symbols, links, or numbers). {models}, so read these "
                f"results with care. {_UNCHANGED}"
            ),
            warns=True,
        )
    if assessment.reason is LanguageReason.DETECTOR_UNAVAILABLE:
        return LanguageNotice(
            headline="Language check unavailable",
            detail=(
                "The language check could not run on this device, so whether this "
                f"text is in a supported language is unknown. {models}. "
                f"{_UNCHANGED}"
            ),
            warns=True,
        )
    if assessment.reason is LanguageReason.DETECTOR_FAILED:
        return LanguageNotice(
            headline="Language check failed for this text",
            detail=(
                "The language check did not finish, so whether this text is in a "
                f"supported language is unknown. {models}. {_UNCHANGED}"
            ),
            warns=True,
        )
    return LanguageNotice(
        headline="Detected language: not assessed",
        detail=(
            "No language check was run for this result, for example because it "
            "was analysed before language checks existed. Nothing is assumed "
            "about its language."
        ),
        warns=False,
    )


@dataclass(frozen=True, slots=True)
class LanguageSummary:
    """How many analysed texts fall in each language-check state."""

    total: int
    supported: int
    unsupported: int
    undetermined: int
    unavailable: int  # the check was attempted and could not finish
    not_assessed: int  # no check was part of the analysis (e.g. an older project)
    unsupported_languages: tuple[tuple[str, int], ...]
    supported_languages: tuple[str, ...] = ()  # what the approved models cover

    @property
    def attention_count(self) -> int:
        return self.unsupported + self.undetermined + self.unavailable


def summarize_languages(assessments: Iterable[LanguageAssessment]) -> LanguageSummary:
    items = tuple(assessments)
    states = Counter(
        "unavailable" if item.check_failed else item.status.value for item in items
    )
    others = Counter(
        item.detected_language
        for item in items
        if item.status is LanguageStatus.UNSUPPORTED and item.detected_language
    )
    ranked = sorted(others.items(), key=lambda pair: (-pair[1], pair[0]))
    return LanguageSummary(
        total=len(items),
        supported=states[LanguageStatus.SUPPORTED.value],
        unsupported=states[LanguageStatus.UNSUPPORTED.value],
        undetermined=states[LanguageStatus.UNDETERMINED.value],
        unavailable=states["unavailable"],
        not_assessed=states[LanguageStatus.NOT_ASSESSED.value],
        unsupported_languages=tuple(ranked),
        supported_languages=tuple(
            sorted({code for item in items for code in item.supported_languages})
        ),
    )


def summarize_result(result: BatchResult) -> LanguageSummary:
    """The language check over every successfully analysed row of a batch."""

    return summarize_languages(
        outcome.report.language
        for outcome in result.outcomes
        if outcome.report is not None
    )


def describe_summary(summary: LanguageSummary) -> LanguageNotice | None:
    """One notice for a whole analysed set, or None when there is nothing analysed."""

    if summary.total == 0:
        return None
    if summary.attention_count:
        parts = []
        if summary.unsupported:
            named = ", ".join(
                f"{language_name(code)} {count}"
                for code, count in summary.unsupported_languages
            )
            parts.append(f"{summary.unsupported} in another language ({named})")
        if summary.undetermined:
            parts.append(f"{summary.undetermined} not confidently determined")
        if summary.unavailable:
            parts.append(f"{summary.unavailable} could not be checked")
        return LanguageNotice(
            headline=(
                f"Language check: {summary.attention_count} of {summary.total} "
                "analysed texts are not confirmed as a supported language"
            ),
            detail=(
                f"{'; '.join(parts)}. {_models(summary.supported_languages)}, so "
                f"read those results with care. "
                f"{_UNCHANGED}"
            ),
            warns=True,
        )
    if summary.not_assessed == summary.total:
        return LanguageNotice(
            headline="Language check: not assessed",
            detail=(
                "These results were analysed before language checks existed, so "
                "nothing is assumed about their language."
            ),
            warns=False,
        )
    note = (
        f" {summary.not_assessed} were analysed before language checks existed."
        if summary.not_assessed
        else ""
    )
    return LanguageNotice(
        headline=(
            f"Language check: {summary.supported} of {summary.total} analysed "
            "texts were detected in a supported language"
        ),
        detail=f"Detected automatically on this device.{note}",
        warns=False,
    )


def language_signal(assessment: LanguageAssessment, separator: str = "|") -> str:
    """One cell of language evidence, for snapshots frozen beside the AI signals."""

    cells = language_export_cells(assessment)
    return separator.join(
        str(cells[key])
        for key in ("language_status", "detected_language", "language_score")
    ) + f"{separator}{cells['language_detector']}"


def language_short(assessment: LanguageAssessment) -> str:
    """A few words for a table cell; the full notice is shown elsewhere."""

    status = assessment.status
    if status is LanguageStatus.SUPPORTED or status is LanguageStatus.UNSUPPORTED:
        name = language_name(assessment.detected_language or "")
        return f"{'⚠ ' if status is LanguageStatus.UNSUPPORTED else ''}{name}"
    if status is LanguageStatus.UNDETERMINED:
        return "⚠ not confidently determined"
    return "⚠ check unavailable" if assessment.check_failed else "not assessed"


def language_caveat(assessment: LanguageAssessment) -> str:
    """The warning headline when the language needs attention, else nothing."""

    notice = describe_language(assessment)
    return notice.headline if notice.warns else ""


LANGUAGE_EXPORT_FIELDS = (
    "detected_language",
    "language_status",
    "language_score",
    "language_reason",
    "language_detector",
)

LANGUAGE_FIELDS_NOTE = (
    "The language column is the value supplied in the file and is never changed. "
    "The detected_language, language_status, language_score, language_reason and "
    "language_detector columns are a local detector's evidence about the text; "
    "language_score is the detector's own score, not a probability. A text in a "
    "language the approved models do not support was still analysed."
)


def language_export_cells(assessment: LanguageAssessment) -> dict[str, object]:
    """The detected-language columns for one analysed record."""

    detector = assessment.detector
    return {
        "detected_language": assessment.detected_language or "",
        "language_status": assessment.status.value,
        "language_score": "" if assessment.score is None else assessment.score,
        "language_reason": "" if assessment.reason is None else assessment.reason.value,
        "language_detector": "" if detector is None else detector.label,
    }


__all__ = [
    "LANGUAGE_EXPORT_FIELDS",
    "LANGUAGE_FIELDS_NOTE",
    "LanguageNotice",
    "LanguageSummary",
    "assess_language",
    "describe_language",
    "describe_summary",
    "language_caveat",
    "language_export_cells",
    "language_name",
    "language_short",
    "language_signal",
    "summarize_languages",
    "summarize_result",
]
