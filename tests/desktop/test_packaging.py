"""Packaged dependency verification must fail safely without models or user data."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from social_text_intelligence.desktop.packaging import verify_runtime


def test_missing_dynamic_dependency_is_a_fixed_failure() -> None:
    def missing(name: str) -> object:
        raise ImportError("private machine detail")

    result = verify_runtime(import_module=missing)
    assert result.ready is False
    assert result.failed == ("torch",)
    assert "private" not in result.message


@pytest.mark.parametrize("broken", ["transformers", "py3langid.langid"])
def test_lazy_classes_and_language_resources_are_required(broken: str) -> None:
    def load(name: str) -> object:
        return SimpleNamespace() if name == broken else complete_module(name)

    result = verify_runtime(import_module=load)
    assert not result.ready
    assert result.failed == (broken,)


def complete_module(name: str) -> object:
    class Identifier:
        @classmethod
        def from_pickled_model(cls, model: object, *, norm_probs: bool) -> Any:
            return SimpleNamespace(classify=lambda text: ("en", 1.0))

    return SimpleNamespace(
        AutoTokenizer=lambda: None,
        AutoModelForSequenceClassification=lambda: None,
        LanguageIdentifier=Identifier,
        model=b"synthetic-resource",
    )


def test_all_dependencies_verify_without_accessing_user_data() -> None:
    names: list[str] = []

    def load(name: str) -> object:
        names.append(name)
        return complete_module(name)

    assert verify_runtime(import_module=load).ready
    assert "transformers.models.roberta.modeling_roberta" in names
    assert "PySide6.QtWidgets" in names


def test_packaged_smoke_uses_temporary_app_data(qapp: Any) -> None:
    from social_text_intelligence.desktop.packaged_entry import smoke

    result = smoke()
    assert result == {
        "window": True,
        "models_unbundled": True,
        "project_rows": 2,
        "invalid_rows": 1,
        "reopened": True,
    }
