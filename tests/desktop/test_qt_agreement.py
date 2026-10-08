"""Headless Qt tests of the Agreement page (real SQLite, synthetic data)."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any, cast

import pytest

if os.environ.get("STI_REQUIRE_QT") != "1":
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from persistence.insight_samples import (  # noqa: E402
    SENTINEL,
    VariedGateway,
    insights_csv,
)

from social_text_intelligence.application.review_workflow import (  # noqa: E402
    ReviewDraft,
    ReviewJudgment,
)
from social_text_intelligence.contracts import (  # noqa: E402
    EmotionLabel,
    SentimentLabel,
)

from .fakes import FakeProvisioning, status  # noqa: E402
from .qt_support import Shell  # noqa: E402

READY = status()
ACCEPT, CORRECT, UNCERTAIN = (
    ReviewJudgment.ACCEPT,
    ReviewJudgment.CORRECT,
    ReviewJudgment.UNCERTAIN,
)


@pytest.fixture
def make_shell(make_shell: Any) -> Any:
    def factory(fake: FakeProvisioning, runner: Any = None) -> Shell:
        return cast(Shell, make_shell(fake, runner, None, VariedGateway()))

    return factory


def text_of(widget: Any) -> str:
    return str(widget.text())


def analysed(make_shell: Any, tmp_path: Path) -> Shell:
    shell: Shell = make_shell(FakeProvisioning(current=READY))
    path = tmp_path / "tickets.csv"
    path.write_bytes(insights_csv())
    shell.platform.csv_file = path
    page = shell.window.projects_page
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    return shell


def review(shell: Shell, row: int, how: str) -> None:
    """Save one judgment through the workflow, as a person would over time."""

    workflow = shell.window.services.reviews
    project_id = shell.window.projects.state.current.summary.project_id  # type: ignore[union-attr]
    record = workflow.open_review(project_id, row=row).record
    assert record is not None
    if how == "accept":
        workflow.accept_both(project_id, row, "", expected=record.review)
    elif how == "correct":
        workflow.save(
            project_id,
            row,
            ReviewDraft(
                sentiment_judgment=CORRECT,
                human_sentiment=SentimentLabel.NEUTRAL,
                emotion_judgment=CORRECT,
                human_dominant_emotion=EmotionLabel.SADNESS,
            ),
            expected=record.review,
        )
    else:
        workflow.save(
            project_id,
            row,
            ReviewDraft(sentiment_judgment=UNCERTAIN, emotion_judgment=ACCEPT),
            expected=record.review,
        )


def go_agreement(shell: Shell) -> Any:
    shell.window.nav_buttons["Agreement"].click()
    page = shell.window.projects_page
    assert page.stack.currentWidget() is page.agreement_page
    return page.agreement_page


def test_with_no_review_the_figures_are_dashes_and_the_page_says_why(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)

    agreement = go_agreement(shell)

    assert [text_of(c.value) for c in agreement.figure_cards] == ["—", "—", "—"]
    assert agreement.empty.isVisibleTo(agreement)
    assert "No definitive reviews yet" in text_of(agreement.empty.title)
    assert text_of(agreement.header.title) == "Agreement, not accuracy"
    assert agreement.export_button.isEnabled()  # an unreviewed export is still valid


def test_reviews_show_their_rates_with_denominators_and_the_confusion_counts(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)
    for row, how in ((1, "accept"), (2, "accept"), (5, "accept"), (6, "correct")):
        review(shell, row, how)

    agreement = go_agreement(shell)

    sentiment = agreement.figure_cards[0]
    assert text_of(sentiment.value) == "75.0%"
    assert text_of(sentiment.caption) == "3 of 4 definitive reviews"
    assert "Sentiment agreement" in sentiment.accessibleName()
    assert text_of(agreement.header.subtitle).startswith("4 of 24 reviewed")
    names = {
        w.accessibleName() for w in agreement.confusion.findChildren(type(agreement.note))
    }
    assert any(n.startswith("AI negative, you neutral: 1") for n in names)
    assert not agreement.empty.isVisibleTo(agreement)
    assert "1 to neutral" in text_of(agreement.corrections)


def test_confidence_bands_wait_for_five_definitive_reviews(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)
    for row in (1, 2, 3, 4):
        review(shell, row, "accept")

    agreement = go_agreement(shell)
    sentiment_panel = agreement.confidence_cards[0]
    assert not sentiment_panel.bars.isVisibleTo(agreement)
    assert "at least five definitive reviews (4 so far)" in text_of(
        sentiment_panel.unavailable
    )

    review(shell, 5, "accept")
    shell.window.nav_buttons["Results"].click()
    agreement = go_agreement(shell)  # re-entering reloads: reviews saved meanwhile show

    assert sentiment_panel.bars.isVisibleTo(agreement)
    assert not sentiment_panel.unavailable.isVisibleTo(agreement)


def test_a_dimension_marked_uncertain_is_left_out_of_the_denominator(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)
    review(shell, 1, "accept")
    review(shell, 2, "uncertain")

    agreement = go_agreement(shell)

    assert text_of(agreement.figure_cards[0].caption) == "1 of 1 definitive reviews"
    assert text_of(agreement.figure_cards[1].caption) == "2 of 2 definitive reviews"


def test_the_reviewed_export_is_written_only_after_choosing_a_file(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)
    review(shell, 1, "accept")
    agreement = go_agreement(shell)
    shell.platform.save_target = None

    agreement.export_button.click()
    assert shell.platform.save_requests == ["reviewed-results.csv"]
    assert not agreement.notice.isVisibleTo(agreement)

    out = tmp_path / "reviewed.csv"
    shell.platform.save_target = out
    agreement.export_button.click()

    rows = list(csv.DictReader(io.StringIO(out.read_text("utf-8"))))
    assert len(rows) == 26 and rows[0]["review_status"]
    assert text_of(agreement.notice.title).endswith("Reviewed CSV saved")
    assert str(tmp_path) not in text_of(agreement.notice.body)
    assert SENTINEL in out.read_text("utf-8")  # the export carries record text


def test_a_failed_export_is_a_fixed_message(make_shell: Any, tmp_path: Path) -> None:
    shell = analysed(make_shell, tmp_path)
    agreement = go_agreement(shell)
    shell.platform.save_target = tmp_path / "missing" / "out.csv"

    agreement.export_button.click()

    assert agreement.notice.code.text() == "export_failed"
    assert str(tmp_path) not in text_of(agreement.notice.body)


def test_no_text_on_the_page_calls_agreement_accuracy(
    make_shell: Any, tmp_path: Path
) -> None:
    shell = analysed(make_shell, tmp_path)
    review(shell, 1, "accept")
    agreement = go_agreement(shell)

    shown = " ".join(
        w.text() for w in agreement.findChildren(type(agreement.note)) if w.isVisibleTo(agreement)
    ).lower()

    assert "not accuracy" in shown
    for claim in ("model accuracy", "is accurate", "calibrated as", "performance"):
        assert claim not in shown
