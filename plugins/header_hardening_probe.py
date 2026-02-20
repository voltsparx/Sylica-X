"""Plugin: header hardening probe."""

from __future__ import annotations


PLUGIN_SPEC = {
    "id": "header_hardening_probe",
    "title": "Header Hardening Probe",
    "description": "Performs deep security-header assessment on target HTTPS response headers.",
    "scopes": ["surface", "fusion"],
    "aliases": ["surface_header_audit", "headers", "tlsaudit"],
    "version": "1.1",
}


RECOMMENDED_HEADERS = {
    "strict-transport-security": "HSTS missing",
    "content-security-policy": "CSP missing",
    "x-content-type-options": "X-Content-Type-Options missing",
    "referrer-policy": "Referrer-Policy missing",
    "permissions-policy": "Permissions-Policy missing",
    "x-frame-options": "X-Frame-Options missing",
}


def run(context: dict) -> dict:
    domain_result = context.get("domain_result") or {}
    https_headers = (domain_result.get("https") or {}).get("headers", {}) or {}
    headers = {str(key).lower(): str(value) for key, value in https_headers.items()}

    missing = [label for key, label in RECOMMENDED_HEADERS.items() if key not in headers]
    present = [key for key in RECOMMENDED_HEADERS.keys() if key in headers]
    weak_values: list[str] = []
    if "x-frame-options" in headers and headers["x-frame-options"].upper() not in {"DENY", "SAMEORIGIN"}:
        weak_values.append("x-frame-options appears weak")
    if "strict-transport-security" in headers and "max-age=" not in headers["strict-transport-security"].lower():
        weak_values.append("strict-transport-security missing max-age")

    header_score = max(0, 100 - (len(missing) * 14) - (len(weak_values) * 8))
    severity = "HIGH" if header_score < 45 else "MEDIUM" if header_score < 70 else "INFO"

    highlights = [f"header_score={header_score}", f"missing={len(missing)}", f"present={len(present)}"]
    summary = (
        f"Header audit evaluated {len(RECOMMENDED_HEADERS)} controls: "
        f"{len(present)} present, {len(missing)} missing, weak_values={len(weak_values)}, score={header_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights + weak_values[:3] + missing[:4],
        "data": {
            "header_score": header_score,
            "missing_controls": missing,
            "present_controls": present,
            "weak_value_signals": weak_values,
        },
    }
