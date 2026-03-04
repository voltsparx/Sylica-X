"""Cross-platform correlation logic for profile scan output."""

from __future__ import annotations

from collections import Counter, defaultdict


def _dedupe_bucket(bucket: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: sorted(set(values)) for key, values in bucket.items() if len(set(values)) > 1}


def _bucket_confidence(results: list[dict]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {"high": [], "medium": [], "low": []}
    for item in results:
        platform = item.get("platform", "unknown")
        confidence = int(item.get("confidence", 0) or 0)
        if confidence >= 85:
            clusters["high"].append(platform)
        elif confidence >= 60:
            clusters["medium"].append(platform)
        elif confidence > 0:
            clusters["low"].append(platform)
    return {key: sorted(values) for key, values in clusters.items()}


def correlate(results: list[dict]) -> dict:
    shared_bios: dict[str, list[str]] = defaultdict(list)
    shared_emails: dict[str, list[str]] = defaultdict(list)
    shared_phones: dict[str, list[str]] = defaultdict(list)
    shared_links: dict[str, list[str]] = defaultdict(list)
    shared_mentions: dict[str, list[str]] = defaultdict(list)

    status_counter: Counter = Counter()
    response_times: list[int] = []
    confidence_values: list[int] = []

    for item in results:
        status = item.get("status", "UNKNOWN")
        status_counter[status] += 1
        confidence_values.append(int(item.get("confidence", 0) or 0))
        if isinstance(item.get("response_time_ms"), int):
            response_times.append(int(item["response_time_ms"]))

        if status != "FOUND":
            continue

        platform = item.get("platform", "unknown")
        bio = (item.get("bio") or "").strip()
        if bio:
            shared_bios[bio].append(platform)

        contacts = item.get("contacts", {})
        for email in contacts.get("emails", []):
            shared_emails[email.strip().lower()].append(platform)
        for phone in contacts.get("phones", []):
            shared_phones[phone.strip()].append(platform)

        for link in item.get("links", []):
            shared_links[link.strip()].append(platform)

        for mention in item.get("mentions", []):
            shared_mentions[mention.strip().lower()].append(platform)

    confidence_clusters = _bucket_confidence(results)
    overlap_points = (
        len(_dedupe_bucket(shared_bios))
        + len(_dedupe_bucket(shared_emails))
        + len(_dedupe_bucket(shared_phones))
        + len(_dedupe_bucket(shared_links))
    )
    identity_overlap_score = min(100, overlap_points * 12 + len(confidence_clusters["high"]) * 4)

    response_time_stats = {
        "min_ms": min(response_times) if response_times else None,
        "max_ms": max(response_times) if response_times else None,
        "avg_ms": int(sum(response_times) / len(response_times)) if response_times else None,
    }

    return {
        "shared_bios": _dedupe_bucket(shared_bios),
        "shared_emails": _dedupe_bucket(shared_emails),
        "shared_phones": _dedupe_bucket(shared_phones),
        "shared_links": _dedupe_bucket(shared_links),
        "shared_mentions": _dedupe_bucket(shared_mentions),
        "confidence_clusters": confidence_clusters["high"],
        "confidence_cluster_map": confidence_clusters,
        "status_distribution": dict(status_counter),
        "response_time_stats": response_time_stats,
        "average_confidence": int(sum(confidence_values) / len(confidence_values)) if confidence_values else 0,
        "identity_overlap_score": identity_overlap_score,
    }
