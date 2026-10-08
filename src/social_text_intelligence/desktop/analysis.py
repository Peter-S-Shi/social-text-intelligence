"""Qt-free controller for the "Analyze one text" page.

Analysis runs off the UI thread (the first call also loads both models, which can
take a while) and always goes through the shared ``AnalysisGate``. A result that was
produced before a mid-session block stays on screen as it was (design decision 11).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from ..application.language import describe_language
from ..application.use_cases import ApplicationUseCases
from ..contracts import AnalysisReport
from ..contracts.errors import AnalysisSetupError, ModelsNotReadyError, ProviderError
from . import copy
from .controller import JobRunner
from .gate import AnalysisSessionBlockedError


@dataclass(frozen=True, slots=True)
class ResultView:
    sentiment: str
    sentiment_confidence: str
    emotion: str
    emotion_confidence: str
    secondary_emotions: tuple[str, ...]
    provenance: tuple[str, ...]
    language_headline: str
    language_detail: str
    language_warns: bool


@dataclass(frozen=True, slots=True)
class AnalysisError:
    code: str
    title: str
    body: str
    offers_verify: bool = False
    offers_models: bool = False


@dataclass(frozen=True, slots=True)
class AnalysisPageState:
    running: bool = False
    result: ResultView | None = None
    error: AnalysisError | None = None


def _percent(value: float) -> str:
    return f"{round(value * 100)}%"


def result_view(report: AnalysisReport) -> ResultView:
    sentiment, emotion = report.sentiment, report.emotion
    language = describe_language(report.language)
    return ResultView(
        sentiment=sentiment.label.value.title(),
        sentiment_confidence=_percent(sentiment.confidence),
        emotion=emotion.dominant_emotion.value.replace("_", " ").title(),
        emotion_confidence=_percent(emotion.confidence),
        secondary_emotions=tuple(
            label.value.replace("_", " ").title()
            for label in emotion.secondary_emotions
        ),
        provenance=tuple(
            f"{meta.model_name} · revision {meta.revision[:7]}"
            for meta in (sentiment.provider, emotion.provider)
        ),
        language_headline=language.headline,
        language_detail=language.detail,
        language_warns=language.warns,
    )


def analysis_error(error: BaseException) -> AnalysisError:
    if isinstance(error, AnalysisSessionBlockedError):
        return AnalysisError(
            error.code, copy.SESSION_BLOCK_TITLE, error.message, offers_models=True
        )
    if isinstance(error, ModelsNotReadyError):
        return AnalysisError(
            error.code, copy.MODELS_NOT_READY_TITLE, error.message, offers_models=True
        )
    if (
        isinstance(error, ProviderError | AnalysisSetupError)
        and error.code == "model_load_failed"
    ):
        return AnalysisError(
            error.code,
            copy.ERROR_TITLES["model_load_failed"],
            copy.ERROR_BODIES["model_load_failed"],
            offers_verify=True,
            offers_models=True,
        )
    if isinstance(error, Exception):
        body = ApplicationUseCases.safe_error(error)
        code = getattr(error, "code", "analysis_failed")
        return AnalysisError(str(code), "Analysis did not finish", body)
    return AnalysisError(
        "analysis_failed",
        "Analysis did not finish",
        "Analysis failed safely. Review the local setup and try again.",
    )


class AnalysisPageController:
    def __init__(
        self, analyze: Callable[[str], AnalysisReport], runner: JobRunner
    ) -> None:
        self._analyze = analyze
        self._runner = runner
        self._state = AnalysisPageState()
        self._listeners: list[Callable[[AnalysisPageState], None]] = []

    @property
    def state(self) -> AnalysisPageState:
        return self._state

    def subscribe(self, listener: Callable[[AnalysisPageState], None]) -> None:
        self._listeners.append(listener)

    def submit(self, text: str) -> bool:
        if self._state.running:
            return False
        self._set(running=True, error=None)
        self._runner.run(lambda: self._analyze(text), self._done)
        return True

    def _done(self, outcome: Any) -> None:
        if isinstance(outcome, BaseException):
            self._set(running=False, error=analysis_error(outcome))
        else:
            self._set(running=False, result=result_view(outcome), error=None)

    def _set(self, **changes: Any) -> None:
        self._state = replace(self._state, **changes)
        for listener in tuple(self._listeners):
            listener(self._state)
