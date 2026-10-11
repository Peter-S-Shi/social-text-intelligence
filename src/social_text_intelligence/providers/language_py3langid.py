"""Local, offline language identification through the ``py3langid`` package.

A source install of ``py3langid`` (the optional ``language`` extra) carries its
statistical model inside the package. The Windows installer ships the package code
without that model; the user can install the identical model separately, and it is
then used only if its bytes match the pinned SHA-256. Detection itself never uses
the network and no data leaves the machine. When the package or a usable model is
missing, the detector reports itself unavailable rather than answering.

The detector's score is the package's own normalised score for the best language. It
is used only to decide when to abstain, and is never presented as a calibrated
probability.
"""

from __future__ import annotations

import hashlib
import importlib
from importlib import metadata
from pathlib import Path
from threading import Lock
from typing import Any

from ..contracts.language import (
    Detection,
    DetectorInfo,
    LanguageDetectorUnavailable,
    LanguageReason,
)

PACKAGE = "py3langid"
# Below this score the detector abstains. Chosen from the bounded evaluation set in
# the tests: real text of any length scored above it, text with too little language
# content (a word like "ok", symbols, links, numbers) scored well below it.
DEFAULT_MIN_SCORE = 0.5
NO_LANGUAGE_CLASS = "zxx"  # the package's "not a language" class: digits, markup, ...
UNDETERMINED_CLASS = "und"
BUNDLED_MODEL = "bundled statistical language model"
INSTALLED_MODEL = "statistical language model installed separately (SHA-256 verified)"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class Py3LangidDetector:
    def __init__(
        self,
        *,
        min_score: float = DEFAULT_MIN_SCORE,
        identifier: Any = None,
        version: str | None = None,
        model_file: Path | None = None,
        model_sha256: str | None = None,
    ) -> None:
        if (model_file is None) != (model_sha256 is None):
            raise ValueError("A separately installed model needs its pinned SHA-256.")
        self._min_score = min_score
        self._identifier = identifier
        self._version = version
        self._model_file = model_file
        self._model_sha256 = model_sha256
        self._model = BUNDLED_MODEL
        self._lock = Lock()

    @property
    def info(self) -> DetectorInfo:
        if self._version is None:
            try:
                self._version = metadata.version(PACKAGE)
            except metadata.PackageNotFoundError as error:
                raise LanguageDetectorUnavailable from error
        return DetectorInfo(
            name=PACKAGE,
            version=self._version,
            model=self._model,
            min_score=self._min_score,
        )

    def _load(self) -> Any:
        identifier = self._identifier
        if identifier is not None:
            return identifier
        with self._lock:
            if self._identifier is None:
                # Not cached on failure: a model installed later is found next time.
                try:
                    module = importlib.import_module(f"{PACKAGE}.langid")
                    model, label = self._model_source(module)
                    self._identifier = module.LanguageIdentifier.from_model_file(
                        model, norm_probs=True
                    )
                    self._model = label
                except Exception as error:  # not installed, or an unusable model
                    raise LanguageDetectorUnavailable from error
            return self._identifier

    def _model_source(self, module: Any) -> tuple[Path, str]:
        """The package's own model first, else the verified separate copy."""

        bundled = Path(module.__file__).parent / module.MODEL_FILE
        if bundled.is_file():
            return bundled, BUNDLED_MODEL
        installed = self._model_file
        if (
            installed is not None
            and installed.is_file()
            and _sha256(installed) == self._model_sha256
        ):
            return installed.absolute(), INSTALLED_MODEL
        raise LanguageDetectorUnavailable

    def detect(self, text: str) -> Detection:
        language, score = self._load().classify(text)
        code = str(language).lower()
        if code == NO_LANGUAGE_CLASS:
            return Detection(language=None, reason=LanguageReason.NO_LANGUAGE_CONTENT)
        score = min(1.0, max(0.0, float(score)))
        if code == UNDETERMINED_CLASS or score < self._min_score:
            return Detection(language=None, reason=LanguageReason.LOW_SCORE)
        return Detection(language=code, score=score)
