"""Local, offline language identification through the ``py3langid`` package.

``py3langid`` bundles its statistical model inside the package: there is no network
access, no model download, and no data leaves the machine. The package is optional
(the ``language`` extra); when it is missing or its model cannot be loaded the
detector reports itself unavailable rather than answering.

The detector's score is the package's own normalised score for the best language. It
is used only to decide when to abstain, and is never presented as a calibrated
probability.
"""

from __future__ import annotations

import importlib
from importlib import metadata
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


class Py3LangidDetector:
    def __init__(
        self,
        *,
        min_score: float = DEFAULT_MIN_SCORE,
        identifier: Any = None,
        version: str | None = None,
    ) -> None:
        self._min_score = min_score
        self._identifier = identifier
        self._version = version
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
            model="bundled statistical language model",
            min_score=self._min_score,
        )

    def _load(self) -> Any:
        identifier = self._identifier
        if identifier is not None:
            return identifier
        with self._lock:
            if self._identifier is None:
                try:
                    module = importlib.import_module(f"{PACKAGE}.langid")
                    self._identifier = module.LanguageIdentifier.from_model_file(
                        module.MODEL_FILE, norm_probs=True
                    )
                except Exception as error:  # not installed, or an unusable model
                    raise LanguageDetectorUnavailable from error
            return self._identifier

    def detect(self, text: str) -> Detection:
        language, score = self._load().classify(text)
        code = str(language).lower()
        if code == NO_LANGUAGE_CLASS:
            return Detection(language=None, reason=LanguageReason.NO_LANGUAGE_CONTENT)
        score = min(1.0, max(0.0, float(score)))
        if code == UNDETERMINED_CLASS or score < self._min_score:
            return Detection(language=None, reason=LanguageReason.LOW_SCORE)
        return Detection(language=code, score=score)
