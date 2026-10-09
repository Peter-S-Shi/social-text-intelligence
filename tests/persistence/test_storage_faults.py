"""Storage faults are reported accurately and never leave a partial commit (M8 A4).

The disk-full cases use SQLite's own ``max_page_count`` limit, which makes the real
engine raise its real ``SQLITE_FULL`` error without filling a disk; OS-level
``ENOSPC`` and the locked/read-only cases are injected or produced on real files
(see docs/V2_M8_TRACK_A_LEDGER.md for what is real and what is emulated).
"""

from __future__ import annotations

import errno
import os
import sqlite3
import stat
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from persistence.samples import SyntheticGateway, one_row_preview
from social_text_intelligence.application.projects import BatchWorkspace
from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.infrastructure import sqlite_support as support
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services import create_review_state
from social_text_intelligence.services.batch import (
    analyze_batch,
    inspect_csv_upload,
    prepare_csv_batch,
)
from social_text_intelligence.services.insights import InsightState


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def sqlite_error(name: str, code: int, text: str) -> sqlite3.OperationalError:
    error = sqlite3.OperationalError(text)
    error.sqlite_errorcode = code
    error.sqlite_errorname = name
    return error


def windows_error(winerror: int, text: str) -> OSError:
    """Windows reports sharing and lock violations with errno EACCES."""

    error = PermissionError(errno.EACCES, text)
    setattr(error, "winerror", winerror)  # noqa: B010 - absent off Windows
    return error


def guarded_raise(error: BaseException) -> ProjectStorageError:
    @support.storage_guarded
    def fail() -> None:
        raise error

    with pytest.raises(ProjectStorageError) as raised:
        fail()
    return raised.value


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (sqlite_error("SQLITE_FULL", 13, "database or disk is full"), "storage_full"),
        (OSError(errno.ENOSPC, "No space left on device"), "storage_full"),
        (
            sqlite_error("SQLITE_READONLY", 8, "attempt to write a readonly database"),
            "storage_read_only",
        ),
        (OSError(errno.EROFS, "Read-only file system"), "storage_read_only"),
        (PermissionError(errno.EACCES, "Access is denied"), "storage_read_only"),
        (
            sqlite_error("SQLITE_CANTOPEN", 14, "unable to open database file"),
            "storage_locked",
        ),
        (
            sqlite_error("SQLITE_BUSY", 5, "database is locked"),
            "project_busy",
        ),
        (sqlite_error("SQLITE_IOERR", 10, "disk I/O error"), "storage_failure"),
        (OSError(errno.EIO, "I/O error"), "storage_failure"),
        (windows_error(32, "sharing violation"), "storage_locked"),
        (windows_error(33, "lock violation"), "storage_locked"),
        (windows_error(112, "disk full"), "storage_full"),
    ],
)
def test_each_fault_gets_its_own_code_and_a_content_free_actionable_message(
    error: BaseException, code: str
) -> None:
    failure = guarded_raise(error)

    assert failure.code == code
    assert failure.__cause__ is None and failure.__context__ is None
    assert str(error) not in failure.message  # fixed text, never the raw error
    if code != "project_busy":
        assert "try again" in failure.message.lower()


def test_the_messages_name_the_fault_and_the_way_out() -> None:
    full = guarded_raise(OSError(errno.ENOSPC, "x")).message
    read_only = guarded_raise(PermissionError(errno.EACCES, "x")).message
    locked = guarded_raise(
        sqlite_error("SQLITE_CANTOPEN", 14, "unable to open database file")
    ).message

    assert "disk space" in full and "Nothing was changed" in full
    assert "read-only" in read_only and "another program" in read_only
    assert "another program" in locked.lower() and "antivirus" in locked


def limit_database_size(
    monkeypatch: pytest.MonkeyPatch, pages: int
) -> Callable[[], None]:
    """Make every new connection hit the real SQLITE_FULL after ``pages`` pages."""

    real_connect = support.connect
    active = {"on": True}

    def connect(path: Path) -> sqlite3.Connection:
        connection = real_connect(path)
        if active["on"]:
            connection.execute(f"PRAGMA max_page_count = {pages}")
        return connection

    monkeypatch.setattr(support, "connect", connect)
    return lambda: active.update(on=False)


def many_rows(count: int = 40) -> BatchWorkspace:
    lines = ["text"] + [f"Synthetic message number {n}." for n in range(count)]
    pending = inspect_csv_upload("\n".join(lines).encode(), max_bytes=100_000)
    preview = prepare_csv_batch(
        pending, text_column="text", max_rows=100, max_text_length=200
    )
    return BatchWorkspace(preview=preview)


def analysed(workspace: BatchWorkspace) -> BatchWorkspace:
    assert workspace.preview is not None
    result = analyze_batch(workspace.preview, SyntheticGateway())
    return BatchWorkspace(
        preview=workspace.preview,
        result=result,
        reviews=create_review_state(result),
        insights=InsightState(),
    )


def test_a_full_disk_during_the_analysis_commit_keeps_the_project_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    original = many_rows()
    token = repo.create(original)
    lease = repo.begin_analysis(token)
    assert lease is not None
    files_before = sorted(p.name for p in (tmp_path / "projects").iterdir())
    size = (tmp_path / "projects" / f"{token}.sqlite3").stat().st_size

    lift = limit_database_size(monkeypatch, size // 4096)
    with pytest.raises(ProjectStorageError) as failure:
        repo.complete_analysis(lease, analysed(lease.workspace))
    lift()

    assert failure.value.code == "storage_full"
    assert repo.cancel_analysis(lease) is True  # the caller's cleanup releases it
    assert repo.get(token) == original  # no partial result
    assert sorted(p.name for p in (tmp_path / "projects").iterdir()) == files_before
    again = repo.begin_analysis(token)  # and the project is usable afterwards
    assert again is not None
    assert repo.complete_analysis(again, analysed(again.workspace)) is True


def test_a_full_disk_during_import_leaves_no_project_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    kept = repo.create_project(BatchWorkspace(preview=one_row_preview()), name="Kept")
    before = sorted(p.name for p in (tmp_path / "projects").iterdir())

    limit_database_size(monkeypatch, 2)
    with pytest.raises(ProjectStorageError) as failure:
        repo.create_project(BatchWorkspace(preview=one_row_preview()), name="New")

    assert failure.value.code == "storage_full"
    assert sorted(p.name for p in (tmp_path / "projects").iterdir()) == before
    assert [p.project_id for p in repo.list_projects()] == [kept.project_id]


def test_a_data_root_that_is_a_file_is_reported_not_crashed(tmp_path: Path) -> None:
    blocker = tmp_path / "root"
    blocker.write_text("not a folder")
    repo = repository(blocker)

    with pytest.raises(ProjectStorageError) as failure:
        repo.create_project(BatchWorkspace(preview=one_row_preview()), name="New")

    assert failure.value.code in {"storage_failure", "storage_read_only"}
    assert blocker.read_text() == "not a folder"  # existing data untouched
    assert repo.list_projects() == ()


def test_a_read_only_project_file_cannot_be_written_but_stays_readable(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    original = BatchWorkspace(preview=one_row_preview())
    token = repo.create(original)
    path = tmp_path / "projects" / f"{token}.sqlite3"
    path.chmod(stat.S_IREAD)
    try:
        assert repo.get(token) == original  # reading still works
        lease = repo.begin_analysis(token)
        assert lease is not None
        try:
            with pytest.raises(ProjectStorageError) as failure:
                repo.complete_analysis(lease, analysed(lease.workspace))
        finally:
            repo.cancel_analysis(lease)
        if sys.platform == "win32":  # on POSIX the code depends on the user (root)
            assert failure.value.code == "storage_read_only"
        if sys.platform == "win32":  # POSIX unlinks a read-only file freely
            with pytest.raises(ProjectStorageError):
                repo.delete(token)  # cannot be removed while read-only
    finally:
        path.chmod(stat.S_IREAD | stat.S_IWRITE)

    assert repo.get(token) == original  # nothing was lost or changed
    assert repo.delete(token) is True  # and recovery works once the setting is cleared


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 share modes")
def test_a_project_file_held_open_by_another_program_is_reported_as_in_use(
    tmp_path: Path,
) -> None:
    from persistence.file_locks import exclusive_handle

    repo = repository(tmp_path)
    original = BatchWorkspace(preview=one_row_preview())
    token = repo.create(original)
    path = tmp_path / "projects" / f"{token}.sqlite3"

    with exclusive_handle(path, 0):  # a program that allows no sharing at all
        with pytest.raises(ProjectStorageError) as failure:
            repo.get(token)
        assert failure.value.code == "storage_locked"
        assert [p.project_id for p in repo.list_projects()] == [token]  # still listed
        with pytest.raises(ProjectStorageError) as removal:
            repo.delete(token)
        assert removal.value.code == "delete_failed"

    assert repo.get(token) == original
    assert os.path.exists(path)
