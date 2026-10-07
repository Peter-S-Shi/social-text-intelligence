"""Per-user application-data locations, injectable so tests need no Windows."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ..contracts.errors import ProjectStorageError

APP_DIRECTORY_NAME = "SocialTextIntelligence"
PROJECTS_DIRECTORY_NAME = "projects"
MODELS_DIRECTORY_NAME = "models"

# FOLDERID_LocalAppData: per-user and non-roaming, so project text never syncs.
_LOCAL_APP_DATA_FOLDER_ID = "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"


@dataclass(frozen=True, slots=True)
class AppDataLocations:
    """Resolved application-data root; no directory exists until it is ensured."""

    root: Path

    @property
    def projects_dir(self) -> Path:
        return self.root / PROJECTS_DIRECTORY_NAME

    @property
    def models_dir(self) -> Path:
        return self.root / MODELS_DIRECTORY_NAME

    def ensure_projects_dir(self) -> Path:
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        return self.projects_dir


def windows_local_app_data() -> Path | None:
    """Resolve %LOCALAPPDATA% through the Windows Known Folder API (stdlib only)."""

    if sys.platform != "win32":
        return None

    import ctypes
    from ctypes import wintypes

    guid = (ctypes.c_byte * 16)()
    ctypes.oledll.ole32.CLSIDFromString(_LOCAL_APP_DATA_FOLDER_ID, guid)
    resolved = ctypes.c_wchar_p()
    get_known_folder = ctypes.windll.shell32.SHGetKnownFolderPath
    get_known_folder.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    try:
        if get_known_folder(guid, 0, None, ctypes.byref(resolved)) != 0:
            return None
        return Path(resolved.value) if resolved.value else None
    finally:
        ctypes.windll.ole32.CoTaskMemFree(resolved)


def default_app_data_locations(
    *,
    platform: str = sys.platform,
    environ: Mapping[str, str] | None = None,
    known_folder: Callable[[], Path | None] = windows_local_app_data,
) -> AppDataLocations:
    """Return the production location: Windows per-user LocalAppData only.

    Other platforms are unclaimed for V2.0; callers there inject an explicit root.
    """

    if platform != "win32":
        raise ProjectStorageError(
            code="unsupported_platform",
            message=(
                "Persistent projects are only supported on Windows by default; "
                "supply an explicit application-data root."
            ),
        )
    variables = os.environ if environ is None else environ
    local: Path | None
    try:
        local = known_folder()
    except OSError:
        local = None
    if local is None and variables.get("LOCALAPPDATA"):
        local = Path(variables["LOCALAPPDATA"])
    if local is None:
        raise ProjectStorageError(
            code="app_data_unavailable",
            message="The per-user application-data folder could not be resolved.",
        )
    return AppDataLocations(local / APP_DIRECTORY_NAME)
