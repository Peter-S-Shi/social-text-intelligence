"""The Qt-free agreement controller over a real SQLite project (synthetic data)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from persistence.workflow_samples import SENTINEL, ScriptedGateway, csv_text

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    ReviewDraft,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.desktop.agreement import (
    AgreementActivity,
    AgreementController,
)
from social_text_intelligence.desktop.projects import NoticeKind
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

from .fakes import ImmediateRunner, ManualRunner

LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)


class Env:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repository = SqliteProjectRepository(AppDataLocations(root))
        flow = ProjectWorkflow(self.repository, ScriptedGateway(), LIMITS)
        self.project_id = flow.import_csv(csv_text(3), name="P").summary.project_id
        self.written: dict[Path, str] = {}

    def analyse(self) -> None:
        ProjectWorkflow(self.repository, ScriptedGateway(), LIMITS).analyze(
            self.project_id
        )

    def review_first(self) -> None:
        flow = ReviewWorkflow(self.repository)
        seen = flow.open_review(self.project_id).record
        assert seen is not None
        flow.save(
            self.project_id,
            1,
            ReviewDraft(
                sentiment_judgment=ReviewJudgment.CORRECT,
                human_sentiment=SentimentLabel.NEGATIVE,
                emotion_judgment=ReviewJudgment.CORRECT,
                human_dominant_emotion=EmotionLabel.ANGER,
            ),
            expected=seen.review,
        )

    def write(self, path: Path, text: str) -> None:
        self.written[path] = text

    def controller(self, runner: Any = None, write: Any = None) -> AgreementController:
        return AgreementController(
            ReviewWorkflow(SqliteProjectRepository(AppDataLocations(self.root))),
            runner or ImmediateRunner(),
            write_file=write or self.write,
        )


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def test_opening_loads_the_summary_of_an_analysed_project(env: Env) -> None:
    env.analyse()
    controller = env.controller()

    assert controller.open(env.project_id) is True

    summary = controller.state.summary
    assert summary is not None
    assert (summary.progress.reviewable_records, summary.progress.reviewed) == (3, 0)
    assert controller.state.active and controller.state.notice is None


def test_reopening_reflects_a_review_saved_in_between(env: Env) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    env.review_first()

    controller.open(env.project_id)

    summary = controller.state.summary
    assert summary is not None and summary.progress.reviewed == 1


def test_a_project_that_is_not_analysed_says_so_instead_of_showing_zeros(
    env: Env,
) -> None:
    controller = env.controller()

    controller.open(env.project_id)

    state = controller.state
    assert state.summary is None
    assert state.notice is not None and state.notice.code == "review_unavailable"


def test_loading_is_off_the_caller_and_one_at_a_time(env: Env) -> None:
    env.analyse()
    runner = ManualRunner()
    controller = env.controller(runner)

    controller.open(env.project_id)

    assert controller.state.activity is AgreementActivity.LOADING
    assert controller.open(env.project_id) is False
    runner.run_next()
    assert controller.state.summary is not None and not controller.state.busy


def test_the_reviewed_export_is_written_where_the_person_chose(env: Env) -> None:
    env.analyse()
    controller = env.controller()
    controller.open(env.project_id)
    target = env.root / "reviewed.csv"

    assert controller.export(target, include_native=False) is True

    assert SENTINEL in env.written[target]
    notice = controller.state.notice
    assert notice is not None and notice.code == "export_saved"
    assert "private" in notice.body


def test_a_failed_write_shows_a_fixed_message_and_keeps_the_page(env: Env) -> None:
    env.analyse()

    def broken(path: Path, text: str) -> None:
        raise OSError(f"cannot write {path}")

    controller = env.controller(write=broken)
    controller.open(env.project_id)

    controller.export(env.root / "private-name.csv", include_native=False)

    notice = controller.state.notice
    assert notice is not None and notice.kind is NoticeKind.ERROR
    assert notice.code == "export_failed"
    assert "private-name" not in notice.body
    assert controller.state.summary is not None


def test_a_vanished_project_is_reported(env: Env) -> None:
    controller = env.controller()

    controller.open("no-such-project")

    assert not controller.state.active
    assert controller.state.notice is not None
    assert controller.state.notice.code == "project_not_found"


def test_export_needs_a_loaded_summary(env: Env) -> None:
    controller = env.controller()

    assert controller.export(env.root / "x.csv", include_native=False) is False
    assert env.written == {}
