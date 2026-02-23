"""Filter: measure responsible-disclosure readiness signals."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "disclosure_readiness_filter",
    "title": "Disclosure Readiness Filter",
    "description": "Assesses whether targets expose clear and structured vulnerability disclosure channels.",
    "scopes": ["surface", "fusion"],
    "aliases": ["disclosure_readiness", "vdp_readiness", "securitytxt_readiness"],
    "version": "1.0",
}


def _parse_security_txt_fields(preview: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for raw_line in str(preview or "").splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        fields.setdefault(key, []).append(value)
    return fields


def run(context: dict) -> dict:
    domain_result = context.get("domain_result") or {}
    results = context.get("results", []) or []

    security_txt_present = bool(domain_result.get("security_txt_present"))
    security_fields = _parse_security_txt_fields(str(domain_result.get("security_preview") or ""))
    contact_field_present = bool(security_fields.get("Contact"))
    policy_field_present = bool(security_fields.get("Policy"))
    expires_field_present = bool(security_fields.get("Expires"))

    contact_artifacts = 0
    for row in results:
        contacts = row.get("contacts", {}) or {}
        contact_artifacts += len(contacts.get("emails", []) or [])
        contact_artifacts += len(contacts.get("phones", []) or [])

    score = 0
    if security_txt_present:
        score += 55
    if contact_field_present:
        score += 20
    if expires_field_present:
        score += 10
    if policy_field_present:
        score += 10
    if contact_artifacts > 0:
        score += 5
    score = min(100, score)

    if score >= 70:
        readiness = "strong"
        severity = "INFO"
    elif score >= 40:
        readiness = "moderate"
        severity = "MEDIUM"
    else:
        readiness = "weak"
        severity = "HIGH"

    summary = (
        f"Disclosure readiness={readiness} with score={score}. "
        f"security_txt_present={security_txt_present}, contact_field={contact_field_present}, policy_field={policy_field_present}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"readiness={readiness}",
            f"score={score}",
            f"security_txt={security_txt_present}",
            f"contact_field={contact_field_present}",
            f"policy_field={policy_field_present}",
        ],
        "data": {
            "readiness": readiness,
            "score": score,
            "security_txt_present": security_txt_present,
            "security_txt_fields": security_fields,
            "contact_artifact_count": contact_artifacts,
        },
    }
