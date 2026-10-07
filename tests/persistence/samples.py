"""Synthetic workspaces for persistence tests; no real or private data."""

from __future__ import annotations

from dataclasses import replace
from functools import cache

from social_text_intelligence.application.projects import (
    BatchWorkspace,
    InMemoryProjectRepository,
)
from social_text_intelligence.application.use_cases import ApplicationUseCases
from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    EmotionScore,
    NativeScore,
    NormalizedTextInput,
    SentimentLabel,
    SentimentScore,
)
from social_text_intelligence.contracts.errors import ProviderError
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService
from social_text_intelligence.services.batch import (
    BatchPreview,
    PendingBatchUpload,
    inspect_csv_upload,
    prepare_csv_batch,
)

# Distinctive strings that must never leak into logs or error messages.
TEXT_SENTINEL = "zq-sentinel-body-4711"
NOTE_SENTINEL = "zq-sentinel-note-4712"
NAME_SENTINEL = "zq-sentinel-name-4713"
CSV_SENTINEL = "zq-sentinel-csv-4714"

RICH_CSV = (
    "record_id,text,source_type,source_label,language,timestamp,topic,"
    "community,parent_record_id,notes,extra_column\n"
    f"case-1,{TEXT_SENTINEL} Thanks for the quick help!,platform,"
    "Support desk,en,2026-01-02T03:04:05Z,shipping,north,,first note,kept?\n"
    "case-2,A second synthetic message with unicode café.,direct,,en,"
    "2026-01-03T10:00:00+05:30,billing,south,case-1,,\n"
    "case-3,Naive timestamp synthetic row.,file,,en,2026-02-01T08:30:00,"
    "shipping,north,,,\n"
    "case-4,Row with a bad timestamp.,file,,en,not-a-date,billing,south,,,\n"
    "dup,Duplicate id one.,file,,en,,billing,south,,,\n"
    "dup,Duplicate id two.,file,,en,,billing,south,,,\n"
    "case-7,This message makes the gateway fail.,file,,en,,shipping,north,,,\n"
    "case-8,Another good synthetic row.,file,,en,2026-02-05T00:00:00Z,"
    "billing,south,,,\n"
)


class SyntheticGateway:
    """Deterministic analysis with awkward float values and one failing row."""

    initialized = True

    def __init__(self) -> None:
        self._service = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(SentimentLabel.POSITIVE),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if "makes the gateway fail" in record.text:
            raise ProviderError(
                provider="synthetic", code="synthetic_failure", message="Row failed."
            )
        report = self._service.analyze(record)
        sentiment = replace(
            report.sentiment,
            confidence=0.7000000000000001,
            scores=(
                SentimentScore(SentimentLabel.POSITIVE, 0.7000000000000001),
                SentimentScore(SentimentLabel.NEGATIVE, 0.1 + 0.2),
                SentimentScore(SentimentLabel.NEUTRAL, 1 / 3),
            ),
        )
        emotion_scores = tuple(
            EmotionScore(
                item.label,
                0.8123456789012345
                if item.score == 0.8
                else 0.6000000000000001
                if item.score == 0.6
                else 0.1 + 0.2,
            )
            for item in report.emotion.scores
        )
        emotion = replace(
            report.emotion,
            confidence=0.8123456789012345,
            scores=emotion_scores,
            native_scores=tuple(
                NativeScore(item.label, 5e-324 if index == 0 else item.score)
                for index, item in enumerate(report.emotion.native_scores)
            ),
        )
        return AnalysisReport(
            record=report.record, sentiment=sentiment, emotion=emotion
        )


def one_row_preview() -> BatchPreview:
    pending = inspect_csv_upload(b"text\nA synthetic example.\n", max_bytes=1000)
    return prepare_csv_batch(
        pending, text_column="text", max_rows=10, max_text_length=100
    )


def pending_upload() -> PendingBatchUpload:
    return inspect_csv_upload(
        f"message,topic\n{CSV_SENTINEL} hello,shipping\n".encode(), max_bytes=1000
    )


@cache
def rich_workspace() -> BatchWorkspace:
    """A fully worked workspace (frozen values, built once per test session)."""

    use_cases = ApplicationUseCases(InMemoryProjectRepository(), SyntheticGateway())
    repository = use_cases.projects
    token = use_cases.upload_batch(
        RICH_CSV.encode(), max_bytes=100_000, max_rows=50, max_text_length=500
    )
    assert use_cases.analyze_workspace(token) is True
    common = {
        "review_filter": "all",
        "sentiment_filter": "all",
        "emotion_filter": "all",
    }
    use_cases.save_review(
        token,
        1,
        action="save",
        values={
            "sentiment_judgment": "correct",
            "human_sentiment": "negative",
            "emotion_judgment": "correct",
            "human_dominant_emotion": "anger",
            "review_note": f"Human note {NOTE_SENTINEL}",
        },
        secondary_emotions=("sadness", "fear"),
        **common,
    )
    use_cases.save_review(
        token, 2, action="accept_both", values={}, secondary_emotions=(), **common
    )
    use_cases.save_review(
        token,
        3,
        action="save",
        values={
            "sentiment_judgment": "uncertain",
            "emotion_judgment": "uncertain",
        },
        secondary_emotions=(),
        **common,
    )
    use_cases.add_note(
        token,
        {
            "association": "topic",
            "association_value": "shipping",
            "phrase": "late",
            "explanation": f"Explains delays {NOTE_SENTINEL}",
            "context_importance": "Affects tone",
        },
        ("sarcasm_possible", "idiom_or_slang"),
    )
    workspace = repository.get(token)
    assert workspace is not None
    view = use_cases.resolve_insights(
        token, workspace, {"grouping": "topic"}, (), (), comparison=False
    )
    assert view is not None
    final = repository.get(token)
    assert final is not None
    assert final.result is not None and final.reviews is not None
    assert final.insights is not None and final.insights.selection is not None
    assert final.insights.notes
    return final
