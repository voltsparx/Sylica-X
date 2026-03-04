"""Entity builders for intelligence analysis without re-collecting data."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from core.collect.domain_intel import normalize_domain
from core.domain import AssetEntity, BaseEntity, DomainEntity, EmailEntity, IpEntity, ProfileEntity, make_entity_id


_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]{1,24}(?:\s+[A-Z][a-z]{1,24}){1,2})\b")
_NAME_LABEL_PATTERN = re.compile(r"(?:^|\b)(?:name|full name)\s*[:=-]\s*([A-Za-z][A-Za-z .'-]{2,60})", re.IGNORECASE)
_PHONE_DIGIT_PATTERN = re.compile(r"\d")


def _safe_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if isinstance(item, str) and str(item).strip()]


def _clamp_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, numeric))


def _normalize_phone(raw: str) -> str:
    digits = "".join(_PHONE_DIGIT_PATTERN.findall(str(raw)))
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def extract_name_candidates(text: str) -> list[str]:
    """Extract lightweight person-name candidates from free text."""

    content = str(text or "").strip()
    if not content:
        return []

    candidates: list[str] = []
    for match in _NAME_LABEL_PATTERN.findall(content):
        token = " ".join(part for part in str(match).strip().split() if part)
        if token:
            candidates.append(token)

    for match in _NAME_PATTERN.findall(content):
        token = " ".join(part for part in str(match).strip().split() if part)
        if token:
            candidates.append(token)

    seen: set[str] = set()
    deduped: list[str] = []
    for item in candidates:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(item)
        if len(deduped) >= 8:
            break
    return deduped


def build_profile_entities(username: str, results: list[dict[str, Any]]) -> list[BaseEntity]:
    """Convert profile-scan rows into normalized entities."""

    target = str(username or "").strip()
    timestamp = datetime.now(tz=timezone.utc)
    found_platform_count = sum(1 for row in results if str(row.get("status", "")).upper() == "FOUND")

    entities: list[BaseEntity] = []
    seen_entity_ids: set[str] = set()

    def _append(entity: BaseEntity) -> None:
        if entity.id in seen_entity_ids:
            return
        seen_entity_ids.add(entity.id)
        entities.append(entity)

    for index, row in enumerate(results):
        if not isinstance(row, dict):
            continue
        platform = str(row.get("platform") or "unknown").strip() or "unknown"
        profile_url = str(row.get("url") or "").strip()
        status = str(row.get("status") or "UNKNOWN").strip().upper() or "UNKNOWN"
        confidence = _clamp_confidence(row.get("confidence", 0))
        bio = str(row.get("bio") or "").strip()
        mentions = _safe_list(row.get("mentions"))
        links = _safe_list(row.get("links"))
        contacts = row.get("contacts") if isinstance(row.get("contacts"), dict) else {}
        emails = _safe_list((contacts or {}).get("emails"))
        phones = _safe_list((contacts or {}).get("phones"))
        name_candidates = extract_name_candidates(bio)

        id_seed = f"{target}:{profile_url}" if profile_url else f"{target}:{platform}:{index}"
        profile_entity_id = make_entity_id("profile", platform, id_seed)
        profile_entity = ProfileEntity(
            id=profile_entity_id,
            value=target or str(row.get("username") or "").strip(),
            source=platform,
            timestamp=timestamp,
            confidence=confidence,
            attributes={
                "status": status,
                "context": row.get("context"),
                "http_status": row.get("http_status"),
                "response_time_ms": row.get("response_time_ms"),
                "links": links,
                "mentions": mentions,
                "contacts": {"emails": emails, "phones": phones},
                "bio": bio,
                "identity_names": name_candidates,
                "platform_count": found_platform_count,
            },
            platform=platform,
            profile_url=profile_url,
            status=status,
        )
        _append(profile_entity)

        for email in emails:
            if "@" not in email:
                continue
            value = email.strip().lower()
            if not value:
                continue
            email_domain = value.rsplit("@", maxsplit=1)[-1].strip().lower()
            _append(
                EmailEntity(
                    id=make_entity_id("email", platform, value),
                    value=value,
                    source=platform,
                    timestamp=timestamp,
                    confidence=min(1.0, confidence + 0.1),
                    attributes={
                        "owner": target,
                        "from_profile_url": profile_url,
                        "email_domain": email_domain,
                    },
                    relationships=(profile_entity_id,),
                    email_domain=email_domain,
                )
            )

        for raw_phone in phones:
            normalized_phone = _normalize_phone(raw_phone)
            if not normalized_phone:
                continue
            _append(
                AssetEntity(
                    id=make_entity_id("asset", platform, f"phone:{normalized_phone}"),
                    value=normalized_phone,
                    source=platform,
                    timestamp=timestamp,
                    confidence=min(1.0, confidence + 0.05),
                    attributes={
                        "owner": target,
                        "raw_phone": raw_phone,
                        "from_profile_url": profile_url,
                        "asset_kind": "contact_phone",
                    },
                    relationships=(profile_entity_id,),
                    asset_kind="contact_phone",
                )
            )

        for name in name_candidates:
            value = " ".join(part for part in name.split() if part)
            if not value:
                continue
            _append(
                AssetEntity(
                    id=make_entity_id("asset", platform, f"name:{value.lower()}"),
                    value=value,
                    source=platform,
                    timestamp=timestamp,
                    confidence=min(1.0, confidence + 0.06),
                    attributes={
                        "owner": target,
                        "from_profile_url": profile_url,
                        "asset_kind": "identity_name",
                        "identity_names": [value],
                    },
                    relationships=(profile_entity_id,),
                    asset_kind="identity_name",
                )
            )

    return entities


def build_surface_entities(domain_result: dict[str, Any]) -> list[BaseEntity]:
    """Convert domain-surface payload to normalized entities."""

    target = normalize_domain(str(domain_result.get("target") or ""))
    if not target:
        return []

    timestamp = datetime.now(tz=timezone.utc)
    domain_entity_id = make_entity_id("domain", "surface", target)
    https_data = dict(domain_result.get("https", {}) or {})
    http_data = dict(domain_result.get("http", {}) or {})
    rdap_data = dict(domain_result.get("rdap", {}) or {})

    entities: list[BaseEntity] = [
        DomainEntity(
            id=domain_entity_id,
            value=target,
            source="surface",
            timestamp=timestamp,
            confidence=0.85 if https_data.get("status") else 0.55,
            attributes={
                "resolved_addresses": _safe_list(domain_result.get("resolved_addresses")),
                "https": https_data,
                "http": http_data,
                "rdap": rdap_data,
                "scan_notes": _safe_list(domain_result.get("scan_notes")),
                "robots_txt_present": bool(domain_result.get("robots_txt_present")),
                "security_txt_present": bool(domain_result.get("security_txt_present")),
            },
            domain=target,
        )
    ]

    for address in _safe_list(domain_result.get("resolved_addresses")):
        ip_version = "ipv6" if ":" in address else "ipv4"
        entities.append(
            IpEntity(
                id=make_entity_id("ip", "dns", address),
                value=address,
                source="dns",
                timestamp=timestamp,
                confidence=0.8,
                attributes={"domain": target},
                relationships=(domain_entity_id,),
                ip_version=ip_version,
            )
        )

    for subdomain in _safe_list(domain_result.get("subdomains")):
        entities.append(
            AssetEntity(
                id=make_entity_id("asset", "ct", subdomain),
                value=subdomain,
                source="certificate_transparency",
                timestamp=timestamp,
                confidence=0.74,
                attributes={"asset_kind": "subdomain", "parent_domain": target},
                relationships=(domain_entity_id,),
                asset_kind="subdomain",
            )
        )

    for nameserver in _safe_list(rdap_data.get("name_servers")):
        entities.append(
            AssetEntity(
                id=make_entity_id("asset", "rdap", f"ns:{nameserver}"),
                value=nameserver,
                source="rdap",
                timestamp=timestamp,
                confidence=0.72,
                attributes={"asset_kind": "nameserver", "parent_domain": target},
                relationships=(domain_entity_id,),
                asset_kind="nameserver",
            )
        )

    if bool(domain_result.get("robots_txt_present")):
        entities.append(
            AssetEntity(
                id=make_entity_id("asset", "http", f"robots:{target}"),
                value=f"https://{target}/robots.txt",
                source="http_probe",
                timestamp=timestamp,
                confidence=0.74,
                attributes={
                    "asset_kind": "robots_txt",
                    "preview": str(domain_result.get("robots_preview") or ""),
                },
                relationships=(domain_entity_id,),
                asset_kind="robots_txt",
            )
        )

    if bool(domain_result.get("security_txt_present")):
        entities.append(
            AssetEntity(
                id=make_entity_id("asset", "http", f"security:{target}"),
                value=f"https://{target}/.well-known/security.txt",
                source="http_probe",
                timestamp=timestamp,
                confidence=0.78,
                attributes={
                    "asset_kind": "security_txt",
                    "preview": str(domain_result.get("security_preview") or ""),
                },
                relationships=(domain_entity_id,),
                asset_kind="security_txt",
            )
        )

    return entities


def build_fusion_entities(
    username: str,
    profile_results: list[dict[str, Any]],
    domain_result: dict[str, Any] | None,
) -> list[BaseEntity]:
    """Build combined entity list for fusion intelligence analysis."""

    items = build_profile_entities(username, profile_results)
    if isinstance(domain_result, dict):
        items.extend(build_surface_entities(domain_result))

    deduped: list[BaseEntity] = []
    seen: set[str] = set()
    for entity in items:
        if entity.id in seen:
            continue
        seen.add(entity.id)
        deduped.append(entity)
    return deduped

