"""The app-data resolver is injectable, and its production default is Windows."""

import os
import sys
from pathlib import Path

import pytest

from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.infrastructure.app_data import (
    APP_DIRECTORY_NAME,
    AppDataLocations,
    default_app_data_locations,
    windows_local_app_data,
)


def test_injected_root_defines_the_projects_directory(tmp_path: Path) -> None:
    locations = AppDataLocations(tmp_path)
    assert locations.projects_dir == tmp_path / "projects"
    assert not locations.projects_dir.exists()  # resolving never touches disk
    locations.ensure_projects_dir()
    assert locations.projects_dir.is_dir()


def test_windows_default_is_the_per_user_local_app_data_folder() -> None:
    local = Path("synthetic-local-app-data")
    locations = default_app_data_locations(
        platform="win32", environ={}, known_folder=lambda: local
    )
    assert locations.root == local / APP_DIRECTORY_NAME
    assert APP_DIRECTORY_NAME == "SocialTextIntelligence"


def test_windows_default_falls_back_to_the_environment_variable() -> None:
    def failing_known_folder() -> Path:
        raise OSError("known folder unavailable")

    locations = default_app_data_locations(
        platform="win32",
        environ={"LOCALAPPDATA": "synthetic-env-local"},
        known_folder=failing_known_folder,
    )
    assert locations.root == Path("synthetic-env-local") / APP_DIRECTORY_NAME


def test_windows_default_reports_unavailable_without_any_source() -> None:
    with pytest.raises(ProjectStorageError) as raised:
        default_app_data_locations(
            platform="win32", environ={}, known_folder=lambda: None
        )
    assert raised.value.code == "app_data_unavailable"


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_other_platforms_are_unclaimed_unless_a_root_is_injected(
    platform: str, tmp_path: Path
) -> None:
    with pytest.raises(ProjectStorageError) as raised:
        default_app_data_locations(
            platform=platform,
            environ={"LOCALAPPDATA": "ignored", "HOME": "ignored"},
            known_folder=lambda: Path("ignored"),
        )
    assert raised.value.code == "unsupported_platform"
    assert AppDataLocations(tmp_path).projects_dir == tmp_path / "projects"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Known Folder API")
def test_the_real_windows_known_folder_matches_the_environment() -> None:
    resolved = windows_local_app_data()
    assert resolved is not None and resolved.is_dir()
    assert os.path.samefile(resolved, os.environ["LOCALAPPDATA"])
    assert default_app_data_locations().root == resolved / APP_DIRECTORY_NAME
