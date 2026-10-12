"""Offline runtime preflight for the production onedir entries (no model weights)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeVerification:
    ready: bool
    failed: tuple[str, ...] = ()
    message: str = "Packaged runtime dependencies are available."
    # The language model is optional: the installer leaves it out, and the user can
    # install it later. Its absence never blocks start-up.
    language_model_bundled: bool = False


def verify_runtime(
    *, import_module: Callable[[str], Any] = importlib.import_module
) -> RuntimeVerification:
    """Exercise offline imports without model weights or user data."""
    language_model_bundled = False
    modules = (
        "torch",
        "transformers",
        "transformers.models.roberta.modeling_roberta",
        "tokenizers",
        "safetensors",
        "huggingface_hub",
        "py3langid.langid",
        # Model downloads verify certificates with it (M10 S5-NET-001).
        "truststore",
        "PySide6.QtWidgets",
    )
    for name in modules:
        try:
            module = import_module(name)
            if name == "transformers":
                for attribute in (
                    "AutoTokenizer",
                    "AutoModelForSequenceClassification",
                ):
                    if not callable(getattr(module, attribute)):
                        raise ImportError("model loader unavailable")
            if name == "py3langid.langid":
                if not callable(module.LanguageIdentifier.from_model_file):
                    raise ImportError("language model loader unavailable")
                language_model_bundled = (
                    Path(module.__file__).parent / module.MODEL_FILE
                ).is_file()
                if language_model_bundled:
                    identifier = module.LanguageIdentifier.from_model_file(
                        module.MODEL_FILE, norm_probs=True
                    )
                    language, _ = identifier.classify(
                        "This software update works well and the interface is easy "
                        "to use."
                    )
                    if language != "en":
                        raise ValueError("language resource unavailable")
        except Exception:
            return RuntimeVerification(
                ready=False,
                failed=(name,),
                message=(
                    "The packaged runtime is incomplete or unavailable. "
                    "Rebuild or repair the application before starting it."
                ),
            )
    return RuntimeVerification(
        ready=True, language_model_bundled=language_model_bundled
    )
