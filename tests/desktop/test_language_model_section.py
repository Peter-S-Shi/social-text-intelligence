"""The optional language-check model in the setup and Models windows (M10 S1)."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from provisioning.fakes import FakeTransport

from social_text_intelligence.application.language_model import LANGUAGE_MODEL_FILE
from social_text_intelligence.application.model_provisioning import (
    LANGUAGE_MODEL,
    ModelFile,
    ModelsStatus,
    ModelStatus,
    ProvisioningOutcome,
    Readiness,
)
from social_text_intelligence.desktop.controller import (
    Activity,
    ControllerState,
    OperationReport,
)
from social_text_intelligence.desktop.language_model_view import (
    build_language_model_view,
)
from social_text_intelligence.desktop.panel import ActionId, ReportKind
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import FakeProvisioning, status

DATA = b"synthetic language model" * 512
SPEC = replace(
    LANGUAGE_MODEL,
    files=(
        ModelFile(LANGUAGE_MODEL_FILE, len(DATA), hashlib.sha256(DATA).hexdigest()),
    ),
)


def language_state(
    readiness: Readiness, *, resumable: int = 0, report: OperationReport | None = None
) -> ControllerState:
    model = ModelStatus(
        key="language",
        model_id=LANGUAGE_MODEL.model_id,
        revision=LANGUAGE_MODEL.revision,
        license=LANGUAGE_MODEL.license,
        readiness=readiness,
        total_bytes=4_586_720,
        installed_bytes=4_586_720 if readiness is Readiness.READY else 0,
        resumable_bytes=resumable,
        problem_files=() if readiness is Readiness.READY else ("model.npz.xz",),
        other_revisions=(),
    )
    return ControllerState(status=ModelsStatus((model,)), report=report)


def test_not_installed_offers_a_download_and_names_the_fallback() -> None:
    view = build_language_model_view(language_state(Readiness.NOT_INSTALLED))
    assert "Language check unavailable" in view.sentence
    assert "Analysis works without it" in view.sentence
    assert [a.action for a in view.actions] == [ActionId.DOWNLOAD]
    assert view.actions[0].keys == ("language",)
    assert "github.com/adbar/py3langid" in view.source
    assert "have not been verified" in view.source  # no corpus-rights claim


def test_ready_offers_nothing_to_do() -> None:
    view = build_language_model_view(language_state(Readiness.READY))
    assert view.actions == ()
    assert "check the language of each text" in view.sentence


def test_an_interrupted_download_can_resume_or_be_discarded() -> None:
    view = build_language_model_view(
        language_state(Readiness.INCOMPLETE, resumable=1_000_000)
    )
    assert [a.action for a in view.actions] == [ActionId.DOWNLOAD, ActionId.DISCARD]
    assert "resume" in view.actions[0].label


def test_a_damaged_file_is_never_used_and_can_be_replaced() -> None:
    view = build_language_model_view(language_state(Readiness.CORRUPT))
    assert "never used" in view.sentence
    assert view.actions[0].label.startswith("Download replacement")


def test_reports_after_a_download() -> None:
    done = OperationReport(Activity.DOWNLOADING, ProvisioningOutcome.COMPLETED)
    failed = OperationReport(
        Activity.DOWNLOADING, ProvisioningOutcome.FAILED, "network_unavailable"
    )
    success = build_language_model_view(language_state(Readiness.READY, report=done))
    error = build_language_model_view(
        language_state(Readiness.NOT_INSTALLED, report=failed)
    )
    assert success.report is not None and success.report.kind is ReportKind.SUCCESS
    assert "saved earlier keep" in success.report.body
    assert error.report is not None and error.report.kind is ReportKind.ERROR
    assert error.report.actions[0].action is ActionId.RETRY


def test_before_the_first_status_nothing_is_offered() -> None:
    view = build_language_model_view(ControllerState(status=ModelsStatus(())))
    assert view.actions == () and view.sentence == "Checking…"


# -- the real Qt windows -------------------------------------------------------


def test_downloading_the_language_model_leaves_the_required_models_alone(
    make_shell: Any, tmp_path: Path
) -> None:
    language = LocalModelProvisioner(
        models_root=tmp_path / "models",
        transport=FakeTransport(
            served={f"{SPEC.download_base}/{LANGUAGE_MODEL_FILE}": DATA}
        ),
        manifest=(SPEC,),
    )
    fake = FakeProvisioning(current=status())
    shell = make_shell(fake, language=language)
    shell.window.ui.show_models()
    section = shell.models.language
    assert section.isVisibleTo(shell.models)
    assert "Not installed" in section.sentence.text()
    required_before = fake.current

    shell.button(section, f"Download language model · {_size()}").click()

    assert language.status().ready
    assert "Ready" in section.chip.text()
    assert section.report.isVisibleTo(section)
    assert fake.current == required_before
    # the required models were never asked to download
    assert not any(name == "download" for name, _ in fake.calls)


def test_the_language_model_never_gates_analysis(make_shell: Any) -> None:
    shell = make_shell(FakeProvisioning(current=status()))
    assert not shell.language.status().ready
    assert (
        shell.window.services.gate.availability(
            shell.window.provisioning.state.status
        ).name
        == "AVAILABLE"
    )


def _size() -> str:
    from social_text_intelligence.desktop.formatting import format_bytes

    return format_bytes(len(DATA))
