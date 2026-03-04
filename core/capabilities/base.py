"""Base capability contract for modular orchestration features."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from core.domain import BaseEntity


class Capability(ABC):
    """Abstract capability contract used by orchestrator."""

    capability_id: str = "base"

    @abstractmethod
    async def execute(self, target: str, context: Mapping[str, Any]) -> list[BaseEntity]:
        """Execute capability and return normalized entities."""

    @abstractmethod
    def supported_entities(self) -> tuple[type[BaseEntity], ...]:
        """Return entity classes emitted by this capability."""
