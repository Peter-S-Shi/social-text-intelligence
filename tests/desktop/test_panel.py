"""View models: states map to copy and enabled actions as the M5.1 design says."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import pytest

from social_text_intelligence.application.model_provisioning import (
    FolderFinding,
    FolderInspection,
    FolderModelFinding,
    ProvisioningOutcome,
    Readiness,
)
from social_text_intelligence.desktop.controller import (
    Activity,
    ControllerState,
    FolderState,
    OperationReport,
)
from social_text_intelligence.desktop.gate import AnalysisAvailability
from social_text_intelligence.desktop.panel import (
    ActionId,
    ActionView,
    PanelView,
    ReportKind,
    build_analysis_block,
    build_folder_view,
    build_panel,
    build_sidebar_status,
)

from .fakes import MB, progress, status

AVAILABLE = AnalysisAvailability.AVAILABLE
NOT_READY = AnalysisAvailability.MODELS_NOT_READY
BLOCKED = AnalysisAvailability.SESSION_BLOCKED


def panel(
    state: ControllerState,
    availability: AnalysisAvailability = NOT_READY,
    window: Literal["setup", "models"] = "models",
) -> PanelView:
    return build_panel(state, availability, window=window)


def labels(actions: Iterable[ActionView]) -> list[str]:
    return [a.label for a in actions]


def test_first_run_offers_download_both_with_size_and_use_a_folder() -> None:
    view = panel(
        ControllerState(status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED)),
        window="setup",
    )
    assert view.headline == "Set up the language models"
    assert labels(view.actions) == [
        "Download both models · 200.0 MB",
        "Use a models folder…",
    ]
    assert all(a.enabled for a in view.actions)
    assert labels(view.cards[0].actions) == ["Download this model · 100.0 MB"]
    assert view.cards[0].chip == "○ Not installed"


def test_steady_state_has_only_verify_and_open_folder() -> None:
    view = panel(ControllerState(status()), AVAILABLE)
    assert labels(view.actions) == ["Verify files", "Open models folder"]
    assert all(card.actions == () for card in view.cards)
    assert view.subline == "2 of 2 models ready"


def test_setup_window_never_offers_verify_or_open_folder() -> None:
    view = panel(
        ControllerState(status(Readiness.READY, Readiness.NOT_INSTALLED)),
        window="setup",
    )
    assert labels(view.actions) == ["Use a models folder…"]


def test_incomplete_with_a_partial_offers_resume_and_discard() -> None:
    state = ControllerState(
        status(
            Readiness.INCOMPLETE,
            Readiness.READY,
            sentiment_args={"resumable": 20 * MB, "problems": ("weights.bin",)},
        )
    )
    card = panel(state).cards[0]
    assert card.sentence == "Interrupted: 20.0 MB kept, 30.0 MB left."
    assert labels(card.actions) == [
        "Download · resume, 30.0 MB left",
        "Discard partial download",
    ]
    assert card.problem_files == ("weights.bin",)
    assert panel(state, window="setup").headline == "Setup was interrupted"


def test_incomplete_without_a_partial_has_nothing_to_discard() -> None:
    state = ControllerState(
        status(
            Readiness.INCOMPLETE,
            Readiness.READY,
            sentiment_args={"problems": ("a.json", "b.json")},
        )
    )
    card = panel(state).cards[0]
    assert labels(card.actions) == ["Download missing files"]
    assert card.sentence == "2 required files missing."
    assert panel(state, window="setup").headline == "Some model files are missing"


def test_corrupt_offers_replacement_verify_again_and_names_the_files() -> None:
    state = ControllerState(
        status(
            Readiness.READY,
            Readiness.CORRUPT,
            emotion_args={"problems": ("model.safetensors",)},
        )
    )
    card = panel(state).cards[1]
    assert card.chip == "✕ Damaged"
    assert labels(card.actions) == [
        "Download replacement · 1 file, 50.0 MB",
        "Verify again",
    ]
    assert card.problem_files == ("model.safetensors",)
    assert panel(state, window="setup").headline == "A model file is damaged"


def test_wrong_revision_is_never_used_and_offers_the_approved_version() -> None:
    state = ControllerState(
        status(
            Readiness.WRONG_REVISION,
            Readiness.READY,
            sentiment_args={"others": ("d616e2b" + "0" * 33,)},
        )
    )
    card = panel(state).cards[0]
    assert "never used" in card.sentence and "d616e2b" in card.sentence
    assert labels(card.actions) == ["Download approved version · 100.0 MB"]
    assert card.problem_files == ()


def test_other_revisions_beside_a_ready_model_are_noted() -> None:
    state = ControllerState(status(sentiment_args={"others": ("d616e2b" + "0" * 33,)}))
    assert panel(state, AVAILABLE).cards[0].also_found == (
        "Also found: version d616e2b · never used, left alone"
    )


def test_details_carry_provenance() -> None:
    card = panel(ControllerState(status())).cards[0]
    details = dict(card.details)
    assert details["Model"] == "synthetic-org/sentiment-model"
    assert details["Revision"] == "a" * 40
    assert details["Licence"] == "CC-BY-4.0"


def test_every_state_chip_pairs_an_icon_with_a_word() -> None:
    icons = set()
    for readiness in Readiness:
        card = panel(ControllerState(status(readiness))).cards[0]
        assert card.chip_icon and card.chip_word
        assert card.chip_word.lower() in card.accessible_name.lower()
        icons.add(card.chip_icon)
    assert len(icons) == len(Readiness)  # distinct shapes, not colour alone


def test_while_busy_everything_but_stop_is_disabled_with_a_sentence() -> None:
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        activity=Activity.DOWNLOADING,
        progress=progress(50 * MB),
    )
    view = panel(state)
    assert view.busy_note
    assert view.actions and not any(a.enabled for a in view.actions)
    assert not any(a.enabled for card in view.cards for a in card.actions)
    assert view.progress is not None and view.progress.can_stop
    assert "partial" in view.progress.note


def test_progress_bars_show_written_values() -> None:
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        activity=Activity.DOWNLOADING,
        progress=progress(50 * MB, 200 * MB),
    )
    view = panel(state).progress
    assert view is not None
    assert [b.label for b in view.bars] == ["This file", "This model", "All selected"]
    assert view.bars[2].text == "50.0 MB of 200.0 MB"
    assert view.bars[2].fraction == pytest.approx(0.25)
    assert "All selected: 50.0 MB of 200.0 MB" in view.accessible_text


def test_verify_progress_has_no_stop_and_says_so() -> None:
    state = ControllerState(
        status(), activity=Activity.VERIFYING, progress=progress(10 * MB)
    )
    view = panel(state, AVAILABLE).progress
    assert view is not None and not view.can_stop
    assert "cannot be stopped" in view.note


def test_stopping_shows_a_stopping_note_and_no_second_stop() -> None:
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        activity=Activity.DOWNLOADING,
        stopping=True,
    )
    view = panel(state).progress
    assert view is not None and view.stopping and not view.can_stop


@pytest.mark.parametrize(
    ("code", "title", "action_labels"),
    [
        (
            "network_unavailable",
            "Connection lost",
            ["Download again · resumes", "Use a models folder…"],
        ),
        (
            "download_rejected",
            "The download was refused",
            ["Download again", "Use a models folder…"],
        ),
        (
            "checksum_mismatch",
            "A file failed its checksum and was discarded",
            ["Download again", "Use a models folder…"],
        ),
        (
            "storage_failed",
            "The models folder could not be read or written",
            ["Try again", "Open models folder"],
        ),
        (
            "provisioning_in_progress",
            "Another model operation is running",
            ["OK"],
        ),
    ],
)
def test_failures_show_title_fixed_message_code_and_recovery(
    code: str, title: str, action_labels: list[str]
) -> None:
    message = f"fixed backend message for {code}"
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        report=OperationReport(
            Activity.DOWNLOADING, ProvisioningOutcome.FAILED, code, message
        ),
    )
    report = panel(state).report
    assert report is not None
    assert report.kind is ReportKind.ERROR and report.assertive
    assert report.title == title
    assert report.code == code
    assert labels(report.actions) == action_labels
    if code == "provisioning_in_progress":
        assert (
            "Verify" in report.body
        )  # the contract text omits it; the desktop adds it
    else:
        assert message in report.body


def test_a_checksum_failure_during_import_points_at_a_different_folder() -> None:
    state = ControllerState(
        status(Readiness.READY, Readiness.NOT_INSTALLED),
        report=OperationReport(
            Activity.IMPORTING,
            ProvisioningOutcome.FAILED,
            "checksum_mismatch",
            "fixed",
        ),
    )
    report = panel(state).report
    assert report is not None
    assert labels(report.actions) == ["Choose a different folder", "Download again"]


def test_verify_storage_failure_says_nothing_was_recorded() -> None:
    state = ControllerState(
        status(),
        report=OperationReport(
            Activity.VERIFYING, ProvisioningOutcome.FAILED, "storage_failed", "fixed"
        ),
    )
    report = panel(state, AVAILABLE).report
    assert report is not None
    assert report.title == "Verify could not read a model file"
    assert "Nothing was recorded" in report.body


def test_network_failure_with_a_partial_says_it_is_kept() -> None:
    state = ControllerState(
        status(
            Readiness.INCOMPLETE,
            Readiness.NOT_INSTALLED,
            sentiment_args={"resumable": 20 * MB, "problems": ("weights.bin",)},
        ),
        report=OperationReport(
            Activity.DOWNLOADING,
            ProvisioningOutcome.FAILED,
            "network_unavailable",
            "fixed",
        ),
    )
    report = panel(state).report
    assert report is not None and "20.0 MB of partial download is kept" in report.body


def test_stopped_download_keeps_the_partial_and_offers_resume() -> None:
    partial = status(
        Readiness.INCOMPLETE,
        Readiness.NOT_INSTALLED,
        sentiment_args={"resumable": 20 * MB, "problems": ("weights.bin",)},
    )
    state = ControllerState(
        partial,
        report=OperationReport(Activity.DOWNLOADING, ProvisioningOutcome.CANCELLED),
    )
    view = panel(state)
    assert view.report is not None and view.report.kind is ReportKind.INFO
    assert "20.0 MB of partial download is kept" in view.report.body
    assert any("resume" in a.label for a in view.cards[0].actions)


def test_a_stopped_import_keeps_nothing_partial() -> None:
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        report=OperationReport(Activity.IMPORTING, ProvisioningOutcome.CANCELLED),
    )
    report = panel(state).report
    assert report is not None and "Nothing partial was kept" in report.body


def test_verify_damage_is_remembered_and_h2_adds_the_restart_text() -> None:
    state = ControllerState(
        status(Readiness.READY, Readiness.CORRUPT),
        report=OperationReport(
            Activity.VERIFYING, ProvisioningOutcome.COMPLETED, found_damage=True
        ),
    )
    plain = panel(state, NOT_READY).report
    assert plain is not None and plain.kind is ReportKind.WARNING
    assert "remembered" in plain.body and "restart the app" not in plain.body

    blocked = panel(state, BLOCKED)
    assert blocked.report is not None
    assert "restart the app" in blocked.report.body
    assert blocked.session_note and "restart" in blocked.session_note.lower()


def test_after_repair_the_models_are_ready_but_the_session_stays_blocked() -> None:
    state = ControllerState(
        status(),
        report=OperationReport(Activity.DOWNLOADING, ProvisioningOutcome.COMPLETED),
    )
    report = panel(state, BLOCKED).report
    assert report is not None
    assert "Analysis stays off in this session" in report.body
    assert "reopen the app" in report.body
    plain = panel(state, AVAILABLE).report
    assert plain is not None
    assert plain.body.startswith("Both models are installed")


def test_report_is_hidden_while_an_operation_runs() -> None:
    state = ControllerState(
        status(),
        activity=Activity.VERIFYING,
        report=OperationReport(Activity.DOWNLOADING, ProvisioningOutcome.COMPLETED),
    )
    assert panel(state, AVAILABLE).report is None


# -- sidebar ----------------------------------------------------------------


def test_sidebar_ready_is_quiet() -> None:
    view = build_sidebar_status(ControllerState(status()), AVAILABLE)
    assert view.title == "✓ Models ready"
    assert view.accessible_name == "Models ready. 2 of 2 models ready. Open models."
    assert view.meter is None


def test_sidebar_reports_the_worst_state_in_words() -> None:
    state = ControllerState(
        status(Readiness.INCOMPLETE, Readiness.CORRUPT),
    )
    view = build_sidebar_status(state, NOT_READY)
    assert view.title == "✕ Emotion model damaged"
    assert "Analysis unavailable" in view.accessible_name
    assert "0 of 2 models ready" in view.line


def test_sidebar_shows_a_meter_while_running() -> None:
    state = ControllerState(
        status(Readiness.NOT_INSTALLED, Readiness.NOT_INSTALLED),
        activity=Activity.DOWNLOADING,
        progress=progress(50 * MB, 200 * MB),
    )
    view = build_sidebar_status(state, NOT_READY)
    assert view.title == "◉ Downloading models…"
    assert view.meter == pytest.approx(0.25)
    assert "25 percent" in view.accessible_name


def test_sidebar_h2_text_is_the_one_shared_wording() -> None:
    damaged = build_sidebar_status(
        ControllerState(status(Readiness.READY, Readiness.CORRUPT)), BLOCKED
    )
    assert damaged.title == "✕ Analysis off until restart"
    assert damaged.line == "damaged files found"
    repaired = build_sidebar_status(ControllerState(status()), BLOCKED)
    assert repaired.line == "models repaired · restart to analyse"
    assert "Analysis off until restart" in repaired.accessible_name


# -- analysis block ---------------------------------------------------------


def test_available_analysis_shows_no_block() -> None:
    assert build_analysis_block(status(), AVAILABLE) is None


def test_models_not_ready_block_uses_the_contract_message_and_lists_models() -> None:
    block = build_analysis_block(
        status(Readiness.READY, Readiness.INCOMPLETE), NOT_READY
    )
    assert block is not None
    assert block.body == (
        "The required local models are not ready. Download them or use a "
        "models folder before analysing."
    )
    assert block.detail == ("Emotion model: Incomplete",)
    assert block.action.label == "Set up models…"


def test_session_block_has_its_own_panel_with_a_route_to_models() -> None:
    block = build_analysis_block(status(), BLOCKED)
    assert block is not None
    assert block.title == "Analysis is off until you restart the app"
    assert "restart" in block.body.lower()
    assert block.action.action is ActionId.OPEN_MODELS


# -- folder dialog ----------------------------------------------------------


def test_folder_view_before_choosing_is_read_only_guidance() -> None:
    view = build_folder_view(None, busy=False)
    assert "read-only" in view.status_line
    assert labels(view.actions) == ["Choose a folder…"]


def test_folder_findings_and_import_label() -> None:
    inspection = FolderInspection(
        (
            FolderModelFinding("sentiment", FolderFinding.FOUND, ()),
            FolderModelFinding(
                "emotion", FolderFinding.MISMATCHED, ("model.safetensors",)
            ),
        )
    )
    view = build_folder_view(
        FolderState(Path("synthetic"), inspection=inspection), busy=False
    )
    assert view.status_line == "Read-only check. Nothing was copied."
    assert [r.title for r in view.rows] == ["Sentiment model", "Emotion model"]
    assert "Ready to import" in view.rows[0].finding
    assert view.rows[1].problems == ("model.safetensors",)
    assert labels(view.actions) == ["Import sentiment model", "Choose another folder…"]


def test_both_found_imports_both_and_unsupported_folder_offers_no_import() -> None:
    both = FolderInspection(
        (
            FolderModelFinding("sentiment", FolderFinding.FOUND, ()),
            FolderModelFinding("emotion", FolderFinding.FOUND, ()),
        )
    )
    view = build_folder_view(FolderState(Path("x"), inspection=both), busy=False)
    assert labels(view.actions)[0] == "Import both models"
    assert view.actions[0].keys == ("sentiment", "emotion")

    nothing = FolderInspection(
        (
            FolderModelFinding("sentiment", FolderFinding.NOT_FOUND, ()),
            FolderModelFinding("emotion", FolderFinding.NOT_FOUND, ()),
        )
    )
    view = build_folder_view(FolderState(Path("x"), inspection=nothing), busy=False)
    assert "does not look like a models folder" in view.status_line
    assert labels(view.actions) == ["Choose another folder…"]


def test_unreadable_folder_shows_the_fixed_message_and_choose_another() -> None:
    folder = FolderState(
        Path("x"),
        error_code="source_unreadable",
        error_message="The chosen folder could not be read.",
    )
    view = build_folder_view(folder, busy=False)
    assert view.error is not None
    assert view.error.title == "Couldn't read that folder"
    assert view.error.body == "The chosen folder could not be read."
    assert labels(view.actions) == ["Choose a folder…"]


def test_download_both_size_counts_only_what_is_left_after_partials() -> None:
    state = ControllerState(
        status(
            Readiness.INCOMPLETE,
            Readiness.NOT_INSTALLED,
            sentiment_args={"resumable": 20 * MB, "problems": ("weights.bin",)},
        )
    )
    both = panel(state).actions[0]
    # 50 MB missing minus 20 MB already held, plus the whole 100 MB model
    assert both.label == "Download both models · 130.0 MB"


def test_a_checksum_failure_after_import_also_offers_download() -> None:
    state = ControllerState(
        status(Readiness.READY, Readiness.NOT_INSTALLED),
        report=OperationReport(
            Activity.IMPORTING,
            ProvisioningOutcome.FAILED,
            "checksum_mismatch",
            "fixed",
        ),
    )
    report = panel(state).report
    assert report is not None
    assert labels(report.actions) == ["Choose a different folder", "Download again"]


def test_models_window_explains_that_the_app_manages_the_folder() -> None:
    models = panel(ControllerState(status()), AVAILABLE, window="models")
    assert models.folder_note is not None
    assert "manages this folder" in models.folder_note
    assert "by hand" in models.folder_note
    setup = panel(ControllerState(status()), AVAILABLE, window="setup")
    assert setup.folder_note is None
