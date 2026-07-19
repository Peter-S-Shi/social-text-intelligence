"""Batch CSV validation, resilient analysis, aggregates, and export tests."""

import csv
import io
import unittest

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.contracts.errors import ProviderError, ValidationError
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService
from social_text_intelligence.services.batch import (
    PendingBatchUpload,
    analyze_batch,
    export_batch_csv,
    inspect_csv_upload,
    prepare_csv_batch,
)


def upload(text: str) -> PendingBatchUpload:
    return inspect_csv_upload(text.encode(), max_bytes=10_000)


def analyzer() -> AnalysisService:
    return AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(SentimentLabel.POSITIVE),
        emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
    )


class SelectiveFailureAnalyzer:
    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if record.record_id == "unsupported":
            raise ProviderError(
                provider="synthetic",
                code="unsupported_language",
                message="Provider does not support language: fr",
            )
        return analyzer().analyze(record)


class BatchServiceTests(unittest.TestCase):
    def test_prepares_supported_metadata_and_ignores_unknown_columns(self) -> None:
        pending = upload(
            "message,topic,language,unknown\n"
            "A synthetic row.,release,en,not-trusted\n"
        )
        preview = prepare_csv_batch(
            pending,
            text_column="message",
            max_rows=10,
            max_text_length=100,
        )

        self.assertEqual(preview.text_column, "message")
        self.assertEqual(preview.ignored_columns, ("unknown",))
        self.assertEqual(preview.rows[0].identity, "batch-row-000001")
        record = preview.rows[0].record
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.topic, "release")

    def test_duplicate_ids_and_invalid_rows_remain_explicit(self) -> None:
        pending = upload(
            "record_id,text,language\n"
            "duplicate,First synthetic row.,en\n"
            "duplicate,Second synthetic row.,en\n"
            "unsupported,Texte synthétique.,fr\n"
            ",,en\n"
        )
        preview = prepare_csv_batch(
            pending,
            text_column="text",
            max_rows=10,
            max_text_length=100,
        )
        result = analyze_batch(preview, SelectiveFailureAnalyzer())

        self.assertEqual(len(result.outcomes), 4)
        self.assertEqual(result.outcomes[0].error_code, "duplicate_record_id")
        self.assertEqual(result.outcomes[1].error_code, "duplicate_record_id")
        self.assertEqual(result.outcomes[2].error_code, "unsupported_language")
        self.assertEqual(result.outcomes[3].error_code, "empty_text")
        self.assertEqual(result.aggregates.failed_count, 4)

    def test_aggregates_keep_three_different_semantics(self) -> None:
        preview = prepare_csv_batch(
            upload("text\nSynthetic one.\nSynthetic two.\n"),
            text_column="text",
            max_rows=10,
            max_text_length=100,
        )
        result = analyze_batch(preview, analyzer())
        sentiment = dict(result.aggregates.sentiment_counts)
        dominant = dict(result.aggregates.dominant_emotion_counts)
        activation = {
            item.label: item.rate for item in result.aggregates.activation_rates
        }

        self.assertEqual(sentiment[SentimentLabel.POSITIVE], 2)
        self.assertEqual(dominant[EmotionLabel.GRATITUDE], 2)
        self.assertEqual(activation[EmotionLabel.GRATITUDE], 1.0)
        self.assertEqual(activation[EmotionLabel.JOY], 1.0)

    def test_export_preserves_results_errors_provenance_and_optional_native(
        self,
    ) -> None:
        preview = prepare_csv_batch(
            upload("record_id,text\nrow-1,=synthetic formula\nrow-2,\n"),
            text_column="text",
            max_rows=10,
            max_text_length=100,
        )
        result = analyze_batch(preview, analyzer())

        compact = list(
            csv.DictReader(
                io.StringIO(export_batch_csv(result, include_native=False))
            )
        )
        native = list(
            csv.DictReader(io.StringIO(export_batch_csv(result, include_native=True)))
        )

        self.assertEqual(len(compact), 2)
        self.assertEqual(compact[0]["text"], "'=synthetic formula")
        self.assertEqual(compact[0]["sentiment_label"], "positive")
        self.assertEqual(compact[0]["emotion_model"], "deterministic-emotion")
        self.assertEqual(compact[1]["error_code"], "empty_text")
        self.assertNotIn("emotion_native_joy", compact[0])
        self.assertIn("emotion_native_joy", native[0])

    def test_file_and_row_limits_are_clear(self) -> None:
        with self.assertRaisesRegex(ValidationError, "exceeds"):
            inspect_csv_upload(b"text\n123\n", max_bytes=3)
        with self.assertRaisesRegex(ValidationError, "1-row"):
            prepare_csv_batch(
                upload("text\none\ntwo\n"),
                text_column="text",
                max_rows=1,
                max_text_length=100,
            )

    def test_normalizes_header_whitespace_and_rejects_extra_cells(self) -> None:
        preview = prepare_csv_batch(
            upload(" text ,topic\nSynthetic row.,test\nSecond row.,test,extra\n"),
            text_column="text",
            max_rows=10,
            max_text_length=100,
        )
        self.assertIsNotNone(preview.rows[0].record)
        self.assertEqual(preview.rows[1].error_code, "invalid_column_count")
