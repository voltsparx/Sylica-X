"""Filter: rank discovered contact channels by expected outreach quality."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "contact_quality_filter",
    "title": "Contact Quality Filter",
    "description": "Ranks discovered emails/phones by likely quality and flags disposable channels.",
    "scopes": ["profile", "fusion"],
    "aliases": ["contact_quality", "contact_ranker", "reachability_filter"],
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
}
DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "10minutemail.com",
    "guerrillamail.com",
    "tempmail.com",
    "yopmail.com",
}


def _email_domain(email: str) -> str:
    token = str(email or "").strip().lower()
    if "@" not in token:
        return ""
    return token.split("@", maxsplit=1)[1]


def run(context: dict) -> dict:
    raw_results = context.get("results", []) or []
    results = [row for row in raw_results if isinstance(row, dict)]

    email_hits: dict[str, set[str]] = {}
    phone_hits: dict[str, set[str]] = {}
    for row in results:
        if str(row.get("status", "")).upper() != "FOUND":
            continue
        platform = str(row.get("platform", "unknown")).strip().lower() or "unknown"
        contacts = row.get("contacts", {}) or {}
        for email in contacts.get("emails", []) or []:
            token = str(email).strip().lower()
            if token:
                email_hits.setdefault(token, set()).add(platform)
        for phone in contacts.get("phones", []) or []:
            token = str(phone).strip()
            if token:
                phone_hits.setdefault(token, set()).add(platform)

    ranked_emails: list[dict[str, object]] = []
    disposable_count = 0
    free_mail_count = 0
    for email, platforms in email_hits.items():
        domain = _email_domain(email)
        if domain in DISPOSABLE_DOMAINS:
            score = 20
            quality = "low"
            disposable_count += 1
        elif domain in FREE_MAIL_PROVIDERS:
            score = 55
            quality = "medium"
            free_mail_count += 1
        else:
            score = 82
            quality = "high"
        if len(platforms) > 1:
            score = min(95, score + 8)
        ranked_emails.append(
            {
                "email": email,
                "domain": domain,
                "quality": quality,
                "score": score,
                "platforms": sorted(platforms),
            }
        )

    ranked_emails.sort(key=lambda item: (-int(item["score"]), str(item["email"])))
    ranked_phones = [
        {"phone": phone, "platforms": sorted(platforms), "score": 70 if len(platforms) > 1 else 58}
        for phone, platforms in phone_hits.items()
    ]
    ranked_phones.sort(key=lambda item: (-int(item["score"]), str(item["phone"])))

    quality_score = min(100, (len([row for row in ranked_emails if row["quality"] == "high"]) * 12) + (len(ranked_phones) * 7))
    severity = "MEDIUM" if disposable_count > 0 else "INFO"
    summary = (
        f"Contact quality ranked {len(ranked_emails)} email(s) and {len(ranked_phones)} phone(s); "
        f"disposable={disposable_count}, free_mail={free_mail_count}, quality_score={quality_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"emails={len(ranked_emails)}",
            f"phones={len(ranked_phones)}",
            f"high_quality_emails={len([row for row in ranked_emails if row['quality'] == 'high'])}",
            f"disposable_emails={disposable_count}",
            f"quality_score={quality_score}",
        ],
        "data": {
            "ranked_emails": ranked_emails[:150],
            "ranked_phones": ranked_phones[:150],
            "disposable_email_count": disposable_count,
            "free_mail_count": free_mail_count,
            "quality_score": quality_score,
        },
    }
