"""Contract checks for project-authored, non-representative UAT inputs."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from social_text_intelligence.services.batch import (
    inspect_csv_upload,
    prepare_csv_batch,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "manual-qa" / "m9-uat" / "fixtures"


def test_synthetic_csv_has_stable_rows_and_real_import_validation() -> None:
    content = (FIXTURES / "feedback-v1.csv").read_bytes()
    rows = list(csv.DictReader(content.decode("utf-8").splitlines()))
    assert len(rows) == 12
    assert set(rows[0]) == {
        "record_id", "message", "source_type", "source_label",
        "language", "topic", "community", "timestamp",
    }
    assert Counter(row["record_id"] for row in rows)["SYN-009"] == 2
    assert next(row for row in rows if row["record_id"] == "SYN-010")["message"] == ""
    french = next(row for row in rows if row["record_id"] == "SYN-007")
    assert french["language"] == "fr"
    assert next(row for row in rows if row["record_id"] == "SYN-011")[
        "source_label"
    ].startswith("=")
    pending = inspect_csv_upload(content, max_bytes=10_000)
    preview = prepare_csv_batch(
        pending, text_column="message", max_rows=20, max_text_length=1000
    )
    assert len(preview.rows) == 12
    assert [row.identity for row in preview.rows] == [row["record_id"] for row in rows]
    assert [row.error_code for row in preview.rows[8:11]] == [
        "duplicate_record_id", "duplicate_record_id", "empty_text"
    ]


def test_long_text_recipe_is_deterministic_and_synthetic() -> None:
    import importlib.util

    recipe = FIXTURES / "make_long_text.py"
    spec = importlib.util.spec_from_file_location("m9_uat_long_text", recipe)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = module.long_text()
    assert text == module.long_text()
    assert len(text) > 7000
    assert text.count("Synthetic app feedback") == 160
