"""Adapter for profile intelligence scanner to entity conversion."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from core.collect.scanner import scan_username
from core.domain import AssetEntity, EmailEntity, ProfileEntity, make_entity_id


_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]{1,24}(?:\s+[A-Z][a-z]{1,24}){1,2})\b")
_PHONE_DIGITS = re.compile(r"\d")


def _extract_name_candidates(text: str) -> list[str]:
    values: list[str] = []
    for match in _NAME_PATTERN.findall(str(text or "")):
        token = " ".join(part for part in str(match).strip().split() if part)
        if token:
            values.append(token)
    seen: set[str] = set()
    deduped: list[str] = []
    for item in values:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(item)
        if len(deduped) >= 8:
            break
    return deduped


def _normalize_phone(raw: str) -> str:
    digits = "".join(_PHONE_DIGITS.findall(str(raw)))
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


class ProfileScannerAdapter:
    """Wrap profile scanner and normalize output into entity objects."""

    async def collect(
        self,
        username: str,
        *,
        timeout_seconds: int,
        max_concurrency: int,
        source_profile: str,
        max_platforms: int | None,
        proxy_url: str | None,
    ) -> list[ProfileEntity | EmailEntity | AssetEntity]:
        rows = await scan_username(
            username=username,
            proxy_url=proxy_url,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            source_profile=source_profile,
            max_platforms=max_platforms,
        )

        timestamp = datetime.now(tz=timezone.utc)
        found_platform_count = sum(1 for row in rows if str(row.get("status", "")).upper() == "FOUND")
        entities: list[ProfileEntity | EmailEntity | AssetEntity] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            platform = str(row.get("platform", "unknown"))
            profile_url = str(row.get("url", ""))
            status = str(row.get("status", "UNKNOWN"))
            confidence = max(0.0, min(float(row.get("confidence", 0)) / 100.0, 1.0))
            profile_entity_id = make_entity_id("profile", platform, f"{username}:{profile_url}")
            contacts_raw = row.get("contacts")
            contacts = contacts_raw if isinstance(contacts_raw, dict) else {}
            emails_raw = contacts.get("emails")
            emails = [item for item in emails_raw if isinstance(item, str)] if isinstance(emails_raw, list) else []
            phones_raw = contacts.get("phones")
            phones = [item for item in phones_raw if isinstance(item, str)] if isinstance(phones_raw, list) else []
            links_raw = row.get("links")
            links = [item for item in links_raw if isinstance(item, str)] if isinstance(links_raw, list) else []
            mentions_raw = row.get("mentions")
            mentions = [item for item in mentions_raw if isinstance(item, str)] if isinstance(mentions_raw, list) else []
            bio = str(row.get("bio") or "")
            identity_names = _extract_name_candidates(bio)

            attributes: dict[str, Any] = {
                "status": status,
                "context": row.get("context"),
                "http_status": row.get("http_status"),
                "response_time_ms": row.get("response_time_ms"),
                "links": links,
                "mentions": mentions,
                "contacts": {"emails": emails, "phones": phones},
                "bio": bio,
                "identity_names": identity_names,
                "platform_count": found_platform_count,
            }

            entities.append(
                ProfileEntity(
                    id=profile_entity_id,
                    value=username,
                    source=platform,
                    timestamp=timestamp,
                    confidence=confidence,
                    attributes=attributes,
                    platform=platform,
                    profile_url=profile_url,
                    status=status,
                )
            )

            for email in emails:
                if not isinstance(email, str) or "@" not in email:
                    continue
                email_domain = email.rsplit("@", maxsplit=1)[-1].strip().lower()
                entities.append(
                    EmailEntity(
                        id=make_entity_id("email", platform, email),
                        value=email.strip().lower(),
                        source=platform,
                        timestamp=timestamp,
                        confidence=min(1.0, confidence + 0.1),
                        attributes={"owner": username, "from_profile_url": profile_url},
                        relationships=(profile_entity_id,),
                        email_domain=email_domain,
                    )
                )

            for raw_phone in phones:
                if not isinstance(raw_phone, str):
                    continue
                normalized_phone = _normalize_phone(raw_phone)
                if not normalized_phone:
                    continue
                entities.append(
                    AssetEntity(
                        id=make_entity_id("asset", platform, f"phone:{normalized_phone}"),
                        value=normalized_phone,
                        source=platform,
                        timestamp=timestamp,
                        confidence=min(1.0, confidence + 0.05),
                        attributes={
                            "owner": username,
                            "raw_phone": raw_phone,
                            "from_profile_url": profile_url,
                            "asset_kind": "contact_phone",
                        },
                        relationships=(profile_entity_id,),
                        asset_kind="contact_phone",
                    )
                )

            for name in identity_names:
                entities.append(
                    AssetEntity(
                        id=make_entity_id("asset", platform, f"name:{name.lower()}"),
                        value=name,
                        source=platform,
                        timestamp=timestamp,
                        confidence=min(1.0, confidence + 0.06),
                        attributes={
                            "owner": username,
                            "from_profile_url": profile_url,
                            "identity_names": [name],
                            "asset_kind": "identity_name",
                        },
                        relationships=(profile_entity_id,),
                        asset_kind="identity_name",
                    )
                )

        return entities
