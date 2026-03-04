"""Scan lifecycle tracing primitives for orchestrated workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LifecycleEvent:
    """Immutable lifecycle event for one orchestration phase."""

    phase: str
    status: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanLifecycle:
    """Mutable lifecycle tracker with explicit phase event recording."""

    target: str
    mode: str
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    ended_at: datetime | None = None
    events: list[LifecycleEvent] = field(default_factory=list)

    def mark(self, phase: str, status: str, **metadata: Any) -> None:
        """Append a lifecycle event entry."""

        self.events.append(LifecycleEvent(phase=phase, status=status, metadata=dict(metadata)))

    def complete(self) -> None:
        """Mark lifecycle end timestamp."""

        self.ended_at = datetime.now(tz=timezone.utc)

    def as_dict(self) -> dict[str, Any]:
        """Serialize lifecycle metadata."""

        return {
            "target": self.target,
            "mode": self.mode,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "events": [
                {
                    "phase": event.phase,
                    "status": event.status,
                    "timestamp": event.timestamp.isoformat(),
                    "metadata": event.metadata,
                }
                for event in self.events
            ],
        }
