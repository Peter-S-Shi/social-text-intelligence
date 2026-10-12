"""The prepared E4 Qt rebuild never installs anything and stays pinned to the source."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/m10/e4_modified_qt.ps1"


def test_e4_pins_the_delivered_qtbase_archive_and_one_modification() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "distribution/source-manifest.json").read_text())
    qtbase = next(
        item for item in manifest["archives"] if item["component"] == "QtBase"
    )
    assert f"$QtBaseSha256 = '{qtbase['sha256']}'" in script
    assert "Version 19\\.44\\." in script
    assert "-ne 1) { throw 'Unexpected qlibraryinfo.cpp" in script
    for forbidden in ("winget", "vs_buildtools", "Invoke-WebRequest", "Start-Process"):
        assert forbidden.lower() not in script.lower()


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell") is None,
    reason="requires Windows PowerShell",
)
def test_e4_stops_before_creating_anything_when_msvc_is_absent(
    tmp_path: Path,
) -> None:
    work = tmp_path / "e4-work"
    environment = dict(
        os.environ, PATH=str(Path(os.environ["SYSTEMROOT"]) / "System32")
    )
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-SourceArchive",
            str(tmp_path / "absent.tar.xz"),
            "-Bundle",
            str(tmp_path),
            "-Work",
            str(work),
            "-BuildPython",
            sys.executable,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
        check=False,
    )
    assert result.returncode == 3, result.stdout + result.stderr
    assert re.search(r"prerequisite missing: cl\.exe", result.stdout)
    assert "never does so" in result.stdout
    assert not work.exists()
