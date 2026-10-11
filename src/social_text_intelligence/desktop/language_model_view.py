"""Pure view model for the optional language-check model (no Qt).

The section sits in the setup and Models windows below the two required models.
It never gates analysis: without the model, results keep saying "Language check
unavailable"; once installed, new analyses check each text's language locally.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.language_model import LANGUAGE_MODEL_SOURCE
from ..application.model_provisioning import (
    ModelStatus,
    ProvisioningOutcome,
    Readiness,
)
from . import copy
from .controller import Activity, ControllerState
from .formatting import format_bytes
from .panel import ActionId, ActionView, ProgressView, ReportKind, ReportView
from .panel import progress_for as _progress_for

LANGUAGE_MODEL_TITLE = "Language check model (optional)"


@dataclass(frozen=True, slots=True)
class LanguageModelView:
    title: str
    chip: str
    sentence: str
    source: str
    actions: tuple[ActionView, ...]
    progress: ProgressView | None
    report: ReportView | None

    @property
    def accessible_name(self) -> str:
        return f"{self.title}: {self.chip}. {self.sentence}"


def _left(model: ModelStatus) -> int:
    return max(model.total_bytes - model.installed_bytes - model.resumable_bytes, 0)


def _sentence(model: ModelStatus) -> str:
    readiness = model.readiness
    if readiness is Readiness.READY:
        return (
            "Installed and checksum-verified. New analyses check the language of "
            "each text on this computer."
        )
    if readiness is Readiness.INCOMPLETE and model.resumable_bytes:
        return (
            f"Interrupted: {format_bytes(model.resumable_bytes)} kept, "
            f"{format_bytes(_left(model))} left."
        )
    if readiness is Readiness.CORRUPT:
        return "The file is damaged or the wrong size, so it is never used."
    if readiness is Readiness.WRONG_REVISION:
        return "Only a different version is present. It is never used."
    return (
        "Not installed. Analysis works without it, but results say "
        '"Language check unavailable" instead of checking the language.'
    )


def _download(model: ModelStatus, busy: bool) -> ActionView | None:
    size = format_bytes(model.total_bytes)
    labels = {
        Readiness.NOT_INSTALLED: f"Download language model · {size}",
        Readiness.WRONG_REVISION: f"Download language model · {size}",
        Readiness.CORRUPT: f"Download replacement · {size}",
        Readiness.INCOMPLETE: (
            f"Download · resume, {format_bytes(_left(model))} left"
            if model.resumable_bytes
            else f"Download language model · {size}"
        ),
    }
    text = labels.get(model.readiness)
    if text is None:
        return None
    return ActionView(ActionId.DOWNLOAD, text, not busy, (model.key,), primary=True)


def _report(state: ControllerState) -> ReportView | None:
    report = state.report
    if report is None or state.busy:
        return None
    if report.outcome is ProvisioningOutcome.FAILED:
        code = report.error_code or "unexpected_error"
        return ReportView(
            ReportKind.ERROR,
            copy.ERROR_TITLES.get(code, copy.ERROR_TITLES["unexpected_error"]),
            copy.ERROR_BODIES.get(code, report.error_message or ""),
            code,
            (ActionView(ActionId.RETRY, "Try again", primary=True),),
        )
    if report.outcome is ProvisioningOutcome.CANCELLED:
        return ReportView(
            ReportKind.INFO, "Stopped", "The partial file is kept.", None, ()
        )
    if report.kind is Activity.DISCARDING:
        return ReportView(
            ReportKind.INFO,
            "Partial download discarded",
            "Nothing else changed.",
            None,
            (),
        )
    return ReportView(
        ReportKind.SUCCESS,
        "Language check model installed",
        "New analyses now check the language of each text. Results saved earlier "
        "keep the language evidence they were saved with.",
        None,
        (),
    )


def build_language_model_view(state: ControllerState) -> LanguageModelView:
    models = state.status.models
    source = (
        "Downloaded only when you choose, from "
        f"{LANGUAGE_MODEL_SOURCE}, and checked against its pinned checksum. The "
        "package is BSD-3-Clause licensed; the terms of the texts the model was "
        "trained on have not been verified."
    )
    if not models:
        return LanguageModelView(
            LANGUAGE_MODEL_TITLE, "", "Checking…", source, (), None, None
        )
    model = models[0]
    icon, word = copy.CHIPS[model.readiness]
    actions: list[ActionView] = []
    download = _download(model, state.busy)
    if download is not None:
        actions.append(download)
    if model.readiness is Readiness.INCOMPLETE and model.resumable_bytes:
        actions.append(
            ActionView(
                ActionId.DISCARD,
                "Discard partial download",
                not state.busy,
                (model.key,),
            )
        )
    return LanguageModelView(
        title=LANGUAGE_MODEL_TITLE,
        chip=f"{icon} {word}",
        sentence=_sentence(model),
        source=source,
        actions=tuple(actions),
        progress=_progress_for(state),
        report=_report(state),
    )
