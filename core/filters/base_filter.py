"""Base filter contract for post-capability refinement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from core.domain import BaseEntity


class BaseFilter(ABC):
    """Stateless filter interface operating on entity collections."""

    filter_id: str = "base"

    @abstractmethod
    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        """Apply filter and return a new entity list."""
