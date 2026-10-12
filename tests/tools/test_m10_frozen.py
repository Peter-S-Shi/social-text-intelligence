"""Opt-in Windows checks of a locally built bundle, never formal human UAT."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not os.environ.get("STI_M10_BUNDLE"),
    reason="requires Windows and an explicitly selected local M10 bundle",
)


def test_frozen_packet_audits_the_bundled_truststore() -> None:
    bundle = Path(os.environ["STI_M10_BUNDLE"])
    inventory = json.loads((bundle / "legal/inventory.json").read_text("utf-8"))
    (component,) = [c for c in inventory["components"] if c["name"] == "truststore"]
    assert component["version"] == "0.10.4"
    assert component["license_expression"] == "MIT"
    assert component["license_notices"]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            "--verify-runtime",
            {"ready": True, "models_loaded": False, "language_model_bundled": False},
        ),
        (
            "--smoke",
            {
                "window": True,
                "models_unbundled": True,
                "project_rows": 2,
                "invalid_rows": 1,
                "reopened": True,
            },
        ),
    ],
)
def test_frozen_offline_entry(
    mode: str, expected: dict[str, object], tmp_path: Path
) -> None:
    bundle = Path(os.environ["STI_M10_BUNDLE"])
    environment = dict(
        os.environ,
        TEMP=str(tmp_path),
        TMP=str(tmp_path),
        HF_HOME=str(tmp_path / "synthetic-hub-cache"),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    environment.pop("QT_QPA_PLATFORM", None)
    result = subprocess.run(
        [str(bundle / "sti-check.exe"), mode],
        capture_output=True,
        text=True,
        timeout=90,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout) == expected
