"""The ProjectRepository port behaves identically in memory and on disk."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from persistence.samples import SyntheticGateway, one_row_preview, rich_workspace
from social_text_intelligence.application.projects import (
    BatchWorkspace,
    InMemoryProjectRepository,
    ProjectRepository,
    WorkspaceMutationConflict,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services import create_review_state
from social_text_intelligence.services.batch import analyze_batch
from social_text_intelligence.services.insights import InsightState


@pytest.fixture(params=["memory", "sqlite"])
def repository(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[ProjectRepository]:
    if request.param == "memory":
        yield InMemoryProjectRepository()
    else:
        yield SqliteProjectRepository(AppDataLocations(tmp_path))


def analyzed(preview_workspace: BatchWorkspace) -> BatchWorkspace:
    assert preview_workspace.preview is not None
    result = analyze_batch(preview_workspace.preview, SyntheticGateway())
    return BatchWorkspace(
        preview=preview_workspace.preview,
        result=result,
        reviews=create_review_state(result),
        insights=InsightState(),
    )


def test_create_then_get_returns_the_same_workspace(
    repository: ProjectRepository,
) -> None:
    workspace = rich_workspace()
    first = repository.create(workspace)
    second = repository.create(BatchWorkspace())
    assert first != second
    assert repository.get(first) == workspace
    assert repository.get(second) == BatchWorkspace()


def test_unknown_and_malformed_tokens_are_absent_not_errors(
    repository: ProjectRepository,
) -> None:
    for token in ("", "missing", "../escape", "..\\escape", "a" * 500, "C:\\x"):
        assert repository.get(token) is None
        assert repository.mutate(token, lambda current: current) is None
        assert repository.begin_analysis(token) is None
        assert repository.delete(token) is False


def test_mutation_derives_from_current_state_and_commits_atomically(
    repository: ProjectRepository,
) -> None:
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    updated = repository.mutate(token, lambda current: replace(current, preview=None))
    assert updated == BatchWorkspace()
    assert repository.get(token) == BatchWorkspace()


def test_failed_mutation_changes_nothing(repository: ProjectRepository) -> None:
    original = BatchWorkspace(preview=one_row_preview())
    token = repository.create(original)

    def explode(current: BatchWorkspace) -> BatchWorkspace:
        raise ValueError("synthetic mutation failure")

    with pytest.raises(ValueError, match="synthetic mutation failure"):
        repository.mutate(token, explode)
    assert repository.get(token) == original


def test_active_lease_blocks_mutation_second_lease_and_delete(
    repository: ProjectRepository,
) -> None:
    original = BatchWorkspace(preview=one_row_preview())
    token = repository.create(original)
    lease = repository.begin_analysis(token)
    assert lease is not None and lease.workspace == original
    with pytest.raises(WorkspaceMutationConflict):
        repository.mutate(token, lambda current: current)
    with pytest.raises(RuntimeError, match="already being analyzed"):
        repository.begin_analysis(token)
    with pytest.raises(RuntimeError, match="cannot be (cleared|deleted)"):
        repository.delete(token)
    assert repository.get(token) == original
    assert repository.cancel_analysis(lease) is True
    assert repository.get(token) == original
    assert repository.delete(token) is True


def test_complete_analysis_commits_once_and_releases_the_lease(
    repository: ProjectRepository,
) -> None:
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    lease = repository.begin_analysis(token)
    assert lease is not None
    finished = analyzed(lease.workspace)
    assert repository.complete_analysis(lease, finished) is True
    assert repository.get(token) == finished
    assert repository.complete_analysis(lease, finished) is False
    assert repository.cancel_analysis(lease) is False
    assert repository.mutate(token, lambda current: current) == finished


def test_cancelled_lease_cannot_commit_later(repository: ProjectRepository) -> None:
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    lease = repository.begin_analysis(token)
    assert lease is not None
    assert repository.cancel_analysis(lease) is True
    assert repository.complete_analysis(lease, analyzed(lease.workspace)) is False
    workspace = repository.get(token)
    assert workspace is not None and workspace.result is None


def test_delete_removes_the_project(repository: ProjectRepository) -> None:
    token = repository.create(rich_workspace())
    assert repository.delete(token) is True
    assert repository.get(token) is None
    assert repository.delete(token) is False
