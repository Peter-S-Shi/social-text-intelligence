"""Language detection inside the shared analysis path (deterministic fakes)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from social_text_intelligence.contracts import (
    Detection,
    DetectorInfo,
    LanguageAssessment,
    LanguageDetectorUnavailable,
    LanguageReason,
    LanguageStatus,
    NormalizedTextInput,
    ProviderMetadata,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService

INFO = DetectorInfo(name="fake", version="1.0", model="fake-model", min_score=0.5)


class FakeDetector:
    info = INFO

    def __init__(self, language: str | None = "en", *, fail: Exception | None = None):
        self.language = language
        self.fail = fail
        self.seen: list[str] = []

    def detect(self, text: str) -> Detection:
        self.seen.append(text)
        if self.fail is not None:
            raise self.fail
        if self.language is None:
            return Detection(language=None, reason=LanguageReason.LOW_SCORE)
        return Detection(language=self.language, score=0.9)


def service(detector: FakeDetector | None) -> AnalysisService:
    return AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(),
        emotion_provider=DeterministicEmotionProvider(),
        language_detector=detector,
    )


def record(
    text: str = "A synthetic sentence.", *, language: str | None = None
) -> NormalizedTextInput:
    return NormalizedTextInput.from_text(text, record_id="r1", language=language)


def test_a_report_carries_the_detected_language_beside_the_ai_results() -> None:
    report = service(FakeDetector("fr")).analyze(record(language="en"))

    assert report.language.status is LanguageStatus.UNSUPPORTED
    assert report.language.detected_language == "fr"
    assert report.language.supported_languages == ("en",)
    assert report.language.detector == INFO


def test_supplied_english_and_detected_french_coexist_and_warn() -> None:
    report = service(FakeDetector("fr")).analyze(record(language="en"))

    assert report.record.language == "en"  # exactly as supplied, never overwritten
    assert report.language.detected_language == "fr"
    assert report.language.needs_attention
    assert report.sentiment.label is not None  # the text is still analysed


def test_supplied_non_english_and_detected_english_is_analysed_without_a_warning() -> (
    None
):
    report = service(FakeDetector("en")).analyze(record(language="fr"))

    assert report.record.language == "fr"  # supplied value untouched
    assert report.language.status is LanguageStatus.SUPPORTED
    assert not report.language.needs_attention


def test_the_detector_sees_only_the_text() -> None:
    detector = FakeDetector("en")

    service(detector).analyze(record("Only these words.", language="de"))

    assert detector.seen == ["Only these words."]


def test_no_detector_means_not_assessed_not_english() -> None:
    report = service(None).analyze(record())

    assert report.language == LanguageAssessment.not_assessed(
        supported_languages=("en",)
    )


def test_an_undetermined_text_is_analysed_and_flagged() -> None:
    report = service(FakeDetector(None)).analyze(record("ok"))

    assert report.language.status is LanguageStatus.UNDETERMINED
    assert report.language.needs_attention


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (LanguageDetectorUnavailable(), LanguageReason.DETECTOR_UNAVAILABLE),
        (RuntimeError("contains the text"), LanguageReason.DETECTOR_FAILED),
    ],
)
def test_a_detector_problem_never_stops_analysis_or_implies_support(
    failure: Exception, reason: LanguageReason
) -> None:
    report = service(FakeDetector(fail=failure)).analyze(record())

    assert report.language.status is LanguageStatus.NOT_ASSESSED
    assert report.language.reason is reason
    assert report.sentiment.record_id == "r1"


def test_models_must_both_support_a_language_for_it_to_count() -> None:
    sentiment = DeterministicSentimentProvider(
        metadata=ProviderMetadata(
            provider="p",
            model_name="m",
            revision="r",
            task=DeterministicSentimentProvider().metadata.task,
            supported_languages=("en", "fr"),
            native_labels=("positive", "negative", "neutral"),
        )
    )
    both = AnalysisService(
        sentiment_provider=sentiment,
        emotion_provider=DeterministicEmotionProvider(),
        language_detector=FakeDetector("fr"),
    )

    report = both.analyze(record())

    assert report.language.status is LanguageStatus.UNSUPPORTED  # emotion is English
    assert report.language.supported_languages == ("en",)


def test_supplied_language_is_not_passed_to_the_models() -> None:
    seen: list[str | None] = []

    class Spy(DeterministicSentimentProvider):
        def analyze(self, record: NormalizedTextInput):  # type: ignore[no-untyped-def]
            seen.append(record.language)
            return super().analyze(record)

    AnalysisService(
        sentiment_provider=Spy(),
        emotion_provider=DeterministicEmotionProvider(),
    ).analyze(record(language="fr"))

    assert seen == [None]


def test_the_assessment_equals_the_policy_applied_to_the_same_text() -> None:
    a = service(FakeDetector("en")).analyze(record("Same text"))
    b = service(FakeDetector("en")).analyze(replace(record("Same text"), language="zz"))

    assert a.language == b.language  # supplied metadata cannot move the evidence
