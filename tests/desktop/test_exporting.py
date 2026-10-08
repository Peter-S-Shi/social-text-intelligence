"""The shared atomic export write (synthetic data, a temporary folder)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from social_text_intelligence.desktop import exporting


def test_the_text_is_written_as_utf_8_with_unix_newlines(tmp_path: Path) -> None:
    target = tmp_path / "out.csv"

    exporting.write_atomic(target, "a,b\ncafé,2\n")

    assert target.read_bytes() == "a,b\ncafé,2\n".encode()
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]  # no temp left over


def test_an_existing_file_is_replaced_whole(tmp_path: Path) -> None:
    target = tmp_path / "out.csv"
    target.write_text("old", encoding="utf-8")

    exporting.write_atomic(target, "new")

    assert target.read_text(encoding="utf-8") == "new"


def test_a_failed_replace_leaves_the_original_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.csv"
    target.write_text("keep", encoding="utf-8")

    def refuse(src: object, dst: object) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(os, "replace", refuse)

    with pytest.raises(PermissionError):
        exporting.write_atomic(target, "lost")

    assert target.read_text(encoding="utf-8") == "keep"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]


def test_a_missing_folder_fails_without_creating_anything(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        exporting.write_atomic(tmp_path / "missing" / "out.csv", "x")

    assert list(tmp_path.iterdir()) == []


def test_the_failure_message_names_no_path_and_no_content() -> None:
    assert "/" not in exporting.EXPORT_FAILED_BODY
    assert "\\" not in exporting.EXPORT_FAILED_BODY
