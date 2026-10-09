"""User-facing wording for provisioning, keyed by state and error code.

The backend's fixed error messages are shown verbatim as the body. The desktop adds
a title and the recovery actions, and replaces the two texts the M5.1 design flagged
(``provisioning_in_progress`` omits Verify; ``model_load_failed`` is V1 offline text).
"""

from __future__ import annotations

from ..application.model_provisioning import ProvisioningPhase, Readiness

MODEL_NAMES = {"sentiment": "Sentiment model", "emotion": "Emotion model"}

# (icon, word): every state pairs a distinct shape with a word, never colour alone.
CHIPS: dict[Readiness, tuple[str, str]] = {
    Readiness.READY: ("✓", "Ready"),
    Readiness.NOT_INSTALLED: ("○", "Not installed"),
    Readiness.INCOMPLETE: ("◆", "Incomplete"),
    Readiness.CORRUPT: ("✕", "Damaged"),
    Readiness.WRONG_REVISION: ("◇", "Different version"),
}

PHASE_WORDS = {
    ProvisioningPhase.DOWNLOADING: "Downloading",
    ProvisioningPhase.COPYING: "Copying and checking",
    ProvisioningPhase.VERIFYING: "Checking files",
}

ERROR_TITLES = {
    "network_unavailable": "Connection lost",
    "download_rejected": "The download was refused",
    "checksum_mismatch": "A file failed its checksum and was discarded",
    "storage_failed": "The models folder could not be read or written",
    "storage_full": "There is not enough free disk space",
    "source_unreadable": "Couldn't read that folder",
    "provisioning_in_progress": "Another model operation is running",
    "provisioning_elsewhere": "Another window is changing the models folder",
    "model_load_failed": "The model files could not be loaded",
    "unexpected_error": "The operation did not finish",
}

# Replacement bodies, chosen by code (no contract change is needed for these).
ERROR_BODIES = {
    "provisioning_in_progress": (
        "Another model download, import or Verify is already running."
    ),
    "model_load_failed": (
        "The approved model files could not be loaded. Verify the model files "
        "to find out whether one is damaged, or open Models to repair them."
    ),
}

VERIFY_STORAGE_TITLE = "Verify could not read a model file"
VERIFY_STORAGE_NOTE = "Nothing was recorded for that file."

SESSION_BLOCK_TITLE = "Analysis is off until you restart the app"
SESSION_BLOCK_STATUS = "Analysis off until restart"
SESSION_BLOCK_REPAIRED = "models repaired · restart to analyse"

MODELS_NOT_READY_TITLE = "Analysis is unavailable"

FOLDER_NOTE = (
    "The app manages this folder. Download, Import, Verify and Discard can add, "
    "replace or tidy up files in it, and changing files by hand can make a model "
    "not ready."
)
BUSY_NOTE = (
    "A model operation is running. The other actions are available when it finishes."
)
VERIFY_NOTE = "Checking every installed file. This cannot be stopped."
STOP_KEEPS_DOWNLOAD = "Stopping keeps finished files and the partial file."
STOP_KEEPS_NOTHING = "Stopping an import keeps nothing partial."
