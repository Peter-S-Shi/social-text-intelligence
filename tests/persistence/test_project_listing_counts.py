"""The project list carries per-project counts, read cheaply and without text."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    ReviewDraft,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import SentimentLabel
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .workflow_samples import ScriptedGateway

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
CSV = (
    b"record_id,text\n"
    b"r1,first record\n"
    b"r2,second record\n"
    b"r3,third record\n"
    b"r4,\n"  # rejected at import: empty text
)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def test_a_freshly_imported_project_counts_its_rows_and_nothing_else(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    flow.import_csv(CSV, name="P")

    summary = repository(tmp_path).list_projects()[0]

    assert summary.row_count == 4
    assert summary.rejected_rows == 1
    assert summary.analysed_rows == 0
    assert summary.reviewed_rows == 0 and summary.corrected_rows == 0


def test_counts_follow_analysis_and_review(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    project_id = flow.import_csv(CSV, name="P").summary.project_id
    flow.analyze(project_id)
    reviews = ReviewWorkflow(repository(tmp_path))
    first = reviews.open_review(project_id, row=1).record
    second = reviews.open_review(project_id, row=2).record
    assert first is not None and second is not None
    reviews.accept_both(project_id, 1, "", expected=first.review)
    reviews.save(
        project_id,
        2,
        ReviewDraft(
            sentiment_judgment=ReviewJudgment.CORRECT,
            human_sentiment=SentimentLabel.NEGATIVE,
            emotion_judgment=ReviewJudgment.ACCEPT,
        ),
        expected=second.review,
    )
    # a partly judged record is not yet "reviewed"
    third = reviews.open_review(project_id, row=3).record
    assert third is not None
    reviews.save(
        project_id,
        3,
        ReviewDraft(sentiment_judgment=ReviewJudgment.ACCEPT),
        expected=third.review,
    )

    summary = repository(tmp_path).list_projects()[0]

    assert (summary.row_count, summary.rejected_rows) == (4, 1)
    assert summary.analysed_rows == 3
    assert summary.reviewed_rows == 2
    assert summary.corrected_rows == 1


def test_listing_reads_counts_without_loading_any_record_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    flow.import_csv(CSV, name="P")
    statements: list[str] = []
    original = sqlite3.connect

    def spying_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection: sqlite3.Connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", spying_connect)
    repository(tmp_path).list_projects()

    text_columns = ("input_values_json", "record_json", "report_json", "note")
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert selects
    assert not any("SELECT *" in s.upper() for s in selects)
    counting = [s for s in selects if "COUNT(" in s.upper()]
    assert len(counting) == 6  # the six listing counts, and nothing that reads rows
    assert not any(column in s for s in selects for column in text_columns)


def test_the_in_memory_repository_has_no_counts() -> None:
    from social_text_intelligence.application.projects import (
        ProjectStatus,
        ProjectSummary,
    )

    summary = ProjectSummary("x" * 32, ProjectStatus.OK, "n")

    assert summary.row_count is None and summary.reviewed_rows is None


def test_a_partly_judged_correction_counts_as_corrected_but_not_reviewed(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    project_id = flow.import_csv(CSV, name="P").summary.project_id
    flow.analyze(project_id)
    reviews = ReviewWorkflow(repository(tmp_path))
    first = reviews.open_review(project_id, row=1).record
    assert first is not None
    reviews.save(
        project_id,
        1,
        ReviewDraft(
            sentiment_judgment=ReviewJudgment.CORRECT,
            human_sentiment=SentimentLabel.NEGATIVE,
        ),
        expected=first.review,
    )

    summary = repository(tmp_path).list_projects()[0]

    # the same rules as the Review page: one corrected dimension marks the record
    assert (summary.reviewed_rows, summary.corrected_rows) == (0, 1)


def test_attempted_rows_tell_a_failed_analysis_from_no_analysis(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    flow.import_csv(CSV, name="P")
    before = repository(tmp_path).list_projects()[0]
    assert before.attempted_rows == 0

    project_id = before.project_id
    flow.analyze(project_id)
    after = repository(tmp_path).list_projects()[0]

    assert after.attempted_rows == 3 and after.analysed_rows == 3


def test_a_failing_count_degrades_the_row_instead_of_hiding_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from social_text_intelligence.infrastructure import sqlite_projects

    flow = ProjectWorkflow(repository(tmp_path), ScriptedGateway(), LIMITS)
    flow.import_csv(CSV, name="P")

    def broken(connection: sqlite3.Connection) -> object:
        raise sqlite3.OperationalError("simulated")

    monkeypatch.setattr(sqlite_projects, "_counts", broken)

    (summary,) = repository(tmp_path).list_projects()

    assert summary.name == "P" and summary.status.value == "ok"
    assert summary.row_count is None and summary.reviewed_rows is None
