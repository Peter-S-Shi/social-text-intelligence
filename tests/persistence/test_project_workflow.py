"""The project workflow over a real SQLite repository (synthetic data)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from social_text_intelligence.application.project_workflow import (
    AnalysisRun,
    CsvLimits,
    ProjectBusyError,
    ProjectChangedError,
    ProjectNotFoundError,
    ProjectPhase,
    ProjectWorkflow,
)
from social_text_intelligence.application.projects import ProjectStatus
from social_text_intelligence.contracts import (
    AnalysisReport,
    NormalizedTextInput,
    ValidationError,
)
from social_text_intelligence.contracts.errors import (
    AnalysisSessionBlockedError,
    ModelsNotReadyError,
    ProjectStorageError,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService
from social_text_intelligence.services.batch import BatchProgress

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
SENTINEL = "ZQX-private-sentinel-77"


def csv_text(rows: int = 5, column: str = "text") -> bytes:
    lines = [f"record_id,{column}"]
    lines += [
        f"r{n},{SENTINEL} synthetic message number {n}." for n in range(1, rows + 1)
    ]
    return ("\n".join(lines) + "\n").encode()


class ScriptedGateway:
    """Deterministic analysis with a hook before each row."""

    initialized = True

    def __init__(self, before_row: Callable[[int], None] | None = None) -> None:
        self._service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(),
            emotion_provider=DeterministicEmotionProvider(),
        )
        self.before_row = before_row
        self.calls = 0

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        self.calls += 1
        if self.before_row is not None:
            self.before_row(self.calls)
        return self._service.analyze(record)


def workflow(root: Path, gateway: ScriptedGateway | None = None) -> ProjectWorkflow:
    return ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(root)),
        gateway or ScriptedGateway(),
        LIMITS,
    )


def project_files(root: Path) -> list[str]:
    directory = root / "projects"
    return sorted(p.name for p in directory.glob("*")) if directory.is_dir() else []


def test_a_csv_with_a_text_column_becomes_a_durable_ready_project(
    tmp_path: Path,
) -> None:
    details = workflow(tmp_path).import_csv(csv_text(5), name="Support tickets")

    assert details.phase is ProjectPhase.READY
    assert details.summary.name == "Support tickets"
    assert (details.text_column, details.row_count) == ("text", 5)
    assert (details.valid_rows, details.invalid_rows) == (5, 0)

    reopened = workflow(tmp_path)  # a fresh process
    assert [p.name for p in reopened.list_projects()] == ["Support tickets"]
    again = reopened.open_project(details.summary.project_id)
    assert again.phase is ProjectPhase.READY and again.row_count == 5


def test_a_csv_without_a_text_column_needs_a_real_selection_step(
    tmp_path: Path,
) -> None:
    flow = workflow(tmp_path)
    details = flow.import_csv(csv_text(4, column="message"), name="Notes")
    assert details.phase is ProjectPhase.NEEDS_COLUMN
    assert details.headers == ("record_id", "message")
    project_id = details.summary.project_id

    # the pending choice survives a restart
    assert workflow(tmp_path).open_project(project_id).phase is (
        ProjectPhase.NEEDS_COLUMN
    )

    chosen = flow.choose_column(project_id, "message")
    assert chosen.phase is ProjectPhase.READY and chosen.text_column == "message"
    assert chosen.row_count == 4


def test_a_missing_column_is_refused_and_a_second_choice_conflicts(
    tmp_path: Path,
) -> None:
    flow = workflow(tmp_path)
    project_id = flow.import_csv(csv_text(2, "message"), name="N").summary.project_id

    with pytest.raises(ValidationError) as missing:
        flow.choose_column(project_id, "nope")
    assert missing.value.code == "missing_text_column"
    assert flow.open_project(project_id).phase is ProjectPhase.NEEDS_COLUMN

    flow.choose_column(project_id, "message")
    with pytest.raises(ProjectChangedError):
        flow.choose_column(project_id, "message")  # already chosen elsewhere


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "empty_file"),
        (b"x" * 30_000, "file_too_large"),
        (b"\xff\xfe\x00bad", "invalid_encoding"),
        (b"record_id,text\n", "no_data_rows"),
        (csv_text(25), "too_many_rows"),
        (b"a,a\n1,2\n", "duplicate_header"),
    ],
)
def test_invalid_csv_creates_no_project_and_shows_a_fixed_message(
    tmp_path: Path, content: bytes, code: str
) -> None:
    flow = workflow(tmp_path)

    with pytest.raises(ValidationError) as failure:
        flow.import_csv(content, name="Bad")

    assert failure.value.code == code
    assert SENTINEL not in failure.value.message
    assert flow.list_projects() == ()
    assert project_files(tmp_path) == []  # nothing durable was left behind


def test_an_awkward_name_falls_back_to_a_default(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    for name in ("", "x" * 500, "bad\x00name"):
        assert flow.import_csv(csv_text(1), name=name).summary.name == (
            "Untitled project"
        )


def test_analysis_reports_row_progress_commits_and_reopens(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    project_id = flow.import_csv(csv_text(6), name="P").summary.project_id
    seen: list[BatchProgress] = []

    outcome = flow.analyze(project_id, progress=seen.append)

    assert outcome is AnalysisRun.COMMITTED
    assert [p.completed for p in seen] == [1, 2, 3, 4, 5, 6]
    assert {p.total for p in seen} == {6}
    again = workflow(tmp_path).open_project(project_id)
    assert again.phase is ProjectPhase.ANALYZED
    assert (again.analyzed_rows, again.failed_rows) == (6, 0)
    assert (
        dict(again.sentiment_counts)["positive"]
        + dict(again.sentiment_counts)["negative"]
        + dict(again.sentiment_counts)["neutral"]
        == 6
    )


def test_cancel_commits_nothing_and_releases_the_lease(tmp_path: Path) -> None:
    stop = threading.Event()
    gateway = ScriptedGateway(lambda n: stop.set() if n == 3 else None)
    flow = workflow(tmp_path, gateway)
    project_id = flow.import_csv(csv_text(6), name="P").summary.project_id

    outcome = flow.analyze(project_id, cancelled=stop.is_set)

    assert outcome is AnalysisRun.CANCELLED
    assert gateway.calls == 3  # it really stopped part-way
    persisted = workflow(tmp_path).open_project(project_id)
    assert persisted.phase is ProjectPhase.READY  # no partial result
    assert persisted.analyzed_rows is None

    stop.clear()
    gateway.before_row = None
    assert flow.analyze(project_id) is AnalysisRun.COMMITTED  # lease was released


@pytest.mark.parametrize(
    "error",
    [ModelsNotReadyError(("emotion",)), AnalysisSessionBlockedError()],
)
def test_an_unavailable_analysis_fails_the_whole_run_and_commits_nothing(
    tmp_path: Path, error: Exception
) -> None:
    def fail_at_row_three(n: int) -> None:
        if n == 3:
            raise error  # H2 latched, or models lost, while the batch was running

    flow = workflow(tmp_path, ScriptedGateway(fail_at_row_three))
    project_id = flow.import_csv(csv_text(6), name="P").summary.project_id

    with pytest.raises(type(error)):
        flow.analyze(project_id)

    persisted = workflow(tmp_path).open_project(project_id)
    assert persisted.phase is ProjectPhase.READY  # not even the rows before it
    flow_again = workflow(tmp_path)
    assert flow_again.analyze(project_id) is AnalysisRun.COMMITTED  # lease released


def test_row_failures_are_recorded_but_do_not_fail_the_run(tmp_path: Path) -> None:
    csv = (
        b"record_id,text\nr1,A fine synthetic message.\nr2,   \nr3,Another fine one.\n"
    )
    flow = workflow(tmp_path)
    project_id = flow.import_csv(csv, name="P").summary.project_id
    details = flow.open_project(project_id)
    assert (details.valid_rows, details.invalid_rows) == (2, 1)

    assert flow.analyze(project_id) is AnalysisRun.COMMITTED
    done = flow.open_project(project_id)
    assert (done.analyzed_rows, done.failed_rows) == (2, 1)


def test_deleting_removes_the_project_files_and_the_listing(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    project_id = flow.import_csv(csv_text(3), name="P").summary.project_id
    flow.analyze(project_id)
    assert project_files(tmp_path)

    assert flow.delete_project(project_id) is True

    assert flow.list_projects() == ()
    assert project_files(tmp_path) == []
    assert flow.delete_project(project_id) is False  # already gone
    with pytest.raises(ProjectNotFoundError):
        flow.open_project(project_id)


def test_delete_is_refused_while_an_analysis_holds_the_project(
    tmp_path: Path,
) -> None:
    flow_box: list[ProjectWorkflow] = []
    refusals: list[Exception] = []
    ids: list[str] = []

    def during_row(n: int) -> None:
        if n == 2:
            try:
                flow_box[0].delete_project(ids[0])
            except ProjectBusyError as error:
                refusals.append(error)

    flow = workflow(tmp_path, ScriptedGateway(during_row))
    flow_box.append(flow)
    ids.append(flow.import_csv(csv_text(4), name="P").summary.project_id)

    assert flow.analyze(ids[0]) is AnalysisRun.COMMITTED

    assert len(refusals) == 1
    assert flow.open_project(ids[0]).phase is ProjectPhase.ANALYZED  # not deleted


def test_a_second_analysis_of_a_running_project_is_refused(tmp_path: Path) -> None:
    refused: list[Exception] = []
    holder: list[ProjectWorkflow] = []
    ids: list[str] = []

    def second_analysis(n: int) -> None:
        if n == 1:
            try:
                holder[0].analyze(ids[0])
            except ProjectBusyError as error:
                refused.append(error)

    flow = workflow(tmp_path, ScriptedGateway(second_analysis))
    holder.append(flow)
    ids.append(flow.import_csv(csv_text(2), name="Q").summary.project_id)

    assert flow.analyze(ids[0]) is AnalysisRun.COMMITTED
    assert len(refused) == 1


def test_unreadable_and_unsupported_entries_are_handled_not_treated_as_projects(
    tmp_path: Path,
) -> None:
    flow = workflow(tmp_path)
    good = flow.import_csv(csv_text(2), name="Good").summary.project_id
    junk_id = "ab" * 16
    (tmp_path / "projects" / f"{junk_id}.sqlite3").write_bytes(b"not a database")

    listed = {p.project_id: p for p in flow.list_projects()}
    assert listed[good].status is ProjectStatus.OK
    assert listed[junk_id].status is ProjectStatus.UNREADABLE
    assert listed[junk_id].name is None

    with pytest.raises(ProjectStorageError) as refused:
        flow.open_project(junk_id)
    assert "not a database" not in refused.value.message
    assert flow.delete_project(junk_id) is True  # it can still be cleaned up
    assert junk_id not in {p.project_id for p in flow.list_projects()}


def test_no_error_text_carries_csv_content_or_paths(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    messages: list[str] = []
    for content in (b"", csv_text(25), SENTINEL.encode() + b"\xff", b"a,a\n1,2\n"):
        with pytest.raises(ValidationError) as failure:
            flow.import_csv(content, name="Bad")
        messages.append(failure.value.message)
    for error in (ProjectBusyError(), ProjectChangedError(), ProjectNotFoundError()):
        messages.append(error.message)
    joined = " ".join(messages)
    assert SENTINEL not in joined and str(tmp_path) not in joined


def test_a_project_deleted_by_another_process_mid_analysis_is_not_resurrected(
    tmp_path: Path,
) -> None:
    other = workflow(tmp_path)  # a second process over the same folder
    ids: list[str] = []

    def delete_elsewhere(n: int) -> None:
        if n == 2:
            assert other.delete_project(ids[0]) is True

    flow = workflow(tmp_path, ScriptedGateway(delete_elsewhere))
    ids.append(flow.import_csv(csv_text(4), name="P").summary.project_id)

    outcome = flow.analyze(ids[0])

    assert outcome is AnalysisRun.STALE
    assert flow.list_projects() == () and project_files(tmp_path) == []
