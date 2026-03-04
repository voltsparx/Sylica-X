"""CLI UX helpers with optional Rich rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from core.interface.cli_config import PROFILE_PRESETS, SURFACE_PRESETS

try:  # pragma: no cover - optional dependency
    from rich.console import Console
    from rich.progress import Progress

    _HAS_RICH = True
except Exception:  # pragma: no cover - optional dependency
    Console = None  # type: ignore[assignment]
    Progress = None  # type: ignore[assignment]
    _HAS_RICH = False


@dataclass
class CLIUI:
    """CLI helper for progress rendering and preset loading."""

    console: Any = field(default=None)

    def __post_init__(self) -> None:
        if self.console is not None:
            return
        self.console = Console() if _HAS_RICH else None

    def render_progress(self, task_name: str, percent: int) -> None:
        bounded = max(0, min(100, int(percent)))
        if _HAS_RICH and self.console is not None:
            with Progress(console=self.console) as progress:
                task_id = progress.add_task(task_name, total=100)
                progress.update(task_id, completed=bounded)
                time.sleep(0.01)
            return

        bar_size = 20
        filled = int((bounded / 100) * bar_size)
        bar = "#" * filled + "-" * (bar_size - filled)
        print(f"{task_name}: [{bar}] {bounded}%")

    def load_profile(self, profile_name: str) -> dict[str, int]:
        name = profile_name.strip().lower()
        if name in PROFILE_PRESETS:
            return dict(PROFILE_PRESETS[name])
        if name in SURFACE_PRESETS:
            return dict(SURFACE_PRESETS[name])
        raise ValueError(f"Unknown profile preset: {profile_name}")

