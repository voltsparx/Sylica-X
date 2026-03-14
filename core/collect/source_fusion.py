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

"""Silica connector orchestration with normalized multi-source signal extraction."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from core.collect.domain_intel import normalize_domain


DEFAULT_SOURCE_ROOT = Path("intel-sources")
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_MAX_CONNECTORS = 4

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,24}\b")


@dataclass(frozen=True)
class ConnectorSpec:
    connector_id: str
    title: str
    scopes: tuple[str, ...]
    binary_candidates: tuple[str, ...] = ()
    source_entrypoints: tuple[str, ...] = ()
    supports_execution: bool = True


@dataclass(frozen=True)
class ConnectorRuntime:
    spec: ConnectorSpec
    binary_path: str | None
    source_entry: str | None
    executable: bool


@dataclass(frozen=True)
class ConnectorCommandPlan:
    connector_id: str
    title: str
    launch_mode: str
    command: tuple[str, ...]
    cwd: str | None


CONNECTOR_REGISTRY: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        connector_id="identity_mesh_alpha",
        title="Identity Mesh Alpha",
        scopes=("profile", "fusion"),
        binary_candidates=("source-pack-06", "source-pack-06.py"),
        source_entrypoints=("intel-sources/source-pack-06/source-pack-06_project/__main__.py",),
    ),
    ConnectorSpec(
        connector_id="identity_mesh_beta",
        title="Identity Mesh Beta",
        scopes=("profile", "fusion"),
        binary_candidates=("source-pack-03",),
        source_entrypoints=("intel-sources/source-pack-03/source-pack-03/__main__.py",),
    ),
    ConnectorSpec(
        connector_id="surface_grid_alpha",
        title="Surface Grid Alpha",
        scopes=("surface", "fusion"),
        binary_candidates=("source-pack-01",),
    ),
    ConnectorSpec(
        connector_id="surface_grid_beta",
        title="Surface Grid Beta",
        scopes=("surface", "fusion"),
        binary_candidates=("source-pack-08",),
    ),
    ConnectorSpec(
        connector_id="signal_graph_core",
        title="Signal Graph Core",
        scopes=("profile", "surface", "fusion"),
        source_entrypoints=("intel-sources/source-pack-07/sf.py", "intel-sources/source-pack-07/sfscan.py"),
        supports_execution=False,
    ),
    ConnectorSpec(
        connector_id="module_fabric_core",
        title="Module Fabric Core",
        scopes=("profile", "surface", "fusion"),
        binary_candidates=("source-pack-05", "source-pack-05-cli"),
        source_entrypoints=(
            "intel-sources/source-pack-05/source-pack-05",
            "intel-sources/source-pack-05/source-pack-05-cli",
        ),
        supports_execution=False,
    ),
    ConnectorSpec(
        connector_id="signal_fabric_core",
        title="Signal Fabric Core",
        scopes=("profile", "surface", "fusion"),
        source_entrypoints=("intel-sources/source-pack-02/source-pack-02.py",),
        supports_execution=False,
    ),
)


def _safe_username(raw_username: str | None) -> str:
    value = str(raw_username or "").strip()
    if not value:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value):
        return ""
    return value


def _safe_domain(raw_domain: str | None) -> str:
    value = normalize_domain(str(raw_domain or ""))
    if not value:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", value):
        return ""
    return value


def _find_binary_path(binary_candidates: tuple[str, ...]) -> str | None:
    for binary_name in binary_candidates:
        resolved = shutil.which(binary_name)
        if resolved:
            return resolved
    return None


def _find_source_entry(source_entrypoints: tuple[str, ...]) -> str | None:
    for entry in source_entrypoints:
        path = Path(entry)
        if path.exists() and path.is_file():
            return str(path)
    return None


def detect_connector_runtimes() -> list[ConnectorRuntime]:
    """Detect runtime availability for known Silica connector specs."""

    runtimes: list[ConnectorRuntime] = []
    for spec in CONNECTOR_REGISTRY:
        binary_path = _find_binary_path(spec.binary_candidates)
        source_entry = _find_source_entry(spec.source_entrypoints)
        executable = bool(spec.supports_execution and (binary_path or source_entry))
        runtimes.append(
            ConnectorRuntime(
                spec=spec,
                binary_path=binary_path,
                source_entry=source_entry,
                executable=executable,
            )
        )
    return runtimes


def _python_launcher(source_entry: str) -> tuple[tuple[str, ...], str | None]:
    entry = Path(source_entry)
    return (sys.executable, str(entry)), str(entry.parent)


def _build_command_plan(
    runtime: ConnectorRuntime,
    *,
    mode: str,
    username: str,
    domain: str,
    timeout_seconds: int,
) -> ConnectorCommandPlan | None:
    if not runtime.executable:
        return None
    if mode not in runtime.spec.scopes:
        return None

    binary_path = runtime.binary_path
    source_entry = runtime.source_entry
    if binary_path:
        launcher: tuple[str, ...] = (binary_path,)
        cwd = None
        launch_mode = "binary"
    elif source_entry:
        launcher, cwd = _python_launcher(source_entry)
        launch_mode = "source"
    else:
        return None

    capped_timeout = max(5, min(120, int(timeout_seconds)))
    connector_id = runtime.spec.connector_id
    if connector_id == "identity_mesh_alpha":
        if not username:
            return None
        command = (*launcher, username, "--print-found", "--timeout", str(min(capped_timeout, 30)))
    elif connector_id == "identity_mesh_beta":
        if not username:
            return None
        command = (
            *launcher,
            username,
            "--no-color",
            "--timeout",
            str(min(capped_timeout, 35)),
            "--retries",
            "0",
        )
    elif connector_id == "surface_grid_alpha":
        if not domain or not binary_path:
            return None
        command = (
            *launcher,
            "enum",
            "-passive",
            "-norecursive",
            "-nolocaldb",
            "-d",
            domain,
        )
    elif connector_id == "surface_grid_beta":
        if not domain or not binary_path:
            return None
        command = (
            *launcher,
            "-d",
            domain,
            "-b",
            "all",
            "-l",
            "100",
        )
    else:
        return None

    return ConnectorCommandPlan(
        connector_id=connector_id,
        title=runtime.spec.title,
        launch_mode=launch_mode,
        command=command,
        cwd=cwd,
    )


def _normalize_ip_candidates(candidates: set[str]) -> list[str]:
    valid: list[str] = []
    for value in candidates:
        parts = value.split(".")
        if len(parts) != 4:
            continue
        if not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            continue
        valid.append(value)
    return sorted(valid)


def _extract_signals(text: str, *, target_domain: str, target_username: str) -> dict[str, list[str]]:
    if not text:
        return {
            "emails": [],
            "urls": [],
            "ips": [],
            "domains": [],
            "subdomains": [],
            "username_mentions": [],
        }

    emails = sorted(set(match.group(0).lower() for match in EMAIL_RE.finditer(text)))
    urls = sorted(set(match.group(0) for match in URL_RE.finditer(text)))
    ips = _normalize_ip_candidates({match.group(0) for match in IPV4_RE.finditer(text)})
    domains = sorted(set(match.group(0).lower() for match in DOMAIN_RE.finditer(text)))

    subdomains: set[str] = set()
    if target_domain:
        suffix = f".{target_domain}"
        for row in domains:
            if row.endswith(suffix) and row != target_domain:
                subdomains.add(row)

    username_mentions: set[str] = set()
    if target_username:
        lowered_target = target_username.lower()
        for token in re.findall(r"[A-Za-z0-9._-]{3,}", text):
            if lowered_target in token.lower():
                username_mentions.add(token)

    return {
        "emails": emails[:200],
        "urls": urls[:200],
        "ips": ips[:200],
        "domains": domains[:200],
        "subdomains": sorted(subdomains)[:200],
        "username_mentions": sorted(username_mentions)[:200],
    }


def _run_connector_command(
    plan: ConnectorCommandPlan,
    *,
    timeout_seconds: int,
    target_domain: str,
    target_username: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(  # noqa: S603
            list(plan.command),
            cwd=plan.cwd,
            capture_output=True,
            text=True,
            timeout=max(5, min(240, int(timeout_seconds))),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if isinstance(exc.stdout, bytes):
            stdout_text = exc.stdout.decode("utf-8", errors="ignore")
        else:
            stdout_text = str(exc.stdout or "")
        if isinstance(exc.stderr, bytes):
            stderr_text = exc.stderr.decode("utf-8", errors="ignore")
        else:
            stderr_text = str(exc.stderr or "")
        text = f"{stdout_text}\n{stderr_text}"
        return {
            "connector_id": plan.connector_id,
            "title": plan.title,
            "status": "timeout",
            "launch_mode": plan.launch_mode,
            "command": list(plan.command),
            "returncode": None,
            "duration_ms": elapsed_ms,
            "signals": _extract_signals(text, target_domain=target_domain, target_username=target_username),
            "stdout_preview": text[:2000],
            "stderr_preview": "",
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "connector_id": plan.connector_id,
            "title": plan.title,
            "status": "failed",
            "launch_mode": plan.launch_mode,
            "command": list(plan.command),
            "returncode": None,
            "duration_ms": elapsed_ms,
            "signals": _extract_signals("", target_domain=target_domain, target_username=target_username),
            "stdout_preview": "",
            "stderr_preview": str(exc)[:500],
        }

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    combined = f"{stdout_text}\n{stderr_text}"
    status = "ok" if completed.returncode == 0 else "error"

    return {
        "connector_id": plan.connector_id,
        "title": plan.title,
        "status": status,
        "launch_mode": plan.launch_mode,
        "command": list(plan.command),
        "returncode": int(completed.returncode),
        "duration_ms": elapsed_ms,
        "signals": _extract_signals(combined, target_domain=target_domain, target_username=target_username),
        "stdout_preview": stdout_text[:2000],
        "stderr_preview": stderr_text[:1000],
    }


def _aggregate_signals(connector_runs: list[dict[str, Any]]) -> dict[str, list[str]]:
    buckets: dict[str, set[str]] = {
        "emails": set(),
        "urls": set(),
        "ips": set(),
        "domains": set(),
        "subdomains": set(),
        "username_mentions": set(),
    }
    for run in connector_runs:
        signals = run.get("signals", {})
        if not isinstance(signals, dict):
            continue
        for key in buckets:
            values = signals.get(key, [])
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str) and value:
                    buckets[key].add(value)
    return {key: sorted(values)[:300] for key, values in buckets.items()}


def collect_source_fusion_intel(
    *,
    mode: str,
    username: str | None = None,
    domain: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_connectors: int = DEFAULT_MAX_CONNECTORS,
) -> dict[str, Any]:
    """Collect normalized intelligence from available Silica connector runtimes."""

    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in {"profile", "surface", "fusion"}:
        normalized_mode = "fusion"
    normalized_username = _safe_username(username)
    normalized_domain = _safe_domain(domain)

    runtimes = detect_connector_runtimes()
    detected_payload = [
        {
            "id": runtime.spec.connector_id,
            "title": runtime.spec.title,
            "scopes": list(runtime.spec.scopes),
            "supports_execution": runtime.spec.supports_execution,
            "binary_available": bool(runtime.binary_path),
            "source_available": bool(runtime.source_entry),
            "executable": runtime.executable,
        }
        for runtime in runtimes
    ]

    plans: list[ConnectorCommandPlan] = []
    for runtime in runtimes:
        plan = _build_command_plan(
            runtime,
            mode=normalized_mode,
            username=normalized_username,
            domain=normalized_domain,
            timeout_seconds=timeout_seconds,
        )
        if plan is not None:
            plans.append(plan)

    if max_connectors > 0:
        plans = plans[: max(1, int(max_connectors))]
    else:
        plans = []

    runs: list[dict[str, Any]] = []
    if plans:
        pool_size = max(1, min(4, len(plans)))
        with ThreadPoolExecutor(max_workers=pool_size, thread_name_prefix="silica-fusion") as executor:
            futures = [
                executor.submit(
                    _run_connector_command,
                    plan,
                    timeout_seconds=timeout_seconds,
                    target_domain=normalized_domain,
                    target_username=normalized_username,
                )
                for plan in plans
            ]
            for future in as_completed(futures):
                runs.append(future.result())
        runs.sort(key=lambda row: str(row.get("connector_id", "")))

    aggregated_signals = _aggregate_signals(runs)
    successful_runs = sum(1 for row in runs if row.get("status") == "ok")
    coverage = {
        "detected": len(runtimes),
        "executable": sum(1 for runtime in runtimes if runtime.executable),
        "planned": len(plans),
        "executed": len(runs),
        "successful": successful_runs,
    }

    return {
        "mode": normalized_mode,
        "username": normalized_username,
        "domain": normalized_domain,
        "detected_connectors": detected_payload,
        "connector_runs": runs,
        "coverage": coverage,
        "signals": aggregated_signals,
    }

