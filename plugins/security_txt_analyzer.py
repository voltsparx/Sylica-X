"""Plugin: analyze /.well-known/security.txt disclosure posture."""

from __future__ import annotations

from datetime import datetime, timezone


PLUGIN_SPEC = {
    "id": "security_txt_analyzer",
    "title": "Security.txt Analyzer",
    "description": "Parses security.txt content for disclosure channels and policy completeness.",
    "scopes": ["surface"],
    "aliases": ["securitytxt", "disclosure_policy", "vdp_policy"],
    "version": "1.0",
}


EXPECTED_FIELDS = ("Contact", "Expires", "Encryption", "Policy", "Acknowledgments", "Canonical")


def _parse_fields(preview: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for raw_line in str(preview or "").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        fields.setdefault(key, []).append(value)
    return fields


def _parse_expiry(value: str) -> datetime | None:
    token = str(value).strip()
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
    present = bool(domain_result.get("security_txt_present"))
    preview = str(domain_result.get("security_preview") or "")
    fields = _parse_fields(preview)

    has_contact = bool(fields.get("Contact"))
    has_expires = bool(fields.get("Expires"))
    expiry_state = "unknown"
    if has_expires:
        expiry_values = fields.get("Expires") or []
        parsed = _parse_expiry(expiry_values[0] if expiry_values else "")
        if parsed is not None:
            expiry_state = "expired" if parsed < datetime.now(timezone.utc) else "valid"

    score = 0
    if present:
        score += 50
    if has_contact:
        score += 20
    if has_expires:
        score += 10
    if fields.get("Policy"):
        score += 10
    if fields.get("Encryption"):
        score += 10
    if expiry_state == "expired":
        score = max(0, score - 25)
    score = min(100, score)

    if not present:
        severity = "MEDIUM"
    elif expiry_state == "expired":
        severity = "HIGH"
    elif score < 60:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    missing = [name for name in EXPECTED_FIELDS if not fields.get(name)]
    highlights = [
        f"present={present}",
        f"contact={has_contact}",
        f"expires={has_expires}",
        f"expiry_state={expiry_state}",
        f"score={score}",
    ]
    highlights.extend([f"missing:{name}" for name in missing[:4]])

    summary = (
        f"security.txt posture score={score} with {len(fields)} parsed field group(s); "
        f"missing expected fields: {len(missing)}. Presence of security.txt indicates a defined vulnerability disclosure process."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "security_txt_present": present,
            "parsed_fields": fields,
            "missing_fields": missing,
            "expiry_state": expiry_state,
            "readiness_score": score,
        },
    }
