"""The language-check types a presentation layer may use, re-exported from services.

Detected language is evidence about a text. It is shown beside, and never in place
of, the language a file supplied.
"""

from __future__ import annotations

from ..contracts.language import LanguageAssessment
from ..services.language import (
    LanguageNotice,
    LanguageSummary,
    describe_language,
    describe_summary,
    language_short,
    summarize_languages,
    summarize_result,
)

__all__ = [
    "LanguageAssessment",
    "LanguageNotice",
    "LanguageSummary",
    "describe_language",
    "describe_summary",
    "language_short",
    "summarize_languages",
    "summarize_result",
]
