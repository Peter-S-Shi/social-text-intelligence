"""The language-check types a presentation layer may use, re-exported from services.

Detected language is evidence about a text. It is shown beside, and never in place
of, the language a file supplied.
"""

from __future__ import annotations

from ..contracts.language import LanguageAssessment, LanguageReason, LanguageStatus
from ..services.language import (
    LanguageNotice,
    LanguageSummary,
    describe_language,
    describe_summary,
    summarize_languages,
)

__all__ = [
    "LanguageAssessment",
    "LanguageNotice",
    "LanguageReason",
    "LanguageStatus",
    "LanguageSummary",
    "describe_language",
    "describe_summary",
    "summarize_languages",
]
