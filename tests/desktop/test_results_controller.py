"""The Qt-free results controller over a real SQLite project (synthetic data)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from persistence.insight_samples import SENTINEL, VariedGateway, insights_csv

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.results_workflow import (
    ResultsFilters,
    ResultsStatus,
    ResultsWorkflow,
)
from social_text_intelligence.contracts import SentimentLabel
from social_text_intelligence.desktop.projects import NoticeKind
from social_text_intelligence.desktop.results import (
    ResultsActivity,
    ResultsController,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner, ManualRunner

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


class Env:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repository = SqliteProjectRepository(AppDataLocations(root))
        self.flow = ProjectWorkflow(self.repository, VariedGateway(), LIMITS)
        self.project_id = self.flow.import_csv(
            insights_csv(), name="P"
        ).summary.project_id
        self.written: dict[Path, str] = {}

    def analyse(self) -> None:
        self.flow.analyze(self.project_id)

    def write(self, path: Path, text: str) -> None:
        self.written[path] = text

    def controller(self, runner: Any = None) -> ResultsController:
        return ResultsController(
            ResultsWorkflow(SqliteProjectRepository(AppDataLocations(self.root))),
            runner or ImmediateRunner(),
            write_file=self.write,
        )


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def test_opening_an_unanalysed_project_shows_its_validation_but_no_results(
    env: Env,
) -> None:
    controller = env.controller()

    assert controller.open(env.project_id) is True

    state = controller.state
    assert state.active and state.loaded
    assert state.validation is not None and state.validation.invalid_rows
    assert state.results is None
    assert state.notice is None


def test_opening_an_analysed_project_loads_validation_and_results(env: Env) -> None:
    env.analyse()
    controller = env.controller()

    controller.open(env.project_id)

    state = controller.state
    assert state.results is not None and state.results.total_rows == 26
    assert [p.row_number for p in state.validation.failed_rows] == [25]  # type: ignore[union-attr]


def test_loading_happens_off_the_caller_and_one_operation_runs_at_a_time(
    env: Env,
) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)

    assert controller.open(env.project_id) is True

    assert controller.state.activity is ResultsActivity.LOADING
    assert controller.state.busy and not controller.state.loaded
    assert controller.open(env.project_id) is False
    runner.run_next()
    assert not controller.state.busy
    assert controller.state.loaded


def test_changing_the_filters_reloads_the_rows_and_keeps_the_aggregates(
    env: Env,
) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    everything = controller.state.results
    assert everything is not None

    controller.set_filters(ResultsFilters(status=ResultsStatus.ERROR))

    state = controller.state
    assert state.results is not None
    assert [row.row_number for row in state.results.rows] == [25, 26]
    assert state.results.aggregates == everything.aggregates
    assert state.filters.status is ResultsStatus.ERROR


def test_a_new_project_starts_with_the_filters_cleared(env: Env) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    controller.set_filters(ResultsFilters(sentiment=SentimentLabel.NEGATIVE))

    controller.close()
    controller.open(env.project_id)

    assert controller.state.filters == ResultsFilters()


def test_export_writes_the_normalized_csv_where_the_person_chose(env: Env) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    target = env.root / "out.csv"

    assert controller.export(target, include_native=False) is True

    assert SENTINEL in env.written[target]  # the export carries the record text
    notice = controller.state.notice
    assert notice is not None and notice.code == "export_saved"
    assert notice.kind is NoticeKind.INFO
    assert "private" in notice.body


def test_a_failed_write_shows_a_fixed_message_without_the_path(env: Env) -> None:
    env.analyse()

    def broken(path: Path, text: str) -> None:
        raise OSError(f"cannot write {path}")

    controller = ResultsController(
        ResultsWorkflow(SqliteProjectRepository(AppDataLocations(env.root))),
        ImmediateRunner(),
        write_file=broken,
    )
    controller.open(env.project_id)

    controller.export(env.root / "secret-name.csv", include_native=False)

    notice = controller.state.notice
    assert notice is not None and notice.code == "export_failed"
    assert notice.kind is NoticeKind.ERROR
    assert "secret-name" not in notice.body and "cannot write" not in notice.body
    assert controller.state.loaded  # the page keeps what it showed


def test_a_project_that_vanished_is_reported_and_leaves_nothing_open(
    env: Env,
) -> None:
    controller = env.controller()

    controller.open("no-such-project")

    state = controller.state
    assert not state.active and not state.loaded
    assert state.notice is not None and state.notice.code == "project_not_found"


def test_export_is_refused_before_anything_is_loaded(env: Env) -> None:
    controller = env.controller()

    assert controller.export(env.root / "x.csv", include_native=False) is False
    assert env.written == {}


def test_notices_never_carry_record_text(env: Env) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    controller.export(env.root / "a.csv", include_native=True)

    notice = controller.state.notice
    assert notice is not None and SENTINEL not in notice.body
