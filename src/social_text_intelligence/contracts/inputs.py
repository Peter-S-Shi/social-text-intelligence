"""Normalized, platform-neutral text input contracts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from .errors import ValidationError

DEFAULT_MAX_TEXT_LENGTH = 20_000
MAX_RECORD_ID_LENGTH = 128
MAX_METADATA_LENGTH = 512
_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


class SourceType(StrEnum):
    """Platform-neutral source categories available to normalized records."""

    DIRECT = "direct"
    MULTILINE = "multiline"
    FILE = "file"
    PLATFORM = "platform"
    OTHER = "other"


def normalize_text(text: str) -> str:
    """Normalize Unicode and line endings without rewriting user wording."""

    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def _clean_required_identifier(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(
            field=field,
            code="required",
            message=f"{field} must not be empty.",
        )
    if len(cleaned) > MAX_RECORD_ID_LENGTH:
        raise ValidationError(
            field=field,
            code="too_long",
            message=f"{field} exceeds {MAX_RECORD_ID_LENGTH} characters.",
        )
    return cleaned


def _clean_optional_metadata(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_METADATA_LENGTH:
        raise ValidationError(
            field=field,
            code="too_long",
            message=f"{field} exceeds {MAX_METADATA_LENGTH} characters.",
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class NormalizedTextInput:
    """Shared input record consumed by providers and analysis services."""

    record_id: str
    text: str
    source_type: SourceType = SourceType.DIRECT
    source_label: str | None = None
    language: str | None = None
    timestamp: datetime | None = None
    topic: str | None = None
    community: str | None = None
    parent_record_id: str | None = None
    notes: str | None = None
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, SourceType):
            raise ValidationError(
                field="source_type",
                code="invalid_source_type",
                message="source_type must be a SourceType value.",
            )
        record_id = _clean_required_identifier(self.record_id, field="record_id")
        normalized_text = normalize_text(self.text)
        if not normalized_text.strip():
            raise ValidationError(
                field="text",
                code="empty_text",
                message="Text must contain at least one non-whitespace character.",
            )
        if self.max_text_length < 1:
            raise ValidationError(
                field="max_text_length",
                code="invalid_limit",
                message="max_text_length must be at least 1.",
            )
        if len(normalized_text) > self.max_text_length:
            raise ValidationError(
                field="text",
                code="text_too_long",
                message=f"Text exceeds {self.max_text_length} characters.",
            )

        language = _clean_optional_metadata(self.language, field="language")
        if language is not None and _LANGUAGE_PATTERN.fullmatch(language) is None:
            raise ValidationError(
                field="language",
                code="invalid_language",
                message=(
                    "Language must be a simple BCP 47-style tag such as en or en-CA."
                ),
            )

        parent_record_id = self.parent_record_id
        if parent_record_id is not None:
            parent_record_id = _clean_required_identifier(
                parent_record_id,
                field="parent_record_id",
            )

        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "text", normalized_text)
        object.__setattr__(
            self,
            "source_label",
            _clean_optional_metadata(self.source_label, field="source_label"),
        )
        object.__setattr__(self, "language", language)
        object.__setattr__(
            self,
            "topic",
            _clean_optional_metadata(self.topic, field="topic"),
        )
        object.__setattr__(
            self,
            "community",
            _clean_optional_metadata(self.community, field="community"),
        )
        object.__setattr__(self, "parent_record_id", parent_record_id)
        object.__setattr__(
            self,
            "notes",
            _clean_optional_metadata(self.notes, field="notes"),
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        record_id: str | None = None,
        source_type: SourceType = SourceType.DIRECT,
        source_label: str | None = None,
        language: str | None = None,
        timestamp: datetime | None = None,
        topic: str | None = None,
        community: str | None = None,
        parent_record_id: str | None = None,
        notes: str | None = None,
        max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ) -> NormalizedTextInput:
        """Create a normalized record with an optional caller-supplied identity."""

        return cls(
            record_id=record_id or uuid4().hex,
            text=text,
            source_type=source_type,
            source_label=source_label,
            language=language,
            timestamp=timestamp,
            topic=topic,
            community=community,
            parent_record_id=parent_record_id,
            notes=notes,
            max_text_length=max_text_length,
        )
