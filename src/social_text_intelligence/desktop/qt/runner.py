"""The one job runner: worker threads in, queued signal back to the UI thread.

Results never reach a widget through a bare lambda connected to a cross-thread
signal (the deadlock found in Architecture spike A). Everything is posted through
one ``QObject`` slot that lives on the UI thread, so it always runs there.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class QtJobRunner(QObject):
    _call_on_ui = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: list[threading.Thread] = []
        self._call_on_ui.connect(self._invoke)

    @Slot(object)
    def _invoke(self, call: Callable[[], None]) -> None:
        call()

    def post(self, call: Callable[[], None]) -> None:
        """Run ``call`` on the UI thread; safe from any thread."""

        self._call_on_ui.emit(call)

    def run(self, work: Callable[[], Any], deliver: Callable[[Any], None]) -> None:
        """Run ``work`` off the UI thread, then ``deliver(result_or_error)`` on it."""

        def target() -> None:
            try:
                outcome: Any = work()
            except BaseException as error:  # delivered, never raised in the worker
                outcome = error
            self.post(lambda: deliver(outcome))

        thread = threading.Thread(target=target, name="sti-worker")
        self._threads = [t for t in self._threads if t.is_alive()]
        self._threads.append(thread)
        thread.start()

    def wait_idle(self, timeout: float = 10.0) -> bool:
        """Join the workers (used at shutdown); False if one is still running."""

        for thread in tuple(self._threads):
            thread.join(timeout)
        return not any(t.is_alive() for t in self._threads)
