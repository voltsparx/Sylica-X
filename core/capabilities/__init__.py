"""Capability registry exports for orchestration layer."""

from core.capabilities.base import Capability
from core.capabilities.correlation_capability import CorrelationCapability
from core.capabilities.domain_enumeration import DomainEnumerationCapability
from core.capabilities.username_lookup import UsernameLookupCapability


def build_capability_registry() -> dict[str, Capability]:
    """Build default capability registry used by the orchestrator."""

    capabilities: list[Capability] = [
        UsernameLookupCapability(),
        DomainEnumerationCapability(),
        CorrelationCapability(),
    ]
    return {capability.capability_id: capability for capability in capabilities}


__all__ = [
    "Capability",
    "CorrelationCapability",
    "DomainEnumerationCapability",
    "UsernameLookupCapability",
    "build_capability_registry",
]
