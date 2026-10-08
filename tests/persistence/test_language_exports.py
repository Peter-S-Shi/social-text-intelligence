"""Every export that carries model evidence also carries the language evidence."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from social_text_intelligence.application.insights_workflow import (
    InsightControls,
    InsightsWorkflow,
)
from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import ReviewWorkflow
from social_text_intelligence.application.use_cases import ApplicationUseCases
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.insights import (
    GroupingDimension,
    InsightMetric,
    InsightPerspective,
)

from .language_samples import (
    LanguageGateway,
    mixed_language_csv,
    strip_language_evidence,
)
from .workflow_samples import ScriptedGateway

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)
LANGUAGE_COLUMNS = (
    "detected_language",
    "language_status",
    "language_score",
    "language_reason",
    "language_detector",
)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def analysed(root: Path, gateway: object | None = None) -> str:
    flow = ProjectWorkflow(repository(root), gateway or LanguageGateway(), LIMITS)  # type: ignore[arg-type]
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id
    flow.analyze(project_id)
    return project_id


def rows_of(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_the_normalized_export_carries_supplied_and_detected_language_apart(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    workspace = repository(tmp_path).get(project_id)
    assert workspace is not None

    text = ApplicationUseCases.export_batch(workspace, include_native=False)
    rows = rows_of(text)

    assert all(column in rows[0] for column in LANGUAGE_COLUMNS)
    by_id = {row["record_id"]: row for row in rows}
    r2, r3, r4, r5 = (by_id[key] for key in ("r2", "r3", "r4", "r5"))
    assert (r2["language"], r2["detected_language"], r2["language_status"]) == (
        "en",
        "fr",
        "unsupported",
    )
    assert (r3["language"], r3["detected_language"], r3["language_status"]) == (
        "fr",
        "en",
        "supported",
    )
    assert r4["language"] == "" and r4["language_status"] == "unsupported"
    assert r5["detected_language"] == "" and r5["language_status"] == "undetermined"
    assert r5["language_reason"] == "low_score"
    assert r2["language_score"] == "0.97"
    assert r2["language_detector"].startswith("fake 1.0")


def test_an_unchecked_result_exports_as_not_assessed_never_as_english(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, ScriptedGateway())  # no detector configured
    strip_language_evidence(tmp_path)  # ...and one stored before M5.6 anyway
    workspace = repository(tmp_path).get(project_id)
    assert workspace is not None

    rows = rows_of(ApplicationUseCases.export_batch(workspace, include_native=False))

    assert {row["language_status"] for row in rows} == {"not_assessed"}
    assert {row["detected_language"] for row in rows} == {""}
    assert {row["language_reason"] for row in rows} == {"not_run"}


def test_a_fresh_analysis_without_a_detector_exports_as_unavailable(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, ScriptedGateway())
    workspace = repository(tmp_path).get(project_id)
    assert workspace is not None

    rows = rows_of(ApplicationUseCases.export_batch(workspace, include_native=False))

    assert {row["language_reason"] for row in rows} == {"detector_unavailable"}


def test_the_reviewed_export_keeps_the_language_evidence(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    rows = rows_of(ReviewWorkflow(repository(tmp_path)).export_csv(project_id))

    assert all(column in rows[0] for column in LANGUAGE_COLUMNS)
    assert {row["record_id"]: row["language_status"] for row in rows}["r2"] == (
        "unsupported"
    )


def test_the_insights_export_carries_language_evidence_beside_supplied_language(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = InsightsWorkflow(repository(tmp_path))
    flow.apply(
        project_id,
        InsightControls(
            grouping=GroupingDimension.LANGUAGE,
            groups=("en",),
            perspective=InsightPerspective.AI,
            metric=InsightMetric.AI_SENTIMENT,
        ),
    )

    rows = rows_of(flow.export_csv(project_id, include_records=True))
    records = {r["record_id"]: r for r in rows if r["section"] == "supporting_record"}

    assert set(records) == {"r1", "r2", "r5"}  # grouped by the *supplied* language
    assert (records["r2"]["language"], records["r2"]["detected_language"]) == (
        "en",
        "fr",
    )
    assert records["r2"]["language_status"] == "unsupported"
    assert records["r5"]["language_status"] == "undetermined"
    metadata = next(r for r in rows if r["section"] == "export_metadata")
    assert "supplied in the file" in metadata["language_fields_note"]
    assert "detector" in metadata["language_fields_note"]
