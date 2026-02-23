"""Filter: identify low-signal findings that can be suppressed for clarity."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "noise_suppression_filter",
    "title": "Noise Suppression Filter",
    "description": "Marks low-signal rows and placeholder artifacts to improve scan readability.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["noise_filter", "suppress_noise", "quiet"],
    "version": "1.0",
}


LOW_SIGNAL_SUBDOMAIN_PREFIXES = ("www.", "m.", "img.", "cdn.", "static.", "assets.")


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    domain_result = context.get("domain_result") or {}

    suppress_profile: list[str] = []
    keep_profile: list[str] = []
    for row in results:
        platform = str(row.get("platform", "Unknown"))
        status = str(row.get("status", "UNKNOWN"))
        confidence = int(row.get("confidence", 0) or 0)
        has_signal = bool(row.get("bio")) or bool(row.get("links")) or bool((row.get("contacts", {}) or {}).get("emails")) or bool((row.get("contacts", {}) or {}).get("phones")) or bool(row.get("mentions"))

        if status in {"NOT FOUND", "INVALID_USERNAME"}:
            suppress_profile.append(platform)
            continue
        if status == "FOUND" and confidence < 55 and not has_signal:
            suppress_profile.append(platform)
            continue
        keep_profile.append(platform)

    subdomains = [str(item).strip().lower() for item in (domain_result.get("subdomains", []) or []) if str(item).strip()]
    suppress_subdomains = [name for name in subdomains if name.startswith(LOW_SIGNAL_SUBDOMAIN_PREFIXES)]
    keep_subdomains = [name for name in subdomains if name not in suppress_subdomains]

    suppress_count = len(suppress_profile) + len(suppress_subdomains)
    severity = "MEDIUM" if suppress_count >= 20 else "INFO"
    summary = (
        f"Noise suppression identified {suppress_count} low-signal artifact(s) "
        f"({len(suppress_profile)} profile rows, {len(suppress_subdomains)} subdomains)."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"suppress_profile={len(suppress_profile)}",
            f"suppress_subdomains={len(suppress_subdomains)}",
            f"keep_profile={len(keep_profile)}",
            f"keep_subdomains={len(keep_subdomains)}",
        ],
        "data": {
            "suppressed_profiles": sorted(set(suppress_profile)),
            "suppressed_subdomains": suppress_subdomains[:80],
            "recommended_profile_focus": sorted(set(keep_profile)),
            "recommended_subdomain_focus_count": len(keep_subdomains),
        },
    }
