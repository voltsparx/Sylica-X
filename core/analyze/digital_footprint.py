"""Digital footprint mapping from public profile, surface, and issue signals."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def _safe_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _safe_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    for item in value:
        token = str(item).strip()
        if token:
            rows.append(token)
    return rows


def _unique(values: Sequence[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        token = str(item).strip()
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(token)
        if len(ordered) >= limit:
            break
    return ordered


def _host_from_value(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    parsed = urlparse(token if "://" in token else f"https://{token}")
    host = parsed.netloc or parsed.path
    if "@" in host:
        host = host.split("@", maxsplit=1)[-1]
    host = host.split(":", maxsplit=1)[0].strip().lower().strip(".")
    return host


def _facets_from_bundle(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return {}
    facets = bundle.get("entity_facets")
    return dict(facets) if isinstance(facets, Mapping) else {}


def _severity_rank(level: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(str(level).upper(), 0)


def _add_connection(
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str]],
    *,
    source: str,
    target: str,
    relation: str,
) -> None:
    left = str(source).strip()
    right = str(target).strip()
    kind = str(relation).strip()
    if not left or not right or not kind:
        return
    key = (left.lower(), right.lower(), kind.lower())
    if key in seen:
        return
    seen.add(key)
    rows.append({"source": left, "target": right, "relation": kind})


def build_digital_footprint_map(
    *,
    target: str,
    mode: str,
    profile_results: Sequence[Mapping[str, Any]] | None = None,
    domain_result: Mapping[str, Any] | None = None,
    issues: Sequence[Mapping[str, Any]] | None = None,
    intelligence_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a monitoring-friendly digital-footprint map from collected public signals."""

    target_label = str(target or "").strip() or "target"
    found_profiles = [
        row for row in _safe_rows(list(profile_results or []))
        if str(row.get("status", "")).strip().upper() == "FOUND"
    ]
    issue_rows = _safe_rows(list(issues or []))
    facets = _facets_from_bundle(intelligence_bundle)

    emails = _safe_text_list(facets.get("emails"))
    phones = _safe_text_list(facets.get("phones"))
    names = _safe_text_list(facets.get("names"))
    mentions = _safe_text_list(facets.get("mentions"))
    if not emails:
        emails = [
            str(email).strip().lower()
            for row in found_profiles
            for email in _safe_text_list(((row.get("contacts") or {}) if isinstance(row.get("contacts"), dict) else {}).get("emails"))
            if "@" in str(email)
        ]
    if not phones:
        phones = [
            str(phone).strip()
            for row in found_profiles
            for phone in _safe_text_list(((row.get("contacts") or {}) if isinstance(row.get("contacts"), dict) else {}).get("phones"))
        ]
    if not mentions:
        mentions = [
            str(mention).strip().lstrip("@")
            for row in found_profiles
            for mention in _safe_text_list(row.get("mentions"))
        ]

    external_links = [
        str(link).strip()
        for row in found_profiles
        for link in _safe_text_list(row.get("links"))
    ]
    external_domains = _unique([_host_from_value(link) for link in external_links], limit=40)

    normalized_domain_result = dict(domain_result) if isinstance(domain_result, Mapping) else {}
    primary_domain = str(normalized_domain_result.get("target") or "").strip().lower()
    resolved_addresses = _unique(_safe_text_list(normalized_domain_result.get("resolved_addresses")), limit=24)
    subdomains = _unique(_safe_text_list(normalized_domain_result.get("subdomains")), limit=50)

    source_lanes: Counter[str] = Counter()
    if found_profiles:
        source_lanes["social"] = len(found_profiles)
    if external_domains:
        source_lanes["web"] = len(external_domains)
    if issue_rows:
        source_lanes["exposure"] = len(issue_rows)
    if primary_domain or subdomains or resolved_addresses:
        source_lanes["surface"] = len(subdomains) + len(resolved_addresses) + (1 if primary_domain else 0)

    connections: list[dict[str, str]] = []
    seen_connections: set[tuple[str, str, str]] = set()

    for row in found_profiles[:24]:
        platform = str(row.get("platform") or "profile").strip() or "profile"
        profile_url = str(row.get("url") or "").strip()
        profile_node = f"profile:{platform.lower()}"
        _add_connection(connections, seen_connections, source=target_label, target=profile_node, relation="profile_presence")
        if profile_url:
            _add_connection(connections, seen_connections, source=profile_node, target=profile_url, relation="profile_url")
        for domain in [_host_from_value(link) for link in _safe_text_list(row.get("links"))][:4]:
            if domain:
                _add_connection(connections, seen_connections, source=profile_node, target=domain, relation="linked_domain")

    for email in _unique(emails, limit=12):
        _add_connection(connections, seen_connections, source=target_label, target=email, relation="contact_email")
    for phone in _unique(phones, limit=8):
        _add_connection(connections, seen_connections, source=target_label, target=phone, relation="contact_phone")
    for mention in _unique([item.lstrip("@") for item in mentions], limit=12):
        _add_connection(connections, seen_connections, source=target_label, target=f"@{mention}", relation="handle_mention")
    for name in _unique(names, limit=8):
        _add_connection(connections, seen_connections, source=target_label, target=name, relation="identity_name")

    if primary_domain:
        _add_connection(connections, seen_connections, source=target_label, target=primary_domain, relation="owned_domain")
        for subdomain in subdomains[:18]:
            _add_connection(connections, seen_connections, source=primary_domain, target=subdomain, relation="subdomain")
        for address in resolved_addresses[:12]:
            _add_connection(connections, seen_connections, source=primary_domain, target=address, relation="resolved_address")

    threat_indicators: list[dict[str, Any]] = []
    for row in sorted(issue_rows, key=lambda item: -_severity_rank(str(item.get("severity", "INFO"))))[:10]:
        threat_indicators.append(
            {
                "title": str(row.get("title") or "Exposure finding").strip() or "Exposure finding",
                "severity": str(row.get("severity") or "INFO").strip().upper() or "INFO",
                "scope": str(row.get("scope") or mode).strip() or mode,
                "evidence": str(row.get("evidence") or "").strip(),
            }
        )

    if len(found_profiles) >= 6:
        threat_indicators.append(
            {
                "title": "Broad public account presence",
                "severity": "LOW",
                "scope": "profile",
                "evidence": f"{len(found_profiles)} confirmed profile endpoints expose the same target identity.",
            }
        )
    if len(external_domains) >= 5:
        threat_indicators.append(
            {
                "title": "Wide linked-domain spread",
                "severity": "MEDIUM",
                "scope": "profile",
                "evidence": f"Profiles reference {len(external_domains)} unique external domains.",
            }
        )
    if len(_unique(emails, limit=20)) + len(_unique(phones, limit=20)) >= 3:
        threat_indicators.append(
            {
                "title": "Multi-contact exposure",
                "severity": "MEDIUM",
                "scope": "identity",
                "evidence": "Multiple contact artifacts were exposed across collected public sources.",
            }
        )
    if len(subdomains) >= 15:
        threat_indicators.append(
            {
                "title": "Expanded surface inventory",
                "severity": "MEDIUM",
                "scope": "surface",
                "evidence": f"{len(subdomains)} subdomains were observed for the associated domain.",
            }
        )

    watchlist = {
        "handles": _unique([target_label, *[item.lstrip("@") for item in mentions]], limit=12),
        "emails": _unique(emails, limit=12),
        "phones": _unique(phones, limit=8),
        "names": _unique(names, limit=8),
        "domains": _unique([primary_domain, *external_domains, *subdomains], limit=20),
        "profile_urls": _unique([str(row.get("url") or "").strip() for row in found_profiles], limit=20),
    }

    platforms: list[dict[str, Any]] = []
    for row in found_profiles[:20]:
        platforms.append(
            {
                "platform": str(row.get("platform") or "Unknown"),
                "url": str(row.get("url") or ""),
                "confidence": int(row.get("confidence", 0) or 0),
                "status": str(row.get("status") or "FOUND"),
            }
        )

    return {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "mode": str(mode or "profile"),
        "target": target_label,
        "summary": {
            "profile_count": len(found_profiles),
            "contact_count": len(_unique(emails, limit=50)) + len(_unique(phones, limit=50)),
            "external_domain_count": len(external_domains),
            "surface_asset_count": len(subdomains) + len(resolved_addresses) + (1 if primary_domain else 0),
            "risk_signal_count": len(threat_indicators),
            "connection_count": len(connections),
        },
        "source_lanes": dict(source_lanes),
        "platforms": platforms,
        "identity_cluster": {
            "names": _unique(names, limit=8),
            "handles": _unique([item.lstrip("@") for item in mentions], limit=12),
            "emails": _unique(emails, limit=12),
            "phones": _unique(phones, limit=8),
        },
        "linked_infrastructure": {
            "primary_domain": primary_domain,
            "external_domains": external_domains,
            "subdomains": subdomains,
            "resolved_addresses": resolved_addresses,
        },
        "connection_paths": connections[:60],
        "threat_indicators": threat_indicators[:12],
        "watchlist": watchlist,
        "live_monitoring": {
            "ready": bool(connections),
            "update_model": "per-run snapshot with live dashboard support",
            "command_hints": [
                f"live {target_label}",
                f"profile {target_label}" if not primary_domain else f"fusion {target_label} {primary_domain}",
            ],
        },
    }
