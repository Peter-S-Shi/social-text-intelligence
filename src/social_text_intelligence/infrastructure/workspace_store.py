"""Read and write one workspace to the project tables, validating its shape.

Only sections that changed are rewritten. AI records and imported rows are replaced
by delete and insert inside the caller's transaction, never edited in place.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..application.projects import BatchWorkspace
from ..contracts.errors import ProjectStorageError
from ..services.batch import BatchOutcome, BatchResult, PreparedBatchRow
from ..services.insights import InsightState
from ..services.review import ReviewState
from . import workspace_codec as codec


@dataclass(frozen=True, slots=True)
class Encoded:
    """Validated column values for one workspace, ready to be written."""

    pending: tuple[bytes, str] | None
    preview: tuple[str, str, str] | None
    rows: tuple[tuple[object, ...], ...]
    aggregates: str | None
    outcomes: tuple[tuple[object, ...], ...]
    reviews: tuple[tuple[object, ...], ...] | None
    selection: str | None
    notes: tuple[tuple[object, ...], ...] | None


def _unsupported_workspace() -> ProjectStorageError:
    return ProjectStorageError(
        code="unsupported_workspace",
        message="This workspace cannot be stored as a project.",
    )


def encode_workspace(workspace: BatchWorkspace) -> Encoded:
    """Validate the shape this store supports, then encode it without side effects."""

    preview = workspace.preview
    result = workspace.result
    rows: tuple[PreparedBatchRow, ...] = () if preview is None else preview.rows
    numbers = [row.row_number for row in rows]
    if numbers != sorted(set(numbers)):
        raise _unsupported_workspace()
    outcomes: tuple[BatchOutcome, ...] = ()
    if result is not None:
        if preview is None or result.preview != preview:
            raise _unsupported_workspace()
        outcomes = result.outcomes
        if len(outcomes) != len(rows) or any(
            outcome.prepared != row for outcome, row in zip(outcomes, rows, strict=True)
        ):
            raise _unsupported_workspace()
        if any(
            outcome.report is not None
            and outcome.report.record != outcome.prepared.record
            for outcome in outcomes
        ):
            raise _unsupported_workspace()
    insights = workspace.insights
    return Encoded(
        pending=(
            None
            if workspace.pending is None
            else codec.encode_pending(workspace.pending)
        ),
        preview=None if preview is None else codec.encode_preview(preview),
        rows=tuple(codec.encode_row(row) for row in rows),
        aggregates=(
            None if result is None else codec.encode_aggregates(result.aggregates)
        ),
        outcomes=tuple(codec.encode_outcome(outcome) for outcome in outcomes),
        reviews=(
            None
            if workspace.reviews is None
            else tuple(codec.encode_review(item) for item in workspace.reviews.reviews)
        ),
        selection=(
            None
            if insights is None or insights.selection is None
            else codec.encode_selection(insights.selection)
        ),
        notes=(
            None
            if insights is None
            else tuple(codec.encode_note(note) for note in insights.notes)
        ),
    )


def write_workspace(
    connection: sqlite3.Connection,
    old: BatchWorkspace,
    new: BatchWorkspace,
    encoded: Encoded,
) -> None:
    """Persist only the sections that changed; AI records are replaced, never edited."""

    if old.pending != new.pending:
        connection.execute("DELETE FROM pending_upload")
        if encoded.pending is not None:
            connection.execute(
                "INSERT INTO pending_upload VALUES (1, ?, ?)", encoded.pending
            )
    preview_changed = old.preview != new.preview
    result_changed = old.result != new.result
    if preview_changed or result_changed:
        connection.execute("DELETE FROM analysis_outcome")
        connection.execute("DELETE FROM analysis_result")
    if preview_changed:
        connection.execute("DELETE FROM prepared_row")
        connection.execute("DELETE FROM batch_preview")
        if encoded.preview is not None:
            connection.execute(
                "INSERT INTO batch_preview VALUES (1, ?, ?, ?)", encoded.preview
            )
            connection.executemany(
                "INSERT INTO prepared_row VALUES (?, ?, ?, ?, ?, ?)", encoded.rows
            )
    if (preview_changed or result_changed) and encoded.aggregates is not None:
        connection.execute(
            "INSERT INTO analysis_result VALUES (1, ?)", (encoded.aggregates,)
        )
        connection.executemany(
            "INSERT INTO analysis_outcome VALUES (?, ?, ?, ?, ?)", encoded.outcomes
        )
    if old.reviews != new.reviews:
        connection.execute("DELETE FROM human_review")
        connection.executemany(
            "INSERT INTO human_review VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(index, *item) for index, item in enumerate(encoded.reviews or ())],
        )
    if old.insights != new.insights:
        connection.execute("DELETE FROM insight_selection")
        connection.execute("DELETE FROM context_note")
        if encoded.selection is not None:
            connection.execute(
                "INSERT INTO insight_selection VALUES (1, ?)", (encoded.selection,)
            )
        connection.executemany(
            "INSERT INTO context_note VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(index, *item) for index, item in enumerate(encoded.notes or ())],
        )


def _read_workspace(connection: sqlite3.Connection) -> tuple[BatchWorkspace, int]:
    """Rebuild a workspace through the original constructors (re-validating it)."""

    project = connection.execute(
        "SELECT revision, has_reviews, has_insights FROM project"
    ).fetchone()
    if project is None:
        raise ValueError("missing project row")
    revision, has_reviews, has_insights = project

    pending_row = connection.execute(
        "SELECT content, headers_json FROM pending_upload"
    ).fetchone()
    pending = None if pending_row is None else codec.decode_pending(*pending_row)

    preview = None
    rows: dict[int, PreparedBatchRow] = {}
    preview_row = connection.execute(
        "SELECT text_column, headers_json, ignored_columns_json FROM batch_preview"
    ).fetchone()
    if preview_row is not None:
        for stored in connection.execute(
            "SELECT row_number, identity, input_values_json, record_json, "
            "error_code, error_message FROM prepared_row ORDER BY row_number"
        ):
            rows[stored[0]] = codec.decode_row(*stored)
        text_column, headers_json, ignored_json = preview_row
        preview = codec.decode_preview(
            text_column, headers_json, ignored_json, tuple(rows.values())
        )

    result = None
    aggregates_row = connection.execute(
        "SELECT aggregates_json FROM analysis_result"
    ).fetchone()
    if aggregates_row is not None:
        if preview is None:
            raise ValueError("analysis without input")
        outcomes = tuple(
            codec.decode_outcome(rows[stored[0]], *stored[1:])
            for stored in connection.execute(
                "SELECT row_number, status, error_code, error_message, report_json "
                "FROM analysis_outcome ORDER BY row_number"
            )
        )
        result = BatchResult(
            preview=preview,
            outcomes=outcomes,
            aggregates=codec.decode_aggregates(aggregates_row[0]),
        )

    reviews = None
    if has_reviews:
        reviews = ReviewState(
            reviews=tuple(
                codec.decode_review(*stored)
                for stored in connection.execute(
                    "SELECT record_id, sentiment_judgment, human_sentiment, "
                    "emotion_judgment, human_dominant_emotion, "
                    "human_secondary_emotions_json, note, reviewed_at "
                    "FROM human_review ORDER BY position"
                )
            )
        )

    insights = None
    if has_insights:
        selection_row = connection.execute(
            "SELECT selection_json FROM insight_selection"
        ).fetchone()
        insights = InsightState(
            notes=tuple(
                codec.decode_note(*stored)
                for stored in connection.execute(
                    "SELECT note_id, association, association_value, phrase, "
                    "explanation, context_importance, tags_json, created_at "
                    "FROM context_note ORDER BY position"
                )
            ),
            selection=(
                None
                if selection_row is None
                else codec.decode_selection(selection_row[0])
            ),
        )
    workspace = BatchWorkspace(
        pending=pending,
        preview=preview,
        result=result,
        reviews=reviews,
        insights=insights,
    )
    return workspace, int(revision)


def load_workspace(connection: sqlite3.Connection) -> tuple[BatchWorkspace, int]:
    try:
        return _read_workspace(connection)
    except sqlite3.Error:
        raise
    except Exception:  # noqa: BLE001 - any contract or parse failure means bad data
        pass
    # Raised outside the handler so the cause, which could quote project content,
    # is not chained onto the error.
    raise ProjectStorageError(
        code="project_data_invalid",
        message="The project file contains data this version cannot read.",
    )


def record_commit(
    connection: sqlite3.Connection,
    *,
    revision: int,
    committed_at: str,
    workspace: BatchWorkspace,
) -> None:
    """Advance the revision that makes a stale lease fail, after a workspace write."""

    connection.execute(
        "UPDATE project SET revision = ?, updated_at = ?, "
        "has_reviews = ?, has_insights = ?",
        (
            revision + 1,
            committed_at,
            int(workspace.reviews is not None),
            int(workspace.insights is not None),
        ),
    )
