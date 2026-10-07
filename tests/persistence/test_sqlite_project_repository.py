"""Durable project behavior: restart round-trips, listing, deletion, versioning."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from persistence.samples import (
    CSV_SENTINEL,
    NAME_SENTINEL,
    NOTE_SENTINEL,
    TEXT_SENTINEL,
    SyntheticGateway,
    one_row_preview,
    pending_upload,
    rich_workspace,
)
from social_text_intelligence.application.projects import (
    BatchWorkspace,
    PersistentProjectRepository,
    ProjectStatus,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.contracts.errors import (
    ProjectStorageError,
    ValidationError,
)
from social_text_intelligence.infrastructure import project_schema
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services import create_review_state
from social_text_intelligence.services.batch import analyze_batch
from social_text_intelligence.services.insights import (
    ContextAssociation,
    ContextNote,
    ContextTag,
    InsightFilters,
    InsightSelection,
    InsightState,
)
from social_text_intelligence.services.review import ReviewState

SENTINELS = (TEXT_SENTINEL, NOTE_SENTINEL, NAME_SENTINEL, CSV_SENTINEL)


def new_repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def make_foreign_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript("CREATE TABLE t (x); INSERT INTO t VALUES (1);")
    finally:
        connection.close()


def project_files(root: Path) -> list[Path]:
    directory = root / "projects"
    return sorted(directory.iterdir()) if directory.exists() else []


def residual_bytes(root: Path) -> bytes:
    return b"".join(path.read_bytes() for path in project_files(root))


def analyzed_from(workspace: BatchWorkspace) -> BatchWorkspace:
    assert workspace.preview is not None
    result = analyze_batch(workspace.preview, SyntheticGateway())
    return BatchWorkspace(
        preview=workspace.preview,
        result=result,
        reviews=create_review_state(result),
        insights=InsightState(),
    )


def make_note(note_id: str) -> ContextNote:
    return ContextNote(
        note_id=note_id,
        association=ContextAssociation.TOPIC,
        association_value="shipping",
        phrase="phrase",
        explanation="explanation",
        context_importance="importance",
        tags=(ContextTag.OTHER,),
        created_at=datetime(2026, 3, 4, 5, 6, 7, 891011, tzinfo=UTC),
    )


def refuse_unlink(monkeypatch: pytest.MonkeyPatch, suffix: str) -> None:
    """Make removing files with this suffix fail, as an antivirus or open handle can."""

    real_unlink = Path.unlink

    def refuse(self: Path, missing_ok: bool = False) -> None:
        if self.suffix == suffix:
            raise PermissionError("synthetic: file in use")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", refuse)


def refuse_database_unlink(monkeypatch: pytest.MonkeyPatch) -> None:
    refuse_unlink(monkeypatch, ".sqlite3")


# --- restart round-trips ---------------------------------------------------------


def test_a_project_survives_closing_and_restarting_with_exact_values(
    tmp_path: Path,
) -> None:
    original = replace(rich_workspace(), pending=pending_upload())
    token = new_repository(tmp_path).create(original)

    reopened = new_repository(tmp_path).get(token)

    assert reopened == original
    assert reopened is not None and reopened.result is not None
    assert original.result is not None
    reports = [o.report for o in reopened.result.outcomes if o.report is not None]
    original_first = original.result.outcomes[0].report
    assert original_first is not None
    assert reports[0].sentiment.confidence == 0.7000000000000001
    assert reports[0].sentiment.scores[1].score == 0.1 + 0.2
    assert reports[0].emotion.native_scores[0].score == 5e-324
    assert reports[0].emotion.provider == original_first.emotion.provider
    assert reports[0].sentiment.provider == original_first.sentiment.provider
    stamps = [
        report.record.timestamp
        for report in reports
        if report.record.timestamp is not None
    ]
    assert [stamp.utcoffset() for stamp in stamps] == [
        timedelta(0),
        timedelta(hours=5, minutes=30),
        None,
        timedelta(0),
    ]


def test_binary_upload_and_structural_none_values_round_trip(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    selection = rich_workspace().insights
    assert selection is not None and selection.selection is not None
    upload = replace(pending_upload(), content=b"\xef\xbb\xbfa,b\r\n1,\x00\r\n")
    cases = [
        BatchWorkspace(pending=upload),
        BatchWorkspace(preview=one_row_preview()),
        replace(rich_workspace(), reviews=ReviewState(reviews=())),
        replace(rich_workspace(), reviews=None, insights=None),
        replace(rich_workspace(), insights=InsightState()),
        replace(
            rich_workspace(),
            insights=InsightState(
                notes=(make_note("n-2"), make_note("n-1")),
                selection=InsightSelection(
                    grouping=selection.selection.grouping,
                    groups=("shipping", "billing"),
                    perspective=selection.selection.perspective,
                    metric=selection.selection.metric,
                    filters=InsightFilters(
                        sentiment=SentimentLabel.NEGATIVE,
                        emotion=EmotionLabel.ANGER,
                        date_from=date(2026, 1, 1),
                        date_to=date(2026, 12, 31),
                    ),
                ),
            ),
        ),
    ]
    for workspace in cases:
        token = repository.create(workspace)
        assert new_repository(tmp_path).get(token) == workspace


def test_free_text_is_stored_exactly_without_normalization(tmp_path: Path) -> None:
    awkward = (
        "nul\x00 emoji \U0001f642 e\N{COMBINING ACUTE ACCENT} "
        "caf\N{LATIN SMALL LETTER E WITH ACUTE} "
        "\N{RIGHT-TO-LEFT OVERRIDE} tab\x09"
    )
    # Project names are normalized to NFC on purpose; free text is not.
    name = "Name \U0001f642 e\N{COMBINING ACUTE ACCENT}"
    stored_name = "Name \U0001f642 \N{LATIN SMALL LETTER E WITH ACUTE}"
    note = replace(make_note("exact"), phrase=awkward, explanation=awkward)
    workspace = replace(
        rich_workspace(), insights=InsightState(notes=(note,), selection=None)
    )
    token = new_repository(tmp_path).create_project(workspace, name=name).project_id
    reopened = new_repository(tmp_path).get(token)
    assert reopened is not None and reopened.insights is not None
    assert reopened.insights.notes[0].phrase == awkward
    assert reopened.insights.notes[0].explanation == awkward
    assert new_repository(tmp_path).list_projects()[0].name == stored_name


def test_text_that_cannot_be_encoded_is_refused_atomically(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    original = rich_workspace()
    token = repository.create(original)
    unencodable = replace(make_note("bad"), phrase="lone surrogate \ud800")
    with pytest.raises(ProjectStorageError) as raised:
        repository.mutate(
            token,
            lambda w: replace(w, insights=InsightState(notes=(unencodable,))),
        )
    assert raised.value.code == "unsupported_text"
    # The original failure holds the offending text, so it must not be reachable.
    assert raised.value.__context__ is None and raised.value.__cause__ is None
    assert new_repository(tmp_path).get(token) == original


def test_the_sqlite_repository_satisfies_the_persistent_port(tmp_path: Path) -> None:
    repository: PersistentProjectRepository = new_repository(tmp_path)
    assert repository.list_projects() == ()


def test_mutations_persist_and_leave_ai_records_untouched(tmp_path: Path) -> None:
    original = rich_workspace()
    repository = new_repository(tmp_path)
    token = repository.create(original)
    assert original.reviews is not None
    first = original.reviews.reviews[0]
    changed = replace(first, note="changed", human_secondary_emotions=())

    def revise(current: BatchWorkspace) -> BatchWorkspace:
        assert current.reviews is not None
        return replace(
            current,
            reviews=ReviewState((changed, *current.reviews.reviews[1:])),
            insights=InsightState(),
        )

    repository.mutate(token, revise)
    reopened = new_repository(tmp_path).get(token)
    assert reopened is not None
    assert reopened.result == original.result
    assert reopened.preview == original.preview
    assert reopened.reviews is not None
    assert reopened.reviews.reviews[0] == changed
    assert reopened.insights == InsightState()


def test_ai_records_cannot_be_edited_in_place(tmp_path: Path) -> None:
    token = new_repository(tmp_path).create(rich_workspace())
    database = tmp_path / "projects" / f"{token}.sqlite3"
    connection = sqlite3.connect(database)
    try:
        for statement in (
            "UPDATE analysis_outcome SET status = 'error'",
            "UPDATE analysis_result SET aggregates_json = '{}'",
            "UPDATE prepared_row SET identity = 'x'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(statement)
    finally:
        connection.close()


def test_storage_uses_write_ahead_logging(tmp_path: Path) -> None:
    token = new_repository(tmp_path).create(BatchWorkspace())
    connection = sqlite3.connect(tmp_path / "projects" / f"{token}.sqlite3")
    try:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        connection.close()


def test_no_sidecar_files_linger_after_operations(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(rich_workspace())
    repository.mutate(token, lambda current: replace(current, insights=InsightState()))
    repository.get(token)
    assert [path.suffix for path in project_files(tmp_path)] == [".sqlite3"]


# --- identity, listing, rename ---------------------------------------------------


def test_listing_reports_identity_and_recency(tmp_path: Path) -> None:
    ticks = iter(
        datetime(2026, 5, 1, tzinfo=UTC) + timedelta(hours=n) for n in range(99)
    )
    repository = SqliteProjectRepository(
        AppDataLocations(tmp_path), clock=lambda: next(ticks)
    )
    assert repository.list_projects() == ()
    first = repository.create_project(BatchWorkspace(), name="  First  ")
    second = repository.create_project(rich_workspace(), name="Second")
    assert first.name == "First"

    listed = repository.list_projects()
    assert [item.name for item in listed] == ["Second", "First"]
    assert [item.project_id for item in listed] == [
        second.project_id,
        first.project_id,
    ]
    assert all(item.status is ProjectStatus.OK for item in listed)
    assert listed[0].created_at == second.created_at

    repository.mutate(first.project_id, lambda w: replace(w, pending=pending_upload()))
    assert repository.list_projects()[0].project_id == first.project_id


@pytest.mark.parametrize("bad", ["", "   ", "x" * 121, "tab\there", "nul\x00name"])
def test_invalid_names_are_rejected_before_anything_is_written(
    tmp_path: Path, bad: str
) -> None:
    repository = new_repository(tmp_path)
    with pytest.raises(ValidationError) as raised:
        repository.create_project(BatchWorkspace(), name=bad)
    assert raised.value.field == "name"
    assert project_files(tmp_path) == []


def test_default_name_is_used_by_the_port_create(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    repository.create(BatchWorkspace())
    assert [item.name for item in repository.list_projects()] == ["Untitled project"]


def test_listing_never_trusts_or_alters_foreign_and_broken_files(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    good = repository.create_project(BatchWorkspace(), name="Good")
    directory = tmp_path / "projects"
    broken = directory / f"{'a' * 32}.sqlite3"
    broken.write_bytes(b"this is not a database " * 50)
    foreign = directory / f"{'b' * 32}.sqlite3"
    make_foreign_database(foreign)
    (directory / "notes.sqlite3").write_bytes(b"ignored by name")
    (directory / "readme.txt").write_bytes(b"ignored")
    before = {p.name: p.read_bytes() for p in (broken, foreign)}

    listed = repository.list_projects()

    assert [item.project_id for item in listed] == [
        good.project_id,
        "a" * 32,
        "b" * 32,
    ]
    assert [item.status for item in listed] == [
        ProjectStatus.OK,
        ProjectStatus.UNREADABLE,
        ProjectStatus.UNREADABLE,
    ]
    assert listed[1].name is None
    assert {p.name: p.read_bytes() for p in (broken, foreign)} == before


# --- deletion --------------------------------------------------------------------


def test_delete_removes_every_project_file_and_leaves_others(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    doomed = repository.create_project(rich_workspace(), name="Doomed")
    kept = repository.create_project(rich_workspace(), name="Kept")
    directory = tmp_path / "projects"
    for suffix in ("-wal", "-shm", "-journal"):
        (directory / f"{doomed.project_id}.sqlite3{suffix}").write_bytes(b"stray")
    backup = directory / f"{doomed.project_id}.pre-migration-v0.sqlite3.bak"
    backup.write_bytes(b"stray backup")

    assert repository.delete(doomed.project_id) is True

    assert [p.name for p in project_files(tmp_path)] == [f"{kept.project_id}.sqlite3"]
    assert repository.get(kept.project_id) == rich_workspace()
    assert [item.name for item in repository.list_projects()] == ["Kept"]


def test_delete_overwrites_content_before_it_unlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = new_repository(tmp_path)
    workspace = replace(rich_workspace(), pending=pending_upload())
    created = repository.create_project(workspace, name=NAME_SENTINEL)
    before = residual_bytes(tmp_path)
    for sentinel in SENTINELS:
        assert sentinel.encode() in before  # the check below is meaningful

    refuse_database_unlink(monkeypatch)
    with pytest.raises(ProjectStorageError) as raised:
        repository.delete(created.project_id)
    assert raised.value.code == "delete_failed"
    after = residual_bytes(tmp_path)
    for sentinel in SENTINELS:
        assert sentinel.encode() not in after
    assert [item.status for item in repository.list_projects()] == [
        ProjectStatus.UNREADABLE
    ]

    monkeypatch.undo()
    assert repository.delete(created.project_id) is True
    assert project_files(tmp_path) == []


def test_delete_cleans_content_a_crashed_writer_left_in_the_wal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    project_id = new_repository(source).create(BatchWorkspace())
    database = source / "projects" / f"{project_id}.sqlite3"
    writer = sqlite3.connect(database)
    crashed = tmp_path / "crashed"
    try:
        writer.execute("PRAGMA wal_autocheckpoint = 0")
        writer.execute("PRAGMA journal_mode = WAL")
        writer.execute(
            "INSERT INTO pending_upload VALUES (1, ?, '[]')", (TEXT_SENTINEL.encode(),)
        )
        writer.commit()
        (crashed / "projects").mkdir(parents=True)
        for suffix in ("", "-wal", "-shm"):  # the files a killed process would leave
            shutil.copy(
                database.with_name(database.name + suffix),
                crashed / "projects" / f"{database.name}{suffix}",
            )
    finally:
        writer.close()
    copied = crashed / "projects" / database.name
    assert TEXT_SENTINEL.encode() in copied.with_name(copied.name + "-wal").read_bytes()
    assert TEXT_SENTINEL.encode() not in copied.read_bytes()

    refuse_database_unlink(monkeypatch)
    with pytest.raises(ProjectStorageError):
        new_repository(crashed).delete(project_id)
    assert TEXT_SENTINEL.encode() not in residual_bytes(crashed)
    assert not list((crashed / "projects").glob("*-wal"))
    assert not list((crashed / "projects").glob("*-shm"))


def make_partly_deleted_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[SqliteProjectRepository, str, Path]:
    """A first delete that removes the main database but not a migration backup."""

    repository = new_repository(tmp_path)
    created = repository.create_project(rich_workspace(), name=NAME_SENTINEL)
    directory = tmp_path / "projects"
    database = directory / f"{created.project_id}.sqlite3"
    backup = directory / f"{created.project_id}.pre-migration-v1.sqlite3.bak"
    shutil.copy(database, backup)  # a migration backup holds the project's data
    (directory / f"{created.project_id}.sqlite3-wal").write_bytes(b"stray")
    assert NAME_SENTINEL.encode() in backup.read_bytes()

    refuse_unlink(monkeypatch, ".bak")
    with pytest.raises(ProjectStorageError) as raised:
        repository.delete(created.project_id)
    assert raised.value.code == "delete_failed"
    assert "cleared" not in raised.value.message  # no guarantee beyond removal
    assert not database.exists()
    return repository, created.project_id, backup


def test_a_partial_delete_does_not_forget_the_residual_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, project_id, backup = make_partly_deleted_project(tmp_path, monkeypatch)
    assert backup.exists()
    assert NAME_SENTINEL.encode() not in backup.read_bytes()  # content was purged
    assert [(item.project_id, item.status) for item in repository.list_projects()] == [
        (project_id, ProjectStatus.UNREADABLE)
    ]


def test_a_retried_delete_removes_every_managed_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, project_id, _ = make_partly_deleted_project(tmp_path, monkeypatch)
    monkeypatch.undo()
    assert repository.delete(project_id) is True
    assert project_files(tmp_path) == []
    assert repository.delete(project_id) is False


def test_only_files_the_store_creates_count_as_project_residue(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    directory = tmp_path / "projects"
    directory.mkdir()
    project_id = "e" * 32
    foreign_file = directory / f"{project_id}.txt"
    foreign_file.write_bytes(b"not ours")
    foreign_directory = directory / f"{project_id}.sqlite3-dir"
    foreign_directory.mkdir()

    assert repository.list_projects() == ()
    assert repository.delete(project_id) is False
    assert foreign_file.exists() and foreign_directory.is_dir()


@pytest.mark.parametrize(
    "suffix", [".sqlite3", ".pre-migration-v1.sqlite3.bak"], ids=["database", "backup"]
)
def test_delete_never_purges_through_a_symlink(tmp_path: Path, suffix: str) -> None:
    outside = tmp_path / "outside.db"
    make_foreign_database(outside)
    project_id = "f" * 32
    directory = tmp_path / "projects"
    directory.mkdir()
    link = directory / f"{project_id}{suffix}"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform or account")

    assert new_repository(tmp_path).delete(project_id) is True

    assert not link.is_symlink()  # the link itself was removed
    connection = sqlite3.connect(outside)
    try:
        assert connection.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    finally:
        connection.close()


def link_to_external_project(
    tmp_path: Path,
) -> tuple[SqliteProjectRepository, str, Path]:
    """A managed-name symlink whose target is a valid project outside the directory."""

    external_root = tmp_path / "external"
    external = new_repository(external_root).create_project(
        rich_workspace(), name="External"
    )
    target = external_root / "projects" / f"{external.project_id}.sqlite3"
    managed_root = tmp_path / "managed"
    (managed_root / "projects").mkdir(parents=True)
    link = managed_root / "projects" / f"{external.project_id}.sqlite3"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform or account")
    return new_repository(managed_root), external.project_id, target


def test_a_symlinked_project_is_never_opened_or_modified(tmp_path: Path) -> None:
    repository, project_id, target = link_to_external_project(tmp_path)
    before = target.read_bytes()

    assert [(i.project_id, i.status) for i in repository.list_projects()] == [
        (project_id, ProjectStatus.UNREADABLE)
    ]
    assert repository.get(project_id) is None
    assert repository.mutate(project_id, lambda w: replace(w, pending=None)) is None
    assert repository.begin_analysis(project_id) is None

    assert target.read_bytes() == before
    external = new_repository(tmp_path / "external")
    assert external.get(project_id) == rich_workspace()


def test_deleting_a_symlinked_project_removes_only_the_link(tmp_path: Path) -> None:
    repository, project_id, target = link_to_external_project(tmp_path)
    before = target.read_bytes()

    assert repository.delete(project_id) is True

    assert not (tmp_path / "managed" / "projects" / target.name).is_symlink()
    assert project_files(tmp_path / "managed") == []
    assert target.read_bytes() == before
    assert new_repository(tmp_path / "external").get(project_id) == rich_workspace()


def test_a_migration_backup_never_writes_through_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = new_repository(tmp_path / "managed")
    token = repository.create(rich_workspace())
    outside = tmp_path / "outside.db"
    make_foreign_database(outside)  # a valid database, so a write would succeed
    before_outside = outside.read_bytes()
    backup = tmp_path / "managed" / "projects" / f"{token}.pre-migration-v1.sqlite3.bak"
    try:
        backup.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform or account")
    database = tmp_path / "managed" / "projects" / f"{token}.sqlite3"
    before = database.read_bytes()
    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: lambda connection: None})

    with pytest.raises(ProjectStorageError) as raised:
        new_repository(tmp_path / "managed").get(token)

    assert raised.value.code == "migration_failed"
    assert outside.read_bytes() == before_outside
    assert database.read_bytes() == before  # the project stays at its old version


def make_outside_file(tmp_path: Path) -> Path:
    outside = tmp_path / "outside.bin"
    outside.write_bytes(bytes(range(256)) * 128)  # 32 KiB with a recognisable pattern
    return outside


def symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform or account")


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_a_symlinked_sidecar_is_never_written_through(
    tmp_path: Path, suffix: str
) -> None:
    repository = new_repository(tmp_path / "managed")
    token = repository.create(rich_workspace())
    outside = make_outside_file(tmp_path)
    before = outside.read_bytes()
    link = tmp_path / "managed" / "projects" / f"{token}.sqlite3{suffix}"
    symlink_or_skip(link, outside)

    assert [(i.project_id, i.status) for i in repository.list_projects()] == [
        (token, ProjectStatus.UNREADABLE)
    ]
    assert repository.get(token) is None
    assert repository.mutate(token, lambda w: replace(w, pending=None)) is None
    assert repository.begin_analysis(token) is None
    assert outside.read_bytes() == before

    assert repository.delete(token) is True
    assert project_files(tmp_path / "managed") == []
    assert outside.read_bytes() == before


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_a_symlinked_backup_sidecar_blocks_migration_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    repository = new_repository(tmp_path / "managed")
    token = repository.create(rich_workspace())
    outside = make_outside_file(tmp_path)
    before = outside.read_bytes()
    directory = tmp_path / "managed" / "projects"
    symlink_or_skip(
        directory / f"{token}.pre-migration-v1.sqlite3.bak{suffix}", outside
    )
    database = directory / f"{token}.sqlite3"
    database_before = database.read_bytes()
    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: lambda connection: None})

    with pytest.raises(ProjectStorageError):
        new_repository(tmp_path / "managed").get(token)

    assert outside.read_bytes() == before
    assert database.read_bytes() == database_before


def test_a_lease_cannot_commit_after_its_file_becomes_a_symlink(
    tmp_path: Path,
) -> None:
    external_root = tmp_path / "external"
    external = new_repository(external_root).create_project(
        BatchWorkspace(preview=one_row_preview()), name="External"
    )
    target = external_root / "projects" / f"{external.project_id}.sqlite3"
    before = target.read_bytes()

    repository = new_repository(tmp_path / "managed")
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    lease = repository.begin_analysis(token)
    assert lease is not None
    database = tmp_path / "managed" / "projects" / f"{token}.sqlite3"
    database.unlink()
    symlink_or_skip(database, target)

    assert repository.complete_analysis(lease, analyzed_from(lease.workspace)) is False
    assert target.read_bytes() == before


def test_corrupted_project_can_still_be_deleted(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    project_id = "c" * 32
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / f"{project_id}.sqlite3").write_bytes(b"garbage" * 99)
    assert repository.delete(project_id) is True
    assert project_files(tmp_path) == []


# --- leases, restarts, and atomic analysis --------------------------------------


def test_cancelled_analysis_commits_nothing_and_survives_restart(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    original = BatchWorkspace(preview=one_row_preview())
    token = repository.create(original)
    lease = repository.begin_analysis(token)
    assert lease is not None
    assert repository.cancel_analysis(lease) is True

    restarted = new_repository(tmp_path)
    assert restarted.get(token) == original
    assert restarted.begin_analysis(token) is not None


def test_a_crash_during_analysis_leaves_a_usable_project(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    original = BatchWorkspace(preview=one_row_preview())
    token = repository.create(original)
    lease = repository.begin_analysis(token)
    assert lease is not None
    # The process dies here: no completion, no cancellation, no result written.

    restarted = new_repository(tmp_path)
    assert restarted.get(token) == original
    assert restarted.mutate(token, lambda w: w) == original
    assert restarted.delete(token) is True


def test_a_lease_cannot_overwrite_changes_made_elsewhere(tmp_path: Path) -> None:
    first = new_repository(tmp_path)
    second = new_repository(tmp_path)
    token = first.create(BatchWorkspace(preview=one_row_preview()))
    lease = first.begin_analysis(token)
    assert lease is not None

    edited = second.mutate(token, lambda w: replace(w, pending=pending_upload()))
    assert edited is not None

    assert first.complete_analysis(lease, analyzed_from(lease.workspace)) is False
    assert first.get(token) == edited
    assert first.begin_analysis(token) is not None  # the stale lease was released


def test_a_failed_commit_rolls_back_the_whole_analysis(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    original = BatchWorkspace(preview=one_row_preview())
    token = repository.create(original)
    lease = repository.begin_analysis(token)
    assert lease is not None
    finished = analyzed_from(lease.workspace)
    clashing = replace(
        finished,
        insights=InsightState(notes=(make_note("same"), make_note("same"))),
    )

    with pytest.raises(ProjectStorageError) as raised:
        repository.complete_analysis(lease, clashing)
    assert raised.value.code == "storage_failure"
    assert new_repository(tmp_path).get(token) == original
    assert repository.cancel_analysis(lease) is True


def test_unsupported_workspace_shapes_are_refused_without_writing(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    analyzed = analyzed_from(BatchWorkspace(preview=one_row_preview()))
    orphan_result = replace(analyzed, preview=None)
    with pytest.raises(ProjectStorageError) as raised:
        repository.create(orphan_result)
    assert raised.value.code == "unsupported_workspace"
    assert project_files(tmp_path) == []

    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    with pytest.raises(ProjectStorageError):
        repository.mutate(token, lambda w: orphan_result)
    assert repository.get(token) == BatchWorkspace(preview=one_row_preview())


# --- concurrency ----------------------------------------------------------------


def test_concurrent_mutations_from_threads_and_instances_lose_nothing(
    tmp_path: Path,
) -> None:
    repositories = [new_repository(tmp_path), new_repository(tmp_path)]
    token = repositories[0].create(replace(rich_workspace(), insights=InsightState()))
    failures: list[BaseException] = []

    def add(repository: SqliteProjectRepository, note_id: str) -> None:
        def change(current: BatchWorkspace) -> BatchWorkspace:
            assert current.insights is not None
            return replace(
                current,
                insights=InsightState(
                    notes=(*current.insights.notes, make_note(note_id)),
                    selection=current.insights.selection,
                ),
            )

        try:
            repository.mutate(token, change)
        except BaseException as error:  # noqa: BLE001 - surfaced in the assertion
            failures.append(error)

    threads = [
        threading.Thread(target=add, args=(repositories[n % 2], f"note-{n}"))
        for n in range(16)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    final = new_repository(tmp_path).get(token)
    assert final is not None and final.insights is not None
    assert sorted(note.note_id for note in final.insights.notes) == sorted(
        f"note-{n}" for n in range(16)
    )


# --- versions, corruption, privacy ----------------------------------------------


def test_a_project_from_a_newer_version_is_refused_and_left_untouched(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(rich_workspace())
    database = tmp_path / "projects" / f"{token}.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute(f"PRAGMA user_version = {project_schema.SCHEMA_VERSION + 1}")
    finally:
        connection.close()
    before = database.read_bytes()

    with pytest.raises(ProjectStorageError) as raised:
        repository.get(token)
    assert raised.value.code == "unsupported_schema_version"
    with pytest.raises(ProjectStorageError):
        repository.mutate(token, lambda w: replace(w, pending=pending_upload()))
    assert repository.list_projects()[0].status is ProjectStatus.UNSUPPORTED_VERSION
    assert database.read_bytes() == before


def test_a_foreign_database_is_not_adopted(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    (tmp_path / "projects").mkdir()
    project_id = "d" * 32
    make_foreign_database(tmp_path / "projects" / f"{project_id}.sqlite3")
    with pytest.raises(ProjectStorageError) as raised:
        repository.get(project_id)
    assert raised.value.code == "not_a_project"


def tamper(tmp_path: Path, token: str, statement: str) -> None:
    connection = sqlite3.connect(tmp_path / "projects" / f"{token}.sqlite3")
    try:
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE human_review SET human_sentiment = 'bogus' WHERE position = 0",
        "UPDATE human_review SET reviewed_at = 'not a timestamp' WHERE position = 0",
        "UPDATE context_note SET association = 'bogus'",
        "UPDATE insight_selection SET selection_json = '{broken'",
        "DELETE FROM prepared_row",
        "DELETE FROM project",
    ],
)
def test_tampered_content_is_reported_without_echoing_project_text(
    tmp_path: Path, statement: str
) -> None:
    repository = new_repository(tmp_path)
    token = repository.create_project(rich_workspace(), name=NAME_SENTINEL).project_id
    tamper(tmp_path, token, statement)
    with pytest.raises(ProjectStorageError) as raised:
        repository.get(token)
    assert raised.value.code == "project_data_invalid"
    rendered = f"{raised.value} {raised.value.__cause__!r} {raised.value.__context__!r}"
    for sentinel in SENTINELS:
        assert sentinel not in rendered


def test_a_tampered_provider_report_is_rejected_by_contract_checks(
    tmp_path: Path,
) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(rich_workspace())
    database = tmp_path / "projects" / f"{token}.sqlite3"
    connection = sqlite3.connect(database)
    try:
        # The immutability trigger guards UPDATE; replace the row to emulate an
        # outside edit that must still fail the original result contracts.
        report, row = connection.execute(
            "SELECT report_json, row_number FROM analysis_outcome "
            "WHERE report_json IS NOT NULL LIMIT 1"
        ).fetchone()
        connection.execute("DELETE FROM analysis_outcome WHERE row_number = ?", (row,))
        connection.execute(
            "INSERT INTO analysis_outcome VALUES (?, 'ok', NULL, NULL, ?)",
            (row, report.replace('"label":"positive"', '"label":"negative"', 1)),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ProjectStorageError) as raised:
        repository.get(token)
    assert raised.value.code == "project_data_invalid"


def test_nothing_is_logged_and_errors_carry_no_project_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    repository = new_repository(tmp_path)
    created = repository.create_project(
        replace(rich_workspace(), pending=pending_upload()), name=NAME_SENTINEL
    )
    repository.get(created.project_id)
    repository.list_projects()
    lease = repository.begin_analysis(created.project_id)
    assert lease is not None
    repository.cancel_analysis(lease)
    repository.delete(created.project_id)
    assert [r for r in caplog.records if r.name.startswith("social_text")] == []
    for record in caplog.records:
        for sentinel in SENTINELS:
            assert sentinel not in record.getMessage()


def test_migration_runs_once_with_a_backup_and_deletes_with_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(rich_workspace())

    def add_column(connection: sqlite3.Connection) -> None:
        connection.execute("ALTER TABLE project ADD COLUMN extra TEXT")

    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: add_column})

    assert new_repository(tmp_path).get(token) == rich_workspace()
    database = tmp_path / "projects" / f"{token}.sqlite3"
    backup = tmp_path / "projects" / f"{token}.pre-migration-v1.sqlite3.bak"
    assert backup.is_file()
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        columns = [r[1] for r in connection.execute("PRAGMA table_info(project)")]
        assert "extra" in columns
    finally:
        connection.close()
    backup_connection = sqlite3.connect(backup)
    try:
        assert backup_connection.execute("PRAGMA user_version").fetchone()[0] == 1
    finally:
        backup_connection.close()
    assert [item.status for item in new_repository(tmp_path).list_projects()] == [
        ProjectStatus.OK
    ]

    assert new_repository(tmp_path).delete(token) is True
    assert project_files(tmp_path) == []


def test_a_failing_migration_changes_nothing_and_keeps_the_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(rich_workspace())

    def broken(connection: sqlite3.Connection) -> None:
        connection.execute("ALTER TABLE project ADD COLUMN extra TEXT")
        raise RuntimeError(f"synthetic failure {TEXT_SENTINEL}")

    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: broken})

    with pytest.raises(ProjectStorageError) as raised:
        new_repository(tmp_path).get(token)
    assert raised.value.code == "migration_failed"
    assert TEXT_SENTINEL not in f"{raised.value} {raised.value.__context__!r}"
    assert (tmp_path / "projects" / f"{token}.pre-migration-v1.sqlite3.bak").is_file()

    monkeypatch.undo()
    assert new_repository(tmp_path).get(token) == rich_workspace()


def test_a_missing_migration_step_is_reported_before_touching_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = new_repository(tmp_path).create(BatchWorkspace())
    database = tmp_path / "projects" / f"{token}.sqlite3"
    before = database.read_bytes()
    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: lambda connection: None})
    with pytest.raises(ProjectStorageError) as raised:
        new_repository(tmp_path).get(token)
    assert raised.value.code == "migration_unavailable"
    assert database.read_bytes() == before
    assert not list((tmp_path / "projects").glob("*.bak"))


def test_listing_reads_older_projects_without_migrating_or_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = new_repository(tmp_path).create_project(rich_workspace(), name="Older")
    database = tmp_path / "projects" / f"{created.project_id}.sqlite3"
    before = database.read_bytes()
    monkeypatch.setattr(project_schema, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(project_schema, "MIGRATIONS", {1: lambda connection: None})

    listed = new_repository(tmp_path).list_projects()

    assert [(item.name, item.status) for item in listed] == [
        ("Older", ProjectStatus.OK)
    ]
    assert not list((tmp_path / "projects").glob("*.bak"))
    assert database.read_bytes() == before


def test_replaced_content_does_not_linger_in_the_wal(tmp_path: Path) -> None:
    repository = new_repository(tmp_path)
    token = repository.create(BatchWorkspace(pending=pending_upload()))
    database = tmp_path / "projects" / f"{token}.sqlite3"
    # An idle open connection keeps the WAL alive, as another reader could.
    reader = sqlite3.connect(database)
    try:
        reader.execute("PRAGMA journal_mode").fetchone()
        repository.mutate(token, lambda w: replace(w, pending=None))
        residue = b"".join(
            path.read_bytes()
            for path in (tmp_path / "projects").iterdir()
            if path.name.startswith(token)
        )
    finally:
        reader.close()
    assert CSV_SENTINEL.encode() not in residue
