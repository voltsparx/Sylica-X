"""Synthetic quicktest templates for offline smoke runs."""

from __future__ import annotations

from copy import deepcopy
import random
from typing import Any


def _profile_row(
    *,
    platform: str,
    status: str,
    url: str,
    confidence: int,
    bio: str = "",
    emails: list[str] | None = None,
    phones: list[str] | None = None,
    links: list[str] | None = None,
    mentions: list[str] | None = None,
    context: str = "",
    http_status: int | None = None,
    response_time_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "platform": platform,
        "status": status,
        "url": url,
        "confidence": confidence,
        "bio": bio,
        "contacts": {"emails": list(emails or []), "phones": list(phones or [])},
        "links": list(links or []),
        "mentions": list(mentions or []),
        "context": context,
        "http_status": http_status,
        "response_time_ms": response_time_ms,
    }


def _subdomains(domain: str, roots: list[str], total: int) -> list[str]:
    values = [f"{root}.{domain}" for root in roots]
    counter = 1
    while len(values) < total:
        values.append(f"node-{counter:03d}.{domain}")
        counter += 1
    return values


TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "atlas-mercier",
        "label": "Atlas Mercier",
        "username": "atlas_mercier",
        "domain": "atlaslab.dev",
        "profile_results": [
            _profile_row(
                platform="GitHub",
                status="FOUND",
                url="https://github.com/atlas_mercier",
                confidence=94,
                bio="Atlas Mercier builds threat graphs and telemetry pipelines.",
                emails=["atlas@atlaslab.dev"],
                phones=["+1-415-555-0191"],
                links=["https://atlaslab.dev", "https://blog.atlaslab.dev"],
                mentions=["Atlas Mercier", "threat intel"],
                http_status=200,
                response_time_ms=182,
            ),
            _profile_row(
                platform="LinkedIn",
                status="FOUND",
                url="https://www.linkedin.com/in/atlas-mercier",
                confidence=90,
                bio="Full Name: Atlas Mercier. Security engineer.",
                emails=["atlas@atlaslab.dev"],
                links=["https://atlaslab.dev"],
                mentions=["incident response"],
                http_status=200,
                response_time_ms=241,
            ),
            _profile_row(
                platform="Twitter/X",
                status="FOUND",
                url="https://x.com/atlas_mercier",
                confidence=88,
                bio="Atlas Mercier | detection and response.",
                links=["https://blog.atlaslab.dev"],
                mentions=["Atlas Mercier"],
                http_status=200,
                response_time_ms=203,
            ),
            _profile_row(
                platform="Discord",
                status="BLOCKED",
                url="https://discord.com/users/atlas_mercier",
                confidence=0,
                context="Anti-automation challenge page returned.",
                http_status=403,
                response_time_ms=411,
            ),
            _profile_row(
                platform="Pastebin",
                status="ERROR",
                url="https://pastebin.com/u/atlas_mercier",
                confidence=0,
                context="Temporary upstream timeout.",
                http_status=503,
                response_time_ms=640,
            ),
            _profile_row(
                platform="Instagram",
                status="NOT FOUND",
                url="https://instagram.com/atlas_mercier",
                confidence=0,
                context="No public profile found for handle.",
                http_status=404,
                response_time_ms=198,
            ),
        ],
        "domain_result": {
            "target": "atlaslab.dev",
            "resolved_addresses": ["104.26.10.41", "172.67.70.91"],
            "https": {
                "status": 200,
                "final_url": "https://atlaslab.dev",
                "headers": {"server": "cloudflare", "x-powered-by": "Express"},
            },
            "http": {"status": 301, "final_url": "https://atlaslab.dev", "redirects_to_https": True},
            "subdomains": _subdomains(
                "atlaslab.dev",
                ["api", "auth", "cdn", "dev", "staging", "status", "vpn", "grafana"],
                120,
            ),
            "rdap": {
                "handle": "ATLASLAB-DEV",
                "name_servers": ["ns1.atlaslab.dev", "ns2.atlaslab.dev"],
                "registrar": "Example Registrar LLC",
            },
            "robots_txt_present": True,
            "robots_preview": "User-agent: *\nDisallow: /internal/",
            "security_txt_present": True,
            "security_preview": "Contact: mailto:security@atlaslab.dev",
            "scan_notes": ["Broad CT host surface observed.", "Header baseline missing HSTS/CSP controls."],
        },
    },
    {
        "id": "noor-akhtar",
        "label": "Noor Akhtar",
        "username": "noor_akhtar",
        "domain": "nordelta-ops.net",
        "profile_results": [
            _profile_row(
                platform="GitHub",
                status="FOUND",
                url="https://github.com/noor_akhtar",
                confidence=91,
                bio="Noor Akhtar automates cloud incident response workflows.",
                emails=["noor@nordelta-ops.net"],
                links=["https://nordelta-ops.net"],
                mentions=["Noor Akhtar"],
                http_status=200,
                response_time_ms=192,
            ),
            _profile_row(
                platform="GitLab",
                status="FOUND",
                url="https://gitlab.com/noor_akhtar",
                confidence=86,
                bio="Noor Akhtar detection automation profile.",
                emails=["noor@nordelta-ops.net"],
                phones=["+1-646-555-0137"],
                links=["https://nordelta-ops.net"],
                mentions=["detection"],
                http_status=200,
                response_time_ms=237,
            ),
            _profile_row(
                platform="LinkedIn",
                status="FOUND",
                url="https://www.linkedin.com/in/noor-akhtar",
                confidence=88,
                bio="Full Name: Noor Akhtar. Principal threat operations analyst.",
                links=["https://status.nordelta-ops.net"],
                mentions=["threat operations"],
                http_status=200,
                response_time_ms=256,
            ),
            _profile_row(
                platform="Telegram",
                status="BLOCKED",
                url="https://t.me/noor_akhtar",
                confidence=0,
                context="Rate-limit and anti-bot threshold hit.",
                http_status=429,
                response_time_ms=522,
            ),
            _profile_row(
                platform="Facebook",
                status="ERROR",
                url="https://facebook.com/noor.akhtar",
                confidence=0,
                context="Upstream page render timeout.",
                http_status=500,
                response_time_ms=781,
            ),
            _profile_row(
                platform="Instagram",
                status="NOT FOUND",
                url="https://instagram.com/noor_akhtar",
                confidence=0,
                context="No public profile found for handle.",
                http_status=404,
                response_time_ms=206,
            ),
        ],
        "domain_result": {
            "target": "nordelta-ops.net",
            "resolved_addresses": ["185.199.110.153", "2606:50c0:8002::153"],
            "https": {
                "status": 503,
                "final_url": "https://nordelta-ops.net",
                "headers": {"server": "nginx/1.20.0"},
            },
            "http": {"status": 200, "final_url": "http://nordelta-ops.net", "redirects_to_https": False},
            "subdomains": _subdomains(
                "nordelta-ops.net",
                ["api", "legacy", "vpn", "mail", "git", "staging", "ci", "ops"],
                86,
            ),
            "rdap": {
                "handle": "NORDELTA-OPS-NET",
                "name_servers": ["ns-a.nordelta-ops.net", "ns-b.nordelta-ops.net"],
                "registrar": "Delta Registry Partners",
            },
            "robots_txt_present": False,
            "robots_preview": "",
            "security_txt_present": False,
            "security_preview": "",
            "scan_notes": ["HTTPS endpoint unstable.", "Legacy HTTP endpoint remains reachable."],
        },
    },
    {
        "id": "juno-harbor",
        "label": "Juno Harbor",
        "username": "juno_harbor",
        "domain": "harbor-grid.io",
        "profile_results": [
            _profile_row(
                platform="GitHub",
                status="FOUND",
                url="https://github.com/juno_harbor",
                confidence=93,
                bio="Juno Harbor builds container telemetry collectors.",
                emails=["juno@harbor-grid.io"],
                links=["https://harbor-grid.io", "https://labs.harbor-grid.io"],
                mentions=["Juno Harbor", "containers"],
                http_status=200,
                response_time_ms=176,
            ),
            _profile_row(
                platform="DockerHub",
                status="FOUND",
                url="https://hub.docker.com/u/juno_harbor",
                confidence=89,
                bio="Juno Harbor image publisher.",
                links=["https://harbor-grid.io/containers"],
                mentions=["docker"],
                http_status=200,
                response_time_ms=214,
            ),
            _profile_row(
                platform="LinkedIn",
                status="FOUND",
                url="https://www.linkedin.com/in/juno-harbor",
                confidence=87,
                bio="Full Name: Juno Harbor. Staff cloud security architect.",
                phones=["+1-202-555-0162"],
                links=["https://harbor-grid.io"],
                mentions=["architecture"],
                http_status=200,
                response_time_ms=248,
            ),
            _profile_row(
                platform="Facebook",
                status="BLOCKED",
                url="https://facebook.com/juno.harbor",
                confidence=0,
                context="Challenge page detected.",
                http_status=403,
                response_time_ms=489,
            ),
            _profile_row(
                platform="Pinterest",
                status="ERROR",
                url="https://pinterest.com/juno_harbor",
                confidence=0,
                context="Gateway timeout from upstream.",
                http_status=504,
                response_time_ms=688,
            ),
            _profile_row(
                platform="TikTok",
                status="NOT FOUND",
                url="https://www.tiktok.com/@juno_harbor",
                confidence=0,
                context="Handle not registered.",
                http_status=404,
                response_time_ms=233,
            ),
        ],
        "domain_result": {
            "target": "harbor-grid.io",
            "resolved_addresses": ["34.117.59.81", "34.149.193.60"],
            "https": {
                "status": 200,
                "final_url": "https://harbor-grid.io",
                "headers": {
                    "server": "envoy",
                    "strict-transport-security": "max-age=31536000",
                    "content-security-policy": "default-src 'self'",
                    "x-frame-options": "DENY",
                    "x-powered-by": "Next.js",
                },
            },
            "http": {"status": 301, "final_url": "https://harbor-grid.io", "redirects_to_https": True},
            "subdomains": _subdomains(
                "harbor-grid.io",
                ["api", "cdn", "assets", "auth", "platform", "docs", "status"],
                54,
            ),
            "rdap": {
                "handle": "HARBOR-GRID-IO",
                "name_servers": ["ns1.harbor-grid.io", "ns2.harbor-grid.io"],
                "registrar": "Harbor Domain Services",
            },
            "robots_txt_present": True,
            "robots_preview": "User-agent: *\nDisallow: /preview/\nAllow: /",
            "security_txt_present": True,
            "security_preview": "Contact: mailto:security@harbor-grid.io",
            "scan_notes": ["Headers mostly hardened.", "Banner disclosure still observed."],
        },
    },
    {
        "id": "raven-ion",
        "label": "Raven Ion",
        "username": "raven_ion",
        "domain": "ionrelay.cloud",
        "profile_results": [
            _profile_row(
                platform="GitHub",
                status="FOUND",
                url="https://github.com/raven_ion",
                confidence=92,
                bio="Raven Ion develops distributed telemetry relays.",
                emails=["raven@ionrelay.cloud"],
                links=["https://ionrelay.cloud"],
                mentions=["Raven Ion", "telemetry"],
                http_status=200,
                response_time_ms=187,
            ),
            _profile_row(
                platform="Twitter/X",
                status="FOUND",
                url="https://x.com/raven_ion",
                confidence=85,
                bio="Raven Ion sharing cloud detection patterns.",
                links=["https://ionrelay.cloud/blog"],
                mentions=["cloud detection"],
                http_status=200,
                response_time_ms=201,
            ),
            _profile_row(
                platform="LinkedIn",
                status="FOUND",
                url="https://www.linkedin.com/in/raven-ion",
                confidence=89,
                bio="Full Name: Raven Ion. Principal SRE and reliability lead.",
                phones=["+44 20 7946 0733"],
                links=["https://ionrelay.cloud"],
                mentions=["reliability"],
                http_status=200,
                response_time_ms=259,
            ),
            _profile_row(
                platform="Discord",
                status="BLOCKED",
                url="https://discord.com/users/raven_ion",
                confidence=0,
                context="Access challenge blocked extraction.",
                http_status=403,
                response_time_ms=438,
            ),
            _profile_row(
                platform="SteamCommunity",
                status="ERROR",
                url="https://steamcommunity.com/id/raven_ion",
                confidence=0,
                context="Profile endpoint returned server error.",
                http_status=500,
                response_time_ms=702,
            ),
            _profile_row(
                platform="Snapchat",
                status="NOT FOUND",
                url="https://snapchat.com/add/raven_ion",
                confidence=0,
                context="No public account discovered.",
                http_status=404,
                response_time_ms=207,
            ),
        ],
        "domain_result": {
            "target": "ionrelay.cloud",
            "resolved_addresses": ["203.0.113.41", "203.0.113.42", "2001:db8:85a3::8a2e:370:7334"],
            "https": {
                "status": 200,
                "final_url": "https://ionrelay.cloud",
                "headers": {"server": "Apache", "x-powered-by": "PHP/8.1"},
            },
            "http": {"status": 301, "final_url": "https://ionrelay.cloud", "redirects_to_https": True},
            "subdomains": _subdomains(
                "ionrelay.cloud",
                ["api", "edge", "relay", "logs", "metrics", "cdn", "portal", "legacy"],
                112,
            ),
            "rdap": {
                "handle": "IONRELAY-CLOUD",
                "name_servers": ["ns1.ionrelay.cloud", "ns2.ionrelay.cloud"],
                "registrar": "Ion Registry",
            },
            "robots_txt_present": True,
            "robots_preview": "User-agent: *\nDisallow: /ops/",
            "security_txt_present": False,
            "security_preview": "",
            "scan_notes": ["IPv6 host observed in DNS records.", "Banner exposure may leak stack versions."],
        },
    },
    {
        "id": "maya-cipher",
        "label": "Maya Cipher",
        "username": "maya_cipher",
        "domain": "ciphertrail.ai",
        "profile_results": [
            _profile_row(
                platform="GitHub",
                status="FOUND",
                url="https://github.com/maya_cipher",
                confidence=95,
                bio="Maya Cipher develops investigation tooling and graph models.",
                emails=["maya@ciphertrail.ai"],
                links=["https://ciphertrail.ai", "https://labs.ciphertrail.ai"],
                mentions=["Maya Cipher", "graph analytics"],
                http_status=200,
                response_time_ms=171,
            ),
            _profile_row(
                platform="LinkedIn",
                status="FOUND",
                url="https://www.linkedin.com/in/maya-cipher",
                confidence=92,
                bio="Full Name: Maya Cipher. Director of adversary simulation.",
                emails=["maya@ciphertrail.ai", "contact@ciphertrail.ai"],
                phones=["+1-303-555-0178"],
                links=["https://ciphertrail.ai"],
                mentions=["purple team"],
                http_status=200,
                response_time_ms=239,
            ),
            _profile_row(
                platform="StackOverflow",
                status="FOUND",
                url="https://stackoverflow.com/users/123456/maya-cipher",
                confidence=84,
                bio="Maya Cipher answers on secure coding and observability.",
                links=["https://ciphertrail.ai/docs"],
                mentions=["python", "security"],
                http_status=200,
                response_time_ms=244,
            ),
            _profile_row(
                platform="Facebook",
                status="BLOCKED",
                url="https://facebook.com/maya.cipher",
                confidence=0,
                context="Automated access blocked by anti-bot controls.",
                http_status=403,
                response_time_ms=463,
            ),
            _profile_row(
                platform="Pinterest",
                status="ERROR",
                url="https://pinterest.com/maya_cipher",
                confidence=0,
                context="Edge upstream error.",
                http_status=502,
                response_time_ms=711,
            ),
            _profile_row(
                platform="TikTok",
                status="NOT FOUND",
                url="https://www.tiktok.com/@maya_cipher",
                confidence=0,
                context="Handle absent.",
                http_status=404,
                response_time_ms=214,
            ),
        ],
        "domain_result": {
            "target": "ciphertrail.ai",
            "resolved_addresses": ["151.101.65.195", "151.101.129.195"],
            "https": {
                "status": 200,
                "final_url": "https://ciphertrail.ai",
                "headers": {
                    "server": "Vercel",
                    "strict-transport-security": "max-age=31536000; includeSubDomains",
                    "x-frame-options": "SAMEORIGIN",
                },
            },
            "http": {"status": 301, "final_url": "https://ciphertrail.ai", "redirects_to_https": True},
            "subdomains": _subdomains(
                "ciphertrail.ai",
                ["api", "labs", "research", "cdn", "docs", "status", "auth", "gateway"],
                98,
            ),
            "rdap": {
                "handle": "CIPHERTRAIL-AI",
                "name_servers": ["ns1.ciphertrail.ai", "ns2.ciphertrail.ai"],
                "registrar": "Cipher Domains",
            },
            "robots_txt_present": True,
            "robots_preview": "User-agent: *\nDisallow: /private/\nAllow: /",
            "security_txt_present": True,
            "security_preview": "Contact: mailto:security@ciphertrail.ai",
            "scan_notes": ["CSP header missing on sampled endpoint.", "Subdomain count indicates broad perimeter."],
        },
    },
]


def quicktest_template_ids() -> list[str]:
    return [str(item.get("id", "")).strip() for item in TEMPLATES if str(item.get("id", "")).strip()]


def list_quicktest_templates() -> list[dict[str, str]]:
    return [
        {
            "id": str(item.get("id", "")),
            "label": str(item.get("label", "")),
            "username": str(item.get("username", "")),
            "domain": str(item.get("domain", "")),
        }
        for item in TEMPLATES
    ]


def pick_quicktest_template(*, template_id: str | None = None, seed: int | None = None) -> dict[str, Any]:
    requested = str(template_id or "").strip().lower()
    if requested:
        for item in TEMPLATES:
            if str(item.get("id", "")).strip().lower() == requested:
                selected = deepcopy(item)
                selected["selection_mode"] = "explicit"
                return selected
        raise ValueError(f"Unknown quicktest template '{requested}'. Available: {', '.join(quicktest_template_ids())}")

    chooser = random.Random(seed).choice if seed is not None else random.SystemRandom().choice
    selected = deepcopy(chooser(TEMPLATES))
    selected["selection_mode"] = "random_seeded" if seed is not None else "random"
    return selected
