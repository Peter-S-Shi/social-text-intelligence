"""PROTOTYPE (throwaway) - Spike A: native Qt shell calling the V1 service directly.

Question: can a native desktop shell drive the existing analysis stack in-process,
with no Flask, no HTTP, no localhost, and a responsive UI thread?

Run (headless, real offline models):
    python spike_a_native_shell.py [--mock] [--cache-dir PATH] [--png OUT.png]
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from social_text_intelligence.contracts import NormalizedTextInput  # noqa: E402
from social_text_intelligence.contracts.errors import (  # noqa: E402
    SocialTextIntelligenceError,
)
from social_text_intelligence.providers import (  # noqa: E402
    CardiffSentimentProvider,
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
    SamLoweEmotionProvider,
)
from social_text_intelligence.services import AnalysisService  # noqa: E402
from social_text_intelligence.services.lazy import LazyAnalysisService  # noqa: E402


def build_service(mock: bool, cache_dir: Path) -> LazyAnalysisService:
    if mock:
        return LazyAnalysisService(
            lambda: AnalysisService(
                DeterministicSentimentProvider(), DeterministicEmotionProvider()
            )
        )
    return LazyAnalysisService(
        lambda: AnalysisService(
            CardiffSentimentProvider(cache_dir=cache_dir, offline=True),
            SamLoweEmotionProvider(cache_dir=cache_dir, offline=True),
        )
    )


class Worker(QObject):
    """Runs the blocking service call off the UI thread; reports via signals."""

    done = Signal(object, float, str)  # report | None, seconds, error text

    def __init__(self, service: LazyAnalysisService) -> None:
        super().__init__()
        self._service = service

    @Slot(str)
    def run(self, text: str) -> None:
        started = time.perf_counter()
        try:
            report = self._service.analyze(NormalizedTextInput.from_text(text))
            self.done.emit(report, time.perf_counter() - started, "")
        except SocialTextIntelligenceError as error:
            self.done.emit(None, time.perf_counter() - started, str(error))


class Shell(QMainWindow):
    request = Signal(str)

    def __init__(self, service: LazyAnalysisService) -> None:
        super().__init__()
        self.setWindowTitle("STI V2 spike A (PROTOTYPE - throwaway)")
        self.text = QPlainTextEdit()
        self.text.setAccessibleName("Text to analyze")
        self.button = QPushButton("Analyze locally")
        self.button.setAccessibleName("Analyze locally")
        self.result = QLabel("No result yet")
        self.result.setAccessibleName("Analysis result")
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box = QVBoxLayout()
        for widget in (self.text, self.button, self.result):
            box.addWidget(widget)
        central = QWidget()
        central.setLayout(box)
        self.setCentralWidget(central)

        self.thread_ = QThread(self)
        self.worker = Worker(service)
        self.worker.moveToThread(self.thread_)
        self.request.connect(self.worker.run)
        self.worker.done.connect(self.on_done)
        self.thread_.start()
        self.button.clicked.connect(lambda: self.request.emit(self.text.toPlainText()))
        self.results: list[dict[str, object]] = []
        self.after_result = None  # set by the driver; runs in the UI thread

    @Slot(object, float, str)
    def on_done(self, report: object, seconds: float, error: str) -> None:
        self._render(report, seconds, error)
        if self.after_result is not None:
            self.after_result()

    def _render(self, report: object, seconds: float, error: str) -> None:
        if report is None:
            self.result.setText(f"Error: {error}")
            self.results.append({"error": error, "seconds": round(seconds, 3)})
            return
        s, e = report.sentiment, report.emotion  # type: ignore[attr-defined]
        self.result.setText(
            f"Sentiment {s.label.value} ({s.confidence:.2f}); "
            f"emotion {e.dominant_emotion.value} ({e.confidence:.2f})"
        )
        self.results.append(
            {
                "sentiment": s.label.value,
                "emotion": e.dominant_emotion.value,
                "model_rev": s.provider.revision[:8],
                "seconds": round(seconds, 3),
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--cache-dir", default="model_cache")
    parser.add_argument("--png")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    shell = Shell(build_service(args.mock, Path(args.cache_dir)))
    shell.resize(520, 320)
    shell.show()

    ticks = {"n": 0}
    tick_timer = QTimer()
    tick_timer.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))
    tick_timer.start(20)  # proves the UI event loop keeps running during inference

    texts = [
        "Thank you so much for the thoughtful help!",
        "The new update finally fixed the login bug, but it still crashes on export.",
        "Oh great, another update that deletes my saved files. Brilliant work, truly.",
    ]
    state = {"i": 0, "ticks_at_send": 0}
    ui_ticks_during: list[int] = []

    def send_next() -> None:
        if state["i"] >= len(texts):
            finish()
            return
        shell.text.setPlainText(texts[state["i"]])
        state["ticks_at_send"] = ticks["n"]
        shell.button.click()

    def after_result() -> None:
        ui_ticks_during.append(ticks["n"] - state["ticks_at_send"])
        state["i"] += 1
        QTimer.singleShot(0, send_next)

    # NOTE: a bare lambda connected to a cross-thread signal runs in the WORKER
    # thread (the first attempt of this spike deadlocked on exactly that). Use a
    # QObject slot (Shell.on_done), which Qt queues onto the UI thread.
    shell.after_result = after_result

    def finish() -> None:
        if args.png:
            shell.grab().save(args.png)
        iface = None
        try:
            from PySide6.QtGui import QAccessible

            iface = QAccessible.queryAccessibleInterface(shell.button)
        except Exception as error:  # pragma: no cover - prototype diagnostics
            iface = f"query failed: {error}"
        summary = {
            "flask_imported": "flask" in sys.modules,
            "http_server_imported": "http.server" in sys.modules or "werkzeug" in sys.modules,
            "torch_imported": "torch" in sys.modules,
            "qt_platform": os.environ.get("QT_QPA_PLATFORM"),
            "results": shell.results,
            "ui_event_loop_ticks_while_waiting": ui_ticks_during,
            "accessible_interface_for_button": "present" if iface not in (None,) and not isinstance(iface, str) and iface.isValid() else str(iface),
            "accessible_name_set": shell.button.accessibleName(),
            "socket_module_used_by_app": False,
        }
        print(json.dumps(summary, indent=2))
        shell.thread_.quit()
        shell.thread_.wait(2000)
        app.quit()

    QTimer.singleShot(100, send_next)
    QTimer.singleShot(180_000, app.quit)  # safety stop
    app.exec()
    _ = socket  # imported only to make the no-network claim explicit in review
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

