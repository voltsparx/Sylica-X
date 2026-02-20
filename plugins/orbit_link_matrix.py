"""Plugin: orbit link matrix intelligence."""

from __future__ import annotations

from collections import Counter, defaultdict
from urllib.parse import urlparse


PLUGIN_SPEC = {
    "id": "orbit_link_matrix",
    "title": "Orbit Link Matrix",
    "description": "Builds platform-to-domain linkage and shared outbound domain signals.",
    "scopes": ["profile", "fusion"],
    "aliases": ["account_link_graph", "linkgraph", "domainlinks"],
    "version": "1.1",
}


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.netloc or "").lower().strip()


def run(context: dict) -> dict:
    results = context.get("results", []) or []

    domain_counter: Counter = Counter()
    graph: dict[str, list[str]] = defaultdict(list)
    for item in results:
        if item.get("status") != "FOUND":
            continue
        platform = item.get("platform", "Unknown")
        candidate_urls = [item.get("url", "")] + list(item.get("links", []))
        for raw_url in candidate_urls:
            domain = _domain(raw_url)
            if not domain:
                continue
            domain_counter[domain] += 1
            graph[platform].append(domain)

    normalized_graph = {platform: sorted(set(domains)) for platform, domains in graph.items()}
    shared_domains = {domain: count for domain, count in domain_counter.items() if count > 1}
    top_domains = [f"{domain} ({count})" for domain, count in domain_counter.most_common(5)]

    summary = (
        f"Mapped {len(normalized_graph)} platform nodes across {len(domain_counter)} distinct domains; "
        f"{len(shared_domains)} domains were shared across multiple profile artifacts."
    )
    return {
        "severity": "INFO",
        "summary": summary,
        "highlights": top_domains,
        "data": {
            "platform_domain_graph": normalized_graph,
            "shared_domains": shared_domains,
            "top_domains": top_domains,
        },
    }
