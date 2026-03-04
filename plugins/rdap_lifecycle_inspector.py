"""Plugin: inspect RDAP lifecycle signals for registrar governance risk."""

from __future__ import annotations

from datetime import datetime, timezone


PLUGIN_SPEC = {
    "id": "rdap_lifecycle_inspector",
    "title": "RDAP Lifecycle Inspector",
    "description": "Evaluates RDAP status, nameserver metadata, and change recency to surface domain governance risk.",
    "scopes": ["surface", "fusion"],
    "aliases": ["rdap_inspector", "domain_lifecycle", "rdap_governance"],
    "version": "1.0",
}


RISKY_STATUS_TOKENS = {
    "inactive",
    "suspended",
    "pending delete",
    "redemption period",
    "client hold",
    "server hold",
}


def _parse_datetime(value: str) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def run(context: dict) -> dict:
    domain_result = context.get("domain_result") or {}
    rdap = domain_result.get("rdap", {}) or {}
    if not isinstance(rdap, dict) or not rdap:
        return {
            "severity": "MEDIUM",
            "summary": "RDAP lifecycle inspector could not evaluate registrar metadata (RDAP data missing).",
            "highlights": ["rdap_available=false", "governance_score=0"],
            "data": {
                "rdap_available": False,
                "risky_status_tokens": [],
                "governance_score": 0,
            },
        }

    statuses = [str(item).strip().lower() for item in (rdap.get("status", []) or []) if str(item).strip()]
    risky_statuses = [token for token in statuses if any(risk in token for risk in RISKY_STATUS_TOKENS)]
    nameservers = [str(item).strip().lower() for item in (rdap.get("name_servers", []) or []) if str(item).strip()]
    last_changed = _parse_datetime(str(rdap.get("last_changed", "")))

    age_days = -1
    if last_changed is not None:
        age_days = max(0, int((datetime.now(timezone.utc) - last_changed).total_seconds() // 86400))

    risk_score = 0
    if risky_statuses:
        risk_score += min(45, len(risky_statuses) * 18)
    if not nameservers:
        risk_score += 20
    if age_days > 3650:
        risk_score += 25
    elif age_days > 1825:
        risk_score += 15
    elif age_days > 730:
        risk_score += 8
    if not str(rdap.get("handle", "")).strip():
        risk_score += 8
    risk_score = min(100, risk_score)
    governance_score = max(0, 100 - risk_score)

    severity = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "INFO"
    summary = (
        f"RDAP lifecycle inspection found status_count={len(statuses)}, risky_status={len(risky_statuses)}, "
        f"nameservers={len(nameservers)}, last_changed_days={age_days if age_days >= 0 else 'unknown'}, "
        f"governance_score={governance_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            "rdap_available=true",
            f"status_count={len(statuses)}",
            f"risky_status={len(risky_statuses)}",
            f"nameservers={len(nameservers)}",
            f"last_changed_days={age_days if age_days >= 0 else 'unknown'}",
            f"governance_score={governance_score}",
        ],
        "data": {
            "rdap_available": True,
            "handle": rdap.get("handle"),
            "statuses": statuses,
            "risky_status_tokens": risky_statuses,
            "nameservers": nameservers,
            "last_changed_days": age_days if age_days >= 0 else None,
            "governance_score": governance_score,
            "risk_score": risk_score,
        },
    }
