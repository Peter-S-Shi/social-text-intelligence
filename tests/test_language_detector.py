"""The py3langid adapter, and a bounded evaluation of the real detector.

The evaluation shows the warning behaviour is sensible on a small synthetic set; it
is not an accuracy benchmark and supports no accuracy claim.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

import pytest
from language_eval_set import ENGLISH, EVAL_SET, OTHER, UNCLEAR

from social_text_intelligence.contracts import (
    LanguageDetectorUnavailable,
    LanguageReason,
    LanguageStatus,
)
from social_text_intelligence.providers.language_py3langid import Py3LangidDetector
from social_text_intelligence.services.language import assess_language

HAVE_PACKAGE = importlib.util.find_spec("py3langid") is not None
REQUIRED = os.environ.get("STI_REQUIRE_LANGID") == "1"


class StubIdentifier:
    def __init__(self, answer: tuple[str, float]) -> None:
        self.answer = answer
        self.seen: list[str] = []

    def classify(self, text: str) -> tuple[str, float]:
        self.seen.append(text)
        return self.answer


def detector(answer: tuple[str, float], min_score: float = 0.5) -> Py3LangidDetector:
    return Py3LangidDetector(
        min_score=min_score, identifier=StubIdentifier(answer), version="0.4.0"
    )


def test_a_confident_language_is_returned_lowercase_with_its_own_score() -> None:
    found = detector(("FR", 0.8)).detect("texte")

    assert (found.language, found.score, found.reason) == ("fr", 0.8, None)


def test_a_score_below_the_threshold_abstains_instead_of_guessing() -> None:
    found = detector(("fr", 0.3)).detect("mot")

    assert found.language is None and found.score is None
    assert found.reason is LanguageReason.LOW_SCORE


def test_the_threshold_itself_is_confident_enough() -> None:
    assert detector(("en", 0.5)).detect("x").language == "en"


def test_the_non_language_class_is_reported_as_no_language_content() -> None:
    found = detector(("zxx", 0.9)).detect("12345")

    assert found.language is None
    assert found.reason is LanguageReason.NO_LANGUAGE_CONTENT


def test_the_undetermined_marker_abstains() -> None:
    assert detector(("und", 0.9)).detect("x").reason is LanguageReason.LOW_SCORE


def test_scores_are_kept_inside_zero_to_one() -> None:
    assert detector(("en", 1.0000001)).detect("x").score == 1.0


def test_the_detector_describes_itself_for_audit() -> None:
    info = detector(("en", 0.9), min_score=0.6).info

    assert (info.name, info.version, info.min_score) == ("py3langid", "0.4.0", 0.6)
    assert "bundled" in info.model


def test_a_missing_package_is_unavailable_not_a_wrong_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(name: str) -> Any:
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", refuse)

    with pytest.raises(LanguageDetectorUnavailable):
        Py3LangidDetector().detect("text")


def test_a_broken_model_is_unavailable_too(monkeypatch: pytest.MonkeyPatch) -> None:
    class Broken:
        class LanguageIdentifier:
            @staticmethod
            def from_model_file(*_args: Any, **_kwargs: Any) -> Any:
                raise ValueError("unsupported model layout")

        MODEL_FILE = "x"

    monkeypatch.setattr(importlib, "import_module", lambda name: Broken)

    with pytest.raises(LanguageDetectorUnavailable):
        Py3LangidDetector(version="0.4.0").detect("text")


def test_the_package_must_be_present_when_ci_requires_it() -> None:
    if REQUIRED:
        assert HAVE_PACKAGE, "py3langid must be installed (STI_REQUIRE_LANGID=1)"


# -- the real detector, over a bounded synthetic set -------------------------------


@pytest.fixture(scope="module")
def real() -> Py3LangidDetector:
    if not HAVE_PACKAGE:
        pytest.skip("py3langid is not installed (set STI_REQUIRE_LANGID=1 to require)")
    return Py3LangidDetector()


def outcome(real: Py3LangidDetector, text: str) -> str:
    result = assess_language(real, text, ("en",))
    if result.status is LanguageStatus.SUPPORTED:
        return ENGLISH
    if result.status is LanguageStatus.UNSUPPORTED:
        return OTHER
    return UNCLEAR


@pytest.mark.parametrize("expected", [ENGLISH, OTHER, UNCLEAR])
def test_the_warning_policy_is_sensible_on_the_bounded_set(
    real: Py3LangidDetector, expected: str
) -> None:
    cases = [(text, want) for text, want in EVAL_SET if want == expected]

    wrong = [text for text, want in cases if outcome(real, text) != want]

    assert len(cases) >= 12
    assert wrong == []


def test_short_or_noisy_text_is_never_called_english_or_foreign(
    real: Py3LangidDetector,
) -> None:
    for text in ("ok", "🙂🙂🙂", "https://example.com/a", "12345", "@a #b", "!!!"):
        result = assess_language(real, text, ("en",))
        assert result.status is LanguageStatus.UNDETERMINED, text
        assert result.detected_language is None


def test_the_real_detector_is_deterministic(real: Py3LangidDetector) -> None:
    text = "Mi pedido llegó dos días tarde."

    assert {real.detect(text) for _ in range(5)} == {real.detect(text)}


def test_the_real_detector_is_described_for_audit(real: Py3LangidDetector) -> None:
    info = real.info

    assert info.name == "py3langid"
    assert info.version.count(".") >= 1
    assert info.min_score == 0.5
