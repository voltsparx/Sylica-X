"""Adapter for domain surface collector to entity conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.collect.domain_intel import normalize_domain, scan_domain_surface
from core.domain import AssetEntity, DomainEntity, IpEntity, make_entity_id


class DomainSurfaceAdapter:
    """Wrap domain intel scanner and normalize output into entity objects."""

    async def collect(
        self,
        domain: str,
        *,
        timeout_seconds: int,
        include_ct: bool,
        include_rdap: bool,
        max_subdomains: int,
    ) -> list[DomainEntity | AssetEntity | IpEntity]:
        normalized_domain = normalize_domain(domain)
        if not normalized_domain:
            return []

        payload = await scan_domain_surface(
            domain=normalized_domain,
            timeout_seconds=timeout_seconds,
            include_ct=include_ct,
            include_rdap=include_rdap,
            max_subdomains=max_subdomains,
        )

        timestamp = datetime.now(tz=timezone.utc)
        entities: list[DomainEntity | AssetEntity | IpEntity] = []

        https_data = payload.get("https") if isinstance(payload.get("https"), dict) else {}
        http_data = payload.get("http") if isinstance(payload.get("http"), dict) else {}
        domain_confidence = 0.85 if https_data.get("status") else 0.55
        domain_entity_id = make_entity_id("domain", "surface", normalized_domain)

        domain_attributes: dict[str, Any] = {
            "resolved_addresses": list(payload.get("resolved_addresses", [])),
            "https": https_data,
            "http": http_data,
            "rdap": payload.get("rdap", {}),
            "scan_notes": list(payload.get("scan_notes", [])),
            "robots_txt_present": bool(payload.get("robots_txt_present")),
            "security_txt_present": bool(payload.get("security_txt_present")),
        }
        entities.append(
            DomainEntity(
                id=domain_entity_id,
                value=normalized_domain,
                source="surface",
                timestamp=timestamp,
                confidence=domain_confidence,
                attributes=domain_attributes,
                domain=normalized_domain,
            )
        )

        for address in payload.get("resolved_addresses", []):
            if not isinstance(address, str):
                continue
            ip_version = "ipv6" if ":" in address else "ipv4"
            entities.append(
                IpEntity(
                    id=make_entity_id("ip", "dns", address),
                    value=address,
                    source="dns",
                    timestamp=timestamp,
                    confidence=0.8,
                    attributes={"domain": normalized_domain},
                    relationships=(domain_entity_id,),
                    ip_version=ip_version,
                )
            )

        for subdomain in payload.get("subdomains", []):
            if not isinstance(subdomain, str):
                continue
            entities.append(
                AssetEntity(
                    id=make_entity_id("asset", "ct", subdomain),
                    value=subdomain,
                    source="certificate_transparency",
                    timestamp=timestamp,
                    confidence=0.72,
                    attributes={"asset_kind": "subdomain", "parent_domain": normalized_domain},
                    relationships=(domain_entity_id,),
                    asset_kind="subdomain",
                )
            )

        if payload.get("robots_txt_present"):
            entities.append(
                AssetEntity(
                    id=make_entity_id("asset", "http", f"robots:{normalized_domain}"),
                    value=f"https://{normalized_domain}/robots.txt",
                    source="http_probe",
                    timestamp=timestamp,
                    confidence=0.74,
                    attributes={"preview": payload.get("robots_preview", "")},
                    relationships=(domain_entity_id,),
                    asset_kind="robots_txt",
                )
            )

        if payload.get("security_txt_present"):
            entities.append(
                AssetEntity(
                    id=make_entity_id("asset", "http", f"security:{normalized_domain}"),
                    value=f"https://{normalized_domain}/.well-known/security.txt",
                    source="http_probe",
                    timestamp=timestamp,
                    confidence=0.78,
                    attributes={"preview": payload.get("security_preview", "")},
                    relationships=(domain_entity_id,),
                    asset_kind="security_txt",
                )
            )

        return entities
