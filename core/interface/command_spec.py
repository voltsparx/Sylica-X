# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------

"""Shared command and scan-control vocabulary for read-only research workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from core.foundation.recon_modes import normalize_recon_mode


PROFILE_COMMAND_ALIASES: Final[tuple[str, ...]] = ("profile", "scan", "persona", "social")
SURFACE_COMMAND_ALIASES: Final[tuple[str, ...]] = ("surface", "domain", "asset")
FUSION_COMMAND_ALIASES: Final[tuple[str, ...]] = ("fusion", "full", "combo")
ORCHESTRATE_COMMAND_ALIASES: Final[tuple[str, ...]] = ("orchestrate", "orch")
OCR_COMMAND_ALIASES: Final[tuple[str, ...]] = ("ocr", "ocr-scan", "image-scan")


@dataclass(frozen=True)
class SurfaceScanTypeSpec:
    """Describe a supported attack-surface scan directive for authorized research."""

    identifier: str
    title: str
    summary: str
    aliases: tuple[str, ...]
    short_flag: str | None = None


@dataclass(frozen=True)
class SurfaceScanDirectives:
    """Normalized surface scan controls for read-only, authorized reconnaissance."""

    recon_mode: str
    scan_types: tuple[str, ...]
    scan_verbosity: str
    os_fingerprint_enabled: bool
    delay_seconds: float
    active_inquiry_requested: bool
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Render a JSON-safe scan-control snapshot for reporting and storage."""

        return {
            "recon_mode": self.recon_mode,
            "scan_types": list(self.scan_types),
            "scan_verbosity": self.scan_verbosity,
            "os_fingerprint_enabled": self.os_fingerprint_enabled,
            "delay_seconds": self.delay_seconds,
            "active_inquiry_requested": self.active_inquiry_requested,
            "notes": list(self.notes),
        }


SURFACE_SCAN_TYPE_SPECS: Final[tuple[SurfaceScanTypeSpec, ...]] = (
    SurfaceScanTypeSpec(
        identifier="arp",
        title="ARP Discovery",
        summary="Layer-2 host discovery for authorized local-network reconnaissance.",
        aliases=("arp", "arp-scan", "arp_discovery", "layer2"),
        short_flag="-aS",
    ),
    SurfaceScanTypeSpec(
        identifier="syn",
        title="SYN Scan",
        summary="Half-open TCP service inquiry for authorized exposure mapping.",
        aliases=("syn", "syn-scan", "half-open", "half_open"),
        short_flag="-sS",
    ),
    SurfaceScanTypeSpec(
        identifier="tcp-connect",
        title="TCP Connect Scan",
        summary="Full TCP-connect inquiry for service reachability validation.",
        aliases=("tcp-connect", "tcp_connect", "tcp", "connect"),
        short_flag="-sT",
    ),
    SurfaceScanTypeSpec(
        identifier="udp",
        title="UDP Scan",
        summary="Read-only UDP service inquiry with longer timeout expectations.",
        aliases=("udp", "udp-scan", "udp_scan"),
        short_flag="-sU",
    ),
    SurfaceScanTypeSpec(
        identifier="fin",
        title="FIN Scan",
        summary="TCP FIN behavior inquiry for authorized firewall and port-state research.",
        aliases=("fin", "fin-scan", "fin_scan"),
        short_flag="-sF",
    ),
    SurfaceScanTypeSpec(
        identifier="null",
        title="NULL Scan",
        summary="TCP no-flag inquiry for authorized firewall and port-state research.",
        aliases=("null", "null-scan", "null_scan"),
        short_flag="-sN",
    ),
    SurfaceScanTypeSpec(
        identifier="xmas",
        title="XMAS Scan",
        summary="TCP FIN/PSH/URG inquiry for authorized firewall and port-state research.",
        aliases=("xmas", "xmas-scan", "xmas_scan"),
        short_flag="-sX",
    ),
    SurfaceScanTypeSpec(
        identifier="os-fingerprint",
        title="OS Fingerprint Research",
        summary="Read-only TTL and TCP-stack inference controls for authorized host fingerprinting.",
        aliases=("os-fingerprint", "os_fingerprint", "os", "osscan", "fingerprint"),
        short_flag="-O",
    ),
    SurfaceScanTypeSpec(
        identifier="service",
        title="Service Version Inquiry",
        summary="Read-only banner and version inquiry for exposed services.",
        aliases=("service", "service-scan", "service_scan", "banner", "version"),
        short_flag="-sV",
    ),
    SurfaceScanTypeSpec(
        identifier="tls",
        title="TLS Inspection",
        summary="Read-only TLS and certificate inspection for exposed endpoints.",
        aliases=("tls", "tls-inspect", "tls_inspect", "ssl", "ssl-tls"),
        short_flag=None,
    ),
)

_SURFACE_SCAN_TYPE_ALIAS_MAP: Final[dict[str, str]] = {
    alias.casefold(): spec.identifier
    for spec in SURFACE_SCAN_TYPE_SPECS
    for alias in (spec.identifier, *spec.aliases)
}

SURFACE_ACTIVE_SCAN_TYPES: Final[frozenset[str]] = frozenset(
    {"arp", "syn", "tcp-connect", "udp", "fin", "null", "xmas", "os-fingerprint", "service", "tls"}
)


def surface_scan_type_specs() -> tuple[SurfaceScanTypeSpec, ...]:
    """Return supported scan-control specs for authorized attack-surface research."""

    return SURFACE_SCAN_TYPE_SPECS


def normalize_surface_scan_type(value: str | None) -> str | None:
    """Normalize operator scan-type aliases into supported Silica-X scan directives."""

    key = str(value or "").strip().lower().replace("_", "-")
    if not key:
        return None
    return _SURFACE_SCAN_TYPE_ALIAS_MAP.get(key.casefold())


def normalize_surface_scan_types(values: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize and deduplicate requested scan directives for authorized research."""

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values or ():
        normalized_value = normalize_surface_scan_type(str(raw_value))
        if normalized_value is None or normalized_value in seen:
            continue
        seen.add(normalized_value)
        normalized.append(normalized_value)
    return tuple(normalized)


def invalid_surface_scan_types(values: Iterable[str] | None) -> tuple[str, ...]:
    """Return unsupported scan-type values so command handlers can fail clearly."""

    invalid: list[str] = []
    for raw_value in values or ():
        text = str(raw_value).strip()
        if text and normalize_surface_scan_type(text) is None:
            invalid.append(text)
    return tuple(invalid)


def resolve_surface_scan_directives(
    *,
    recon_mode: str | None,
    requested_scan_types: Iterable[str] | None = None,
    os_fingerprint_enabled: bool = False,
    scan_verbosity: str | None = None,
    delay_seconds: float | int | None = None,
) -> SurfaceScanDirectives:
    """Resolve surface scan controls into a single read-only reconnaissance plan."""

    normalized_recon_mode = normalize_recon_mode(recon_mode)
    normalized_scan_types = list(normalize_surface_scan_types(requested_scan_types))
    if os_fingerprint_enabled and "os-fingerprint" not in normalized_scan_types:
        normalized_scan_types.append("os-fingerprint")

    normalized_verbosity = str(scan_verbosity or "standard").strip().lower() or "standard"
    if normalized_verbosity not in {"standard", "verbose"}:
        normalized_verbosity = "standard"

    try:
        normalized_delay = float(delay_seconds or 0.0)
    except (TypeError, ValueError):
        normalized_delay = 0.0
    if normalized_delay < 0.0:
        normalized_delay = 0.0

    active_requested = bool(set(normalized_scan_types) & SURFACE_ACTIVE_SCAN_TYPES) or bool(os_fingerprint_enabled)
    notes: list[str] = []
    effective_recon_mode = normalized_recon_mode
    if active_requested and normalized_recon_mode == "passive":
        effective_recon_mode = "active"
        notes.append("Active scan directives upgraded recon mode from passive to active.")
    if os_fingerprint_enabled:
        notes.append("OS fingerprinting is a read-only inference control and remains scope-gated.")
    if normalized_delay > 0.0:
        notes.append(f"Configured inter-inquiry delay: {normalized_delay:.2f}s.")

    return SurfaceScanDirectives(
        recon_mode=effective_recon_mode,
        scan_types=tuple(normalized_scan_types),
        scan_verbosity=normalized_verbosity,
        os_fingerprint_enabled=bool(os_fingerprint_enabled),
        delay_seconds=normalized_delay,
        active_inquiry_requested=active_requested,
        notes=tuple(notes),
    )
