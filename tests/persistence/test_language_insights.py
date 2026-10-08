"""Insights keeps grouping by the supplied language; detection never leaks into it."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from social_text_intelligence.application.insights_workflow import (
    InsightControls,
    InsightsWorkflow,
)
from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.insights import (
    GroupingDimension,
    InsightMetric,
    InsightPerspective,
)

from .language_samples import LanguageGateway, mixed_language_csv

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def analysed(root: Path) -> str:
    flow = ProjectWorkflow(repository(root), LanguageGateway(), LIMITS)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id
    flow.analyze(project_id)
    return project_id


def by_language(root: Path, project_id: str, *groups: str):  # type: ignore[no-untyped-def]
    return InsightsWorkflow(repository(root)).apply(
        project_id,
        InsightControls(
            grouping=GroupingDimension.LANGUAGE,
            groups=groups,
            perspective=InsightPerspective.AI,
            metric=InsightMetric.AI_SENTIMENT,
        ),
    )


def test_the_language_grouping_is_the_supplied_value_not_the_detected_one(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = by_language(tmp_path, project_id, "en")

    assert set(snapshot.groups_for(GroupingDimension.LANGUAGE)) == {
        "(not supplied)",
        "en",
        "fr",
    }
    (en,) = snapshot.summaries
    assert en.total_count == 3  # r1, r2 (French text!) and r5 all *supplied* en
    assert en.successful_count == 3
    assert "French" not in snapshot.metric_definition


def test_a_row_supplying_french_stays_in_french_even_when_the_text_is_english(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    (fr,) = by_language(tmp_path, project_id, "fr").summaries

    assert fr.total_count == 1  # r3: supplied fr, detected en


def test_a_missing_language_is_not_supplied_never_english(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    (missing,) = by_language(tmp_path, project_id, "(not supplied)").summaries

    assert missing.total_count == 1  # r4


def test_an_old_projects_invented_english_is_regrouped_as_not_supplied(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    (path,) = (tmp_path / "projects").glob("*")
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TRIGGER prepared_row_is_immutable")
        payload = connection.execute(
            "SELECT record_json FROM prepared_row WHERE identity = 'r4'"
        ).fetchone()[0]
        data = json.loads(payload)
        data["language"] = "en"  # what an older import stored for an empty column
        connection.execute(
            "UPDATE prepared_row SET record_json = ? WHERE identity = 'r4'",
            (json.dumps(data),),
        )
        connection.commit()
    finally:
        connection.close()

    snapshot = by_language(tmp_path, project_id, "en")

    (en,) = snapshot.summaries
    assert en.total_count == 3  # the invented "en" is not counted as supplied
    assert "(not supplied)" in snapshot.groups_for(GroupingDimension.LANGUAGE)


def test_a_group_counts_the_analysed_texts_not_confirmed_as_supported(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    (en,) = by_language(tmp_path, project_id, "en").summaries

    # r1 English, r2 French and r5 too short: two of the three need a caveat
    assert (en.language_attention_count, en.filtered_successful_count) == (2, 3)


def test_the_snapshot_summarises_the_language_check_over_every_analysed_text(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = by_language(tmp_path, project_id, "fr")

    assert snapshot.language.total == 5
    assert (snapshot.language.supported, snapshot.language.unsupported) == (2, 2)
    assert snapshot.language.undetermined == 1


def test_the_language_count_never_changes_the_metric_or_its_denominator(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    (en,) = by_language(tmp_path, project_id, "en").summaries

    assert en.eligible_count == 3  # every analysed text still counts, unchanged
    assert sum(v.count for v in en.values) == 3


def test_a_representative_case_carries_its_language_assessment(
    tmp_path: Path,
) -> None:
    from social_text_intelligence.application.insights_workflow import (
        ExampleControls,
        ExampleMode,
    )

    project_id = analysed(tmp_path)
    flow = InsightsWorkflow(repository(tmp_path))

    snapshot = flow.open_insights(
        project_id,
        examples=ExampleControls(mode=ExampleMode.LOWEST_AI_CONFIDENCE),
    )

    languages = {
        e.outcome.prepared.identity: e.outcome.report.language.status.value
        for e in snapshot.examples
        if e.outcome.report is not None
    }
    assert languages["r2"] == "unsupported"
