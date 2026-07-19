"""CSV batch preparation, resilient analysis, aggregates, and explicit export."""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
    SourceType,
)
from ..contracts.errors import (
    ProviderError,
    SocialTextIntelligenceError,
    ValidationError,
)

DEFAULT_MAX_BATCH_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_BATCH_ROWS = 500
SUPPORTED_BATCH_FIELDS = (
    "record_id",
    "source_type",
    "source_label",
    "language",
    "timestamp",
    "topic",
    "community",
    "parent_record_id",
    "notes",
)


class CombinedAnalyzer(Protocol):
    def analyze(self, record: NormalizedTextInput) -> AnalysisReport: ...


@dataclass(frozen=True, slots=True)
class PendingBatchUpload:
    content: bytes
    headers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreparedBatchRow:
    row_number: int
    identity: str
    input_values: tuple[tuple[str, str], ...]
    record: NormalizedTextInput | None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def value_map(self) -> dict[str, str]:
        return dict(self.input_values)


@dataclass(frozen=True, slots=True)
class BatchPreview:
    text_column: str
    headers: tuple[str, ...]
    ignored_columns: tuple[str, ...]
    rows: tuple[PreparedBatchRow, ...]

    @property
    def valid_count(self) -> int:
        return sum(row.record is not None for row in self.rows)

    @property
    def invalid_count(self) -> int:
        return len(self.rows) - self.valid_count


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    prepared: PreparedBatchRow
    status: str
    report: AnalysisReport | None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ActivationRate:
    label: EmotionLabel
    active_count: int
    analyzed_count: int

    @property
    def rate(self) -> float:
        if self.analyzed_count == 0:
            return 0.0
        return self.active_count / self.analyzed_count


@dataclass(frozen=True, slots=True)
class BatchAggregates:
    sentiment_counts: tuple[tuple[SentimentLabel, int], ...]
    dominant_emotion_counts: tuple[tuple[EmotionLabel, int], ...]
    activation_rates: tuple[ActivationRate, ...]
    analyzed_count: int
    failed_count: int


@dataclass(frozen=True, slots=True)
class BatchResult:
    preview: BatchPreview
    outcomes: tuple[BatchOutcome, ...]
    aggregates: BatchAggregates


def inspect_csv_upload(content: bytes, *, max_bytes: int) -> PendingBatchUpload:
    if not content:
        raise ValidationError(
            field="file", code="empty_file", message="The CSV file is empty."
        )
    if len(content) > max_bytes:
        raise ValidationError(
            field="file",
            code="file_too_large",
            message=f"The CSV file exceeds the {max_bytes}-byte limit.",
        )
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError(
            field="file",
            code="invalid_encoding",
            message="The CSV file must use UTF-8 encoding.",
        ) from error
    try:
        reader = csv.reader(io.StringIO(decoded, newline=""))
        headers = next(reader)
    except (StopIteration, csv.Error) as error:
        raise ValidationError(
            field="file", code="invalid_csv", message="The CSV header is invalid."
        ) from error
    cleaned = tuple(header.strip() for header in headers)
    if not cleaned or any(not header for header in cleaned):
        raise ValidationError(
            field="file",
            code="invalid_header",
            message="Every CSV column must have a non-empty header.",
        )
    if len(cleaned) != len(set(cleaned)):
        raise ValidationError(
            field="file",
            code="duplicate_header",
            message="CSV column headers must be unique.",
        )
    return PendingBatchUpload(content=content, headers=cleaned)


def _parse_timestamp(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(
            field="timestamp",
            code="invalid_timestamp",
            message="timestamp must use ISO 8601 format.",
        ) from error


def _parse_source_type(value: str) -> SourceType:
    cleaned = value.strip()
    if not cleaned:
        return SourceType.FILE
    try:
        return SourceType(cleaned)
    except ValueError as error:
        raise ValidationError(
            field="source_type",
            code="invalid_source_type",
            message="source_type is not a supported value.",
        ) from error


def prepare_csv_batch(
    upload: PendingBatchUpload,
    *,
    text_column: str,
    max_rows: int,
    max_text_length: int,
) -> BatchPreview:
    selected = text_column.strip()
    if selected not in upload.headers:
        raise ValidationError(
            field="text_column",
            code="missing_text_column",
            message="Select a text column that exists in the CSV file.",
        )
    decoded = upload.content.decode("utf-8-sig")
    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=""))
        _ = reader.fieldnames
        reader.fieldnames = list(upload.headers)
        raw_rows = list(reader)
    except csv.Error as error:
        raise ValidationError(
            field="file", code="invalid_csv", message="The CSV rows are invalid."
        ) from error
    if not raw_rows:
        raise ValidationError(
            field="file",
            code="no_data_rows",
            message="The CSV file contains no data rows.",
        )
    if len(raw_rows) > max_rows:
        raise ValidationError(
            field="file",
            code="too_many_rows",
            message=f"The CSV file exceeds the {max_rows}-row limit.",
        )

    supplied_ids = [
        (row.get("record_id") or "").strip() for row in raw_rows
    ]
    duplicate_ids = {
        record_id
        for record_id, count in Counter(item for item in supplied_ids if item).items()
        if count > 1
    }
    ignored = tuple(
        header
        for header in upload.headers
        if header != selected and header not in SUPPORTED_BATCH_FIELDS
    )
    prepared: list[PreparedBatchRow] = []
    for row_number, raw in enumerate(raw_rows, start=1):
        supplied_id = supplied_ids[row_number - 1]
        identity = supplied_id or f"batch-row-{row_number:06d}"
        values = {field: (raw.get(field) or "") for field in SUPPORTED_BATCH_FIELDS}
        values["text"] = raw.get(selected) or ""
        values["record_id"] = identity
        input_values = tuple(
            (field, values.get(field, ""))
            for field in ("record_id", "text", *SUPPORTED_BATCH_FIELDS[1:])
        )
        if raw.get(None):
            prepared.append(
                PreparedBatchRow(
                    row_number=row_number,
                    identity=identity,
                    input_values=input_values,
                    record=None,
                    error_code="invalid_column_count",
                    error_message="The row contains more values than the CSV header.",
                )
            )
            continue
        if supplied_id in duplicate_ids:
            prepared.append(
                PreparedBatchRow(
                    row_number=row_number,
                    identity=identity,
                    input_values=input_values,
                    record=None,
                    error_code="duplicate_record_id",
                    error_message="record_id must be unique within the batch.",
                )
            )
            continue
        try:
            record = NormalizedTextInput.from_text(
                values["text"],
                record_id=identity,
                source_type=_parse_source_type(values["source_type"]),
                source_label=values["source_label"],
                language=values["language"] or "en",
                timestamp=_parse_timestamp(values["timestamp"]),
                topic=values["topic"],
                community=values["community"],
                parent_record_id=values["parent_record_id"] or None,
                notes=values["notes"],
                max_text_length=max_text_length,
            )
        except ValidationError as error:
            prepared.append(
                PreparedBatchRow(
                    row_number=row_number,
                    identity=identity,
                    input_values=input_values,
                    record=None,
                    error_code=error.code,
                    error_message=error.message,
                )
            )
        else:
            prepared.append(
                PreparedBatchRow(
                    row_number=row_number,
                    identity=identity,
                    input_values=input_values,
                    record=record,
                )
            )
    return BatchPreview(
        text_column=selected,
        headers=upload.headers,
        ignored_columns=ignored,
        rows=tuple(prepared),
    )


def analyze_batch(preview: BatchPreview, analyzer: CombinedAnalyzer) -> BatchResult:
    outcomes: list[BatchOutcome] = []
    for row in preview.rows:
        if row.record is None:
            outcomes.append(
                BatchOutcome(
                    prepared=row,
                    status="error",
                    report=None,
                    error_code=row.error_code,
                    error_message=row.error_message,
                )
            )
            continue
        try:
            report = analyzer.analyze(row.record)
        except SocialTextIntelligenceError as error:
            if isinstance(error, (ValidationError, ProviderError)):
                code = error.code
                message = error.message
            else:
                code = "analysis_error"
                message = str(error)
            outcomes.append(
                BatchOutcome(
                    prepared=row,
                    status="error",
                    report=None,
                    error_code=code,
                    error_message=message,
                )
            )
        except Exception:
            outcomes.append(
                BatchOutcome(
                    prepared=row,
                    status="error",
                    report=None,
                    error_code="analysis_failed",
                    error_message="Analysis failed safely for this row.",
                )
            )
        else:
            outcomes.append(BatchOutcome(row, "ok", report))
    successful = tuple(item.report for item in outcomes if item.report is not None)
    sentiment = Counter(report.sentiment.label for report in successful)
    dominant = Counter(report.emotion.dominant_emotion for report in successful)
    activations = tuple(
        ActivationRate(
            label=label,
            active_count=sum(
                any(
                    score.label is label and score.score >= report.emotion.threshold
                    for score in report.emotion.scores
                )
                for report in successful
            ),
            analyzed_count=len(successful),
        )
        for label in EmotionLabel
        if label is not EmotionLabel.NEUTRAL
    )
    aggregates = BatchAggregates(
        sentiment_counts=tuple((label, sentiment[label]) for label in SentimentLabel),
        dominant_emotion_counts=tuple(
            (label, dominant[label]) for label in EmotionLabel
        ),
        activation_rates=activations,
        analyzed_count=len(successful),
        failed_count=len(outcomes) - len(successful),
    )
    return BatchResult(preview, tuple(outcomes), aggregates)


def _safe_spreadsheet_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_batch_csv(result: BatchResult, *, include_native: bool) -> str:
    input_fields = ("record_id", "text", *SUPPORTED_BATCH_FIELDS[1:])
    sentiment_fields = tuple(f"sentiment_{label}" for label in SentimentLabel)
    emotion_fields = tuple(f"emotion_{label}" for label in EmotionLabel)
    native_fields: tuple[str, ...] = ()
    native_labels: tuple[str, ...] = ()
    first_report = next(
        (outcome.report for outcome in result.outcomes if outcome.report is not None),
        None,
    )
    if include_native and first_report is not None:
        native_labels = first_report.emotion.provider.native_labels
        native_fields = tuple(f"emotion_native_{label}" for label in native_labels)
    fieldnames = (
        "row_number",
        *input_fields,
        "status",
        "error_code",
        "error_message",
        "sentiment_label",
        "sentiment_confidence",
        *sentiment_fields,
        "dominant_emotion",
        "secondary_emotions",
        "emotion_confidence",
        "emotion_threshold",
        *emotion_fields,
        "sentiment_provider",
        "sentiment_model",
        "sentiment_revision",
        "emotion_provider",
        "emotion_model",
        "emotion_revision",
        *native_fields,
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for outcome in result.outcomes:
        values = outcome.prepared.value_map
        row: dict[str, object] = {
            "row_number": outcome.prepared.row_number,
            **{
                field: _safe_spreadsheet_text(values.get(field, ""))
                for field in input_fields
            },
            "status": outcome.status,
            "error_code": outcome.error_code or "",
            "error_message": outcome.error_message or "",
        }
        report = outcome.report
        if report is not None:
            sentiment_scores = {
                item.label: item.score for item in report.sentiment.scores
            }
            emotion_scores = {item.label: item.score for item in report.emotion.scores}
            row.update(
                {
                    "sentiment_label": report.sentiment.label,
                    "sentiment_confidence": report.sentiment.confidence,
                    **{
                        f"sentiment_{label}": sentiment_scores[label]
                        for label in SentimentLabel
                    },
                    "dominant_emotion": report.emotion.dominant_emotion,
                    "secondary_emotions": "|".join(report.emotion.secondary_emotions),
                    "emotion_confidence": report.emotion.confidence,
                    "emotion_threshold": report.emotion.threshold,
                    **{
                        f"emotion_{label}": emotion_scores[label]
                        for label in EmotionLabel
                    },
                    "sentiment_provider": report.sentiment.provider.provider,
                    "sentiment_model": report.sentiment.provider.model_name,
                    "sentiment_revision": report.sentiment.provider.revision,
                    "emotion_provider": report.emotion.provider.provider,
                    "emotion_model": report.emotion.provider.model_name,
                    "emotion_revision": report.emotion.provider.revision,
                }
            )
            if include_native:
                native_scores = {
                    item.label: item.score for item in report.emotion.native_scores
                }
                row.update(
                    {
                        f"emotion_native_{label}": native_scores[label]
                        for label in native_labels
                    }
                )
        writer.writerow(row)
    return output.getvalue()
