"""Deterministic doubles for the desktop layer: a scripted provisioner and runners."""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from social_text_intelligence.application.model_provisioning import (
    FolderInspection,
    ModelsStatus,
    ModelStatus,
    ProgressCallback,
    ProvisioningOutcome,
    ProvisioningPhase,
    ProvisioningProgress,
    ProvisioningResult,
    Readiness,
)
from social_text_intelligence.contracts import AnalysisReport, NormalizedTextInput
from social_text_intelligence.contracts.errors import ModelProvisioningError

MB = 1024 * 1024


def model(
    key: str,
    readiness: Readiness = Readiness.READY,
    *,
    total: int = 100 * MB,
    resumable: int = 0,
    problems: tuple[str, ...] = (),
    others: tuple[str, ...] = (),
) -> ModelStatus:
    installed = {
        Readiness.READY: total,
        Readiness.NOT_INSTALLED: 0,
        Readiness.WRONG_REVISION: 0,
    }.get(readiness, total // 2)
    return ModelStatus(
        key=key,
        model_id=f"synthetic-org/{key}-model",
        revision=("a" if key == "sentiment" else "b") * 40,
        license="CC-BY-4.0" if key == "sentiment" else "MIT",
        readiness=readiness,
        total_bytes=total,
        installed_bytes=installed,
        resumable_bytes=resumable,
        problem_files=problems,
        other_revisions=others,
    )


def status(
    sentiment: Readiness = Readiness.READY,
    emotion: Readiness = Readiness.READY,
    *,
    sentiment_args: dict[str, Any] | None = None,
    emotion_args: dict[str, Any] | None = None,
) -> ModelsStatus:
    return ModelsStatus(
        (
            model("sentiment", sentiment, **(sentiment_args or {})),
            model("emotion", emotion, **(emotion_args or {})),
        )
    )


def progress(
    done: int,
    total: int = 200 * MB,
    phase: ProvisioningPhase = ProvisioningPhase.DOWNLOADING,
) -> ProvisioningProgress:
    return ProvisioningProgress(
        phase=phase,
        model_key="sentiment",
        file_name="weights.bin",
        file_bytes_done=done,
        file_bytes_total=total,
        model_bytes_done=done,
        model_bytes_total=total,
        overall_bytes_done=done,
        overall_bytes_total=total,
    )


@dataclass
class FakeProvisioning:
    """Scripted ``ModelProvisioning``; each long call can block on ``hold``."""

    current: ModelsStatus = field(default_factory=status)
    root: Path = Path("synthetic-models")
    calls: list[tuple[str, Any]] = field(default_factory=list)
    next_download: ProvisioningResult | BaseException | None = None
    next_import: ProvisioningResult | BaseException | None = None
    next_verify: ModelsStatus | BaseException | None = None
    next_inspection: FolderInspection | BaseException | None = None
    next_discard: ModelsStatus | BaseException | None = None
    emit: list[ProvisioningProgress] = field(default_factory=list)
    hold: threading.Event | None = None
    started: threading.Event = field(default_factory=threading.Event)
    saw_cancel: bool = False
    thread_ids: list[int] = field(default_factory=list)

    @property
    def models_root(self) -> Path:
        return self.root

    def status(self) -> ModelsStatus:
        self.calls.append(("status", None))
        self.thread_ids.append(threading.get_ident())
        return self.current

    def _wait(self, cancelled: Callable[[], bool] | None) -> None:
        self.thread_ids.append(threading.get_ident())
        self.started.set()
        if self.hold is not None:
            while not self.hold.wait(0.005):
                if cancelled is not None and cancelled():
                    self.saw_cancel = True
                    return

    def verify(self, *, on_progress: ProgressCallback | None = None) -> ModelsStatus:
        self.calls.append(("verify", None))
        self._push(on_progress)
        self._wait(None)
        outcome = self.next_verify
        if isinstance(outcome, BaseException):
            raise outcome
        if outcome is not None:
            self.current = outcome
        return self.current

    def download(
        self,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ProvisioningResult:
        self.calls.append(("download", keys))
        self._push(on_progress)
        self._wait(cancelled)
        return self._finish(self.next_download, cancelled)

    def import_folder(
        self,
        folder: Path,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ProvisioningResult:
        self.calls.append(("import", (folder, keys)))
        self._push(on_progress)
        self._wait(cancelled)
        return self._finish(self.next_import, cancelled)

    def discard_partial_downloads(
        self, keys: tuple[str, ...] | None = None
    ) -> ModelsStatus:
        self.calls.append(("discard", keys))
        self.thread_ids.append(threading.get_ident())
        outcome = self.next_discard
        if isinstance(outcome, BaseException):
            raise outcome
        if outcome is not None:
            self.current = outcome
        return self.current

    def inspect_folder(self, folder: Path) -> FolderInspection:
        self.calls.append(("inspect", folder))
        self._wait(None)
        outcome = self.next_inspection
        if isinstance(outcome, BaseException):
            raise outcome
        assert outcome is not None
        return outcome

    def _push(self, on_progress: ProgressCallback | None) -> None:
        if on_progress is not None:
            for item in self.emit:
                on_progress(item)

    def _finish(
        self,
        outcome: ProvisioningResult | BaseException | None,
        cancelled: Callable[[], bool] | None,
    ) -> ProvisioningResult:
        if self.saw_cancel or (cancelled is not None and cancelled()):
            self.saw_cancel = True
            return ProvisioningResult(ProvisioningOutcome.CANCELLED, self.current)
        if isinstance(outcome, BaseException):
            raise outcome
        result = outcome or ProvisioningResult(
            ProvisioningOutcome.COMPLETED, self.current
        )
        self.current = result.status
        return result


def failed(code: str, current: ModelsStatus) -> ProvisioningResult:
    message = ModelProvisioningError(code).message
    return ProvisioningResult(
        ProvisioningOutcome.FAILED, current, error_code=code, error_message=message
    )


class ManualRunner:
    """Runs work only when the test pumps it, so UI-thread rules are observable."""

    def __init__(self) -> None:
        self.jobs: deque[tuple[Callable[[], Any], Callable[[Any], None]]] = deque()
        self.posted: deque[Callable[[], None]] = deque()

    def run(self, work: Callable[[], Any], deliver: Callable[[Any], None]) -> None:
        self.jobs.append((work, deliver))

    def post(self, call: Callable[[], None]) -> None:
        self.posted.append(call)

    def wait_idle(self, timeout: float = 10.0) -> bool:
        return True

    def pump_posts(self) -> None:
        while self.posted:
            self.posted.popleft()()

    def run_next(self) -> None:
        work, deliver = self.jobs.popleft()
        try:
            outcome: Any = work()
        except BaseException as error:  # mirrors the real runner
            outcome = error
        self.pump_posts()
        deliver(outcome)


class ImmediateRunner(ManualRunner):
    """Executes each job synchronously, then delivers on the caller."""

    def run(self, work: Callable[[], Any], deliver: Callable[[Any], None]) -> None:
        super().run(work, deliver)
        self.run_next()


class ThreadedRunner:
    """Real worker threads; results reach the 'UI thread' only via ``drain``."""

    def __init__(self) -> None:
        self.ui_thread = threading.get_ident()
        self._queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._threads: list[threading.Thread] = []

    def run(self, work: Callable[[], Any], deliver: Callable[[Any], None]) -> None:
        def target() -> None:
            try:
                outcome: Any = work()
            except BaseException as error:
                outcome = error
            self.post(lambda: deliver(outcome))

        thread = threading.Thread(target=target)
        self._threads.append(thread)
        thread.start()

    def post(self, call: Callable[[], None]) -> None:
        self._queue.put(call)

    def drain(self, until: Callable[[], bool], timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while not until():
            remaining = deadline - time.monotonic()
            assert remaining > 0, "timed out waiting for the worker"
            try:
                call = self._queue.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue
            assert threading.get_ident() == self.ui_thread
            call()

    def join(self) -> None:
        for thread in self._threads:
            thread.join(5)

    def wait_idle(self, timeout: float = 10.0) -> bool:
        self.join()
        return True


def synthetic_report(text: str = "A synthetic sentence.") -> AnalysisReport:
    from social_text_intelligence.providers import (
        DeterministicEmotionProvider,
        DeterministicSentimentProvider,
    )
    from social_text_intelligence.services import AnalysisService

    record = NormalizedTextInput.from_text(text, language="en", max_text_length=1000)
    return AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(),
        emotion_provider=DeterministicEmotionProvider(),
    ).analyze(record)


class StubGateway:
    """An ``AnalysisGateway`` double that records calls and flips ``initialized``."""

    def __init__(self, report: AnalysisReport | None = None) -> None:
        self.initialized = False
        self.report = report
        self.records: list[NormalizedTextInput] = []

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        self.initialized = True
        self.records.append(record)
        assert self.report is not None
        return self.report
