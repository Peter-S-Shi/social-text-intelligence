"""OS-level process locks: exclusive per scope, gone with the process."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_text_intelligence.infrastructure.process_locks import FileProcessLocks

from .harness import Peer, eventually


def test_a_scope_can_be_held_by_one_holder_at_a_time(tmp_path: Path) -> None:
    locks = FileProcessLocks(tmp_path / "locks")

    first = locks.try_acquire("models")
    assert first is not None
    assert locks.try_acquire("models") is None  # refused, never blocks
    first.release()

    again = locks.try_acquire("models")
    assert again is not None
    again.release()


def test_release_is_idempotent_and_scopes_are_independent(tmp_path: Path) -> None:
    locks = FileProcessLocks(tmp_path / "locks")
    a = locks.try_acquire("project-a")
    b = locks.try_acquire("project-b")
    assert a is not None and b is not None

    a.release()
    a.release()  # a second release is harmless
    assert locks.try_acquire("project-b") is None
    assert locks.try_acquire("project-a") is not None
    b.release()


def test_a_scope_name_can_never_name_a_path(tmp_path: Path) -> None:
    locks = FileProcessLocks(tmp_path / "locks")
    for bad in ("", "../escape", "a/b", "a\\b", "x" * 200, "A B"):
        with pytest.raises(ValueError):
            locks.try_acquire(bad)
    assert not (tmp_path / "escape").exists()


def test_another_process_holding_a_scope_refuses_us(tmp_path: Path) -> None:
    peer = Peer("hold", tmp_path / "sig", root=str(tmp_path), scope="models")
    peer.wait_started()
    locks = FileProcessLocks(tmp_path / "locks")
    try:
        assert locks.try_acquire("models") is None
        other = locks.try_acquire("project-x")  # other scopes stay free
        assert other is not None
        other.release()
    finally:
        assert peer.finish() == {"held": True}
    after = locks.try_acquire("models")
    assert after is not None
    after.release()


def test_a_hard_killed_holder_leaves_no_stale_lock(tmp_path: Path) -> None:
    peer = Peer("hold", tmp_path / "sig", root=str(tmp_path), scope="models")
    peer.wait_started()
    locks = FileProcessLocks(tmp_path / "locks")
    assert locks.try_acquire("models") is None

    peer.kill()  # no release, no cleanup code runs

    again = eventually(
        lambda: locks.try_acquire("models"), accept=lambda held: held is not None
    )
    assert again is not None
    again.release()
