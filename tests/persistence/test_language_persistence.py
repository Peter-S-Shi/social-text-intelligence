"""Detected-language evidence is stored with the immutable analysis result."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from social_text_intelligence.application.project_workflow import (
    AnalysisRun,
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import ReviewWorkflow
from social_text_intelligence.contracts import (
    AnalysisReport,
    LanguageAssessment,
    LanguageReason,
    LanguageStatus,
    NormalizedTextInput,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .language_samples import (
    INFO,
    LanguageGateway,
    mixed_language_csv,
    strip_language_evidence,
)
from .workflow_samples import ScriptedGateway

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def analysed(root: Path, gateway: Any = None) -> str:
    flow = ProjectWorkflow(repository(root), gateway or LanguageGateway(), LIMITS)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id
    assert flow.analyze(project_id) is AnalysisRun.COMMITTED
    return project_id


def report_of(root: Path, project_id: str, row: int) -> AnalysisReport:
    record = ReviewWorkflow(repository(root)).open_review(project_id, row=row).record
    assert record is not None
    return record.report


def test_detected_language_survives_a_restart_beside_the_supplied_language(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    r2 = report_of(tmp_path, project_id, 2)  # a fresh repository: a restart
    r3 = report_of(tmp_path, project_id, 3)
    r4 = report_of(tmp_path, project_id, 4)
    r5 = report_of(tmp_path, project_id, 5)

    assert (r2.record.language, r2.language.status, r2.language.detected_language) == (
        "en",
        LanguageStatus.UNSUPPORTED,
        "fr",
    )
    assert (r3.record.language, r3.language.status, r3.language.detected_language) == (
        "fr",
        LanguageStatus.SUPPORTED,
        "en",
    )
    assert r4.record.language is None  # nothing supplied is not "en"
    assert r4.language.status is LanguageStatus.UNSUPPORTED
    assert r5.language.status is LanguageStatus.UNDETERMINED
    assert r5.language.reason is LanguageReason.LOW_SCORE
    assert r2.language.score == 0.97 and r2.language.detector == INFO
    assert r2.language.supported_languages == ("en",)


def test_every_assessment_state_round_trips_exactly(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    live = LanguageGateway()
    texts = [
        "Everything arrived on time.",
        "bonjour tout le monde merci",
        "Everything arrived on time.",
        "bonjour encore une fois",
        "ok",
    ]

    stored = [report_of(tmp_path, project_id, row).language for row in range(1, 6)]
    expected = [
        live.analyze(NormalizedTextInput.from_text(text, record_id=f"x{n}")).language
        for n, text in enumerate(texts)
    ]

    assert stored == expected


def test_a_project_analysed_before_language_checks_opens_as_not_assessed(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path, ScriptedGateway())
    strip_language_evidence(tmp_path)  # the exact pre-M5.6 stored shape

    legacy = report_of(tmp_path, project_id, 2)

    assert legacy.language == LanguageAssessment.not_assessed()
    assert legacy.language.reason is LanguageReason.NOT_RUN
    assert legacy.language.detected_language is None  # never invented as English
    assert not legacy.language.needs_attention
    assert legacy.sentiment.label is not None  # the AI record is untouched


def test_opening_a_project_never_runs_the_detector(tmp_path: Path) -> None:
    gateway = LanguageGateway()
    project_id = analysed(tmp_path, gateway)
    calls = gateway.calls

    ReviewWorkflow(repository(tmp_path)).open_review(project_id, row=1)
    ProjectWorkflow(repository(tmp_path), gateway, LIMITS).open_project(project_id)

    assert gateway.calls == calls  # reading is never re-analysing


def test_a_cancelled_analysis_commits_no_language_evidence(tmp_path: Path) -> None:
    gateway = LanguageGateway()
    flow = ProjectWorkflow(repository(tmp_path), gateway, LIMITS)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id

    run = flow.analyze(project_id, cancelled=lambda: gateway.calls >= 3)

    assert run is AnalysisRun.CANCELLED
    stored = repository(tmp_path).get(project_id)
    assert stored is not None and stored.result is None  # nothing partial


def test_a_failed_row_leaves_its_siblings_language_evidence_intact(
    tmp_path: Path,
) -> None:
    def fail_on_third(call: int) -> None:
        if call == 3:
            raise RuntimeError("a row-level failure")

    flow = ProjectWorkflow(
        repository(tmp_path), LanguageGateway(before_row=fail_on_third), LIMITS
    )
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id

    flow.analyze(project_id)  # a row failure is a row result, not a lost project

    stored = repository(tmp_path).get(project_id)
    assert stored is not None and stored.result is not None
    failed = [o for o in stored.result.outcomes if o.report is None]
    assert [o.prepared.row_number for o in failed] == [3]
    statuses = {
        o.prepared.identity: o.report.language.status
        for o in stored.result.outcomes
        if o.report is not None
    }
    assert statuses == {
        "r1": LanguageStatus.SUPPORTED,
        "r2": LanguageStatus.UNSUPPORTED,
        "r4": LanguageStatus.UNSUPPORTED,
        "r5": LanguageStatus.UNDETERMINED,
    }


def test_the_project_summary_counts_the_language_states(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    summary = ProjectWorkflow(
        repository(tmp_path), LanguageGateway(), LIMITS
    ).open_project(project_id).language

    assert summary is not None
    assert (summary.total, summary.supported, summary.unsupported) == (5, 2, 2)
    assert (summary.undetermined, summary.unavailable) == (1, 0)
    assert summary.not_assessed == 0
    assert summary.unsupported_languages == (("fr", 2),)


def test_a_project_not_yet_analysed_has_no_language_summary(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), LanguageGateway(), LIMITS)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id

    assert flow.open_project(project_id).language is None


def test_a_review_record_names_the_supplied_language_exactly_as_the_file_gave_it(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = ReviewWorkflow(repository(tmp_path))

    def supplied(row: int) -> str | None:
        record = flow.open_review(project_id, row=row).record
        assert record is not None
        return record.supplied_language

    assert [supplied(row) for row in range(1, 6)] == ["en", "en", "fr", None, "en"]
