"""One explicit, atomic file write shared by every export (reviewed and insights).

An export happens only after the person chose a destination in a save dialog (the
dialog itself asks before replacing a file). The text is written beside the target
and then moved into place, so a failure never leaves a half-written file, and the
fixed failure message carries no path and no record text.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

EXPORT_FAILED_TITLE = "The file was not saved"
EXPORT_FAILED_BODY = (
    "The file could not be saved. Check that the location can be written to and "
    "that the file is not open in another program. Nothing in the project changed."
)


def write_atomic(path: Path, text: str) -> None:
    """Write UTF-8 beside the target, then replace it: no half-written export."""

    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        temporary.write_bytes(text.encode("utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
