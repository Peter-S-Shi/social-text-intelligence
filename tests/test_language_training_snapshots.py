"""Moderation and triage snapshots freeze model evidence, so they freeze its caveat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from persistence.language_samples import KeywordDetector

from social_text_intelligence.contracts import (
    CaseDifficulty,
    LearningObjective,
    TicketComplexity,
)
from social_text_intelligence.contracts.triage import TriageMode
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import (
    AnalysisService,
    analyze_batch,
    inspect_csv_upload,
    prepare_csv_batch,
)
from social_text_intelligence.services.batch import BatchResult
from social_text_intelligence.services.insights import InsightState
from social_text_intelligence.services.moderation_training import (
    ModerationLimits,
    ModerationWorkspace,
    prepare_workspace_case,
)
from social_text_intelligence.services.review import create_review_state
from social_text_intelligence.services.support_triage import (
    TriageLimits,
    TriageWorkspace,
    prepare_workspace_ticket,
)
from social_text_intelligence.services.triage_resources import load_triage_guide

CSV = (
    b"record_id,text,language\n"
    b"fr-row,bonjour tout le monde merci,en\n"
    b"en-row,Everything arrived on time.,fr\n"
    b"none-row,Everything arrived on time.,\n"
)


def batch() -> BatchResult:
    preview = prepare_csv_batch(
        inspect_csv_upload(CSV, max_bytes=10_000),
        text_column="text",
        max_rows=10,
        max_text_length=200,
    )
    analyzer = AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(),
        emotion_provider=DeterministicEmotionProvider(),
        language_detector=KeywordDetector(),
    )
    return analyze_batch(preview, analyzer)


def moderation_snapshot(record_id: str) -> Any:
    result = batch()
    workspace = prepare_workspace_case(
        ModerationWorkspace(),
        result,
        create_review_state(result),
        InsightState(),
        record_id=record_id,
        excerpt="",
        difficulty=CaseDifficulty.BEGINNER,
        learning_objective=next(iter(LearningObjective)),
        reference=None,
        mock_recommendation=None,
        policy_id="p",
        policy_version="1",
        valid_policy_clause_ids=(),
        limits=ModerationLimits(),
    )
    return workspace.prepared_cases[0].source_snapshot


def triage_snapshot(record_id: str) -> Any:
    result = batch()
    guide = load_triage_guide()
    workspace = prepare_workspace_ticket(
        TriageWorkspace(
            mode=TriageMode.INDEPENDENT,
            source_batch_token=None,
            entries=(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        result,
        create_review_state(result),
        InsightState(),
        record_id=record_id,
        excerpt="",
        complexity=TicketComplexity.BASIC,
        guide=guide,
        applicable_rule_ids=(guide.rule_ids[0],),
        mock_suggestion=None,
        limits=TriageLimits(),
    )
    return workspace.entries[0].ticket.source_snapshot


def test_a_moderation_snapshot_keeps_the_language_evidence_with_the_ai_signals() -> (
    None
):
    snapshot = moderation_snapshot("fr-row")

    assert snapshot.language_signal.startswith("unsupported|fr|")
    assert "French (fr)" in snapshot.language_caveat
    assert snapshot.sentiment is not None  # the AI signals themselves are unchanged


def test_a_supported_snapshot_carries_the_evidence_but_no_caveat() -> None:
    snapshot = moderation_snapshot("en-row")

    assert snapshot.language_signal.startswith("supported|en|")
    assert snapshot.language_caveat == ""


def test_snapshot_metadata_language_is_the_supplied_value_exactly() -> None:
    supplied = dict(moderation_snapshot("en-row").trusted_metadata)["language"]
    none = dict(moderation_snapshot("none-row").trusted_metadata)["language"]
    elsewhere = dict(moderation_snapshot("fr-row").trusted_metadata)["language"]

    assert (supplied, none, elsewhere) == ("fr", "", "en")


def test_a_triage_snapshot_keeps_the_language_evidence_too() -> None:
    snapshot = triage_snapshot("fr-row")

    assert snapshot.language_signal.startswith("unsupported | fr | ")
    assert "French (fr)" in snapshot.language_caveat
    assert dict(snapshot.trusted_metadata)["language"] == "en"  # as supplied


def test_a_record_with_no_check_has_an_honest_signal_not_an_empty_one() -> None:
    from dataclasses import replace

    from social_text_intelligence.contracts import LanguageAssessment

    result = batch()
    first = result.outcomes[0]
    assert first.report is not None
    legacy = replace(
        first, report=replace(first.report, language=LanguageAssessment.not_assessed())
    )
    result = replace(result, outcomes=(legacy, *result.outcomes[1:]))
    workspace = prepare_workspace_case(
        ModerationWorkspace(),
        result,
        create_review_state(result),
        InsightState(),
        record_id="fr-row",
        excerpt="",
        difficulty=CaseDifficulty.BEGINNER,
        learning_objective=next(iter(LearningObjective)),
        reference=None,
        mock_recommendation=None,
        policy_id="p",
        policy_version="1",
        valid_policy_clause_ids=(),
        limits=ModerationLimits(),
    )

    snapshot = workspace.prepared_cases[0].source_snapshot

    assert snapshot is not None
    assert snapshot.language_signal.startswith("not_assessed||")
    assert snapshot.language_caveat == ""  # legacy: nothing assumed, no warning
