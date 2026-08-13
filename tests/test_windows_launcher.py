from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "start_social_text_intelligence.bat"


def test_windows_launcher_is_portable_offline_and_self_explanatory() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in source
    assert '.venv\\Scripts\\sti-web.exe' in source
    assert '"%STI_WEB%" --offline' in source
    assert "http://127.0.0.1:5000" in source
    assert "if not exist" in source
    assert "README.md" in source
    assert "Press Ctrl+C" in source
    assert ":\\Users\\" not in source
    assert ":\\CodexWorkspaces\\" not in source
