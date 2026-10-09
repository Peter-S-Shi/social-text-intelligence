"""The results workflow over a real SQLite project (synthetic data).

The 26-row project is described in ``insight_samples``: 24 rows analyse (7 positive,
7 negative, 10 neutral), row 25 fails inside the gateway and row 26 fails validation.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectNotFoundError,
    ProjectWorkflow,
)
from social_text_intelligence.application.results_workflow import (
    ResultsFilters,
    ResultsStatus,
    ResultsUnavailableError,
    ResultsWorkflow,
    ValidationUnavailableError,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .insight_samples import SENTINEL, VariedGateway, insights_csv

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def results(root: Path) -> ResultsWorkflow:
    """A fresh workflow, as after an application restart."""

    return ResultsWorkflow(repository(root))


def imported(root: Path) -> str:
    flow = ProjectWorkflow(repository(root), VariedGateway(), LIMITS)
    return flow.import_csv(insights_csv(), name="P").summary.project_id


def analysed(root: Path) -> str:
    project_id = imported(root)
    ProjectWorkflow(repository(root), VariedGateway(), LIMITS).analyze(project_id)
    return project_id


# -- validation -------------------------------------------------------------


def test_validation_lists_each_row_that_could_not_be_prepared(tmp_path: Path) -> None:
    project_id = imported(tmp_path)

    snapshot = results(tmp_path).validation(project_id)

    assert (snapshot.total_rows, snapshot.valid_rows) == (26, 25)
    assert [(p.row_number, p.record_id) for p in snapshot.invalid_rows] == [(26, "r26")]
    problem = snapshot.invalid_rows[0]
    assert problem.code  # the stored validation code, whatever the service named it
    assert problem.message
    assert snapshot.failed_rows == ()  # nothing has been analysed yet
    assert snapshot.analysed is False
    assert snapshot.text_column == "text"


def test_validation_after_analysis_adds_the_row_that_failed_with_its_reason(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = results(tmp_path).validation(project_id)

    assert snapshot.analysed is True
    assert [p.row_number for p in snapshot.invalid_rows] == [26]
    assert [(p.row_number, p.record_id) for p in snapshot.failed_rows] == [(25, "r25")]
    assert snapshot.failed_rows[0].code == "synthetic_failure"
    assert snapshot.failed_rows[0].message == "Row failed."


def test_validation_has_nothing_to_show_until_a_text_column_is_chosen(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), VariedGateway(), LIMITS)
    pending = flow.import_csv(b"id,body\n1,hello there friend\n", name="Q")
    assert pending.phase.value == "needs_column"

    with pytest.raises(ValidationUnavailableError):
        results(tmp_path).validation(pending.summary.project_id)


def test_validation_of_a_missing_project_says_so(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        results(tmp_path).validation("no-such-project")


# -- results ----------------------------------------------------------------


def test_results_carry_the_aggregates_the_batch_stored(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = results(tmp_path).results(project_id)

    aggregates = snapshot.aggregates
    assert (aggregates.analyzed_count, aggregates.failed_count) == (24, 2)
    assert dict(aggregates.sentiment_counts) == {
        SentimentLabel.POSITIVE: 7,
        SentimentLabel.NEGATIVE: 7,
        SentimentLabel.NEUTRAL: 10,
    }
    assert (snapshot.total_rows, len(snapshot.rows)) == (26, 26)


def test_every_row_keeps_its_place_status_and_reason(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    rows = results(tmp_path).results(project_id).rows

    assert [row.row_number for row in rows] == list(range(1, 27))
    first, failed, invalid = rows[0], rows[24], rows[25]
    assert (first.record_id, first.status) == ("r1", "ok")
    assert first.sentiment is SentimentLabel.POSITIVE
    assert first.dominant_emotion is EmotionLabel.JOY
    assert (failed.status, failed.error_code) == ("error", "synthetic_failure")
    assert failed.sentiment is None and failed.dominant_emotion is None
    assert (invalid.status, invalid.record_id) == ("error", "r26")
    assert invalid.error_code and invalid.error_message
    # a rejected row never reached the models; a failed one did
    assert (invalid.rejected_at_import, failed.rejected_at_import) == (True, False)
    assert first.rejected_at_import is False


def test_the_status_filter_keeps_only_that_status(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = results(tmp_path).results(
        project_id, ResultsFilters(status=ResultsStatus.ERROR)
    )

    assert [row.row_number for row in snapshot.rows] == [25, 26]
    assert snapshot.total_rows == 26  # the denominator stays the whole batch


def test_the_sentiment_filter_keeps_analysed_rows_with_that_label(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = results(tmp_path).results(
        project_id, ResultsFilters(sentiment=SentimentLabel.NEGATIVE)
    )

    # r5-r8 shipping anger, r13-r15 billing anger
    assert [row.row_number for row in snapshot.rows] == [5, 6, 7, 8, 13, 14, 15]


def test_filters_combine_and_can_match_nothing(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    workflow = results(tmp_path)

    both = workflow.results(
        project_id,
        ResultsFilters(sentiment=SentimentLabel.POSITIVE, emotion=EmotionLabel.JOY),
    )
    none = workflow.results(
        project_id,
        ResultsFilters(sentiment=SentimentLabel.POSITIVE, emotion=EmotionLabel.ANGER),
    )

    assert len(both.rows) == 7
    assert none.rows == ()


def test_rows_carry_the_language_check_beside_the_labels(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    row = results(tmp_path).results(project_id).rows[0]

    assert row.language is not None  # the stored assessment, not a re-run
    summary = results(tmp_path).results(project_id).language
    assert summary is not None


def test_results_of_a_project_not_analysed_yet_are_unavailable(tmp_path: Path) -> None:
    project_id = imported(tmp_path)

    with pytest.raises(ResultsUnavailableError):
        results(tmp_path).results(project_id)


def test_results_of_a_missing_project_say_so(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        results(tmp_path).results("no-such-project")


def test_result_rows_carry_only_a_bounded_excerpt_of_the_text(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = results(tmp_path).results(project_id)

    first = snapshot.rows[0]
    assert SENTINEL in first.excerpt  # the start of the text, for the TEXT column
    assert all(len(row.excerpt) <= 100 for row in snapshot.rows)
    assert all("\n" not in row.excerpt for row in snapshot.rows)


def test_a_long_text_is_cut_and_its_tail_is_never_held(tmp_path: Path) -> None:
    tail = "TAILMARK-" + "z" * 40
    text = "start of a long record " + "word " * 80 + tail
    csv_bytes = f'record_id,text\nr1,"{text}"\nr2,short one\nr3,\n'.encode()
    flow = ProjectWorkflow(repository(tmp_path), VariedGateway(), LIMITS)
    project_id = flow.import_csv(csv_bytes, name="P").summary.project_id
    flow.analyze(project_id)
    workflow = results(tmp_path)

    shown = repr(workflow.results(project_id)) + repr(workflow.validation(project_id))

    assert "start of a long record" in shown
    assert "TAILMARK" not in shown
    long_row = workflow.results(project_id).rows[0]
    assert long_row.excerpt.endswith("…") and len(long_row.excerpt) <= 100


def test_validation_lists_every_row_with_its_state_and_a_short_text(
    tmp_path: Path,
) -> None:
    project_id = imported(tmp_path)

    snapshot = results(tmp_path).validation(project_id)

    assert len(snapshot.rows) == 26
    assert [row.row_number for row in snapshot.rows] == list(range(1, 27))
    ready = [row for row in snapshot.rows if not row.rejected]
    rejected = [row for row in snapshot.rows if row.rejected]
    assert len(ready) == 25 and [row.record_id for row in rejected] == ["r26"]
    assert rejected[0].code and rejected[0].message
    assert ready[0].code is None and ready[0].message is None
    assert SENTINEL in ready[0].excerpt
    assert all(len(row.excerpt) <= 100 for row in snapshot.rows)


def test_a_rejected_empty_row_shows_a_marker_instead_of_an_empty_text(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(repository(tmp_path), VariedGateway(), LIMITS)
    project_id = flow.import_csv(
        b"record_id,text\nr1,hello there\nr2,\n", name="P"
    ).summary.project_id

    rows = results(tmp_path).validation(project_id).rows

    assert [row.excerpt for row in rows] == ["hello there", "(empty)"]
    assert [row.rejected for row in rows] == [False, True]


# -- export -----------------------------------------------------------------


def test_the_normalized_export_has_every_row_and_separates_the_languages(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    text = results(tmp_path).export_csv(project_id)

    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 26
    header = tuple(rows[0])
    assert "language" in header and "detected_language" in header
    assert rows[24]["status"] == "error" and rows[24]["error_code"] == (
        "synthetic_failure"
    )


def test_native_scores_are_added_only_when_asked_for(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    workflow = results(tmp_path)

    plain = workflow.export_csv(project_id)
    native = workflow.export_csv(project_id, include_native=True)

    assert len(native.splitlines()[0]) > len(plain.splitlines()[0])


def test_the_export_of_a_project_not_analysed_yet_is_unavailable(
    tmp_path: Path,
) -> None:
    with pytest.raises(ResultsUnavailableError):
        results(tmp_path).export_csv(imported(tmp_path))
