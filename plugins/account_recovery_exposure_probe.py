"""Plugin: map publicly exposed account-recovery contact surface."""

from __future__ import annotations


PLUGIN_SPEC = {
    "id": "account_recovery_exposure_probe",
    "title": "Account Recovery Exposure Probe",
    "description": "Measures how much account-recovery metadata is publicly exposed across discovered profiles.",
    "scopes": ["profile", "fusion"],
    "aliases": ["recovery_exposure", "contact_surface", "recovery_probe"],
    "version": "1.0",
}


FREE_MAIL_PROVIDERS = {
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
}


def _domain_of(email: str) -> str:
    token = str(email or "").strip().lower()
    if "@" not in token:
        return ""
    return token.split("@", maxsplit=1)[1]


def run(context: dict) -> dict:
    raw_results = context.get("results", []) or []
    results = [row for row in raw_results if isinstance(row, dict)]

    email_platforms: dict[str, set[str]] = {}
    phone_platforms: dict[str, set[str]] = {}
    profiles_with_contact: set[str] = set()

    for row in results:
        if str(row.get("status", "")).upper() != "FOUND":
            continue
        platform = str(row.get("platform", "unknown")).strip().lower() or "unknown"
        contacts = row.get("contacts", {}) or {}
        emails = [str(item).strip().lower() for item in (contacts.get("emails", []) or []) if str(item).strip()]
        phones = [str(item).strip() for item in (contacts.get("phones", []) or []) if str(item).strip()]

        if emails or phones:
            profiles_with_contact.add(platform)
        for email in emails:
            email_platforms.setdefault(email, set()).add(platform)
        for phone in phones:
            phone_platforms.setdefault(phone, set()).add(platform)

    unique_emails = sorted(email_platforms.keys())
    unique_phones = sorted(phone_platforms.keys())
    reused_emails = {key: sorted(values) for key, values in email_platforms.items() if len(values) > 1}
    reused_phones = {key: sorted(values) for key, values in phone_platforms.items() if len(values) > 1}

    free_provider_count = 0
    custom_provider_count = 0
    for email in unique_emails:
        domain = _domain_of(email)
        if not domain:
            continue
        if domain in FREE_MAIL_PROVIDERS:
            free_provider_count += 1
        else:
            custom_provider_count += 1

    risk_score = min(
        100,
        (len(profiles_with_contact) * 8)
        + (len(unique_emails) * 5)
        + (len(unique_phones) * 7)
        + (len(reused_emails) * 12)
        + (len(reused_phones) * 10)
        + (free_provider_count * 2),
    )
    severity = "HIGH" if risk_score >= 65 else "MEDIUM" if risk_score >= 35 else "INFO"

    summary = (
        f"Recovery-contact exposure analysis found {len(unique_emails)} unique email(s) and "
        f"{len(unique_phones)} phone number(s) across {len(profiles_with_contact)} profile(s), "
        f"risk_score={risk_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"profiles_with_contact={len(profiles_with_contact)}",
            f"unique_emails={len(unique_emails)}",
            f"unique_phones={len(unique_phones)}",
            f"cross_platform_email_reuse={len(reused_emails)}",
            f"cross_platform_phone_reuse={len(reused_phones)}",
            f"risk_score={risk_score}",
        ],
        "data": {
            "profiles_with_contact": sorted(profiles_with_contact),
            "unique_emails": unique_emails[:120],
            "unique_phones": unique_phones[:120],
            "reused_emails": reused_emails,
            "reused_phones": reused_phones,
            "free_provider_count": free_provider_count,
            "custom_provider_count": custom_provider_count,
            "risk_score": risk_score,
        },
    }
