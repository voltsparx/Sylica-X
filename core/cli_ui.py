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

"""CLI UX helpers with optional Rich rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import time
from types import ModuleType
from typing import Any

from core.interface.cli_config import PROFILE_PRESETS, SURFACE_PRESETS

try:  # pragma: no cover - optional dependency
    _rich_console: ModuleType | None = importlib.import_module("rich.console")
    _rich_progress: ModuleType | None = importlib.import_module("rich.progress")
except Exception:  # pragma: no cover - optional dependency
    _rich_console = None
    _rich_progress = None

_HAS_RICH = _rich_console is not None and _rich_progress is not None


@dataclass
class CLIUI:
    """CLI helper for progress rendering and preset loading."""

    console: Any = field(default=None)

    def __post_init__(self) -> None:
        if self.console is not None:
            return
        self.console = _rich_console.Console() if _rich_console is not None else None

    def render_progress(self, task_name: str, percent: int) -> None:
        bounded = max(0, min(100, int(percent)))
        if _rich_progress is not None and self.console is not None:
            with _rich_progress.Progress(console=self.console) as progress:
                task_id = progress.add_task(task_name, total=100)
                progress.update(task_id, completed=bounded)
                time.sleep(0.01)
            return

        bar_size = 20
        filled = int((bounded / 100) * bar_size)
        bar = "#" * filled + "-" * (bar_size - filled)
        print(f"{task_name}: [{bar}] {bounded}%")

    def load_profile(self, profile_name: str) -> dict[str, object]:
        name = profile_name.strip().lower()
        if name in PROFILE_PRESETS:
            return dict(PROFILE_PRESETS[name])
        if name in SURFACE_PRESETS:
            return dict(SURFACE_PRESETS[name])
        raise ValueError(f"Unknown profile preset: {profile_name}")

