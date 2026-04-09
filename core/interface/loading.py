# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Terminal loading helpers for startup diagnostics."""

from __future__ import annotations

from collections.abc import Callable
import sys
import threading
import time
from typing import Protocol, TypeVar


_T = TypeVar("_T")
_DEFAULT_FRAMES = ("/", "-", "\\", "|")


class SpinnerStream(Protocol):
    def write(self, text: str) -> object: ...

    def flush(self) -> object: ...

    def isatty(self) -> bool: ...


def spinner_frames() -> tuple[str, ...]:
    """Return the Metasploit-style spinner cycle used at startup."""

    return _DEFAULT_FRAMES


class ConsoleSpinner:
    """Render a lightweight terminal spinner while a task is running."""

    def __init__(
        self,
        message: str,
        *,
        interval: float = 0.10,
        stream: SpinnerStream | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.message = str(message)
        self.interval = max(0.05, float(interval))
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = self._resolve_enabled(enabled)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _resolve_enabled(self, enabled: bool | None) -> bool:
        if enabled is not None:
            return bool(enabled)
        isatty = getattr(self.stream, "isatty", None)
        return bool(callable(isatty) and isatty())

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._spin, name="silica_x_spinner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval * 4)
        clear_width = len(self.message) + 4
        self.stream.write("\r" + (" " * clear_width) + "\r")
        flush = getattr(self.stream, "flush", None)
        if callable(flush):
            flush()
        self._thread = None

    def _spin(self) -> None:
        flush = getattr(self.stream, "flush", None)
        while not self._stop.is_set():
            for frame in spinner_frames():
                if self._stop.is_set():
                    return
                self.stream.write(f"\r{self.message}{frame}")
                if callable(flush):
                    flush()
                time.sleep(self.interval)

    def __enter__(self) -> ConsoleSpinner:
        self.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.stop()


def run_with_spinner(
    message: str,
    func: Callable[[], _T],
    *,
    interval: float = 0.10,
    stream: SpinnerStream | None = None,
    enabled: bool | None = None,
) -> _T:
    """Execute a function while rendering a terminal spinner when possible."""

    with ConsoleSpinner(message, interval=interval, stream=stream, enabled=enabled):
        return func()
