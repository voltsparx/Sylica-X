"""Reverse-engineering knowledge map helpers for Silica-X."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress
import re
from typing import Sequence


DEFAULT_MAP_PATH = Path("reverse-engineering-temp/reverse-engineering-tools-map.txt")


@dataclass(frozen=True)
class ToolInsight:
    """Structured metadata extracted from reverse-engineering study notes."""

    name: str
    bullets: tuple[str, ...]
    github_url: str | None = None


@dataclass(frozen=True)
class ReverseEngineeringMap:
    """Container for parsed tool insights."""

    tools: tuple[ToolInsight, ...]
    source_path: Path


@dataclass(frozen=True)
class FrameworkCapabilityProfile:
    """Capability signal summary extracted from local framework source trees."""

    framework: str
    file_count: int
    feature_hits: dict[str, int]
    path: Path


_TOOL_HEADING_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
_URL_RE = re.compile(r"https?://[^\s)]+")
_FEATURE_PATTERNS: dict[str, tuple[str, ...]] = {
    "async_engine": ("asyncio", "aiohttp", "httpx", "trio", "anyio"),
    "retry_backoff": ("retry", "backoff", "tenacity"),
    "rate_limit": ("rate limit", "ratelimit", "throttle", "semaphore"),
    "caching": ("cache", "ttl", "memo", "lru"),
    "workspace_db": ("sqlite", "sqlalchemy"),
    "plugin_module_system": ("plugin", "module", "extension"),
    "parallel_workers": ("threadpool", "executor", "multiprocessing", "concurrent.futures", "queue"),
    "exports_reporting": ("json", "csv", "html", "xlsx", "pdf", "gexf", "graphml"),
    "tor_proxy_ops": ("tor", "proxy", "socks5"),
    "test_coverage": ("pytest", "unittest"),
}


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    if not match:
        return None
    return match.group(0).strip()


def load_reverse_engineering_map(path: str | Path = DEFAULT_MAP_PATH) -> ReverseEngineeringMap:
    """Parse the reverse-engineering map text file into structured entries."""

    source_path = Path(path)
    if not source_path.exists():
        return ReverseEngineeringMap(tools=(), source_path=source_path)

    tools: list[ToolInsight] = []
    current_name: str | None = None
    current_bullets: list[str] = []
    current_url: str | None = None

    for raw_line in source_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_match = _TOOL_HEADING_RE.match(line)
        if heading_match:
            if current_name:
                tools.append(
                    ToolInsight(
                        name=current_name,
                        bullets=tuple(current_bullets),
                        github_url=current_url,
                    )
                )
            current_name = heading_match.group(2).strip()
            current_bullets = []
            current_url = None
            continue

        if current_name is None:
            continue

        if line.startswith("*"):
            bullet = line.lstrip("*").strip()
            url = _extract_url(bullet)
            if url:
                current_url = url
            current_bullets.append(bullet)
            continue

        # Keep plain continuation lines if present under a tool entry.
        url = _extract_url(line)
        if url:
            current_url = url
        current_bullets.append(line)

    if current_name:
        tools.append(
            ToolInsight(
                name=current_name,
                bullets=tuple(current_bullets),
                github_url=current_url,
            )
        )

    return ReverseEngineeringMap(tools=tuple(tools), source_path=source_path)


def map_tools_to_silica_modules(
    mapping: ReverseEngineeringMap,
) -> dict[str, list[str]]:
    """Map external framework strengths to Silica-X module focus areas."""

    module_map: dict[str, list[str]] = {
        "core/scanner.py": [],
        "core/domain_intel.py": [],
        "core/signal_forge.py": [],
        "core/signal_sieve.py": [],
        "core/output.py": [],
        "core/html_report.py": [],
    }

    for tool in mapping.tools:
        lowered = " ".join((tool.name, *tool.bullets)).lower()
        if any(token in lowered for token in ("username", "profile", "account", "sherlock", "maigret")):
            module_map["core/scanner.py"].append(tool.name)
        if any(token in lowered for token in ("domain", "subdomain", "network", "amass", "harvester")):
            module_map["core/domain_intel.py"].append(tool.name)
        if any(token in lowered for token in ("modular", "module", "plugin", "recon-ng", "spiderfoot")):
            module_map["core/signal_forge.py"].append(tool.name)
        if any(token in lowered for token in ("correlation", "workspace", "normalization", "datasploit")):
            module_map["core/signal_sieve.py"].append(tool.name)
        if any(token in lowered for token in ("output", "json", "html", "report", "cli")):
            module_map["core/output.py"].append(tool.name)
            module_map["core/html_report.py"].append(tool.name)

    # De-duplicate while preserving insertion order.
    deduped: dict[str, list[str]] = {}
    for module_name, names in module_map.items():
        seen: set[str] = set()
        ordered: list[str] = []
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            ordered.append(name)
        deduped[module_name] = ordered
    return deduped


def recommend_research_focus(workflow: str, mapping: ReverseEngineeringMap) -> list[str]:
    """Return human-readable research recommendations for a workflow area."""

    module_map = map_tools_to_silica_modules(mapping)
    key = workflow.strip().lower()
    if key == "profile":
        targets = module_map.get("core/scanner.py", [])
    elif key == "surface":
        targets = module_map.get("core/domain_intel.py", [])
    elif key == "fusion":
        targets = module_map.get("core/signal_sieve.py", []) + module_map.get("core/output.py", [])
    else:
        targets = []

    if not targets:
        return ["No mapped research target yet."]
    return [f"Study patterns from: {', '.join(targets)}"]


def scan_framework_capabilities(
    root: str | Path = "reverse-engineering-temp",
    *,
    max_file_bytes: int = 1_500_000,
) -> tuple[FrameworkCapabilityProfile, ...]:
    """Scan local reverse-engineering trees for capability signals."""

    base = Path(root)
    if not base.exists():
        return ()

    profiles: list[FrameworkCapabilityProfile] = []
    for framework_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        feature_hits = {key: 0 for key in _FEATURE_PATTERNS}
        files = [path for path in framework_dir.rglob("*") if path.is_file()]

        for file_path in files:
            with suppress(Exception):
                if file_path.stat().st_size > max_file_bytes:
                    continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            for feature, tokens in _FEATURE_PATTERNS.items():
                if any(token in text for token in tokens):
                    feature_hits[feature] += 1

        profiles.append(
            FrameworkCapabilityProfile(
                framework=framework_dir.name,
                file_count=len(files),
                feature_hits=feature_hits,
                path=framework_dir,
            )
        )
    return tuple(profiles)


def build_capability_gap_report(
    profiles: Sequence[FrameworkCapabilityProfile],
) -> dict[str, object]:
    """Build comparative gap report across scanned frameworks."""

    if not profiles:
        return {
            "frameworks": 0,
            "leaders": {},
            "recommendations": ["No reverse-engineering frameworks were discovered."],
        }

    leaders: dict[str, dict[str, object]] = {}
    for feature in _FEATURE_PATTERNS:
        ranked = sorted(
            profiles,
            key=lambda item: item.feature_hits.get(feature, 0),
            reverse=True,
        )
        top_score = ranked[0].feature_hits.get(feature, 0)
        leaders[feature] = {
            "score": top_score,
            "frameworks": [item.framework for item in ranked if item.feature_hits.get(feature, 0) == top_score],
        }

    recommendations: list[str] = []
    if leaders["retry_backoff"]["score"]:
        recommendations.append(
            "Strengthen retry/backoff/rate-limit strategy in scanner + domain collectors."
        )
    if leaders["workspace_db"]["score"]:
        recommendations.append(
            "Introduce queryable workspace indexing for historical artifacts and correlation replay."
        )
    if leaders["plugin_module_system"]["score"]:
        recommendations.append(
            "Expand plugin/filter orchestration with strict metadata validation and parallel lanes."
        )
    if leaders["exports_reporting"]["score"]:
        recommendations.append(
            "Broaden reporting with richer graphs and analyst-focused export variants."
        )
    if leaders["test_coverage"]["score"]:
        recommendations.append(
            "Increase coverage around network error paths, plugin failures, and regression fixtures."
        )

    return {
        "frameworks": len(profiles),
        "leaders": leaders,
        "recommendations": recommendations,
    }


def render_capability_markdown(profiles: Sequence[FrameworkCapabilityProfile]) -> str:
    """Render a compact markdown summary for scanned framework capabilities."""

    lines = [
        "# Reverse Engineering Capability Scan",
        "",
        f"Frameworks scanned: {len(profiles)}",
        "",
        "| Framework | Files | Async | Retry | RateLimit | Cache | Plugins | Parallel | Exports | Tor/Proxy | Tests |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for profile in profiles:
        hits = profile.feature_hits
        lines.append(
            "| "
            + " | ".join(
                [
                    profile.framework,
                    str(profile.file_count),
                    str(hits.get("async_engine", 0)),
                    str(hits.get("retry_backoff", 0)),
                    str(hits.get("rate_limit", 0)),
                    str(hits.get("caching", 0)),
                    str(hits.get("plugin_module_system", 0)),
                    str(hits.get("parallel_workers", 0)),
                    str(hits.get("exports_reporting", 0)),
                    str(hits.get("tor_proxy_ops", 0)),
                    str(hits.get("test_coverage", 0)),
                ]
            )
            + " |"
        )

    gap = build_capability_gap_report(profiles)
    lines.extend(["", "## Recommendations", ""])
    for item in gap.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_capability_report(
    output_path: str | Path = "reverse-engineering-temp/silica-x-capability-scan.md",
) -> Path:
    """Scan frameworks and write markdown capability report to disk."""

    profiles = scan_framework_capabilities()
    report = render_capability_markdown(profiles)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path
