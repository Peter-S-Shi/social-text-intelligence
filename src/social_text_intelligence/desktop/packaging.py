"""Offline runtime preflight for the production onedir entries (no model weights)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeVerification:
    ready: bool
    failed: tuple[str, ...] = ()
    message: str = "Packaged runtime dependencies are available."


def verify_runtime(
    *, import_module: Callable[[str], Any] = importlib.import_module
) -> RuntimeVerification:
    """Exercise offline imports without model weights or user data."""
    modules = (
        "torch",
        "transformers",
        "transformers.models.roberta.modeling_roberta",
        "tokenizers",
        "safetensors",
        "huggingface_hub",
        "py3langid.langid",
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
                identifier = module.LanguageIdentifier.from_model_file(
                    module.MODEL_FILE, norm_probs=True
                )
                language, _ = identifier.classify(
                    "This software update works well and the interface is easy to use."
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
    return RuntimeVerification(ready=True)
