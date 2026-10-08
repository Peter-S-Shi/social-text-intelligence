"""The projects controller over a real SQLite repository and a scripted gateway."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from persistence.workflow_samples import (
    SENTINEL,
    ScriptedGateway,
    csv_text,
)

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectPhase,
    ProjectWorkflow,
)
from social_text_intelligence.application.projects import ProjectStatus
from social_text_intelligence.contracts.errors import (
    AnalysisSessionBlockedError,
    ModelsNotReadyError,
)
from social_text_intelligence.desktop.projects import (
    ProjectsActivity,
    ProjectsController,
    ProjectsState,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner, ManualRunner, ThreadedRunner

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)


class Rig:
    def __init__(
        self,
        tmp_path: Path,
        runner: ManualRunner | ThreadedRunner | None = None,
        gateway: ScriptedGateway | None = None,
    ) -> None:
        self.root = tmp_path / "app"
        self.files = tmp_path / "files"
        self.files.mkdir(exist_ok=True)
        self.gateway = gateway or ScriptedGateway()
        self.runner = runner or ImmediateRunner()
        self.workflow = ProjectWorkflow(
            SqliteProjectRepository(AppDataLocations(self.root)),
            self.gateway,
            LIMITS,
        )
        self.controller = ProjectsController(
            self.workflow, self.runner, max_file_bytes=LIMITS.max_bytes
        )
        self.states: list[ProjectsState] = []
        self.controller.subscribe(self.states.append)

    def csv(self, name: str, content: bytes) -> Path:
        path = self.files / name
        path.write_bytes(content)
        return path

    @property
    def state(self) -> ProjectsState:
        return self.controller.state


def test_refresh_lists_projects_and_marks_the_listing_done(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    assert not rig.state.listed

    rig.controller.refresh()

    assert rig.state.listed and rig.state.projects == ()
    assert rig.state.activity is ProjectsActivity.IDLE


def test_importing_a_csv_creates_a_durable_project_and_opens_it(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)

    assert rig.controller.import_csv(rig.csv("Support tickets.csv", csv_text(4)))

    current = rig.state.current
    assert current is not None and current.phase is ProjectPhase.READY
    assert current.summary.name == "Support tickets"
    assert [p.name for p in rig.state.projects] == ["Support tickets"]
    assert rig.state.notice is None
    # durable: a brand-new workflow over the same folder sees it
    again = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(rig.root)), ScriptedGateway(), LIMITS
    )
    assert [p.name for p in again.list_projects()] == ["Support tickets"]


def test_a_csv_without_text_goes_through_the_column_step(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("notes.csv", csv_text(3, column="message")))
    current = rig.state.current
    assert current is not None and current.phase is ProjectPhase.NEEDS_COLUMN
    assert current.headers == ("record_id", "message")

    assert rig.controller.choose_column("message")

    ready = rig.state.current
    assert ready is not None and ready.phase is ProjectPhase.READY
    assert ready.text_column == "message"


def test_a_wrong_column_shows_a_fixed_message_and_keeps_the_step(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("notes.csv", csv_text(3, column="message")))

    rig.controller.choose_column("nope")

    assert rig.state.notice is not None
    assert rig.state.notice.code == "missing_text_column"
    assert rig.state.current is not None
    assert rig.state.current.phase is ProjectPhase.NEEDS_COLUMN


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "empty_file"),
        (csv_text(25), "too_many_rows"),
        (b"\xff\xfe\x00bad", "invalid_encoding"),
        (b"x" * 25_000, "file_too_large"),
    ],
)
def test_invalid_csv_shows_a_safe_error_and_creates_nothing(
    tmp_path: Path, content: bytes, code: str
) -> None:
    rig = Rig(tmp_path)

    rig.controller.import_csv(rig.csv("bad.csv", content))

    notice = rig.state.notice
    assert notice is not None and notice.code == code
    assert SENTINEL not in notice.body and str(tmp_path) not in notice.body
    assert rig.state.current is None and rig.state.projects == ()
    assert rig.state.activity is ProjectsActivity.IDLE


def test_an_unreadable_file_is_a_fixed_message_without_the_path(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)

    rig.controller.import_csv(rig.files / "does-not-exist.csv")

    notice = rig.state.notice
    assert notice is not None and notice.code == "file_unreadable"
    assert "does-not-exist" not in notice.body and str(tmp_path) not in notice.body


def test_a_huge_file_is_not_read_into_memory(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    big = rig.files / "big.csv"
    with big.open("wb") as handle:
        handle.seek(50_000_000)
        handle.write(b"x")  # a sparse 50 MB file

    rig.controller.import_csv(big)

    notice = rig.state.notice
    assert notice is not None and notice.code == "file_too_large"


def test_analysis_reports_rows_and_ends_analysed_with_a_fresh_list(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(5)))
    before = rig.state.projects[0].updated_at

    assert rig.controller.analyze()

    done = rig.state.current
    assert done is not None and done.phase is ProjectPhase.ANALYZED
    assert (done.analyzed_rows, done.failed_rows) == (5, 0)
    assert rig.state.progress is None and not rig.state.cancelling
    updated = rig.state.projects[0].updated_at
    assert before is not None and updated is not None and updated >= before
    seen = [s.progress.completed for s in rig.states if s.progress is not None]
    assert seen == sorted(seen) and seen[-1] == 5


def test_cancel_stops_part_way_commits_nothing_and_allows_a_retry(
    tmp_path: Path,
) -> None:
    started, proceed = threading.Event(), threading.Event()

    def pause_at_row_three(n: int) -> None:
        if n == 3:
            started.set()
            proceed.wait(5)

    gateway = ScriptedGateway(pause_at_row_three)
    runner = ThreadedRunner()
    rig = Rig(tmp_path, runner, gateway)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(8)))
    runner.drain(lambda: rig.state.current is not None)

    try:
        rig.controller.analyze()
        runner.drain(started.is_set)
        assert rig.controller.can_cancel
        rig.controller.cancel()
        assert rig.state.cancelling
        proceed.set()
        runner.drain(lambda: rig.state.activity is ProjectsActivity.IDLE)
    finally:
        proceed.set()
        runner.join()

    assert gateway.calls == 3
    notice = rig.state.notice
    assert notice is not None and notice.code == "analysis_cancelled"
    assert "Nothing was saved" in notice.body
    current = rig.state.current
    assert current is not None and current.phase is ProjectPhase.READY
    reopened = rig.workflow.open_project(current.summary.project_id)
    assert reopened.phase is ProjectPhase.READY and reopened.analyzed_rows is None

    # the lease was released, so the same project can be analysed again
    gateway.before_row = None
    assert rig.controller.analyze()
    runner.drain(
        lambda: (
            rig.state.current is not None
            and rig.state.current.phase is ProjectPhase.ANALYZED
        )
    )
    runner.join()


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ModelsNotReadyError(("emotion",)), "models_not_ready"),
        (AnalysisSessionBlockedError(), "analysis_session_blocked"),
    ],
)
def test_unavailable_analysis_fails_the_run_safely(
    tmp_path: Path, error: Exception, code: str
) -> None:
    def fail_at_three(n: int) -> None:
        if n == 3:
            raise error

    rig = Rig(tmp_path, gateway=ScriptedGateway(fail_at_three))
    rig.controller.import_csv(rig.csv("p.csv", csv_text(6)))

    rig.controller.analyze()

    notice = rig.state.notice
    assert notice is not None and notice.code == code
    current = rig.state.current
    assert current is not None and current.phase is ProjectPhase.READY
    assert rig.state.activity is ProjectsActivity.IDLE


def test_only_one_operation_runs_at_a_time(tmp_path: Path) -> None:
    runner = ManualRunner()
    rig = Rig(tmp_path, runner)
    path = rig.csv("p.csv", csv_text(2))

    assert rig.controller.import_csv(path)
    assert not rig.controller.import_csv(path)
    assert not rig.controller.refresh()
    assert not rig.controller.delete("ab" * 16)
    assert len(runner.jobs) == 1


def test_delete_removes_the_project_and_says_it_conservatively(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    project_id = rig.state.projects[0].project_id

    assert rig.controller.delete(project_id)

    assert rig.state.projects == () and rig.state.current is None
    notice = rig.state.notice
    assert notice is not None and notice.code == "project_deleted"
    assert "application's data files" in notice.body
    assert "erase" not in notice.body.lower()
    assert not list((rig.root / "projects").glob("*"))


def test_opening_a_missing_project_refreshes_the_list_and_explains(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    project_id = rig.state.projects[0].project_id
    rig.workflow.delete_project(project_id)  # removed behind the UI's back

    rig.controller.open_project(project_id)

    assert rig.state.notice is not None
    assert rig.state.notice.code == "project_not_found"
    assert rig.state.projects == () and rig.state.current is None


def test_an_unreadable_entry_is_listed_but_cannot_be_opened(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    junk = "cd" * 16
    (rig.root / "projects" / f"{junk}.sqlite3").write_bytes(b"not a database")
    rig.controller.refresh()
    listed = {p.project_id: p for p in rig.state.projects}
    assert listed[junk].status is ProjectStatus.UNREADABLE

    rig.controller.open_project(junk)

    assert rig.state.current is None or rig.state.current.summary.project_id != junk
    notice = rig.state.notice
    assert notice is not None and notice.code == "unreadable_project"
    assert "not a database" not in notice.body
    assert rig.controller.delete(junk)  # it can still be removed
    assert junk not in {p.project_id for p in rig.state.projects}


def test_work_runs_off_the_ui_thread_and_listeners_run_on_it(tmp_path: Path) -> None:
    runner = ThreadedRunner()
    rig = Rig(tmp_path, runner)
    threads: list[int] = []
    rig.controller.subscribe(lambda state: threads.append(threading.get_ident()))

    rig.controller.import_csv(rig.csv("p.csv", csv_text(3)))
    runner.drain(lambda: rig.state.current is not None)
    rig.controller.analyze()
    runner.drain(
        lambda: (
            rig.state.current is not None
            and rig.state.current.phase is ProjectPhase.ANALYZED
        )
    )
    runner.join()

    assert threads and set(threads) == {threading.get_ident()}


def test_progress_updates_are_coalesced(tmp_path: Path) -> None:
    runner = ManualRunner()
    rig = Rig(tmp_path, runner)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(6)))
    runner.run_next()  # the import job
    assert rig.controller.analyze()

    work, deliver = runner.jobs.popleft()
    outcome = work()
    assert len(runner.posted) == 1  # six rows, one pending UI update
    runner.pump_posts()
    progress = rig.state.progress
    assert progress is not None and progress.completed == 6
    deliver(outcome)
    assert rig.state.progress is None


def test_close_project_returns_to_the_list(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    rig.controller.close_project()
    assert rig.state.current is None and len(rig.state.projects) == 1


def test_notices_never_carry_content_or_paths(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    for name, content in (("a.csv", b""), ("b.csv", SENTINEL.encode() + b"\xff")):
        rig.controller.import_csv(rig.csv(name, content))
        notice = rig.state.notice
        assert notice is not None
        assert SENTINEL not in notice.body + notice.title
        assert str(tmp_path) not in notice.body + notice.title
        assert name not in notice.body


def test_a_model_load_failure_through_the_gate_fails_the_run_and_stays_retryable(
    tmp_path: Path,
) -> None:
    from social_text_intelligence.contracts.errors import ProviderError
    from social_text_intelligence.desktop.gate import AnalysisGate

    def fail_first(n: int) -> None:
        raise ProviderError(
            provider="p", code="model_load_failed", message="V1 offline mode text"
        )

    gateway = ScriptedGateway(fail_first)
    rig = Rig(tmp_path, gateway=gateway)
    rig.workflow = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(rig.root)),
        AnalysisGate(gateway),
        LIMITS,
    )
    rig.controller = ProjectsController(
        rig.workflow, rig.runner, max_file_bytes=LIMITS.max_bytes
    )
    rig.controller.import_csv(rig.csv("p.csv", csv_text(4)))

    rig.controller.analyze()

    notice = rig.controller.state.notice
    assert notice is not None and notice.code == "model_load_failed"
    assert "offline mode" not in notice.body
    current = rig.controller.state.current
    assert current is not None and current.phase is ProjectPhase.READY  # retryable
    assert gateway.calls == 1  # it did not grind through every row


def test_nothing_to_analyse_says_so_instead_of_doing_nothing(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", b"record_id,text\nr1,  \n"))

    rig.controller.analyze()

    notice = rig.state.notice
    assert notice is not None and notice.code == "nothing_to_analyze"


def test_choosing_a_column_for_a_project_removed_elsewhere_resyncs(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("n.csv", csv_text(2, column="message")))
    project_id = rig.state.projects[0].project_id
    rig.workflow.delete_project(project_id)  # another process removed it

    rig.controller.choose_column("message")

    assert rig.state.notice is not None
    assert rig.state.notice.code == "project_not_found"
    assert rig.state.current is None and rig.state.projects == ()
    assert rig.state.activity is ProjectsActivity.IDLE


def test_analysing_a_project_removed_elsewhere_resyncs(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    rig.workflow.delete_project(rig.state.projects[0].project_id)

    rig.controller.analyze()

    assert rig.state.notice is not None
    assert rig.state.notice.code == "project_not_found"
    assert rig.state.current is None and rig.state.projects == ()


def test_a_failed_operation_re_lists_before_it_goes_idle(tmp_path: Path) -> None:
    runner = ManualRunner()
    rig = Rig(tmp_path, runner)
    runner.run_next() if runner.jobs else None
    ran: list[str] = []
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    runner.run_next()
    project_id = rig.state.projects[0].project_id
    rig.workflow.delete_project(project_id)

    rig.controller.open_project(project_id)
    rig.controller.when_idle(lambda: ran.append("idle"))
    runner.run_next()  # the open fails; the re-list is chained, not yet idle

    assert rig.state.busy and ran == []
    runner.run_next()
    assert not rig.state.busy and ran == ["idle"]
    assert rig.state.projects == ()


def test_deleting_an_already_removed_project_does_not_claim_a_deletion(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    project_id = rig.state.projects[0].project_id
    rig.workflow.delete_project(project_id)

    rig.controller.delete(project_id)

    notice = rig.state.notice
    assert notice is not None and notice.title == "Already removed"
    assert "deleted" not in notice.body.lower()


def test_a_cancel_that_arrives_after_the_commit_point_is_reported_truthfully(
    tmp_path: Path,
) -> None:
    runner = ManualRunner()
    rig = Rig(tmp_path, runner)
    rig.controller.import_csv(rig.csv("p.csv", csv_text(2)))
    runner.run_next()
    rig.controller.analyze()
    work, deliver = runner.jobs.popleft()
    outcome = work()  # the batch already committed...
    rig.controller.cancel()  # ...when Cancel arrives
    deliver(outcome)

    notice = rig.state.notice
    assert notice is not None and notice.code == "analysis_saved"
    current = rig.state.current
    assert current is not None and current.phase is ProjectPhase.ANALYZED
