"""Two application instances on one data root: scoped project exclusion."""

from __future__ import annotations

from pathlib import Path

import pytest
from persistence.workflow_samples import ScriptedGateway, csv_text

from social_text_intelligence.application.project_workflow import (
    AnalysisRun,
    CsvLimits,
    ProjectBusyError,
    ProjectPhase,
    ProjectWorkflow,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .harness import Peer, eventually

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)


def instance(root: Path, gateway: ScriptedGateway | None = None) -> ProjectWorkflow:
    return ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(root)),
        gateway or ScriptedGateway(),
        LIMITS,
    )


def test_a_second_instance_cannot_start_a_duplicate_analysis(tmp_path: Path) -> None:
    project = instance(tmp_path).import_csv(csv_text(4), name="P").summary.project_id
    peer = Peer("analyze", tmp_path / "sig", root=str(tmp_path), project=project)
    peer.wait_started()
    gateway = ScriptedGateway()
    try:
        with pytest.raises(ProjectBusyError) as busy:
            instance(tmp_path, gateway).analyze(project)
    finally:
        assert peer.finish() == {"run": "committed"}

    assert gateway.calls == 0  # no inference time was spent on the duplicate
    assert busy.value.code == "project_busy"
    assert "another window" in busy.value.message
    assert "cancel it" not in busy.value.message  # it cannot be cancelled from here

    done = instance(tmp_path)
    details = done.open_project(project)
    assert details.phase is ProjectPhase.ANALYZED and details.analyzed_rows == 4
    assert done.analyze(project) is AnalysisRun.NOTHING_TO_ANALYZE  # still recoverable


def test_exclusion_is_scoped_to_the_same_project(tmp_path: Path) -> None:
    flow = instance(tmp_path)
    held = flow.import_csv(csv_text(3), name="A").summary.project_id
    other = flow.import_csv(csv_text(3), name="B").summary.project_id
    peer = Peer("analyze", tmp_path / "sig", root=str(tmp_path), project=held)
    peer.wait_started()
    try:
        assert instance(tmp_path).analyze(other) is AnalysisRun.COMMITTED
        listed = {p.project_id for p in instance(tmp_path).list_projects()}
        assert listed == {held, other}  # listing is never blocked
        assert instance(tmp_path).open_project(held).phase is ProjectPhase.READY
    finally:
        assert peer.finish() == {"run": "committed"}


def test_delete_is_refused_while_another_instance_analyses(tmp_path: Path) -> None:
    project = instance(tmp_path).import_csv(csv_text(3), name="P").summary.project_id
    peer = Peer("analyze", tmp_path / "sig", root=str(tmp_path), project=project)
    peer.wait_started()
    try:
        with pytest.raises(ProjectBusyError) as busy:
            instance(tmp_path).delete_project(project)
        assert "another window" in busy.value.message
    finally:
        assert peer.finish() == {"run": "committed"}

    details = instance(tmp_path).open_project(project)  # nothing was removed
    assert details.phase is ProjectPhase.ANALYZED


def test_a_hard_killed_analyser_never_blocks_the_project(tmp_path: Path) -> None:
    project = instance(tmp_path).import_csv(csv_text(3), name="P").summary.project_id
    peer = Peer("analyze", tmp_path / "sig", root=str(tmp_path), project=project)
    peer.wait_started()
    with pytest.raises(ProjectBusyError):
        instance(tmp_path).analyze(project)

    peer.kill()

    flow = instance(tmp_path)
    assert flow.open_project(project).phase is ProjectPhase.READY  # untouched
    run = eventually(lambda: flow.analyze(project), retry_on=(ProjectBusyError,))
    assert run is AnalysisRun.COMMITTED
    assert flow.open_project(project).analyzed_rows == 3


def test_a_refused_analysis_leaves_no_hold_behind_in_this_process(
    tmp_path: Path,
) -> None:
    project = instance(tmp_path).import_csv(csv_text(3), name="P").summary.project_id
    mine = instance(tmp_path)
    peer = Peer("analyze", tmp_path / "sig", root=str(tmp_path), project=project)
    peer.wait_started()
    with pytest.raises(ProjectBusyError):
        mine.analyze(project)
    assert peer.finish() == {"run": "committed"}

    assert mine.analyze(project) is AnalysisRun.NOTHING_TO_ANALYZE
    assert mine.delete_project(project) is True  # not wedged by a leftover hold


def test_cancellation_still_commits_nothing_and_frees_the_project(
    tmp_path: Path,
) -> None:
    flow = instance(tmp_path)
    project = flow.import_csv(csv_text(5), name="P").summary.project_id
    stop = {"now": False}
    gateway = ScriptedGateway(lambda n: stop.update(now=True) if n == 2 else None)

    run = instance(tmp_path, gateway).analyze(project, cancelled=lambda: stop["now"])

    assert run is AnalysisRun.CANCELLED
    assert flow.open_project(project).phase is ProjectPhase.READY
    assert instance(tmp_path).analyze(project) is AnalysisRun.COMMITTED
