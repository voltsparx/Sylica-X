"""Capability source map helpers for Silica-X."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress
import json
import re
from typing import Sequence


DEFAULT_SOURCE_SCAN_ROOT = Path("intel-sources")
DEFAULT_SOURCE_MAP_PATH = DEFAULT_SOURCE_SCAN_ROOT / "tools-map.txt"
DEFAULT_CAPABILITY_PACK_ROOT = Path("intel")
DEFAULT_PLUGIN_CAPABILITY_ROOT = Path("plugins/_intel")
DEFAULT_FILTER_CAPABILITY_ROOT = Path("filters/_intel")


@dataclass(frozen=True)
class ToolInsight:
    """Structured metadata extracted from capability source study notes."""

    name: str
    bullets: tuple[str, ...]
    github_url: str | None = None


@dataclass(frozen=True)
class CapabilitySourceMap:
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
    "signal_fusion_lane": ("osint", "recon", "collector", "intel", "subdomain", "username"),
    "test_coverage": ("pytest", "unittest"),
}
_FEATURE_DESCRIPTIONS: dict[str, str] = {
    "async_engine": "Asynchronous request orchestration and non-blocking collectors.",
    "retry_backoff": "Resilient retries, transient-failure handling, and backoff behavior.",
    "rate_limit": "Concurrency/rate controls to reduce bans and unstable collection.",
    "caching": "Result caching and TTL reuse to reduce duplicate calls and latency.",
    "workspace_db": "Queryable persistent storage for historical OSINT artifacts.",
    "plugin_module_system": "Dynamic module/plugin discovery and orchestration.",
    "parallel_workers": "Thread/process/queue worker models for throughput scaling.",
    "exports_reporting": "Analyst exports and multi-format report outputs.",
    "tor_proxy_ops": "Proxy/Tor routing and anonymized collection channels.",
    "signal_fusion_lane": "Unified connector lanes for integrating multi-source intelligence into Silica workflows.",
    "test_coverage": "Automated tests and confidence gates for regressions.",
}
_FEATURE_TARGET_MODULES: dict[str, tuple[str, ...]] = {
    "async_engine": ("core/engines/async_engine.py", "core/collect/scanner.py", "core/collect/domain_intel.py"),
    "retry_backoff": ("core/collect/http_resilience.py", "core/collect/scanner.py", "core/collect/domain_intel.py"),
    "rate_limit": (
        "core/engines/async_engine.py",
        "core/engines/thread_engine.py",
        "core/engines/parallel_engine.py",
    ),
    "caching": ("core/engines/fusion_engine.py", "core/intel/capability_matrix.py", "core/artifacts/storage.py"),
    "workspace_db": ("core/artifacts/storage.py", "core/artifacts/output.py", "core/analyze/correlator.py"),
    "plugin_module_system": ("core/extensions/plugin_manager.py", "core/extensions/signal_forge.py", "core/extensions/signal_sieve.py"),
    "parallel_workers": ("core/engines/parallel_engine.py", "core/engines/thread_engine.py"),
    "exports_reporting": ("core/artifacts/reporting.py", "core/artifacts/output.py", "core/artifacts/html_report.py"),
    "tor_proxy_ops": ("core/collect/network.py", "core/foundation/security_manager.py", "core/collect/anonymity.py"),
    "signal_fusion_lane": (
        "core/collect/source_fusion.py",
        "plugins/signal_fusion_core.py",
        "filters/signal_lane_fusion.py",
    ),
    "test_coverage": ("tests/",),
}
_WORKFLOW_FEATURES: dict[str, tuple[str, ...]] = {
    "profile": (
        "async_engine",
        "retry_backoff",
        "rate_limit",
        "plugin_module_system",
        "signal_fusion_lane",
        "exports_reporting",
        "test_coverage",
    ),
    "surface": (
        "async_engine",
        "retry_backoff",
        "rate_limit",
        "workspace_db",
        "signal_fusion_lane",
        "tor_proxy_ops",
        "exports_reporting",
    ),
    "fusion": (
        "parallel_workers",
        "plugin_module_system",
        "signal_fusion_lane",
        "workspace_db",
        "caching",
        "exports_reporting",
        "test_coverage",
    ),
}


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    if not match:
        return None
    return match.group(0).strip()


def _dedupe(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _resolve_source_map_path(path: str | Path) -> Path:
    return Path(path)


def _resolve_source_scan_root(root: str | Path) -> Path:
    return Path(root)


def _workflow_capability_plan(
    workflow: str,
    features: Sequence[str],
    feature_index: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    for feature in features:
        feature_meta = feature_index.get(feature, {})
        plan.append(
            {
                "feature": feature,
                "priority": str(feature_meta.get("priority", "optimize")),
                "action": str(feature_meta.get("action", _feature_action(feature))),
            }
        )
    return plan


def load_source_map(path: str | Path = DEFAULT_SOURCE_MAP_PATH) -> CapabilitySourceMap:
    """Parse the capability source map text file into structured entries."""

    requested_path = Path(path)
    source_path = _resolve_source_map_path(requested_path)
    if not source_path.exists():
        return CapabilitySourceMap(tools=(), source_path=requested_path)

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

    return CapabilitySourceMap(tools=tuple(tools), source_path=requested_path)


def map_sources_to_core_modules(
    mapping: CapabilitySourceMap,
) -> dict[str, list[str]]:
    """Map source-study strengths to Silica-X module focus areas."""

    module_map: dict[str, list[str]] = {
        "core/collect/scanner.py": [],
        "core/collect/domain_intel.py": [],
        "core/extensions/signal_forge.py": [],
        "core/extensions/signal_sieve.py": [],
        "core/artifacts/output.py": [],
        "core/artifacts/html_report.py": [],
    }

    for tool in mapping.tools:
        lowered = " ".join((tool.name, *tool.bullets)).lower()
        if any(token in lowered for token in ("username", "profile", "account", "identity", "social")):
            module_map["core/collect/scanner.py"].append(tool.name)
        if any(token in lowered for token in ("domain", "subdomain", "network", "dns", "surface")):
            module_map["core/collect/domain_intel.py"].append(tool.name)
        if any(token in lowered for token in ("modular", "module", "plugin", "workflow", "collector")):
            module_map["core/extensions/signal_forge.py"].append(tool.name)
        if any(token in lowered for token in ("correlation", "workspace", "normalization", "pipeline")):
            module_map["core/extensions/signal_sieve.py"].append(tool.name)
        if any(token in lowered for token in ("output", "json", "html", "report", "cli")):
            module_map["core/artifacts/output.py"].append(tool.name)
            module_map["core/artifacts/html_report.py"].append(tool.name)

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


def recommend_focus_modules(workflow: str, mapping: CapabilitySourceMap) -> list[str]:
    """Return human-readable source-study recommendations for a workflow area."""

    module_map = map_sources_to_core_modules(mapping)
    key = workflow.strip().lower()
    if key == "profile":
        targets = module_map.get("core/collect/scanner.py", [])
    elif key == "surface":
        targets = module_map.get("core/collect/domain_intel.py", [])
    elif key == "fusion":
        targets = module_map.get("core/extensions/signal_sieve.py", []) + module_map.get("core/artifacts/output.py", [])
    else:
        targets = []

    if not targets:
        return ["No mapped source focus target yet."]
    return [f"Study patterns from: {', '.join(targets)}"]


def scan_source_capabilities(
    root: str | Path = DEFAULT_SOURCE_SCAN_ROOT,
    *,
    max_file_bytes: int = 1_500_000,
) -> tuple[FrameworkCapabilityProfile, ...]:
    """Scan local source trees for capability signals."""

    base = _resolve_source_scan_root(root)
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
            "recommendations": ["No capability source frameworks were discovered."],
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
        "# Silica Capability Scan",
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
    recommendations = gap.get("recommendations")
    if isinstance(recommendations, list):
        for item in recommendations:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_capability_report(
    output_path: str | Path = "docs/silica-capability-scan.md",
    *,
    build_pack: bool = True,
) -> Path:
    """Scan frameworks and write markdown capability report to disk."""

    profiles = scan_source_capabilities()
    report = render_capability_markdown(profiles)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    if build_pack:
        build_capability_pack()
    return path


def _feature_strength(coverage_ratio: float) -> str:
    if coverage_ratio >= 0.75:
        return "core"
    if coverage_ratio >= 0.4:
        return "established"
    if coverage_ratio > 0.0:
        return "specialized"
    return "unobserved"


def _feature_priority(coverage_ratio: float) -> str:
    if coverage_ratio < 0.25:
        return "expand"
    if coverage_ratio < 0.6:
        return "optimize"
    return "harden"


def _feature_action(feature: str) -> str:
    actions = {
        "async_engine": "Increase non-blocking collectors and connector reuse.",
        "retry_backoff": "Tune retry windows, jitter, and transient-error handling.",
        "rate_limit": "Calibrate concurrency with adaptive workload backpressure.",
        "caching": "Extend TTL-aware cache layers for expensive enrichment calls.",
        "workspace_db": "Improve indexed storage for historical correlation replay.",
        "plugin_module_system": "Strengthen module contracts and discovery validation.",
        "parallel_workers": "Balance async/thread/process lanes by workload shape.",
        "exports_reporting": "Expand analyst outputs with richer graph/report artifacts.",
        "tor_proxy_ops": "Harden routing controls and privacy-aware collection profiles.",
        "signal_fusion_lane": "Expand connector orchestration to leverage high-value multi-source collectors safely.",
        "test_coverage": "Close regression gaps around failure paths and adapters.",
    }
    return actions.get(feature, "Advance this capability in the core pipeline.")


def _build_plugin_capability_views(
    feature_index: dict[str, dict[str, object]],
    *,
    output_root: Path,
) -> Path:
    from core.extensions.signal_forge import list_plugin_descriptors

    plans_dir = output_root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    inventory = list_plugin_descriptors(scope=None)
    index_payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "plugins",
        "inventory_count": len(inventory),
        "inventory": inventory,
    }
    (output_root / "index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    for workflow, features in _WORKFLOW_FEATURES.items():
        scoped_inventory = list_plugin_descriptors(scope=workflow)
        payload = {
            "workflow": workflow,
            "capability_plan": _workflow_capability_plan(workflow, features, feature_index),
            "recommended_plugins": [
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "aliases": [str(alias) for alias in (item.get("aliases") or [])],
                }
                for item in scoped_inventory
            ],
        }
        (plans_dir / f"{workflow}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    readme_lines = [
        "# Plugin Intel Views",
        "",
        "Silica-native plugin recommendations by workflow.",
        "",
        f"- Plugin inventory: {len(inventory)}",
        f"- Workflow profiles: {len(_WORKFLOW_FEATURES)}",
        "",
    ]
    (output_root / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    return output_root


def _build_filter_capability_views(
    feature_index: dict[str, dict[str, object]],
    *,
    output_root: Path,
) -> Path:
    from core.extensions.signal_sieve import list_filter_descriptors

    plans_dir = output_root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    inventory = list_filter_descriptors(scope=None)
    index_payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "filters",
        "inventory_count": len(inventory),
        "inventory": inventory,
    }
    (output_root / "index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    for workflow, features in _WORKFLOW_FEATURES.items():
        scoped_inventory = list_filter_descriptors(scope=workflow)
        payload = {
            "workflow": workflow,
            "capability_plan": _workflow_capability_plan(workflow, features, feature_index),
            "recommended_filters": [
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "aliases": [str(alias) for alias in (item.get("aliases") or [])],
                }
                for item in scoped_inventory
            ],
        }
        (plans_dir / f"{workflow}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    readme_lines = [
        "# Filter Intel Views",
        "",
        "Silica-native filter recommendations by workflow.",
        "",
        f"- Filter inventory: {len(inventory)}",
        f"- Workflow profiles: {len(_WORKFLOW_FEATURES)}",
        "",
    ]
    (output_root / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    return output_root


def build_capability_pack(
    root: str | Path = DEFAULT_SOURCE_SCAN_ROOT,
    *,
    output_root: str | Path = DEFAULT_CAPABILITY_PACK_ROOT,
    plugin_output_root: str | Path = DEFAULT_PLUGIN_CAPABILITY_ROOT,
    filter_output_root: str | Path = DEFAULT_FILTER_CAPABILITY_ROOT,
) -> Path:
    """Build internal intel assets from scanned capability signals."""

    profiles = scan_source_capabilities(root)
    out_root = Path(output_root)
    baseline_dir = out_root / "baseline"
    features_dir = out_root / "features"
    plans_dir = out_root / "plans"
    wiring_dir = out_root / "wiring"
    for folder in (out_root, baseline_dir, features_dir, plans_dir, wiring_dir):
        folder.mkdir(parents=True, exist_ok=True)

    source_count = len(profiles)
    files_scanned = sum(profile.file_count for profile in profiles)
    feature_totals: dict[str, int] = {}
    feature_presence: dict[str, int] = {}
    for feature in _FEATURE_PATTERNS:
        total = sum(int(profile.feature_hits.get(feature, 0)) for profile in profiles)
        presence = sum(1 for profile in profiles if int(profile.feature_hits.get(feature, 0)) > 0)
        feature_totals[feature] = total
        feature_presence[feature] = presence

    baseline_payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count": source_count,
        "files_scanned": files_scanned,
        "feature_totals": feature_totals,
        "feature_presence": feature_presence,
    }
    (baseline_dir / "scan-summary.json").write_text(
        json.dumps(baseline_payload, indent=2),
        encoding="utf-8",
    )

    feature_index: dict[str, dict[str, object]] = {}
    for feature in _FEATURE_PATTERNS:
        coverage_ratio = 0.0
        if source_count > 0:
            coverage_ratio = feature_presence[feature] / float(source_count)
        feature_dir = features_dir / feature
        feature_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature": feature,
            "description": _FEATURE_DESCRIPTIONS.get(feature, ""),
            "target_modules": list(_FEATURE_TARGET_MODULES.get(feature, ())),
            "signal_total": feature_totals[feature],
            "coverage_ratio": round(coverage_ratio, 4),
            "strength": _feature_strength(coverage_ratio),
            "priority": _feature_priority(coverage_ratio),
            "action": _feature_action(feature),
        }
        (feature_dir / "details.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        feature_index[feature] = payload

    workflow_index: dict[str, dict[str, object]] = {}
    for workflow, features in _WORKFLOW_FEATURES.items():
        modules: list[str] = []
        for feature in features:
            modules.extend(_FEATURE_TARGET_MODULES.get(feature, ()))
        deduped_modules: list[str] = []
        seen: set[str] = set()
        for module in modules:
            if module in seen:
                continue
            seen.add(module)
            deduped_modules.append(module)
        payload = {
            "workflow": workflow,
            "features": list(features),
            "capability_plan": _workflow_capability_plan(workflow, features, feature_index),
            "target_modules": deduped_modules,
        }
        (plans_dir / f"{workflow}.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        workflow_index[workflow] = payload

    feature_to_modules = {
        feature: list(_FEATURE_TARGET_MODULES.get(feature, ()))
        for feature in _FEATURE_PATTERNS
    }
    workflow_to_features = {
        workflow: list(features)
        for workflow, features in _WORKFLOW_FEATURES.items()
    }
    (wiring_dir / "feature-module-map.json").write_text(
        json.dumps(feature_to_modules, indent=2),
        encoding="utf-8",
    )
    (wiring_dir / "workflow-feature-map.json").write_text(
        json.dumps(workflow_to_features, indent=2),
        encoding="utf-8",
    )

    index_payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_root": str(Path(root)),
        "source_count": source_count,
        "files_scanned": files_scanned,
        "features": feature_index,
        "workflows": workflow_index,
    }
    (out_root / "index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
    readme_lines = [
        "# Silica-X Intel",
        "",
        "Generated internal capability intelligence for Silica-X architecture alignment.",
        "",
        f"- Sources scanned: {source_count}",
        f"- Files scanned: {files_scanned}",
        f"- Features mapped: {len(_FEATURE_PATTERNS)}",
        f"- Workflow profiles: {len(_WORKFLOW_FEATURES)}",
        "",
        "Folders:",
        "- `baseline/`: scan coverage totals and aggregate feature presence",
        "- `features/`: per-feature details, priority, and implementation action",
        "- `plans/`: workflow-level plans mapped from detected feature signals",
        "- `wiring/`: feature/module and workflow/feature map files",
        "",
    ]
    (out_root / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")

    plugin_root = Path(plugin_output_root)
    filter_root = Path(filter_output_root)
    _build_plugin_capability_views(feature_index, output_root=plugin_root)
    _build_filter_capability_views(feature_index, output_root=filter_root)

    return out_root


def load_capability_index(path: str | Path = DEFAULT_CAPABILITY_PACK_ROOT / "index.json") -> dict[str, object]:
    """Load previously generated capability-pack index payload."""

    payload_path = Path(path)
    if not payload_path.exists():
        return {}
    try:
        parsed = json.loads(payload_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def recommend_capability_priorities(
    workflow: str,
    *,
    capability_index_path: str | Path = DEFAULT_CAPABILITY_PACK_ROOT / "index.json",
) -> list[str]:
    """Recommend capability priorities from capability-pack index."""

    payload = load_capability_index(capability_index_path)
    workflows = payload.get("workflows")
    if not isinstance(workflows, dict):
        return []

    selected = workflows.get(workflow.strip().lower())
    if not isinstance(selected, dict):
        return []
    features_payload = payload.get("features")
    if not isinstance(features_payload, dict):
        return []
    selected_features = selected.get("features")
    if not isinstance(selected_features, list):
        return []

    hints: list[str] = []
    for feature in selected_features:
        feature_key = str(feature)
        feature_data = features_payload.get(feature_key, {})
        if not isinstance(feature_data, dict):
            continue
        priority = str(feature_data.get("priority") or "optimize")
        action = str(feature_data.get("action") or _feature_action(feature_key))
        hints.append(f"Capability priority ({feature_key}, {priority}): {action}")
    return hints[:3]

