"""Where the py3langid adapter finds its model (M10 S1).

A source install uses the package's own model. The Windows installer leaves that
model out; a separately installed copy is used only when its SHA-256 matches the
pin, and otherwise the check stays unavailable. Absence is never cached, so a
model installed later is found on the next analysis.
"""

from __future__ import annotations

import hashlib
import importlib
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from language_eval_set import EVAL_SET

from social_text_intelligence.application.language_model import (
    LANGUAGE_MODEL_SHA256,
    installed_language_model,
)
from social_text_intelligence.application.settings import language_detector
from social_text_intelligence.contracts import LanguageDetectorUnavailable
from social_text_intelligence.providers import language_py3langid
from social_text_intelligence.providers.language_py3langid import (
    BUNDLED_MODEL,
    INSTALLED_MODEL,
    Py3LangidDetector,
)

HAVE_PACKAGE = importlib.util.find_spec("py3langid") is not None
MODEL = b"synthetic language model bytes"


class Loader:
    """Stands in for ``py3langid.langid``; records which model file it loaded."""

    def __init__(self, package_dir: Path) -> None:
        self.__file__ = str(package_dir / "langid.py")
        self.MODEL_FILE = "data/model.npz.xz"
        self.loaded: list[Path] = []
        outer = self

        class Identifier:
            @classmethod
            def from_model_file(cls, model: Path, *, norm_probs: bool) -> Any:
                outer.loaded.append(Path(model))
                return SimpleNamespace(classify=lambda text: ("en", 0.99))

        self.LanguageIdentifier = Identifier


def wired(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, sha: str | None = None
) -> tuple[Py3LangidDetector, Loader, Path]:
    loader = Loader(tmp_path / "package")
    monkeypatch.setattr(
        language_py3langid, "importlib", SimpleNamespace(import_module=lambda _: loader)
    )
    installed = tmp_path / "models" / "model.npz.xz"
    found = Py3LangidDetector(
        version="0.4.0",
        model_file=installed,
        model_sha256=sha or hashlib.sha256(MODEL).hexdigest(),
    )
    return found, loader, installed


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_the_package_model_comes_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    found, loader, installed = wired(monkeypatch, tmp_path)
    put(tmp_path / "package" / "data" / "model.npz.xz", b"bundled")
    put(installed, MODEL)
    assert found.detect("text").language == "en"
    assert loader.loaded == [tmp_path / "package" / "data" / "model.npz.xz"]
    assert found.info.model == BUNDLED_MODEL


def test_a_verified_separate_model_is_used_without_a_bundled_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    found, loader, installed = wired(monkeypatch, tmp_path)
    put(installed, MODEL)
    assert found.detect("text").language == "en"
    assert loader.loaded == [installed.absolute()]
    assert found.info.model == INSTALLED_MODEL


def test_a_file_with_other_bytes_is_never_loaded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    found, loader, installed = wired(monkeypatch, tmp_path, sha="0" * 64)
    put(installed, MODEL)
    with pytest.raises(LanguageDetectorUnavailable):
        found.detect("text")
    assert loader.loaded == []


def test_absence_is_not_cached_so_a_later_install_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    found, loader, installed = wired(monkeypatch, tmp_path)
    with pytest.raises(LanguageDetectorUnavailable):
        found.detect("text")
    put(installed, MODEL)
    assert found.detect("text").language == "en"
    assert loader.loaded == [installed.absolute()]


def test_a_separate_model_needs_its_pin() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        Py3LangidDetector(model_file=Path("model.npz.xz"))


def test_the_desktop_detector_reads_the_pinned_file_in_the_models_folder(
    tmp_path: Path,
) -> None:
    found = language_detector(tmp_path)
    assert found._model_file == installed_language_model(tmp_path)
    assert found._model_sha256 == LANGUAGE_MODEL_SHA256
    assert installed_language_model(tmp_path).name == "model.npz.xz"


@pytest.fixture
def short_root() -> Any:
    # The store's layout adds about 110 characters; pytest's own temporary paths
    # can then pass the classic Windows path limit.
    with tempfile.TemporaryDirectory(prefix="sti") as root:
        yield Path(root)


@pytest.mark.skipif(not HAVE_PACKAGE, reason="the optional 'language' extra")
def test_the_real_model_loaded_separately_gives_identical_results(
    monkeypatch: pytest.MonkeyPatch, short_root: Path
) -> None:
    """The pinned upstream bytes restore exactly the bundled behaviour."""

    tmp_path = short_root

    real = importlib.import_module("py3langid.langid")
    bundled = Path(str(real.__file__)).parent / real.MODEL_FILE
    if hashlib.sha256(bundled.read_bytes()).hexdigest() != LANGUAGE_MODEL_SHA256:
        pytest.skip("the installed package carries a different model")
    reference = Py3LangidDetector(version="0.4.0")
    reference.detect("loaded before the bundle is hidden")
    installed = installed_language_model(tmp_path / "models")
    installed.parent.mkdir(parents=True)
    shutil.copyfile(bundled, installed)
    without_bundle = SimpleNamespace(
        __file__=str(tmp_path / "package" / "langid.py"),
        MODEL_FILE=real.MODEL_FILE,
        LanguageIdentifier=real.LanguageIdentifier,
    )
    monkeypatch.setattr(
        language_py3langid,
        "importlib",
        SimpleNamespace(import_module=lambda _: without_bundle),
    )
    separate = language_detector(tmp_path / "models")
    for text, _ in EVAL_SET:
        assert separate.detect(text) == reference.detect(text), text
    assert separate.info.model == INSTALLED_MODEL


def test_the_packaged_language_check_reports_absence_and_presence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from social_text_intelligence.desktop.qt.packaged_entry import language_check

    loader = Loader(tmp_path / "package")
    monkeypatch.setattr(
        language_py3langid, "importlib", SimpleNamespace(import_module=lambda _: loader)
    )
    root = tmp_path / "m"
    assert language_check(root) == {
        "available": False,
        "model_file_present": False,
        "detected": {},
    }
    monkeypatch.setattr(
        "social_text_intelligence.application.settings.LANGUAGE_MODEL_SHA256",
        hashlib.sha256(MODEL).hexdigest(),
    )
    put(installed_language_model(root), MODEL)
    found = language_check(root)
    assert found["available"] is True
    assert found["model"] == INSTALLED_MODEL
