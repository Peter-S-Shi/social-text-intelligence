"""The owner-trial scenario CSV keeps importing the way its walkthrough says."""

from __future__ import annotations

from pathlib import Path

from persistence.workflow_samples import ScriptedGateway

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

SCENARIO = Path(__file__).resolve().parents[1] / "manual-qa" / "owner-trial"
LIMITS = CsvLimits(max_bytes=2 * 1024 * 1024, max_rows=500, max_text_length=20_000)


def test_the_scenario_csv_imports_with_the_counts_the_walkthrough_states(
    tmp_path: Path,
) -> None:
    flow = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(tmp_path)), ScriptedGateway(), LIMITS
    )

    details = flow.import_csv((SCENARIO / "scenario.csv").read_bytes(), name="Trial")

    assert (details.row_count, details.valid_rows, details.invalid_rows) == (29, 26, 3)
    assert {"record_id", "source_label", "topic", "timestamp"} <= set(details.headers)


def test_the_walkthrough_states_the_counts_and_owner_overall_decision() -> None:
    walkthrough = (SCENARIO / "WALKTHROUGH.md").read_text(encoding="utf-8")
    log = (SCENARIO / "FRICTION_LOG.md").read_text(encoding="utf-8")

    assert "owner completed and approved the exploratory trial overall" in walkthrough
    assert "No item-level observations or friction entries were supplied" in log
    assert "empty log does not mean zero friction" in log
    assert "29 rows, 26 ready, 3 rejected" in walkthrough
    assert "Analyze 26 rows" in walkthrough
