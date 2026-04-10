# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

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


def _normalize_text(value: str | None) -> str | None:
    """Normalize optional investigator-facing text values."""

    if value is None:
        return None
    normalized = " ".join(str(value).strip().split())
    return normalized or None


def _deduplicate_terms(terms: list[str]) -> tuple[str, ...]:
    """Deduplicate ordered service query terms while preserving semantic order."""

    unique_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in terms:
        normalized_key = term.casefold()
        if normalized_key in seen_terms:
            continue
        unique_terms.append(term)
        seen_terms.add(normalized_key)
    return tuple(unique_terms)


@dataclass(frozen=True)
class BaseEntity:
    """Base immutable entity shared across capability outputs."""

    id: str
    value: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    confidence: float = 0.0
    attributes: Mapping[str, Any] = field(default_factory=dict)
    relationships: tuple[str, ...] = field(default_factory=tuple)
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
        object.__setattr__(self, "relationships", tuple(str(item) for item in self.relationships if item))

    @property
    def type(self) -> str:
        """Compatibility alias for entity type."""

        return self.entity_type

    @property
    def confidence_score(self) -> float:
        """Compatibility alias for confidence score."""

        return self.confidence

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Compatibility alias for entity metadata."""

        return self.attributes

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
                "confidence_score": self.confidence,
                "entity_type": self.entity_type,
                "type": self.entity_type,
                "metadata": dict(self.attributes),
                "relationships": list(self.relationships),
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


@dataclass(frozen=True)
class ServiceEntity(BaseEntity):
    """Entity representing an observed authorized service for read-only research."""

    authorized_host: str = ""
    port: int = 0
    transport_protocol: str = "tcp"
    service_product: str = ""
    service_vendor: str | None = None
    service_version: str | None = None
    banner_text: str | None = None
    detected_cpe: str | None = None
    entity_type: str = field(default="service", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535.")
        if not self.authorized_host.strip():
            raise ValueError("Authorized host is required.")
        if not self.service_product.strip():
            raise ValueError("Service product is required.")

        object.__setattr__(self, "authorized_host", self.authorized_host.strip())
        object.__setattr__(self, "transport_protocol", self.transport_protocol.strip().lower())
        object.__setattr__(self, "service_product", self.service_product.strip())
        object.__setattr__(self, "service_vendor", _normalize_text(self.service_vendor))
        object.__setattr__(self, "service_version", _normalize_text(self.service_version))
        object.__setattr__(self, "banner_text", _normalize_text(self.banner_text))
        object.__setattr__(self, "detected_cpe", _normalize_text(self.detected_cpe))

    @property
    def keyword_terms(self) -> tuple[str, ...]:
        """Return ordered keyword terms for read-only vulnerability matching."""

        query_terms: list[str] = []
        if self.service_vendor:
            query_terms.append(self.service_vendor)
        query_terms.append(self.service_product)
        if self.service_version:
            query_terms.append(self.service_version)
        return _deduplicate_terms(query_terms)

    @property
    def keyword_query(self) -> str:
        """Build a keyword query from observed service metadata."""

        return " ".join(self.keyword_terms)


@dataclass(frozen=True)
class VulnerabilityReference:
    """Reference URL attached to a correlated vulnerability record."""

    source: str
    url: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VulnerabilityEntity(BaseEntity):
    """Entity representing a read-only CVE correlation result."""

    cve_id: str = ""
    summary: str = ""
    severity: str = "UNKNOWN"
    cvss_base_score: float | None = None
    cwes: tuple[str, ...] = field(default_factory=tuple)
    published: str | None = None
    last_modified: str | None = None
    references: tuple[VulnerabilityReference, ...] = field(default_factory=tuple)
    entity_type: str = field(default="vulnerability", init=False)
