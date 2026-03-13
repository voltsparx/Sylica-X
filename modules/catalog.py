# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Silica source-intel module catalog builder and query helpers."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone
from importlib import resources as importlib_resources
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from core.foundation.metadata import PROJECT_NAME, VERSION, VERSION_THEME


DEFAULT_SOURCE_ROOT = Path("intel-sources")
DEFAULT_MODULES_ROOT = Path("modules")
DEFAULT_INDEX_PATH = DEFAULT_MODULES_ROOT / "index.json"
DEFAULT_PLUGIN_INDEX_PATH = DEFAULT_MODULES_ROOT / "plugin-modules.json"
DEFAULT_FILTER_INDEX_PATH = DEFAULT_MODULES_ROOT / "filter-modules.json"
DEFAULT_CATALOG_VERSION = "2.1"
DEFAULT_MAX_WORKERS = max(4, min(16, (os.cpu_count() or 4) * 2))
MAX_QUERY_LIMIT = 1000

SUPPORTED_EXTENSIONS = {
    ".py",
    ".go",
    ".js",
    ".ts",
    ".rb",
    ".php",
    ".java",
    ".cs",
    ".sh",
    ".ps1",
}
SKIP_DIR_NAMES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "docs",
    "doc",
    "test",
    "tests",
    "examples",
    "example",
    "samples",
    "sample",
    "static",
}

PLUGIN_HINTS = (
    "plugin",
    "plugins",
    "module",
    "modules",
    "mixin",
    "collector",
    "source",
    "extractor",
    "enrich",
    "intel",
    "scan",
    "recon",
)
FILTER_HINTS = (
    "filter",
    "filters",
    "normalize",
    "normalizer",
    "sanitize",
    "sanitizer",
    "dedupe",
    "dedup",
    "classifier",
    "resolver",
    "parser",
    "transform",
    "reduce",
    "clean",
)
PROFILE_HINTS = (
    "profile",
    "username",
    "account",
    "social",
    "identity",
    "persona",
    "email",
    "name",
    "user",
)
SURFACE_HINTS = (
    "surface",
    "domain",
    "subdomain",
    "dns",
    "rdap",
    "http",
    "https",
    "header",
    "whois",
    "network",
    "ip",
    "host",
)
FUSION_HINTS = (
    "fusion",
    "graph",
    "timeline",
    "correlat",
    "risk",
    "score",
    "cluster",
    "link",
    "merge",
    "aggregate",
)
CAPABILITY_HINTS: dict[str, tuple[str, ...]] = {
    "identity": ("username", "profile", "persona", "social", "account", "email", "name"),
    "infrastructure": ("domain", "subdomain", "dns", "whois", "ip", "host", "network", "rdap"),
    "web": ("http", "https", "endpoint", "url", "header", "crawl", "scrape"),
    "enrichment": ("enrich", "extract", "parser", "resolver", "intel", "collector", "source"),
    "correlation": ("fusion", "graph", "link", "merge", "timeline", "cluster", "correlat"),
    "automation": ("batch", "queue", "async", "thread", "worker", "pipeline", "scheduler"),
    "reporting": ("report", "html", "csv", "json", "export", "dashboard", "summary"),
    "risk": ("risk", "confidence", "severity", "score", "exposure", "threat", "priority"),
}

SCOPE_ORDER = ("profile", "surface", "fusion")
VALID_KINDS = {"plugin", "filter"}
SORTABLE_FIELDS = {
    "framework",
    "file",
    "kind",
    "power_score",
    "confidence_score",
    "plugin_score",
    "filter_score",
    "profile_score",
    "surface_score",
    "fusion_score",
    "capability_count",
}
TEXT_SORT_FIELDS = {"framework", "file", "kind"}


def _silica_meta() -> dict[str, str]:
    return {
        "project": PROJECT_NAME,
        "version": VERSION,
        "theme": VERSION_THEME,
        "component": "module_catalog",
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json_resource(package: str, relative_path: str) -> dict[str, Any] | None:
    try:
        resource = importlib_resources.files(package).joinpath(relative_path)
    except Exception:
        return None
    if not resource.is_file():
        return None
    try:
        payload = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_module_catalog_resource(payload_path: Path) -> dict[str, Any] | None:
    parts = payload_path.parts
    if not parts:
        return None
    if parts[0] != DEFAULT_MODULES_ROOT.name:
        return None
    relative = Path(*parts[1:]).as_posix()
    if not relative:
        return None
    return _load_json_resource(DEFAULT_MODULES_ROOT.name, relative)


def _normalize_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "module"


def _normalize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _score(text: str, tokens: tuple[str, ...]) -> int:
    return sum(1 for token in tokens if token in text)


def _iter_framework_source_files(framework_root: Path) -> list[Path]:
    matches: list[Path] = []
    for root, dirs, files in os.walk(framework_root):
        dirs[:] = [
            name
            for name in dirs
            if name.lower() not in SKIP_DIR_NAMES and not name.startswith(".")
        ]
        for filename in files:
            suffix = Path(filename).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            matches.append(Path(root) / filename)
    return matches


def _read_text_sample(
    file_path: Path,
    *,
    max_file_bytes: int,
    sample_bytes: int,
) -> tuple[str, int]:
    with suppress(OSError):
        if file_path.stat().st_size > max_file_bytes:
            return "", 0
    try:
        with file_path.open("rb") as handle:
            payload = handle.read(max(1, sample_bytes))
    except OSError:
        return "", 0
    return payload.decode("utf-8", errors="ignore").lower(), len(payload)


def _infer_kind(path_text: str, content_text: str) -> tuple[str, int, int]:
    combined = f"{path_text} {content_text}"
    plugin_score = _score(combined, PLUGIN_HINTS)
    filter_score = _score(combined, FILTER_HINTS)

    if "filter" in path_text:
        return "filter", plugin_score, filter_score
    if filter_score > plugin_score:
        return "filter", plugin_score, filter_score
    return "plugin", plugin_score, filter_score


def _infer_scopes(path_text: str, content_text: str) -> tuple[tuple[str, ...], dict[str, int]]:
    combined = f"{path_text} {content_text}"
    scores = {
        "profile": _score(combined, PROFILE_HINTS),
        "surface": _score(combined, SURFACE_HINTS),
        "fusion": _score(combined, FUSION_HINTS),
    }
    scopes = tuple(scope for scope in SCOPE_ORDER if scores[scope] > 0)
    if scopes:
        return scopes, scores
    return SCOPE_ORDER, scores


def _infer_capabilities(path_text: str, content_text: str) -> tuple[list[str], dict[str, int]]:
    combined = f"{path_text} {content_text}"
    scores: dict[str, int] = {}
    for capability, hints in CAPABILITY_HINTS.items():
        hit_count = _score(combined, hints)
        if hit_count > 0:
            scores[capability] = hit_count

    if not scores:
        return ["general"], {"general": 1}

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [key for key, _ in ranked], scores


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _signal_value(row: dict[str, Any], key: str) -> int:
    signals = row.get("signals", {})
    if not isinstance(signals, dict):
        return 0
    return _safe_int(signals.get(key), 0)


def _power_score(
    *,
    kind: str,
    plugin_score: int,
    filter_score: int,
    scope_scores: dict[str, int],
    capabilities: list[str],
    capability_scores: dict[str, int],
    line_estimate: int,
    language: str,
) -> int:
    primary_signal = max(plugin_score, filter_score)
    scope_total = sum(_safe_int(scope_scores.get(scope), 0) for scope in SCOPE_ORDER)
    capability_peak = max((_safe_int(value, 0) for value in capability_scores.values()), default=0)

    score = 0
    score += min(32, primary_signal * 4)
    score += min(24, scope_total * 2)
    score += min(18, len(capabilities) * 4)
    score += min(12, capability_peak * 2)
    score += 4 if kind in VALID_KINDS else 0
    score += 3 if language in {"py", "go", "js", "ts"} else 1
    if line_estimate >= 400:
        score += 7
    elif line_estimate >= 160:
        score += 4
    elif line_estimate >= 40:
        score += 2

    return max(0, min(score, 100))


def _confidence_score(
    *,
    kind: str,
    path_text: str,
    plugin_score: int,
    filter_score: int,
    scopes: tuple[str, ...],
) -> int:
    score = 20
    score += min(26, max(plugin_score, filter_score) * 3)
    score += min(20, abs(plugin_score - filter_score) * 4)
    score += min(18, len(scopes) * 6)
    if kind == "filter" and "filter" in path_text:
        score += 12
    if kind == "plugin" and any(token in path_text for token in ("plugin", "module", "collector", "source")):
        score += 12
    return max(0, min(score, 100))


def _match_search(row: dict[str, Any], search: str | None) -> bool:
    if not search:
        return True
    tokens = [token for token in re.split(r"\s+", search.strip().lower()) if token]
    if not tokens:
        return True

    capabilities = row.get("capabilities", [])
    scopes = row.get("scopes", [])
    haystack = " ".join(
        [
            str(row.get("id", "")).lower(),
            str(row.get("framework", "")).lower(),
            str(row.get("path", "")).lower(),
            str(row.get("file", "")).lower(),
            str(row.get("language", "")).lower(),
            str(row.get("kind", "")).lower(),
            " ".join(str(value).lower() for value in capabilities if isinstance(value, str)),
            " ".join(str(value).lower() for value in scopes if isinstance(value, str)),
        ]
    )
    return all(token in haystack for token in tokens)


def _match_tags(row: dict[str, Any], tags: list[str] | None) -> bool:
    normalized_tags = {_normalize_tag(value) for value in (tags or []) if value and value.strip()}
    if not normalized_tags:
        return True

    row_tags = {
        _normalize_tag(str(value))
        for value in (row.get("capabilities", []) or [])
        if isinstance(value, str) and value.strip()
    }
    return normalized_tags.issubset(row_tags)


def _power_value(row: dict[str, Any]) -> int:
    metrics = row.get("metrics", {})
    if isinstance(metrics, dict):
        return _safe_int(metrics.get("power_score"), 0)
    return 0


def _sort_value(row: dict[str, Any], sort_by: str) -> Any:
    field = sort_by if sort_by in SORTABLE_FIELDS else "framework"
    if field == "framework":
        return str(row.get("framework", "")).lower()
    if field == "file":
        return str(row.get("file", "")).lower()
    if field == "kind":
        return str(row.get("kind", "")).lower()
    if field == "power_score":
        return _power_value(row)

    metrics = row.get("metrics", {})
    if field == "confidence_score" and isinstance(metrics, dict):
        return _safe_int(metrics.get("confidence_score"), 0)

    if field == "capability_count":
        capabilities = row.get("capabilities", [])
        if isinstance(capabilities, list):
            return len(capabilities)
        return 0

    signal_field = {
        "plugin_score": "plugin_score",
        "filter_score": "filter_score",
        "profile_score": "profile_score",
        "surface_score": "surface_score",
        "fusion_score": "fusion_score",
    }.get(field)
    if signal_field:
        return _signal_value(row, signal_field)

    return str(row.get("framework", "")).lower()


def _top_counts(counter: Counter[str], *, limit: int = 8) -> list[str]:
    return [f"{name}:{count}" for name, count in counter.most_common(limit)]


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def _normalize_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    return max(1, min(MAX_QUERY_LIMIT, _safe_int(limit, 1)))


def _normalize_offset(offset: int | None) -> int:
    return max(0, _safe_int(offset, 0))


def _collect_source_file_jobs(
    source_root: Path,
    frameworks: list[Path],
) -> list[tuple[str, Path, Path]]:
    jobs: list[tuple[str, Path, Path]] = []
    for framework_root in frameworks:
        framework_name = framework_root.name
        for file_path in _iter_framework_source_files(framework_root):
            jobs.append((framework_name, framework_root, file_path))

    jobs.sort(key=lambda item: (item[0].lower(), item[2].relative_to(source_root).as_posix().lower()))
    return jobs


def _compute_source_fingerprint(
    source_root: Path,
    source_files: list[Path] | None = None,
) -> str:
    digest = hashlib.sha256()
    digest.update(source_root.as_posix().encode("utf-8"))

    if source_files is None:
        files = [
            path
            for path in source_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        files.sort(key=lambda path: path.relative_to(source_root).as_posix().lower())
    else:
        files = sorted(source_files, key=lambda path: path.relative_to(source_root).as_posix().lower())

    for file_path in files:
        relative = file_path.relative_to(source_root).as_posix().lower()
        digest.update(relative.encode("utf-8"))
        with suppress(OSError):
            stat = file_path.stat()
            digest.update(str(int(stat.st_size)).encode("utf-8"))
            digest.update(str(int(stat.st_mtime_ns)).encode("utf-8"))

    return digest.hexdigest()


def _resolve_max_workers(value: int | None) -> int:
    if value is None:
        return DEFAULT_MAX_WORKERS
    return max(1, min(64, _safe_int(value, DEFAULT_MAX_WORKERS)))


def _analyze_source_file(
    *,
    source_root: Path,
    framework_name: str,
    framework_root: Path,
    file_path: Path,
    max_file_bytes: int,
    sample_bytes: int,
) -> dict[str, Any]:
    relative_framework_path = file_path.relative_to(framework_root).as_posix()
    relative_full_path = file_path.relative_to(source_root).as_posix()
    path_text = f"{framework_name.lower()} {relative_framework_path.lower()}"
    content_text, sampled_bytes = _read_text_sample(
        file_path,
        max_file_bytes=max_file_bytes,
        sample_bytes=sample_bytes,
    )
    kind, plugin_score, filter_score = _infer_kind(path_text, content_text)
    scopes, scope_scores = _infer_scopes(path_text, content_text)
    capabilities, capability_scores = _infer_capabilities(path_text, content_text)

    file_size = 0
    with suppress(OSError):
        file_size = int(file_path.stat().st_size)

    line_estimate = max(1, content_text.count("\n") + (1 if content_text else 0))
    power_score = _power_score(
        kind=kind,
        plugin_score=plugin_score,
        filter_score=filter_score,
        scope_scores=scope_scores,
        capabilities=capabilities,
        capability_scores=capability_scores,
        line_estimate=line_estimate,
        language=file_path.suffix.lstrip(".").lower(),
    )
    confidence_score = _confidence_score(
        kind=kind,
        path_text=path_text,
        plugin_score=plugin_score,
        filter_score=filter_score,
        scopes=scopes,
    )

    file_stem = Path(relative_framework_path).with_suffix("").as_posix()
    return {
        "id": _normalize_id(f"{framework_name}-{file_stem}"),
        "framework": framework_name,
        "path": relative_full_path,
        "file": relative_framework_path,
        "language": file_path.suffix.lstrip(".").lower(),
        "kind": kind,
        "scopes": list(scopes),
        "capabilities": capabilities,
        "signals": {
            "plugin_score": plugin_score,
            "filter_score": filter_score,
            "profile_score": scope_scores["profile"],
            "surface_score": scope_scores["surface"],
            "fusion_score": scope_scores["fusion"],
            "capability_scores": capability_scores,
        },
        "metrics": {
            "power_score": power_score,
            "confidence_score": confidence_score,
            "file_size_bytes": file_size,
            "line_estimate": line_estimate,
            "sampled_bytes": sampled_bytes,
        },
    }


def _kind_payload(
    kind: str,
    modules: list[dict[str, Any]],
    *,
    source_root: Path,
) -> dict[str, Any]:
    selected = [row for row in modules if str(row.get("kind", "")).lower() == kind]
    framework_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()

    total_power = 0
    for row in selected:
        framework = str(row.get("framework", "")).strip()
        if framework:
            framework_counts[framework] += 1
        for scope in row.get("scopes", []) or []:
            scope_name = str(scope).strip().lower()
            if scope_name in SCOPE_ORDER:
                scope_counts[scope_name] += 1
        for capability in row.get("capabilities", []) or []:
            cap_name = str(capability).strip().lower()
            if cap_name:
                capability_counts[cap_name] += 1
        total_power += _power_value(row)

    avg_power = 0.0
    if selected:
        avg_power = round(total_power / float(len(selected)), 2)

    return {
        "silica": _silica_meta(),
        "generated_at_utc": _now_utc(),
        "kind": kind,
        "source_root": source_root.as_posix(),
        "module_count": len(selected),
        "framework_counts": dict(sorted(framework_counts.items(), key=lambda item: item[0])),
        "scope_counts": {
            "profile": scope_counts.get("profile", 0),
            "surface": scope_counts.get("surface", 0),
            "fusion": scope_counts.get("fusion", 0),
        },
        "power_score_avg": avg_power,
        "top_capabilities": _top_counts(capability_counts, limit=8),
        "modules": selected,
    }


def build_module_catalog(
    source_root: str | Path = DEFAULT_SOURCE_ROOT,
    *,
    output_root: str | Path = DEFAULT_MODULES_ROOT,
    max_file_bytes: int = 2_000_000,
    sample_bytes: int = 24_000,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Build module catalog and write index artifacts under modules/."""

    scan_started = time.perf_counter()
    scan_started_utc = _now_utc()

    source = Path(source_root)
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)

    frameworks = sorted(path for path in source.iterdir() if path.is_dir()) if source.exists() else []
    jobs = _collect_source_file_jobs(source, frameworks) if source.exists() else []
    source_files = [file_path for _framework_name, _framework_root, file_path in jobs]
    source_fingerprint = _compute_source_fingerprint(source, source_files) if source.exists() else "missing-root"
    resolved_max_workers = _resolve_max_workers(max_workers)

    module_rows: list[dict[str, Any]]
    if jobs and resolved_max_workers > 1:
        with ThreadPoolExecutor(max_workers=resolved_max_workers, thread_name_prefix="silica-modcat") as executor:
            module_rows = list(
                executor.map(
                    lambda job: _analyze_source_file(
                        source_root=source,
                        framework_name=job[0],
                        framework_root=job[1],
                        file_path=job[2],
                        max_file_bytes=max_file_bytes,
                        sample_bytes=sample_bytes,
                    ),
                    jobs,
                )
            )
    else:
        module_rows = [
            _analyze_source_file(
                source_root=source,
                framework_name=framework_name,
                framework_root=framework_root,
                file_path=file_path,
                max_file_bytes=max_file_bytes,
                sample_bytes=sample_bytes,
            )
            for framework_name, framework_root, file_path in jobs
        ]

    kind_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    score_bands: Counter[str] = Counter()

    framework_stats_raw: dict[str, dict[str, Any]] = {}
    total_power = 0

    for row in module_rows:
        kind = str(row.get("kind", "")).strip().lower()
        if kind in VALID_KINDS:
            kind_counts[kind] += 1

        power_score = _power_value(row)
        total_power += power_score
        if power_score >= 70:
            score_bands["high"] += 1
        elif power_score >= 40:
            score_bands["medium"] += 1
        else:
            score_bands["low"] += 1

        language = str(row.get("language", "")).strip().lower()
        if language:
            language_counts[language] += 1

        framework = str(row.get("framework", "")).strip()
        if framework not in framework_stats_raw:
            framework_stats_raw[framework] = {
                "module_count": 0,
                "plugin_count": 0,
                "filter_count": 0,
                "profile_count": 0,
                "surface_count": 0,
                "fusion_count": 0,
                "power_score_total": 0,
                "capability_counts": Counter(),
                "language_counts": Counter(),
            }

        framework_row = framework_stats_raw[framework]
        framework_row["module_count"] += 1
        framework_row["power_score_total"] += power_score
        if kind == "plugin":
            framework_row["plugin_count"] += 1
        elif kind == "filter":
            framework_row["filter_count"] += 1

        framework_row["language_counts"][language] += 1
        for capability in row.get("capabilities", []) or []:
            cap_name = str(capability).strip().lower()
            if cap_name:
                capability_counts[cap_name] += 1
                framework_row["capability_counts"][cap_name] += 1

        for scope in row.get("scopes", []) or []:
            scope_name = str(scope).strip().lower()
            if scope_name not in SCOPE_ORDER:
                continue
            scope_counts[scope_name] += 1
            framework_row[f"{scope_name}_count"] += 1

    framework_stats: dict[str, dict[str, Any]] = {}
    for framework, values in sorted(framework_stats_raw.items(), key=lambda item: item[0]):
        module_count = _safe_int(values.get("module_count"), 0)
        avg_power = 0.0
        if module_count > 0:
            avg_power = round(_safe_int(values.get("power_score_total"), 0) / float(module_count), 2)
        framework_stats[framework] = {
            "module_count": module_count,
            "plugin_count": _safe_int(values.get("plugin_count"), 0),
            "filter_count": _safe_int(values.get("filter_count"), 0),
            "profile_count": _safe_int(values.get("profile_count"), 0),
            "surface_count": _safe_int(values.get("surface_count"), 0),
            "fusion_count": _safe_int(values.get("fusion_count"), 0),
            "power_score_avg": avg_power,
            "top_capabilities": _top_counts(values["capability_counts"], limit=6),
            "language_counts": dict(sorted(values["language_counts"].items(), key=lambda item: item[0])),
        }

    power_score_avg = 0.0
    if module_rows:
        power_score_avg = round(total_power / float(len(module_rows)), 2)

    scan_duration_ms = int((time.perf_counter() - scan_started) * 1000)
    payload = {
        "silica": _silica_meta(),
        "catalog_version": DEFAULT_CATALOG_VERSION,
        "generated_at_utc": _now_utc(),
        "source_root": source.as_posix(),
        "framework_count": len(frameworks),
        "module_count": len(module_rows),
        "kind_counts": {
            "plugin": kind_counts.get("plugin", 0),
            "filter": kind_counts.get("filter", 0),
        },
        "scope_counts": {
            "profile": scope_counts.get("profile", 0),
            "surface": scope_counts.get("surface", 0),
            "fusion": scope_counts.get("fusion", 0),
        },
        "capability_counts": dict(sorted(capability_counts.items(), key=lambda item: item[0])),
        "language_counts": dict(sorted(language_counts.items(), key=lambda item: item[0])),
        "score_bands": {
            "high": score_bands.get("high", 0),
            "medium": score_bands.get("medium", 0),
            "low": score_bands.get("low", 0),
        },
        "power_score_avg": power_score_avg,
        "build_stats": {
            "scan_started_utc": scan_started_utc,
            "scan_finished_utc": _now_utc(),
            "scan_duration_ms": scan_duration_ms,
            "max_file_bytes": max(1, int(max_file_bytes)),
            "sample_bytes": max(1, int(sample_bytes)),
            "max_workers": resolved_max_workers,
            "source_file_count": len(jobs),
            "source_fingerprint": source_fingerprint,
        },
        "frameworks": framework_stats,
        "modules": module_rows,
    }

    _atomic_write_json(out_root / "index.json", payload)
    _atomic_write_json(out_root / "plugin-modules.json", _kind_payload("plugin", module_rows, source_root=source))
    _atomic_write_json(out_root / "filter-modules.json", _kind_payload("filter", module_rows, source_root=source))

    readme_lines = [
        "# Modules Catalog",
        "",
        "Generated index for module-like capabilities discovered under `intel-sources/`.",
        "",
        f"- Generated by {PROJECT_NAME} v{VERSION} [{VERSION_THEME}]",
        "- `index.json`: full catalog with capability tags, scoring, and scope hints",
        "- `plugin-modules.json`: plugin-like subset",
        "- `filter-modules.json`: filter-like subset",
        "",
        "Refresh from CLI:",
        "- `python silica-x.py modules --sync`",
        "",
        "Advanced query examples:",
        "- `python silica-x.py modules --search dns --sort-by power_score --descending`",
        "- `python silica-x.py modules --kind plugin --tag identity --min-score 55`",
        "",
    ]
    (out_root / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    return payload


def load_module_catalog(path: str | Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    """Load module catalog index payload from disk."""

    payload_path = Path(path)
    payload = _load_json_payload(payload_path)
    if payload is not None:
        return payload
    package_payload = _load_module_catalog_resource(payload_path)
    if package_payload is not None:
        return package_payload
    return {}


def validate_module_catalog(
    catalog: dict[str, Any],
    *,
    expected_version: str = DEFAULT_CATALOG_VERSION,
) -> tuple[bool, list[str]]:
    """Validate basic catalog integrity and schema compatibility."""

    errors: list[str] = []
    if not isinstance(catalog, dict):
        return False, ["catalog payload is not a dictionary"]

    version = str(catalog.get("catalog_version") or "")
    if version != expected_version:
        errors.append(f"catalog_version mismatch: expected={expected_version} got={version or '-'}")

    rows = catalog.get("modules", [])
    if not isinstance(rows, list):
        errors.append("modules field is not a list")
        return False, errors

    required_fields = ("id", "framework", "path", "file", "language", "kind", "scopes", "signals", "metrics")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"module row {index} is not an object")
            if len(errors) >= 20:
                break
            continue
        for field in required_fields:
            if field not in row:
                errors.append(f"module row {index} missing field '{field}'")
                if len(errors) >= 20:
                    break
        if len(errors) >= 20:
            break

        if str(row.get("kind", "")).strip().lower() not in VALID_KINDS:
            errors.append(f"module row {index} has invalid kind '{row.get('kind')}'")
        if not isinstance(row.get("scopes", []), list):
            errors.append(f"module row {index} scopes is not a list")
        if not isinstance(row.get("signals", {}), dict):
            errors.append(f"module row {index} signals is not an object")
        if not isinstance(row.get("metrics", {}), dict):
            errors.append(f"module row {index} metrics is not an object")
        if len(errors) >= 20:
            break

    return len(errors) == 0, errors


def ensure_module_catalog(
    *,
    refresh: bool = False,
    source_root: str | Path = DEFAULT_SOURCE_ROOT,
    output_root: str | Path = DEFAULT_MODULES_ROOT,
    validate_catalog: bool = True,
    verify_source_fingerprint: bool = False,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Load module catalog or rebuild it when missing/stale."""

    index_path = Path(output_root) / "index.json"
    if refresh:
        return build_module_catalog(source_root, output_root=output_root, max_workers=max_workers)

    payload = load_module_catalog(index_path)
    if not payload:
        return build_module_catalog(source_root, output_root=output_root, max_workers=max_workers)

    if validate_catalog:
        valid, _errors = validate_module_catalog(payload)
        if not valid:
            return build_module_catalog(source_root, output_root=output_root, max_workers=max_workers)

    if verify_source_fingerprint:
        expected = str((payload.get("build_stats") or {}).get("source_fingerprint") or "").strip()
        source = Path(source_root)
        if expected and source.exists():
            current = _compute_source_fingerprint(source)
            if current != expected:
                return build_module_catalog(source_root, output_root=output_root, max_workers=max_workers)

    return payload


def select_module_entries(
    catalog: dict[str, Any],
    *,
    kind: str = "all",
    scope: str = "all",
    frameworks: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    tags: list[str] | None = None,
    min_score: int = 0,
    sort_by: str = "framework",
    descending: bool = False,
) -> list[dict[str, Any]]:
    """Filter module entries by kind, scope, framework, and relevance selectors."""

    rows_raw = catalog.get("modules", [])
    if not isinstance(rows_raw, list):
        return []

    kind_value = kind.strip().lower() if isinstance(kind, str) else "all"
    scope_value = scope.strip().lower() if isinstance(scope, str) else "all"
    framework_set = {item.strip().lower() for item in (frameworks or []) if item and item.strip()}
    min_power = max(0, _safe_int(min_score, 0))
    normalized_limit = _normalize_limit(limit)
    normalized_offset = _normalize_offset(offset)

    selected: list[dict[str, Any]] = []
    for row in rows_raw:
        if not isinstance(row, dict):
            continue

        row_kind = str(row.get("kind", "")).strip().lower()
        if kind_value in VALID_KINDS and row_kind != kind_value:
            continue

        row_scopes = [str(item).strip().lower() for item in (row.get("scopes", []) or [])]
        if scope_value in SCOPE_ORDER and scope_value not in row_scopes:
            continue

        row_framework = str(row.get("framework", "")).strip().lower()
        if framework_set and row_framework not in framework_set:
            continue

        if not _match_search(row, search):
            continue
        if not _match_tags(row, tags):
            continue
        if _power_value(row) < min_power:
            continue

        selected.append(row)

    normalized_sort = sort_by if sort_by in SORTABLE_FIELDS else "framework"
    selected.sort(key=lambda row: _sort_value(row, normalized_sort), reverse=bool(descending))

    if normalized_offset >= len(selected):
        return []

    paged = selected[normalized_offset:]
    if normalized_limit is not None:
        return paged[:normalized_limit]
    return paged


def query_module_catalog(
    catalog: dict[str, Any],
    *,
    kind: str = "all",
    scope: str = "all",
    frameworks: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    tags: list[str] | None = None,
    min_score: int = 0,
    sort_by: str = "framework",
    descending: bool = False,
) -> dict[str, Any]:
    """Return a structured query payload (summary + query metadata + entries)."""

    framework_values = [item.strip() for item in (frameworks or []) if item and item.strip()]
    tag_values = [_normalize_tag(item) for item in (tags or []) if item and item.strip()]
    full_entries = select_module_entries(
        catalog,
        kind=kind,
        scope=scope,
        frameworks=framework_values,
        limit=None,
        offset=0,
        search=search,
        tags=tag_values,
        min_score=min_score,
        sort_by=sort_by,
        descending=descending,
    )
    normalized_limit = _normalize_limit(limit) or 50
    normalized_offset = _normalize_offset(offset)
    matched_total = len(full_entries)
    entries = full_entries[normalized_offset : normalized_offset + normalized_limit]
    has_more = normalized_offset + len(entries) < matched_total
    return {
        "summary": summarize_module_catalog(catalog),
        "query": {
            "scope": scope,
            "kind": kind,
            "frameworks": framework_values,
            "search": str(search or "").strip(),
            "tags": tag_values,
            "min_score": max(0, _safe_int(min_score, 0)),
            "sort_by": sort_by if sort_by in SORTABLE_FIELDS else "framework",
            "descending": bool(descending),
            "limit": normalized_limit,
            "offset": normalized_offset,
        },
        "matched_total": matched_total,
        "returned_count": len(entries),
        "has_more": has_more,
        "entries": entries,
    }


def summarize_module_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Return compact summary stats for module catalog payload."""

    rows_raw = catalog.get("modules", [])
    if not isinstance(rows_raw, list):
        rows_raw = []

    frameworks: set[str] = set()
    kind_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    score_bands: Counter[str] = Counter()

    total_power = 0
    for row in rows_raw:
        if not isinstance(row, dict):
            continue
        framework = str(row.get("framework", "")).strip()
        if framework:
            frameworks.add(framework)

        kind = str(row.get("kind", "")).strip().lower()
        if kind in VALID_KINDS:
            kind_counts[kind] += 1

        language = str(row.get("language", "")).strip().lower()
        if language:
            language_counts[language] += 1

        for scope in row.get("scopes", []) or []:
            scope_name = str(scope).strip().lower()
            if scope_name in SCOPE_ORDER:
                scope_counts[scope_name] += 1

        for capability in row.get("capabilities", []) or []:
            cap_name = str(capability).strip().lower()
            if cap_name:
                capability_counts[cap_name] += 1

        power_score = _power_value(row)
        total_power += power_score
        if power_score >= 70:
            score_bands["high"] += 1
        elif power_score >= 40:
            score_bands["medium"] += 1
        else:
            score_bands["low"] += 1

    power_avg = 0.0
    if rows_raw:
        power_avg = round(total_power / float(len(rows_raw)), 2)
    catalog_power_avg = _safe_float(catalog.get("power_score_avg"), power_avg)

    framework_list = sorted(frameworks)
    framework_count = len(framework_list)
    module_count = len(rows_raw)
    if not rows_raw:
        framework_count = _safe_int(catalog.get("framework_count"), framework_count)
        module_count = _safe_int(catalog.get("module_count"), module_count)

    return {
        "catalog_version": str(catalog.get("catalog_version") or DEFAULT_CATALOG_VERSION),
        "generated_at_utc": str(catalog.get("generated_at_utc", "")),
        "framework_count": framework_count,
        "frameworks": framework_list,
        "module_count": module_count,
        "kind_counts": {
            "plugin": _safe_int((catalog.get("kind_counts") or {}).get("plugin"), kind_counts.get("plugin", 0)),
            "filter": _safe_int((catalog.get("kind_counts") or {}).get("filter"), kind_counts.get("filter", 0)),
        },
        "scope_counts": {
            "profile": _safe_int((catalog.get("scope_counts") or {}).get("profile"), scope_counts.get("profile", 0)),
            "surface": _safe_int((catalog.get("scope_counts") or {}).get("surface"), scope_counts.get("surface", 0)),
            "fusion": _safe_int((catalog.get("scope_counts") or {}).get("fusion"), scope_counts.get("fusion", 0)),
        },
        "capability_counts": dict(sorted(capability_counts.items(), key=lambda item: item[0])),
        "language_counts": dict(sorted(language_counts.items(), key=lambda item: item[0])),
        "score_bands": {
            "high": score_bands.get("high", 0),
            "medium": score_bands.get("medium", 0),
            "low": score_bands.get("low", 0),
        },
        "power_score_avg": round(catalog_power_avg, 2),
    }
