"""Fusion analytics engine for profile + domain intelligence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from statistics import mean
from typing import Any


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


@dataclass
class FusionEngine:
    """Fuses profile and domain results into a coherent intelligence object."""

    cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _cache_key(self, profile_data: dict[str, Any], domain_data: dict[str, Any]) -> str:
        profile_target = str(profile_data.get("target") or profile_data.get("username") or "").strip().lower()
        domain_target = str(
            domain_data.get("target")
            or domain_data.get("domain")
            or (domain_data.get("domain_result") or {}).get("target")
            or ""
        ).strip().lower()
        return f"{profile_target}|{domain_target}"

    async def fuse_profile_domain(
        self,
        profile_data: dict[str, Any],
        domain_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Build fused intelligence summary with confidence and anomaly signals."""

        cache_key = self._cache_key(profile_data, domain_data)
        if cache_key in self.cache:
            return self.cache[cache_key]

        results = list(profile_data.get("results", []) or [])
        found_rows = [item for item in results if str(item.get("status")) == "FOUND"]
        confidence_values = [_safe_int(item.get("confidence")) for item in found_rows]
        avg_confidence = int(mean(confidence_values)) if confidence_values else 0

        correlation = dict(profile_data.get("correlation", {}) or {})
        overlap_score = _safe_int(correlation.get("identity_overlap_score"), 0)

        domain_result = dict(
            domain_data.get("domain_result", domain_data)
            if isinstance(domain_data, dict)
            else {}
        )
        subdomain_count = len(domain_result.get("subdomains", []) or [])
        resolved_ip_count = len(domain_result.get("resolved_addresses", []) or [])
        https_status = domain_result.get("https", {}).get("status")

        risk_summary = dict(profile_data.get("issue_summary", {}) or {})
        risk_score = _safe_int(risk_summary.get("risk_score"), 0)
        if not risk_score:
            risk_score = _safe_int((domain_data.get("issue_summary") or {}).get("risk_score"), 0)

        confidence_score = max(
            0,
            min(
                100,
                int(
                    avg_confidence * 0.45
                    + overlap_score * 0.35
                    + min(subdomain_count, 50) * 0.3
                    + min(resolved_ip_count, 10) * 0.5
                    - risk_score * 0.25
                ),
            ),
        )

        anomaly_flags: list[str] = []
        if found_rows and overlap_score < 12:
            anomaly_flags.append("weak_identity_overlap")
        if subdomain_count >= 100:
            anomaly_flags.append("broad_attack_surface")
        if https_status not in {200, 301, 302}:
            anomaly_flags.append("unstable_https_surface")
        if risk_score >= 60:
            anomaly_flags.append("high_exposure_risk")

        fused = {
            "target": {
                "username": profile_data.get("target"),
                "domain": domain_result.get("target"),
            },
            "profile": {
                "found_profiles": len(found_rows),
                "average_confidence": avg_confidence,
                "identity_overlap_score": overlap_score,
            },
            "domain": {
                "subdomain_count": subdomain_count,
                "resolved_ip_count": resolved_ip_count,
                "https_status": https_status,
            },
            "risk": {
                "risk_score": risk_score,
            },
            "confidence_score": confidence_score,
            "anomalies": anomaly_flags,
        }
        self.cache[cache_key] = fused
        await asyncio.sleep(0)  # cooperative yield for large workflows
        return fused

    async def generate_graph(self, fused_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """Generate simple node-edge graph from fused intelligence payload."""

        target = fused_data.get("target", {}) or {}
        username = str(target.get("username") or "unknown-user")
        domain = str(target.get("domain") or "unknown-domain")

        nodes: list[dict[str, Any]] = [
            {"id": f"user:{username}", "label": username, "type": "username"},
            {"id": f"domain:{domain}", "label": domain, "type": "domain"},
            {
                "id": f"risk:{fused_data.get('risk', {}).get('risk_score', 0)}",
                "label": f"risk={fused_data.get('risk', {}).get('risk_score', 0)}",
                "type": "risk",
            },
        ]
        edges: list[dict[str, Any]] = [
            {"source": f"user:{username}", "target": f"domain:{domain}", "relation": "correlated_with"},
            {
                "source": f"domain:{domain}",
                "target": f"risk:{fused_data.get('risk', {}).get('risk_score', 0)}",
                "relation": "assessed_as",
            },
        ]

        for anomaly in fused_data.get("anomalies", []) or []:
            anomaly_id = f"anomaly:{anomaly}"
            nodes.append({"id": anomaly_id, "label": anomaly, "type": "anomaly"})
            edges.append({"source": f"domain:{domain}", "target": anomaly_id, "relation": "flagged"})

        await asyncio.sleep(0)
        return {"nodes": nodes, "edges": edges}
