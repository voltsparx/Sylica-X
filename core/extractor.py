import re
from html import unescape

EMAIL_REGEX = r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
PHONE_REGEX = r"(?:\+?\d[\d\s().-]{6,}\d)"
SCRIPT_STYLE_REGEX = r"<(script|style)\b[^>]*>.*?</\1>"
TAG_REGEX = r"<[^>]+>"
META_DESCRIPTION_PATTERNS = (
    r"<meta[^>]*name=['\"]description['\"][^>]*content=['\"](.*?)['\"][^>]*>",
    r"<meta[^>]*content=['\"](.*?)['\"][^>]*name=['\"]description['\"][^>]*>",
    r"<meta[^>]*property=['\"]og:description['\"][^>]*content=['\"](.*?)['\"][^>]*>",
    r"<meta[^>]*content=['\"](.*?)['\"][^>]*property=['\"]og:description['\"][^>]*>",
    r"<meta[^>]*name=['\"]twitter:description['\"][^>]*content=['\"](.*?)['\"][^>]*>",
    r"<meta[^>]*content=['\"](.*?)['\"][^>]*name=['\"]twitter:description['\"][^>]*>",
)


def _strip_scripts_and_styles(text):
    return re.sub(SCRIPT_STYLE_REGEX, " ", text or "", flags=re.I | re.S)


def _strip_tags(text):
    return re.sub(TAG_REGEX, " ", text or "")


def clean(text):
    if not text:
        return None
    normalized = unescape(text)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()
    return normalized or None


def _html_to_text(payload):
    without_scripts = _strip_scripts_and_styles(payload)
    return clean(_strip_tags(without_scripts)) or ""


def extract_bio(html):
    for pattern in META_DESCRIPTION_PATTERNS:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return clean(match.group(1))

    paragraph = re.search(r"<p[^>]*>(.*?)</p>", html, re.I | re.S)
    if paragraph:
        return clean(re.sub("<.*?>", "", paragraph.group(1)))

    return None


def extract_links(html):
    links = re.findall(r"href\s*=\s*['\"](https?://[^'\"#]+)['\"]", html, re.I)
    deduped = []
    seen = set()
    for link in links:
        normalized = clean(link)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def extract_contacts(html):
    text = _html_to_text(html)
    emails = sorted({match.lower() for match in re.findall(EMAIL_REGEX, text)})

    phones = set()
    for candidate in re.findall(PHONE_REGEX, text):
        normalized = clean(candidate) or ""
        digits = re.sub(r"\D", "", normalized)
        if 8 <= len(digits) <= 15:
            phones.add(normalized)

    return {
        "emails": emails,
        "phones": sorted(phones),
    }


def extract_username_mentions(html, username):
    mentions = set()
    text = _html_to_text(html)
    patterns = [
        rf"\b{re.escape(username)}\b",
        rf"@{re.escape(username)}",
        rf"/{re.escape(username)}",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text, re.I):
            mentions.add(match)

    return sorted(mentions)
