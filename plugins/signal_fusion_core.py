"""Plugin: high-fidelity multi-source signal fusion for Silica workflows."""

from __future__ import annotations

from core.collect.source_fusion import collect_source_fusion_intel
from modules.catalog import ensure_module_catalog, summarize_module_catalog


PLUGIN_SPEC = {
    "id": "signal_fusion_core",
    "title": "Signal Fusion Core",
    "description": "Runs internal connector lanes and merges normalized signals into Silica workflows.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["fusion_core", "signal_core", "connector_core"],
    "version": "1.0",
}


def _resolve_target_context(context: dict) -> tuple[str, str]:
    username = ""
    domain = ""
    mode = str(context.get("mode", "fusion")).strip().lower()

    if mode in {"profile", "fusion"}:
        username = str(context.get("target", "")).strip()
    if mode in {"surface", "fusion"}:
        domain_result = context.get("domain_result", {})
        if isinstance(domain_result, dict):
            domain = str(domain_result.get("target", "")).strip()
        if not domain:
            domain = str(context.get("domain", "")).strip()
        if not domain and mode == "surface":
            domain = str(context.get("target", "")).strip()
    return username, domain


def run(context: dict) -> dict:
    mode = str(context.get("mode", "fusion")).strip().lower()
    if mode not in {"profile", "surface", "fusion"}:
        mode = "fusion"

    username, domain = _resolve_target_context(context)
    fusion_intel = collect_source_fusion_intel(
        mode=mode,
        username=username,
        domain=domain,
        timeout_seconds=35,
        max_connectors=4,
    )
    catalog_summary = summarize_module_catalog(ensure_module_catalog(refresh=False))

    coverage = fusion_intel.get("coverage", {})
    signals = fusion_intel.get("signals", {})
    signal_total = sum(len(values) for values in signals.values() if isinstance(values, list))
    successful = int(coverage.get("successful", 0) or 0)
    executed = int(coverage.get("executed", 0) or 0)

    if successful >= 2 and signal_total >= 25:
        severity = "HIGH"
    elif successful >= 1 and signal_total >= 8:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    summary = (
        f"Signal Fusion Core executed {executed} connector run(s), "
        f"with {successful} successful run(s) and {signal_total} normalized signal(s)."
    )
    highlights = [
        f"mode={mode}",
        f"executed={executed}",
        f"successful={successful}",
        f"signals={signal_total}",
        f"catalog_modules={catalog_summary.get('module_count', 0)}",
    ]
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "fusion_intel": fusion_intel,
            "catalog_summary": catalog_summary,
        },
    }

