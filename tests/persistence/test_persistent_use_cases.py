"""The shared use cases work unchanged on a durable project across restarts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from persistence.samples import RICH_CSV, SyntheticGateway
from social_text_intelligence.application.projects import BatchWorkspace
from social_text_intelligence.application.use_cases import ApplicationUseCases
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.batch import BatchCancelled, BatchProgress

LIMITS = {"max_bytes": 100_000, "max_rows": 50, "max_text_length": 500}
FILTERS = {
    "review_filter": "all",
    "sentiment_filter": "all",
    "emotion_filter": "all",
}


def session(root: Path) -> ApplicationUseCases:
    """A fresh repository and use cases, as after an application restart."""

    return ApplicationUseCases(
        SqliteProjectRepository(AppDataLocations(root)), SyntheticGateway()
    )


def workspace_of(use_cases: ApplicationUseCases, token: str) -> BatchWorkspace:
    workspace = use_cases.projects.get(token)
    assert workspace is not None
    return workspace


def test_a_batch_project_can_be_closed_restarted_and_continued(
    tmp_path: Path,
) -> None:
    csv_without_text_column = RICH_CSV.replace(",text,", ",message,", 1).replace(
        "record_id,text", "record_id,message", 1
    )
    first = session(tmp_path)
    token = first.upload_batch(csv_without_text_column.encode(), **LIMITS)
    assert workspace_of(first, token).pending is not None

    second = session(tmp_path)
    assert second.select_batch_column(
        token, "message", max_rows=50, max_text_length=500
    )
    assert second.analyze_workspace(token) is True
    second.save_review(
        token,
        1,
        action="save",
        values={
            "sentiment_judgment": "correct",
            "human_sentiment": "negative",
            "emotion_judgment": "accept",
            "review_note": "Persisted human note",
        },
        secondary_emotions=("sadness",),
        **FILTERS,
    )
    saved = workspace_of(second, token)
    exported = second.export_reviews(saved, include_native=True)
    details = second.review_details(saved, 1, **FILTERS)
    assert details is not None

    third = session(tmp_path)
    reopened = workspace_of(third, token)
    assert reopened == saved
    assert third.export_reviews(reopened, include_native=True) == exported
    reopened_details = third.review_details(reopened, 1, **FILTERS)
    assert reopened_details is not None
    assert reopened_details.summary == details.summary
    assert reopened_details.current == details.current

    # Continue where the previous session stopped.
    third.save_review(
        token,
        2,
        action="accept_both",
        values={},
        secondary_emotions=(),
        **FILTERS,
    )
    third.add_note(
        token,
        {
            "association": "topic",
            "association_value": "shipping",
            "phrase": "late",
            "explanation": "Context note",
            "context_importance": "Tone",
        },
        ("sarcasm_possible",),
    )
    view = third.resolve_insights(
        token,
        workspace_of(third, token),
        {"grouping": "topic", "perspective": "human"},
        (),
        (),
        comparison=False,
    )
    assert view is not None and view.error_message is None
    assert view.selection.perspective.value == "human"

    fourth = session(tmp_path)
    final = workspace_of(fourth, token)
    assert final.reviews is not None
    assert [r.is_reviewed for r in final.reviews.reviews][:2] == [True, True]
    assert final.insights is not None and len(final.insights.notes) == 1
    assert final.insights.selection == view.selection
    assert final.result == saved.result  # AI records never change after analysis


def test_a_cancelled_batch_commits_no_partial_result(tmp_path: Path) -> None:
    use_cases = session(tmp_path)
    token = use_cases.upload_batch(RICH_CSV.encode(), **LIMITS)
    seen: list[BatchProgress] = []

    def cancel_midway() -> bool:
        return len(seen) >= 3

    with pytest.raises(BatchCancelled):
        use_cases.analyze_workspace(
            token, progress=seen.append, cancelled=cancel_midway
        )
    assert len(seen) == 3  # work really was interrupted part-way through

    restarted = session(tmp_path)
    workspace = workspace_of(restarted, token)
    assert workspace.result is None and workspace.reviews is None
    database = tmp_path / "projects" / f"{token}.sqlite3"
    connection = sqlite3.connect(database)
    try:
        for table in ("analysis_result", "analysis_outcome", "human_review"):
            assert (
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            )
    finally:
        connection.close()

    # The project is immediately usable again and a full run commits atomically.
    assert restarted.analyze_workspace(token) is True
    assert workspace_of(restarted, token).result is not None


def test_a_failed_row_is_stored_as_a_failure_and_survives_restart(
    tmp_path: Path,
) -> None:
    use_cases = session(tmp_path)
    token = use_cases.upload_batch(RICH_CSV.encode(), **LIMITS)
    assert use_cases.analyze_workspace(token) is True
    result = workspace_of(session(tmp_path), token).result
    assert result is not None
    failures = {
        o.prepared.row_number: o.error_code for o in result.outcomes if not o.report
    }
    assert failures == {
        4: "invalid_timestamp",
        5: "duplicate_record_id",
        6: "duplicate_record_id",
        7: "synthetic_failure",
    }
    assert result.aggregates.failed_count == 4
    assert result.aggregates.analyzed_count == 4
