"""Domain entities and strict data contracts for orchestration layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
import hashlib


def make_entity_id(kind: str, source: str, value: str) -> str:
    """Build a stable entity identifier from semantic keys."""

    material = f"{kind.strip().lower()}::{source.strip().lower()}::{value.strip().lower()}"
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:14]
    return f"{kind.strip().lower()}-{digest}"


@dataclass(frozen=True)
class BaseEntity:
    """Base immutable entity shared across capability outputs."""

    id: str
    value: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    confidence: float = 0.0
    attributes: Mapping[str, Any] = field(default_factory=dict)
    entity_type: str = field(default="base", init=False)

    def __post_init__(self) -> None:
        clamped_confidence = max(0.0, min(float(self.confidence), 1.0))
        object.__setattr__(self, "confidence", clamped_confidence)

        timestamp = self.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            object.__setattr__(self, "timestamp", timestamp)

        frozen_attributes = MappingProxyType(dict(self.attributes))
        object.__setattr__(self, "attributes", frozen_attributes)

    def as_dict(self) -> dict[str, Any]:
        """Convert entity into a JSON-friendly dictionary."""

        payload = dict(self.attributes)
        payload.update(
            {
                "id": self.id,
                "value": self.value,
                "source": self.source,
                "timestamp": self.timestamp.isoformat(),
                "confidence": self.confidence,
                "entity_type": self.entity_type,
            }
        )
        return payload


@dataclass(frozen=True)
class ProfileEntity(BaseEntity):
    """Entity representing a discovered profile signal."""

    platform: str = ""
    profile_url: str = ""
    status: str = "unknown"
    entity_type: str = field(default="profile", init=False)


@dataclass(frozen=True)
class DomainEntity(BaseEntity):
    """Entity representing primary domain intelligence."""

    domain: str = ""
    entity_type: str = field(default="domain", init=False)


@dataclass(frozen=True)
class EmailEntity(BaseEntity):
    """Entity representing an email address artifact."""

    email_domain: str = ""
    entity_type: str = field(default="email", init=False)


@dataclass(frozen=True)
class IpEntity(BaseEntity):
    """Entity representing an IPv4/IPv6 artifact."""

    ip_version: str = "unknown"
    entity_type: str = field(default="ip", init=False)


@dataclass(frozen=True)
class AssetEntity(BaseEntity):
    """Entity representing a generic infrastructure or web asset."""

    asset_kind: str = "asset"
    entity_type: str = field(default="asset", init=False)
