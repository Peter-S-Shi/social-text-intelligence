"""A project that exists is never reported missing or half-written (M8 A2).

The M7 gate saw one unexplained "project not available" for a file that existed.
These regressions pin the suspects found by reading the listing and open paths: a
transient stat failure must not make a project vanish from the listing, a project
being created must not appear as unreadable, and a concurrent writer must not
disturb a reader.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from persistence.samples import one_row_preview
from social_text_intelligence.application.projects import (
    BatchWorkspace,
    ProjectStatus,
)
from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.infrastructure import project_schema
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


@contextmanager
def transient_stat_denial(target: Path) -> Iterator[None]:
    """Make the file system refuse to stat one file, as a scanner or sync client can.

    Windows reports a sharing violation or access-denied for a moment while another
    program has the file open exclusively or has it pending deletion."""

    real_stat, real_lstat = os.stat, os.lstat

    def refuse(real: Any) -> Any:
        def guarded(path: Any, *args: Any, **kwargs: Any) -> Any:
            if os.fspath(path) == os.fspath(target):
                raise PermissionError(13, "Access is denied")
            return real(path, *args, **kwargs)

        return guarded

    os.stat, os.lstat = refuse(real_stat), refuse(real_lstat)
    try:
        yield
    finally:
        os.stat, os.lstat = real_stat, real_lstat


def test_a_transient_stat_failure_never_makes_a_project_vanish_from_the_listing(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    first = repo.create_project(BatchWorkspace(preview=one_row_preview()), name="A")
    second = repo.create_project(BatchWorkspace(preview=one_row_preview()), name="B")
    target = tmp_path / "projects" / f"{first.project_id}.sqlite3"

    with transient_stat_denial(target):
        listed = {item.project_id: item.status for item in repo.list_projects()}

    assert set(listed) == {first.project_id, second.project_id}  # nothing vanished
    assert listed[first.project_id] is ProjectStatus.UNREADABLE  # honest, transient
    assert listed[second.project_id] is ProjectStatus.OK
    healed = {item.project_id: item.status for item in repo.list_projects()}
    assert healed[first.project_id] is ProjectStatus.OK  # nothing was lost


def test_a_transient_stat_failure_is_a_storage_error_never_not_found(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    summary = repo.create_project(BatchWorkspace(preview=one_row_preview()), name="A")
    target = tmp_path / "projects" / f"{summary.project_id}.sqlite3"

    with transient_stat_denial(target):
        with pytest.raises(ProjectStorageError):
            repo.get(summary.project_id)  # None would mean "no such project"
        with pytest.raises(ProjectStorageError):
            repo.mutate(summary.project_id, lambda workspace: workspace)
        with pytest.raises(ProjectStorageError):
            repo.begin_analysis(summary.project_id)

    assert repo.get(summary.project_id) is not None  # and the project is intact
    lease = repo.begin_analysis(summary.project_id)
    assert lease is not None  # the failed attempt left no hold behind
    repo.cancel_analysis(lease)


def test_a_project_being_created_is_not_listed_as_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creator = repository(tmp_path)
    observer = repository(tmp_path)
    seen: list[list[tuple[str, ProjectStatus]]] = []
    real_create_schema = project_schema.create_schema

    def create_schema_then_look(connection: sqlite3.Connection) -> None:
        # another instance lists the folder while this project is half-written
        seen.append([(i.project_id, i.status) for i in observer.list_projects()])
        real_create_schema(connection)

    monkeypatch.setattr(project_schema, "create_schema", create_schema_then_look)
    summary = creator.create_project(
        BatchWorkspace(preview=one_row_preview()), name="New"
    )

    assert seen, "the observer never ran"
    assert all(status is ProjectStatus.OK for _, status in seen[0]), seen[0]
    final = {i.project_id: i.status for i in observer.list_projects()}
    assert final == {summary.project_id: ProjectStatus.OK}


def test_readers_are_not_disturbed_by_a_writer_holding_the_write_lock(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    summary = repo.create_project(BatchWorkspace(preview=one_row_preview()), name="A")
    path = tmp_path / "projects" / f"{summary.project_id}.sqlite3"

    writer = sqlite3.connect(path, isolation_level=None)
    try:
        writer.execute("BEGIN IMMEDIATE")  # a commit in progress elsewhere
        listed = repo.list_projects()
        opened = repo.get(summary.project_id)
    finally:
        writer.execute("ROLLBACK")
        writer.close()

    assert [(i.project_id, i.status) for i in listed] == [
        (summary.project_id, ProjectStatus.OK)
    ]
    assert opened is not None
