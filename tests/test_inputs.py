"""Tests for normalized text input validation and metadata."""

import unittest

from social_text_intelligence.contracts import (
    NormalizedTextInput,
    SourceType,
    ValidationError,
)


class NormalizedTextInputTests(unittest.TestCase):
    def test_normalizes_unicode_line_endings_and_metadata(self) -> None:
        record = NormalizedTextInput.from_text(
            "Cafe\u0301\r\nSecond line",
            record_id=" record-1 ",
            source_type=SourceType.MULTILINE,
            source_label=" feedback ",
            language="en-CA",
            topic=" quality ",
        )

        self.assertEqual(record.record_id, "record-1")
        self.assertEqual(record.text, "Café\nSecond line")
        self.assertEqual(record.source_label, "feedback")
        self.assertEqual(record.topic, "quality")
        self.assertEqual(record.language, "en-CA")

    def test_rejects_whitespace_only_text(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            NormalizedTextInput.from_text(" \r\n ", record_id="record-1")

        self.assertEqual(caught.exception.field, "text")
        self.assertEqual(caught.exception.code, "empty_text")

    def test_rejects_oversized_text(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            NormalizedTextInput.from_text(
                "abcd",
                record_id="record-1",
                max_text_length=3,
            )

        self.assertEqual(caught.exception.code, "text_too_long")

    def test_rejects_invalid_language_metadata(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            NormalizedTextInput.from_text(
                "Synthetic text.",
                record_id="record-1",
                language="english",
            )

        self.assertEqual(caught.exception.code, "invalid_language")

    def test_rejects_untyped_source_value(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            NormalizedTextInput(
                record_id="record-1",
                text="Synthetic text.",
                source_type="direct",  # type: ignore[arg-type]
            )

        self.assertEqual(caught.exception.code, "invalid_source_type")


if __name__ == "__main__":
    unittest.main()
