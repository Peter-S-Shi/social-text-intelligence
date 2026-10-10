"""The demo launcher deletes only what it owns, and refuses everything else."""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "tools" / "demo" / "launch_demo.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launch_demo_under_test", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def demo() -> ModuleType:
    return load()


@pytest.fixture
def real(tmp_path: Path) -> Path:
    folder = tmp_path / "real-app-data"
    folder.mkdir()
    return folder


def prepare(demo: ModuleType, root: Path, real: Path, *, reset: bool = False) -> bool:
    result: bool = demo.prepare_workspace(
        root, real_app_data=real, repo=Path(demo.REPO), reset=reset
    )
    return result


def tool_owned(demo: ModuleType, root: Path) -> None:
    """Make a finished tool workspace: sentinel, marker, and some tool children."""

    root.mkdir(parents=True, exist_ok=True)
    (root / demo.SENTINEL).write_text("sti demo workspace\n", encoding="utf-8")
    (root / demo.SEEDED_MARKER).write_text("seeded\n", encoding="utf-8")
    (root / "projects").mkdir()
    (root / "projects" / "p.sqlite3").write_bytes(b"x")
    (root / "models").mkdir()


def test_a_missing_root_is_created_and_claimed_before_seeding(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "fresh" / "demo"

    assert prepare(demo, root, real) is True  # seeding is needed

    assert (root / demo.SENTINEL).is_file()  # an interrupted seed is still ours


def test_an_empty_root_is_claimed(demo: ModuleType, real: Path, tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()

    assert prepare(demo, root, real) is True
    assert (root / demo.SENTINEL).is_file()


def test_a_finished_workspace_is_reopened_without_seeding(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)

    assert prepare(demo, root, real) is False
    assert (root / "projects" / "p.sqlite3").is_file()


def test_reset_removes_only_the_known_tool_children(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)

    assert prepare(demo, root, real, reset=True) is True

    assert not (root / "projects").exists() and not (root / "models").exists()
    assert not (root / demo.SEEDED_MARKER).exists()
    assert (root / demo.SENTINEL).is_file()


def test_an_interrupted_seed_is_recovered_by_the_same_rule(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    (root / demo.SEEDED_MARKER).unlink()  # the seed never finished

    assert prepare(demo, root, real) is True
    assert not (root / "projects").exists()


@pytest.mark.parametrize("reset", [False, True])
def test_a_user_file_next_to_tool_files_blocks_every_deletion(
    demo: ModuleType, real: Path, tmp_path: Path, reset: bool
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    mine = root / "thesis-notes.txt"
    mine.write_text("keep me", encoding="utf-8")

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=reset)

    assert mine.read_text(encoding="utf-8") == "keep me"
    assert (root / "projects" / "p.sqlite3").is_file()


@pytest.mark.parametrize("reset", [False, True])
def test_a_user_file_blocks_recovery_when_the_marker_is_missing(
    demo: ModuleType, real: Path, tmp_path: Path, reset: bool
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    (root / demo.SEEDED_MARKER).unlink()
    mine = root / "thesis-notes.txt"
    mine.write_text("keep me", encoding="utf-8")

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=reset)

    assert mine.read_text(encoding="utf-8") == "keep me"
    assert (root / "projects" / "p.sqlite3").is_file()


@pytest.mark.parametrize("reset", [False, True])
def test_a_non_empty_folder_without_the_sentinel_is_never_touched(
    demo: ModuleType, real: Path, tmp_path: Path, reset: bool
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    (root / "report.docx").write_bytes(b"precious")
    (root / "projects").mkdir()  # even a look-alike child does not make it ours

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=reset)

    assert (root / "report.docx").read_bytes() == b"precious"
    assert (root / "projects").is_dir()


def test_a_file_is_not_a_workspace(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    target = tmp_path / "a-file"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, target, real)

    assert target.read_text(encoding="utf-8") == "x"


def test_the_real_app_data_folder_and_its_neighbours_are_refused(
    demo: ModuleType, real: Path
) -> None:
    inside = real / "demo"
    for root in (real, inside, real.parent):
        with pytest.raises(demo.UnsafeRoot):
            prepare(demo, root, real)
    assert real.is_dir() and not inside.exists()


def test_drive_home_and_repository_roots_are_refused(
    demo: ModuleType, real: Path
) -> None:
    repo = Path(demo.REPO)
    home = Path.home()
    for root in (repo, repo.parent, home, Path(home.anchor)):
        with pytest.raises(demo.UnsafeRoot):
            prepare(demo, root, real)


def test_a_symlinked_root_is_refused(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "link"
    try:
        os.symlink(elsewhere, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, link, real, reset=True)

    assert (elsewhere / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_a_symlinked_child_is_refused_not_followed(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    (root / "models").rmdir()
    try:
        os.symlink(outside, root / "models", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=True)

    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("flag", [[], ["--reset"]])
def test_main_refuses_with_a_nonzero_status_and_a_plain_message(
    demo: ModuleType,
    real: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flag: list[str],
) -> None:
    root = tmp_path / "mine"
    root.mkdir()
    (root / "notes.txt").write_text("keep", encoding="utf-8")

    status = demo.main(["--root", str(root), *flag], real_app_data=real)

    assert status != 0
    err = capsys.readouterr().err
    assert "Refusing" in err and "not created by this tool" in err
    assert (root / "notes.txt").read_text(encoding="utf-8") == "keep"


def test_main_refuses_the_real_folder(
    demo: ModuleType, real: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = demo.main(["--root", str(real)], real_app_data=real)

    assert status == 2
    assert "real application-data folder" in capsys.readouterr().err


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Every entry under root (links not followed) with file bytes; None for dirs."""

    state: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        key = path.relative_to(root).as_posix()
        if path.is_symlink():
            state[key] = b"link:" + os.readlink(path).encode()
        elif path.is_dir():
            state[key] = None
        else:
            state[key] = path.read_bytes()
    return state


def _models_as_file(demo: ModuleType, root: Path) -> None:
    (root / "models").rmdir()
    (root / "models").write_text("not a folder", encoding="utf-8")


def _locks_as_file(demo: ModuleType, root: Path) -> None:
    (root / "locks").rmdir()
    (root / "locks").write_text("not a folder", encoding="utf-8")


def _marker_as_dir(demo: ModuleType, root: Path) -> None:
    (root / demo.SEEDED_MARKER).unlink()
    (root / demo.SEEDED_MARKER).mkdir()


def _sentinel_as_dir(demo: ModuleType, root: Path) -> None:
    (root / demo.SENTINEL).unlink()
    (root / demo.SENTINEL).mkdir()


def _sentinel_wrong_text(demo: ModuleType, root: Path) -> None:
    (root / demo.SENTINEL).write_text("something else\n", encoding="utf-8")


def _sentinel_empty(demo: ModuleType, root: Path) -> None:
    (root / demo.SENTINEL).write_text("", encoding="utf-8")


MALFORMED: list[Callable[[ModuleType, Path], None]] = [
    _models_as_file,
    _locks_as_file,
    _marker_as_dir,
    _sentinel_as_dir,
    _sentinel_wrong_text,
    _sentinel_empty,
]


@pytest.mark.parametrize("damage", MALFORMED, ids=lambda f: f.__name__)
@pytest.mark.parametrize("reset", [False, True])
def test_a_malformed_layout_is_refused_before_anything_is_deleted(
    demo: ModuleType,
    real: Path,
    tmp_path: Path,
    damage: Callable[[ModuleType, Path], None],
    reset: bool,
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    (root / "locks").mkdir()
    damage(demo, root)
    before = snapshot(root)

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=reset)

    assert snapshot(root) == before  # projects/ and every sibling untouched


def test_a_linked_child_with_a_well_typed_sibling_deletes_nothing(
    demo: ModuleType, real: Path, tmp_path: Path
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    try:
        os.symlink(outside, root / "locks", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    before = snapshot(root)

    with pytest.raises(demo.UnsafeRoot):
        prepare(demo, root, real, reset=True)

    assert snapshot(root) == before
    assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_main_reports_a_malformed_layout_and_deletes_nothing(
    demo: ModuleType,
    real: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "demo"
    tool_owned(demo, root)
    _models_as_file(demo, root)
    before = snapshot(root)

    status = demo.main(["--root", str(root), "--reset"], real_app_data=real)

    assert status == 2
    assert "Refusing" in capsys.readouterr().err
    assert snapshot(root) == before
