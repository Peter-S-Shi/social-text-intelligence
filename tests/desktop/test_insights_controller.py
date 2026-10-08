"""The Qt-free insights controller over a real SQLite project (synthetic data)."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import pytest
from persistence.insight_samples import SENTINEL, VariedGateway, insights_csv

from social_text_intelligence.application.insights_workflow import (
    ContextAssociation,
    ContextTag,
    ExampleControls,
    ExampleMode,
    GroupingDimension,
    InsightMetric,
    InsightPerspective,
    InsightsWorkflow,
    NoteDraft,
)
from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.desktop.insights import (
    InsightsActivity,
    InsightsController,
    InsightsState,
)
from social_text_intelligence.desktop.projects import NoticeKind
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner, ManualRunner

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


class Env:
    def __init__(self, root: Path) -> None:
        self.root = root
        repository = SqliteProjectRepository(AppDataLocations(root))
        flow = ProjectWorkflow(repository, VariedGateway(), LIMITS)
        self.project_id = flow.import_csv(insights_csv(), name="P").summary.project_id
        flow.analyze(self.project_id)
        self.written: dict[Path, str] = {}

    def workflow(self) -> InsightsWorkflow:
        return InsightsWorkflow(SqliteProjectRepository(AppDataLocations(self.root)))

    def write(self, path: Path, text: str) -> None:
        self.written[path] = text

    def controller(
        self, runner: Any = None, workflow: Any = None
    ) -> InsightsController:
        return InsightsController(
            workflow or self.workflow(),
            runner or ImmediateRunner(),
            write_file=self.write,
        )


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def opened(env: Env, **kwargs: Any) -> InsightsController:
    controller = env.controller(**kwargs)
    assert controller.open(env.project_id)
    return controller


def snap(state: InsightsState) -> Any:
    assert state.snapshot is not None
    return state.snapshot


def note(**changes: object) -> NoteDraft:
    base: dict[str, object] = {
        "association": ContextAssociation.TOPIC,
        "association_value": "shipping",
        "phrase": "running late",
        "explanation": "A common phrase here.",
        "context_importance": "It may mean delay, not anger.",
    }
    return NoteDraft(**{**base, **changes})  # type: ignore[arg-type]


def test_opening_loads_the_saved_view_off_the_caller_until_pumped(env: Env) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)

    assert controller.open(env.project_id) is True

    assert controller.state.activity is InsightsActivity.LOADING
    assert controller.state.busy and controller.state.snapshot is None
    assert controller.open(env.project_id) is False  # one operation at a time
    runner.run_next()
    state = controller.state
    assert state.activity is InsightsActivity.IDLE and state.is_open
    assert state.controls is not None
    assert state.controls.grouping is GroupingDimension.TOPIC
    assert state.controls.groups == ("billing",)
    assert state.controls.comparison is False
    assert state.has_unsaved_changes is False


def test_choosing_a_grouping_offers_its_groups_and_a_compatible_metric(
    env: Env,
) -> None:
    controller = opened(env)

    controller.set_grouping(GroupingDimension.COMMUNITY)
    controller.set_perspective(InsightPerspective.HUMAN)

    controls = controller.state.controls
    assert controls is not None
    assert controls.grouping is GroupingDimension.COMMUNITY
    assert controls.groups == ("north",)  # the first group of the new grouping
    assert controls.perspective is InsightPerspective.HUMAN
    assert controls.metric is InsightMetric.HUMAN_SENTIMENT  # first human metric
    assert snap(controller.state).selection.grouping is GroupingDimension.TOPIC
    # nothing is applied or saved until Apply
    assert env.workflow().open_insights(env.project_id).selection.groups == ("billing",)


def test_applying_runs_the_view_and_saves_it(env: Env) -> None:
    controller = opened(env)
    controller.set_grouping(GroupingDimension.TOPIC)
    controller.set_groups(("shipping",))
    controller.set_filters(metric=InsightMetric.AI_DOMINANT_EMOTION)

    assert controller.apply() is True

    state = controller.state
    (summary,) = snap(state).summaries
    assert summary.group == "shipping"
    assert snap(state).selection.metric is InsightMetric.AI_DOMINANT_EMOTION
    assert env.workflow().open_insights(env.project_id).selection.groups == (
        "shipping",
    )


def test_a_comparison_needs_two_groups_and_keeps_the_view_when_refused(
    env: Env,
) -> None:
    controller = opened(env)
    controller.set_comparison(True)
    controller.set_groups(("shipping",))

    controller.apply()

    state = controller.state
    assert state.notice is not None and state.notice.kind is NoticeKind.ERROR
    assert state.notice.code == "comparison_group_count"
    assert snap(state).comparison is False  # the shown view is unchanged
    assert state.controls is not None and state.controls.comparison is True
    controller.set_groups(("shipping", "billing"))
    controller.apply()
    assert [s.group for s in snap(controller.state).summaries] == [
        "shipping",
        "billing",
    ]
    assert snap(controller.state).comparison is True
    assert controller.state.notice is None


def test_a_bad_date_is_refused_with_its_field_and_nothing_changes(env: Env) -> None:
    controller = opened(env)
    controller.set_filters(date_from="02/03/2026")

    controller.apply()

    notice = controller.state.notice
    assert notice is not None and notice.field == "date_from"
    assert notice.code == "invalid_date"
    assert (
        env.workflow().open_insights(env.project_id).selection.filters.date_from is None
    )


def test_changing_the_example_rule_reselects_cases_without_changing_the_view(
    env: Env,
) -> None:
    controller = opened(env)
    controller.set_comparison(True)
    controller.set_groups(("billing", "shipping"))
    controller.apply()

    controller.set_examples(ExampleControls(mode=ExampleMode.HIGHEST_AI_SCORE))
    assert controller.select_cases() is True

    state = controller.state
    assert snap(state).example_mode is ExampleMode.HIGHEST_AI_SCORE
    assert snap(state).example_emotion.value == "anger"
    assert snap(state).comparison is True
    assert [s.group for s in snap(state).summaries] == ["billing", "shipping"]


def test_adding_a_note_saves_it_clears_the_draft_and_refreshes_the_cases(
    env: Env,
) -> None:
    controller = opened(env)
    controller.set_examples(ExampleControls(mode=ExampleMode.CONTEXT_NOTES))
    controller.select_cases()
    controller.set_note_draft(
        note(association=ContextAssociation.RECORD, association_value="r7")
    )
    assert controller.state.has_unsaved_changes

    assert controller.add_note() is True

    state = controller.state
    assert [n.phrase for n in snap(state).notes] == ["running late"]
    assert state.note_draft == NoteDraft()
    assert state.has_unsaved_changes is False
    assert state.notice is not None and state.notice.code == "note_added"
    assert [e.outcome.prepared.row_number for e in snap(state).examples] == [7]


def test_an_invalid_note_shows_the_field_message_and_keeps_the_draft(env: Env) -> None:
    controller = opened(env)
    draft = note(phrase="  ")
    controller.set_note_draft(draft)

    controller.add_note()

    state = controller.state
    assert state.notice is not None and state.notice.field == "phrase"
    assert state.notice.code == "required"
    assert state.note_draft == draft and state.has_unsaved_changes  # nothing lost
    assert snap(state).notes == ()


def test_removing_a_note_removes_it_and_a_stale_removal_is_explained(env: Env) -> None:
    controller = opened(env)
    controller.set_note_draft(note())
    controller.add_note()
    (stored,) = snap(controller.state).notes
    env.workflow().remove_note(env.project_id, stored.note_id)  # gone elsewhere

    controller.remove_note(stored.note_id)

    state = controller.state
    assert state.notice is not None and state.notice.code == "note_not_found"
    assert snap(state).notes == ()  # the list now matches what is stored


def test_discarding_the_note_draft_keeps_the_view(env: Env) -> None:
    controller = opened(env)
    controller.set_note_draft(note())
    assert controller.state.has_unsaved_changes

    controller.discard_changes()

    assert controller.state.note_draft == NoteDraft()
    assert controller.state.has_unsaved_changes is False
    assert controller.state.is_open


def test_export_writes_only_when_asked_and_follows_the_options(env: Env) -> None:
    controller = opened(env)
    controller.set_groups(("shipping",))
    controller.apply()
    target = env.root / "out" / "insights.csv"
    assert env.written == {}  # viewing never exports

    assert controller.export(target, include_records=True, include_native=True) is True

    text = env.written[target]
    sections = {r["section"] for r in csv.DictReader(io.StringIO(text))}
    assert "supporting_record" in sections and "group_summary" in sections
    notice = controller.state.notice
    assert notice is not None and notice.code == "export_saved"
    assert str(env.root) not in notice.body and SENTINEL not in notice.body


def test_a_failed_write_gives_a_fixed_message_and_changes_nothing(env: Env) -> None:
    def failing(path: Path, text: str) -> None:
        raise PermissionError(f"{path} {SENTINEL}")

    controller = InsightsController(
        env.workflow(), ImmediateRunner(), write_file=failing
    )
    controller.open(env.project_id)
    controller.set_note_draft(note())
    controller.add_note()

    controller.export(env.root / "x.csv", include_records=False, include_native=False)

    notice = controller.state.notice
    assert notice is not None and notice.code == "export_failed"
    assert SENTINEL not in notice.body and str(env.root) not in notice.body
    assert [n.phrase for n in snap(controller.state).notes] == ["running late"]


def test_storage_and_unexpected_errors_are_fixed_messages(env: Env) -> None:
    class Broken(InsightsWorkflow):
        def apply(self, *args: Any, **kwargs: Any) -> Any:
            raise ProjectStorageError(
                code="storage_failed", message="The project could not be read."
            )

        def add_note(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"/secret/path {SENTINEL}")

    repository = SqliteProjectRepository(AppDataLocations(env.root))
    controller = env.controller(workflow=Broken(repository))
    controller.open(env.project_id)
    controller.set_note_draft(note(phrase=f"note {SENTINEL}"))

    controller.apply()
    first = controller.state.notice
    controller.add_note()
    second = controller.state.notice

    assert first is not None and first.kind is NoticeKind.ERROR
    assert second is not None and second.code == "unexpected_error"
    assert SENTINEL not in first.body + second.body + second.title
    assert "secret" not in second.body
    assert controller.state.has_unsaved_changes  # the person's note is still there


def test_a_project_removed_elsewhere_closes_the_insights_with_a_notice(
    env: Env,
) -> None:
    controller = opened(env)
    ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(env.root)), VariedGateway(), LIMITS
    ).delete_project(env.project_id)

    controller.apply()

    state = controller.state
    assert state.is_open is False and state.active is False
    assert state.notice is not None and state.notice.code == "project_not_found"


def test_closing_is_refused_while_busy_and_discards_the_draft(env: Env) -> None:
    runner = ManualRunner()
    controller = env.controller(runner)
    controller.open(env.project_id)
    runner.run_next()
    controller.set_note_draft(note())
    controller.add_note()  # queued

    assert controller.close() is False
    runner.run_next()
    assert controller.close() is True

    assert controller.state.is_open is False
    assert controller.state.note_draft == NoteDraft()


def test_the_view_and_notes_are_durable_across_a_fresh_controller(env: Env) -> None:
    controller = opened(env)
    controller.set_groups(("shipping",))
    controller.apply()
    controller.set_note_draft(note(tags=(ContextTag.MIXED_STANCE,)))
    controller.add_note()

    fresh = env.controller()
    fresh.open(env.project_id)

    assert fresh.state.controls is not None
    assert fresh.state.controls.groups == ("shipping",)
    assert [n.phrase for n in snap(fresh.state).notes] == ["running late"]


class FailingRefresh(InsightsWorkflow):
    """Opens once, then cannot refresh: the write has already happened."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.opened = 0

    def open_insights(self, *args: Any, **kwargs: Any) -> Any:
        self.opened += 1
        if self.opened > 1:
            raise ProjectStorageError(
                code="storage_failed", message="The project could not be read."
            )
        return super().open_insights(*args, **kwargs)


def test_a_note_saved_before_a_failed_refresh_is_not_kept_as_a_draft(env: Env) -> None:
    repository = SqliteProjectRepository(AppDataLocations(env.root))
    controller = env.controller(workflow=FailingRefresh(repository))
    controller.open(env.project_id)
    controller.set_note_draft(note())

    controller.add_note()

    state = controller.state
    assert state.note_draft == NoteDraft()  # it is saved: a retry would repeat it
    assert state.notice is not None and state.notice.code == "note_saved_not_shown"
    assert [n.phrase for n in env.workflow().open_insights(env.project_id).notes] == [
        "running late"
    ]


def test_a_removal_before_a_failed_refresh_says_so(env: Env) -> None:
    controller = opened(env)
    controller.set_note_draft(note())
    controller.add_note()
    (stored,) = snap(controller.state).notes
    repository = SqliteProjectRepository(AppDataLocations(env.root))
    failing = FailingRefresh(repository)
    failing.opened = 1  # the next refresh fails
    broken = env.controller(workflow=failing)
    broken._state = controller.state

    broken.remove_note(stored.note_id)

    notice = broken.state.notice
    assert notice is not None and notice.code == "note_saved_not_shown"
    assert env.workflow().open_insights(env.project_id).notes == ()
