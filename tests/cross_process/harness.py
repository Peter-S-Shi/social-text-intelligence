"""Spawn and steer a second application instance for cross-process tests."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")
PEER = Path(__file__).with_name("peer.py")
TIMEOUT = 60.0


class Peer:
    """One peer process; ``started`` means it now holds its resource."""

    def __init__(self, scenario: str, signal: Path, **options: str) -> None:
        signal.mkdir(parents=True, exist_ok=True)
        self.signal = signal
        self._out = signal / "out.txt"
        command = [sys.executable, str(PEER), scenario, "--signal", str(signal)]
        for key, value in options.items():
            command += [f"--{key}", value]
        self._handle = self._out.open("w", encoding="utf-8")
        self._process = subprocess.Popen(
            command, stdout=self._handle, stderr=subprocess.DEVNULL
        )

    def wait_started(self) -> None:
        deadline = time.monotonic() + TIMEOUT
        while not (self.signal / "started").exists():
            if self._process.poll() is not None:
                raise AssertionError(f"peer exited early: {self.result()}")
            if time.monotonic() > deadline:
                self.kill()
                raise AssertionError("peer did not start in time")
            time.sleep(0.02)

    def release(self) -> None:
        (self.signal / "release").write_text("1")

    def kill(self) -> None:
        self._process.kill()
        self._process.wait(timeout=TIMEOUT)
        self._handle.close()

    def result(self) -> dict[str, Any]:
        try:
            self._process.wait(timeout=TIMEOUT)
        finally:
            self._handle.close()
        for line in self._out.read_text(encoding="utf-8").splitlines():
            if line.startswith("RESULT "):
                return dict(json.loads(line[7:]))
        raise AssertionError("peer reported nothing")

    def finish(self) -> dict[str, Any]:
        self.release()
        return self.result()


def eventually(
    action: Callable[[], T],
    *,
    retry_on: tuple[type[BaseException], ...] = (),
    accept: Callable[[T], bool] = lambda value: True,
    timeout: float = 10.0,
) -> T:
    """Retry ``action`` until it returns an accepted value without a retry error.

    Windows releases a killed process's file locks while it tears the process
    down, a moment after ``wait`` returns, so a freshly killed holder may still
    look held for a few milliseconds.
    """

    deadline = time.monotonic() + timeout
    while True:
        try:
            value = action()
        except retry_on:
            if time.monotonic() > deadline:
                raise
        else:
            if accept(value) or time.monotonic() > deadline:
                return value
        time.sleep(0.05)
