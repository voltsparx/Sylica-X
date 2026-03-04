"""Filter: normalize and prioritize signals from Signal Fusion Core output."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "signal_lane_fusion",
    "title": "Signal Lane Fusion",
    "description": "Deduplicates and prioritizes connector-derived signals into actionable intelligence lanes.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["lane_fusion", "signal_router", "fusion_router"],
    "version": "1.0",
}


def _extract_fusion_signals(context: dict) -> dict[str, list[str]]:
    plugins = context.get("plugins", [])
    if not isinstance(plugins, list):
        return {
            "emails": [],
            "urls": [],
            "ips": [],
            "domains": [],
            "subdomains": [],
            "username_mentions": [],
        }

    for row in plugins:
        if not isinstance(row, dict):
            continue
        if str(row.get("id", "")).strip().lower() != "signal_fusion_core":
            continue
        data = row.get("data", {})
        if not isinstance(data, dict):
            continue
        fusion_intel = data.get("fusion_intel", {})
        if not isinstance(fusion_intel, dict):
            continue
        signals = fusion_intel.get("signals", {})
        if isinstance(signals, dict):
            return {
                "emails": [value for value in signals.get("emails", []) if isinstance(value, str)],
                "urls": [value for value in signals.get("urls", []) if isinstance(value, str)],
                "ips": [value for value in signals.get("ips", []) if isinstance(value, str)],
                "domains": [value for value in signals.get("domains", []) if isinstance(value, str)],
                "subdomains": [value for value in signals.get("subdomains", []) if isinstance(value, str)],
                "username_mentions": [
                    value for value in signals.get("username_mentions", []) if isinstance(value, str)
                ],
            }
    return {
        "emails": [],
        "urls": [],
        "ips": [],
        "domains": [],
        "subdomains": [],
        "username_mentions": [],
    }


def _build_lanes(signals: dict[str, list[str]]) -> list[str]:
    lanes: list[str] = []
    if signals["emails"] or signals["username_mentions"]:
        lanes.append("identity-correlation-lane")
    if signals["domains"] or signals["subdomains"] or signals["ips"]:
        lanes.append("infrastructure-surface-lane")
    if signals["urls"]:
        lanes.append("endpoint-enrichment-lane")
    if not lanes:
        lanes.append("baseline-observability-lane")
    return lanes


def run(context: dict) -> dict:
    signals = _extract_fusion_signals(context)
    normalized = {key: sorted(set(values)) for key, values in signals.items()}
    total = sum(len(values) for values in normalized.values())
    lanes = _build_lanes(normalized)

    if total >= 40:
        severity = "HIGH"
    elif total >= 12:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    return {
        "severity": severity,
        "summary": f"Fused {total} signal(s) into {len(lanes)} prioritized lane(s).",
        "highlights": [
            f"signals={total}",
            f"lanes={len(lanes)}",
            f"emails={len(normalized['emails'])}",
            f"domains={len(normalized['domains'])}",
            f"subdomains={len(normalized['subdomains'])}",
            f"urls={len(normalized['urls'])}",
            f"ips={len(normalized['ips'])}",
        ],
        "data": {
            "signals": normalized,
            "lanes": lanes,
        },
    }

