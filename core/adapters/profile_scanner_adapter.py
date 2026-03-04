"""Adapter for profile intelligence scanner to entity conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.collect.scanner import scan_username
from core.domain import EmailEntity, ProfileEntity, make_entity_id


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
    ) -> list[ProfileEntity | EmailEntity]:
        rows = await scan_username(
            username=username,
            proxy_url=proxy_url,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            source_profile=source_profile,
            max_platforms=max_platforms,
        )

        timestamp = datetime.now(tz=timezone.utc)
        entities: list[ProfileEntity | EmailEntity] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            platform = str(row.get("platform", "unknown"))
            profile_url = str(row.get("url", ""))
            status = str(row.get("status", "UNKNOWN"))
            confidence = max(0.0, min(float(row.get("confidence", 0)) / 100.0, 1.0))
            profile_entity_id = make_entity_id("profile", platform, f"{username}:{profile_url}")

            attributes: dict[str, Any] = {
                "status": status,
                "context": row.get("context"),
                "http_status": row.get("http_status"),
                "response_time_ms": row.get("response_time_ms"),
                "links": list(row.get("links", [])),
                "mentions": list(row.get("mentions", [])),
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

            contacts = row.get("contacts") if isinstance(row.get("contacts"), dict) else {}
            email_values = contacts.get("emails") if isinstance(contacts.get("emails"), list) else []
            for email in email_values:
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

        return entities
