"""Plugin: evaluate HTTP/HTTPS transport stability and redirect posture."""

from __future__ import annotations


PLUGIN_SPEC = {
    "id": "surface_transport_stability_probe",
    "title": "Surface Transport Stability Probe",
    "description": "Scores transport availability, redirect posture, and probe failures for domain surface resilience.",
    "scopes": ["surface", "fusion"],
    "aliases": ["transport_stability", "http_https_probe", "surface_transport"],
    "version": "1.0",
}


def _status_penalty(status: int | None) -> int:
    if status is None:
        return 35
    if status >= 500:
        return 40
    if status >= 400:
        return 24
    if status >= 300:
        return 10
    return 0


def run(context: dict) -> dict:
    domain_result = context.get("domain_result", {}) or {}
    https_data = domain_result.get("https", {}) or {}
    http_data = domain_result.get("http", {}) or {}
    notes = [str(item).strip() for item in (domain_result.get("scan_notes", []) or []) if str(item).strip()]
    addresses = [str(item).strip() for item in (domain_result.get("resolved_addresses", []) or []) if str(item).strip()]

    https_status = https_data.get("status")
    http_status = http_data.get("status")
    redirects_to_https = bool(http_data.get("redirects_to_https"))
    https_error = str(https_data.get("error", "")).strip()
    http_error = str(http_data.get("error", "")).strip()

    risk_penalty = _status_penalty(https_status)
    risk_penalty += max(0, _status_penalty(http_status) // 2)

    if http_status is not None and not redirects_to_https:
        risk_penalty += 18
    if https_error:
        risk_penalty += 16
    if http_error:
        risk_penalty += 8
    if not addresses:
        risk_penalty += 18
    if len(notes) >= 2:
        risk_penalty += 8

    risk_score = min(100, max(0, risk_penalty))
    stability_score = max(0, 100 - risk_score)
    severity = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "INFO"

    summary = (
        f"Transport probe assessed HTTPS={https_status} HTTP={http_status} redirect_to_https={redirects_to_https}; "
        f"stability_score={stability_score}, risk_score={risk_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"https_status={https_status}",
            f"http_status={http_status}",
            f"redirect_to_https={redirects_to_https}",
            f"resolved_addresses={len(addresses)}",
            f"notes={len(notes)}",
            f"stability_score={stability_score}",
        ],
        "data": {
            "https_status": https_status,
            "http_status": http_status,
            "redirects_to_https": redirects_to_https,
            "https_error": https_error or None,
            "http_error": http_error or None,
            "resolved_addresses": addresses,
            "scan_notes": notes[:40],
            "stability_score": stability_score,
            "risk_score": risk_score,
        },
    }

