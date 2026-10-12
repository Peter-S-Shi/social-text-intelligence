"""Packaged dependency verification must fail safely without models or user data."""

from __future__ import annotations

from pathlib import Path
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


def complete_module(name: str, package_dir: Path | None = None) -> object:
    class Identifier:
        @classmethod
        def from_model_file(cls, model: object, *, norm_probs: bool) -> Any:
            return SimpleNamespace(classify=lambda text: ("en", 1.0))

    return SimpleNamespace(
        AutoTokenizer=lambda: None,
        AutoModelForSequenceClassification=lambda: None,
        LanguageIdentifier=Identifier,
        MODEL_FILE="synthetic-resource",
        __file__=str((package_dir or Path(__file__).parent) / "langid.py"),
    )


def test_all_dependencies_verify_without_accessing_user_data() -> None:
    names: list[str] = []

    def load(name: str) -> object:
        names.append(name)
        return complete_module(name)

    result = verify_runtime(import_module=load)
    assert result.ready
    assert "transformers.models.roberta.modeling_roberta" in names
    assert "truststore" in names
    assert "PySide6.QtWidgets" in names


def test_a_missing_certificate_verifier_is_a_fixed_failure() -> None:
    def load(name: str) -> object:
        if name == "truststore":
            raise ImportError("not bundled")
        return complete_module(name)

    result = verify_runtime(import_module=load)
    assert not result.ready
    assert result.failed == ("truststore",)


def test_packaged_smoke_uses_temporary_app_data(qapp: Any) -> None:
    from social_text_intelligence.desktop.qt.packaged_entry import smoke

    result = smoke()
    assert result == {
        "window": True,
        "models_unbundled": True,
        "project_rows": 2,
        "invalid_rows": 1,
        "reopened": True,
        "application_icon": True,
    }


def test_an_absent_language_model_never_blocks_start_up() -> None:
    # The installer leaves the statistical model out; the code must still import.
    result = verify_runtime(import_module=complete_module)
    assert result.ready
    assert result.language_model_bundled is False


def test_a_bundled_language_model_is_exercised(tmp_path: Path) -> None:
    (tmp_path / "synthetic-resource").write_bytes(b"synthetic model placeholder")
    result = verify_runtime(import_module=lambda name: complete_module(name, tmp_path))
    assert result.ready
    assert result.language_model_bundled is True


def test_actual_bundled_language_resource_verifies() -> None:
    import importlib

    def load(name: str) -> object:
        if name == "py3langid.langid":
            return importlib.import_module(name)
        return complete_module(name)

    result = verify_runtime(import_module=load)
    assert result.ready
    assert result.language_model_bundled is True  # source install: bundled model
