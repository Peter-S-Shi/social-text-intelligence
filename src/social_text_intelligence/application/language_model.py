"""The optional language-check model: what it is, where it comes from, where it lives.

The installer does not include py3langid's statistical model. A user who wants the
language check downloads it, by explicit choice, from the package's own upstream
repository at the exact commit of its 0.4.0 release. The bytes are pinned by size
and SHA-256, so a different file is never installed or loaded. This model is not
part of the sentiment and emotion readiness gate: analysis never waits for it, and
without it the language check reports itself unavailable (docs/LANGUAGE_DETECTION.md).
The provisioning entry built from these values is ``LANGUAGE_MODEL`` in
``model_provisioning``.
"""

from __future__ import annotations

from pathlib import Path

LANGUAGE_MODEL_KEY = "language"
LANGUAGE_MODEL_ID = "adbar/py3langid"
LANGUAGE_MODEL_REVISION = "3b99caf00d0dcbc9416a9d06f8e5b690e919a74e"  # tag v0.4.0
LANGUAGE_MODEL_FILE = "model.npz.xz"
LANGUAGE_MODEL_SIZE = 4_586_720
LANGUAGE_MODEL_SHA256 = (
    "f4f4a2c3465ca1f081541037f9cac23021d68151c2f709c55ae5eedfca522963"
)
LANGUAGE_MODEL_URL_BASE = (
    "https://raw.githubusercontent.com/adbar/py3langid/"
    f"{LANGUAGE_MODEL_REVISION}/py3langid/data"
)
LANGUAGE_MODEL_SOURCE = "github.com/adbar/py3langid (py3langid 0.4.0)"


def installed_language_model(models_root: Path) -> Path:
    """The installed file, in the same layout the model store writes."""

    org, name = LANGUAGE_MODEL_ID.split("/", maxsplit=1)
    return (
        models_root
        / f"models--{org}--{name}"
        / "snapshots"
        / LANGUAGE_MODEL_REVISION
        / LANGUAGE_MODEL_FILE
    )
