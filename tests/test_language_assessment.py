"""The detected-language evidence and the policy that turns a detection into it."""

from __future__ import annotations

import pytest

from social_text_intelligence.contracts import (
    Detection,
    DetectorInfo,
    LanguageAssessment,
    LanguageReason,
    LanguageStatus,
)
from social_text_intelligence.contracts.errors import ValidationError
from social_text_intelligence.contracts.language import LanguageDetectorUnavailable
from social_text_intelligence.services.language import (
    assess_language,
    describe_language,
    describe_summary,
    summarize_languages,
)

INFO = DetectorInfo(name="fake", version="1.0", model="fake-model", min_score=0.5)


class FakeDetector:
    """A deterministic detector that records what it was shown."""

    info = INFO

    def __init__(self, outcome: Detection | Exception) -> None:
        self.outcome = outcome
        self.seen: list[str] = []

    def detect(self, text: str) -> Detection:
        self.seen.append(text)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_an_english_detection_is_supported_by_the_english_models() -> None:
    detector = FakeDetector(Detection(language="en", score=0.97))

    result = assess_language(detector, "some text", supported=("en",))

    assert result.status is LanguageStatus.SUPPORTED
    assert result.detected_language == "en"
    assert result.score == 0.97
    assert result.supported_languages == ("en",)
    assert result.detector == INFO
    assert detector.seen == ["some text"]


def test_another_language_is_unsupported_and_is_still_a_result() -> None:
    result = assess_language(
        FakeDetector(Detection(language="fr", score=0.99)), "texte", supported=("en",)
    )

    assert result.status is LanguageStatus.UNSUPPORTED
    assert result.detected_language == "fr"
    assert result.needs_attention


def test_a_detector_that_abstains_is_undetermined_not_a_guess() -> None:
    result = assess_language(
        FakeDetector(Detection(language=None, reason=LanguageReason.LOW_SCORE)),
        "ok",
        supported=("en",),
    )

    assert result.status is LanguageStatus.UNDETERMINED
    assert result.detected_language is None
    assert result.score is None
    assert result.reason is LanguageReason.LOW_SCORE
    assert result.needs_attention


def test_text_without_language_content_says_so() -> None:
    result = assess_language(
        FakeDetector(
            Detection(language=None, reason=LanguageReason.NO_LANGUAGE_CONTENT)
        ),
        "12345",
        supported=("en",),
    )

    assert result.reason is LanguageReason.NO_LANGUAGE_CONTENT


def test_support_comes_from_the_models_not_from_the_detection() -> None:
    result = assess_language(
        FakeDetector(Detection(language="fr", score=0.9)), "texte", supported=("fr",)
    )

    assert result.status is LanguageStatus.SUPPORTED  # a model that covers French


def test_an_unconfigured_detector_is_a_visible_unavailable_check_not_a_pass() -> None:
    result = assess_language(None, "text", supported=("en",))

    assert result.status is LanguageStatus.NOT_ASSESSED
    assert result.reason is LanguageReason.DETECTOR_UNAVAILABLE
    assert result.needs_attention  # a fresh analysis is never silently "fine"


@pytest.mark.parametrize(
    "answer",
    [
        Detection(language="", score=0.9),  # blank code
        Detection(language=" ", score=0.5),  # whitespace only
    ],
)
def test_a_detector_that_returns_nonsense_is_a_failed_check_not_a_crash(
    answer: Detection,
) -> None:
    result = assess_language(FakeDetector(answer), "text", supported=("en",))

    assert result.status is LanguageStatus.NOT_ASSESSED
    assert result.reason is LanguageReason.DETECTOR_FAILED


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (LanguageDetectorUnavailable(), LanguageReason.DETECTOR_UNAVAILABLE),
        (RuntimeError("boom with text: secret"), LanguageReason.DETECTOR_FAILED),
    ],
)
def test_a_detector_that_cannot_run_is_never_treated_as_supported(
    failure: Exception, reason: LanguageReason
) -> None:
    result = assess_language(FakeDetector(failure), "text", supported=("en",))

    assert result.status is LanguageStatus.NOT_ASSESSED
    assert result.reason is reason
    assert result.needs_attention  # the person is told the check did not happen
    assert result.detected_language is None
    # nothing of the failure (which can contain record text) is kept anywhere
    assert "secret" not in repr(result) + repr(result.detector)


def test_the_assessment_carries_no_supplied_metadata() -> None:
    # The policy only ever sees the text: supplied language cannot influence it.
    detector = FakeDetector(Detection(language="en", score=0.9))

    assess_language(detector, "only the text", supported=("en",))

    assert detector.seen == ["only the text"]


# -- the contract ---------------------------------------------------------------


def test_the_default_assessment_is_not_assessed() -> None:
    result = LanguageAssessment.not_assessed()

    assert result.status is LanguageStatus.NOT_ASSESSED
    assert result.reason is LanguageReason.NOT_RUN


@pytest.mark.parametrize(
    "changes",
    [
        {"status": LanguageStatus.SUPPORTED, "detected_language": "fr", "score": 0.9},
        {"status": LanguageStatus.UNSUPPORTED, "detected_language": "en", "score": 0.9},
        {"status": LanguageStatus.SUPPORTED, "detected_language": None, "score": 0.9},
        {"status": LanguageStatus.SUPPORTED, "detected_language": "en", "score": 1.5},
        {"status": LanguageStatus.SUPPORTED, "detected_language": "en", "score": None},
        {
            "status": LanguageStatus.SUPPORTED,
            "detected_language": "en",
            "score": 0.9,
            "detector": None,
        },
        {
            "status": LanguageStatus.UNDETERMINED,
            "detected_language": "en",
            "reason": LanguageReason.LOW_SCORE,
        },
        {"status": LanguageStatus.UNDETERMINED, "reason": None},
        {"status": LanguageStatus.NOT_ASSESSED, "detected_language": "en"},
        {"status": LanguageStatus.NOT_ASSESSED, "reason": LanguageReason.LOW_SCORE},
    ],
)
def test_an_incoherent_assessment_is_refused(changes: dict[str, object]) -> None:
    base: dict[str, object] = {
        "status": LanguageStatus.SUPPORTED,
        "detected_language": "en",
        "score": 0.9,
        "supported_languages": ("en",),
        "detector": INFO,
        "reason": None,
    }

    with pytest.raises(ValidationError):
        LanguageAssessment(**{**base, **changes})  # type: ignore[arg-type]


def test_a_detector_info_must_be_complete() -> None:
    with pytest.raises(ValidationError):
        DetectorInfo(name="", version="1", model="m", min_score=0.5)
    with pytest.raises(ValidationError):
        DetectorInfo(name="d", version="1", model="m", min_score=1.5)


# -- the words the person reads -------------------------------------------------


def test_an_unsupported_notice_names_the_language_and_makes_no_claim_about_people() -> (
    None
):
    notice = describe_language(
        assess_language(
            FakeDetector(Detection(language="fr", score=0.99)), "texte", ("en",)
        )
    )

    assert notice.warns
    assert "French (fr)" in notice.headline
    text = f"{notice.headline} {notice.detail}".lower()
    assert "still analysed" in text
    assert "not been changed" in text
    for forbidden in ("nationality", "culture", "writer is", "accurate", "probab"):
        assert forbidden not in text


def test_a_supported_notice_does_not_warn_and_calls_the_score_a_detector_score() -> (
    None
):
    notice = describe_language(
        assess_language(
            FakeDetector(Detection(language="en", score=0.97)), "text", ("en",)
        )
    )

    assert not notice.warns
    assert "English (en)" in notice.headline
    assert "not a probability" in notice.detail


def test_undetermined_and_failed_notices_warn_and_not_run_does_not() -> None:
    undetermined = describe_language(
        assess_language(
            FakeDetector(Detection(language=None, reason=LanguageReason.LOW_SCORE)),
            "ok",
            ("en",),
        )
    )
    unavailable = describe_language(
        assess_language(FakeDetector(LanguageDetectorUnavailable()), "x", ("en",))
    )
    not_run = describe_language(LanguageAssessment.not_assessed())

    assert undetermined.warns and "not confidently determined" in undetermined.headline
    assert unavailable.warns and "unavailable" in unavailable.headline.lower()
    assert not not_run.warns and "not assessed" in not_run.headline.lower()


def test_an_unknown_language_code_is_shown_as_its_code() -> None:
    notice = describe_language(
        assess_language(
            FakeDetector(Detection(language="zzz", score=0.9)), "x", ("en",)
        )
    )

    assert "zzz" in notice.headline


# -- a project-level summary ----------------------------------------------------


def _assessments() -> list[LanguageAssessment]:
    def made(detection: Detection | Exception) -> LanguageAssessment:
        return assess_language(FakeDetector(detection), "t", ("en",))

    return [
        made(Detection(language="en", score=0.9)),
        made(Detection(language="en", score=0.9)),
        made(Detection(language="fr", score=0.9)),
        made(Detection(language="fr", score=0.9)),
        made(Detection(language="es", score=0.9)),
        made(Detection(language=None, reason=LanguageReason.LOW_SCORE)),
        made(LanguageDetectorUnavailable()),
        LanguageAssessment.not_assessed(),
    ]


def test_the_summary_counts_every_state_and_names_the_languages() -> None:
    summary = summarize_languages(_assessments())

    assert (
        summary.total,
        summary.supported,
        summary.unsupported,
        summary.undetermined,
        summary.unavailable,
        summary.not_assessed,
    ) == (8, 2, 3, 1, 1, 1)
    assert summary.unsupported_languages == (("fr", 2), ("es", 1))
    assert summary.attention_count == 5  # 3 unsupported + 1 undetermined + 1 unchecked


def test_the_summary_wording_warns_without_claiming_more_than_it_knows() -> None:
    notice = describe_summary(summarize_languages(_assessments()))

    assert notice is not None and notice.warns
    assert "5 of 8" in notice.headline
    assert "French (fr) 2" in notice.detail and "Spanish (es) 1" in notice.detail
    assert "still analysed" in notice.detail
    assert "not been changed" in notice.detail


def test_a_clean_summary_does_not_warn_and_a_legacy_one_says_not_assessed() -> None:
    clean = describe_summary(
        summarize_languages([_assessments()[0], _assessments()[1]])
    )
    legacy = describe_summary(summarize_languages([LanguageAssessment.not_assessed()]))

    assert clean is not None and not clean.warns
    assert legacy is not None and not legacy.warns
    assert "not assessed" in legacy.headline.lower()
    assert describe_summary(summarize_languages([])) is None
