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

"""Central orchestration brain for policy-driven capability execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.capabilities import build_capability_registry
from core.domain import BaseEntity
from core.engines.engine_result import EngineResult
from core.engine_manager import get_engine
from core.execution_policy import ExecutionPolicy, load_execution_policy
from core.filters import FilterPipeline, build_filter_registry
from core.fusion import FusionEngine
from core.intelligence import IntelligenceEngine, StrategicAdvisor
from core.lifecycle import ScanLifecycle
from core.reporting import ReportManager
from core.security import build_proxy_settings
from core.utils.logging import get_logger


LOGGER = get_logger("orchestrator")


class Orchestrator:
    """Central coordinator for execution policy, capabilities, and fusion."""

    def __init__(self, target: str, mode: str, config: Mapping[str, Any] | None = None) -> None:
        self.target = str(target or "").strip()
        self.mode = str(mode or "profile").strip().lower()
        self.config = dict(config or {})

        profile_name = str(self.config.get("profile", self.mode)).strip().lower()
        self.policy: ExecutionPolicy = load_execution_policy(profile_name)
        self.lifecycle = ScanLifecycle(target=self.target, mode=self.mode)

        self._engine = get_engine(self.policy)
        self._capabilities = build_capability_registry()
        self._filter_registry = build_filter_registry()
        self._fusion_engine = FusionEngine()
        self._intelligence_engine = IntelligenceEngine()
        self._advisor = StrategicAdvisor()
        self._report_manager = ReportManager()
        self._last_engine_results: list[dict[str, Any]] = []

    async def run(self) -> dict[str, Any]:
        """Execute full orchestration lifecycle and return presentation payloads."""

        self.lifecycle.mark("policy", "loaded", profile=self.policy.name, engine=self.policy.engine_type)

        entities = await self.execute_capabilities()
        status_counts = self._engine_status_counts()
        self.lifecycle.mark(
            "capabilities",
            "completed",
            count=len(entities),
            succeeded=status_counts["success"],
            failed=status_counts["failed"],
            timed_out=status_counts["timeout"],
        )

        engine_health = self._safe_engine_health()
        self.lifecycle.mark("engine", "health", **engine_health)

        filtered_entities = self.apply_filters(entities)
        self.lifecycle.mark("filters", "completed", count=len(filtered_entities))

        fused = self.fuse(filtered_entities)
        self.lifecycle.mark(
            "fusion",
            "completed",
            confidence=fused.get("confidence_score", 0.0),
            anomalies=len(fused.get("anomalies", [])),
        )

        report_payload = self.generate_report(fused)
        self.lifecycle.mark("report", "completed")
        self.lifecycle.complete()

        report_payload["lifecycle"] = self.lifecycle.as_dict()
        report_payload["engine_health"] = engine_health
        report_payload["engine_results"] = list(self._last_engine_results)
        return report_payload

    async def execute_capabilities(self) -> list[BaseEntity]:
        """Execute policy-enabled capabilities through selected engine."""

        enabled = list(self.policy.enabled_capabilities)
        context = self._build_context(existing_entities=[])

        async_capabilities = [
            self._capabilities[capability_id]
            for capability_id in enabled
            if capability_id in self._capabilities and capability_id != "correlation"
        ]

        task_factories = []
        for capability in async_capabilities:
            capability_target = self._target_for_capability(capability.capability_id)
            factory = (
                lambda capability=capability, capability_target=capability_target: capability.execute(
                    capability_target,
                    context,
                )
            )
            setattr(factory, "_silica_x_task_name", capability.capability_id)
            task_factories.append(factory)
        runtime_context = {"max_workers": self.policy.max_workers, "timeout": self.policy.timeout}

        raw_results: list[Any] = []
        detailed_results: list[EngineResult] = []
        if hasattr(self._engine, "run_detailed"):
            detailed_results = await self._engine.run_detailed(task_factories, runtime_context)
            self._last_engine_results = [
                {
                    "name": item.name,
                    "status": item.status,
                    "error": item.error,
                    "execution_time": round(float(item.execution_time), 4),
                }
                for item in detailed_results
            ]
            raw_results = [item.data.get("payload") for item in detailed_results if item.status == "success"]
            for item in detailed_results:
                if item.status == "success":
                    continue
                LOGGER.warning("Capability execution [%s] %s: %s", item.status, item.name, item.error)
        else:  # pragma: no cover - compatibility fallback
            raw_results = await self._engine.run(task_factories, runtime_context)
            self._last_engine_results = []

        entities: list[BaseEntity] = []

        for item in raw_results:
            if isinstance(item, Exception):
                LOGGER.warning("Capability execution error: %s", item)
                continue
            if isinstance(item, list):
                entities.extend(entity for entity in item if isinstance(entity, BaseEntity))

        if "correlation" in enabled and "correlation" in self._capabilities:
            correlation_capability = self._capabilities["correlation"]
            correlation_context = self._build_context(existing_entities=entities)
            correlation_target = self._target_for_capability(correlation_capability.capability_id)
            try:
                correlation_entities = await correlation_capability.execute(correlation_target, correlation_context)
                entities.extend(entity for entity in correlation_entities if isinstance(entity, BaseEntity))
            except Exception as exc:  # pragma: no cover - correlation isolation
                LOGGER.warning("Correlation capability execution error: %s", exc)

        return entities

    def apply_filters(self, entities: list[BaseEntity]) -> list[BaseEntity]:
        """Apply policy-driven filter pipeline to entities."""

        selected_filters = [
            self._filter_registry[filter_id]
            for filter_id in self.policy.enabled_filters
            if filter_id in self._filter_registry
        ]
        pipeline = FilterPipeline(selected_filters)

        min_confidence = float(self.config.get("min_confidence", 0.25))
        depth = int(self.config.get("depth", self.policy.enrichment_depth))
        filtered = pipeline.run(
            entities,
            {
                "target": self.target,
                "targets": self._filter_targets(),
                "mode": self.mode,
                "min_confidence": min_confidence,
                "depth": depth,
                "keywords": self.config.get("keywords", []),
                "allowed_sources": self.config.get("allowed_sources", []),
                "allowed_types": self.config.get("allowed_types", []),
                "blocked_terms": self.config.get("blocked_terms", []),
                "entity_limit": self.config.get("entity_limit"),
            },
        )
        return filtered

    def fuse(self, entities: list[BaseEntity]) -> dict[str, Any]:
        """Fuse refined entities into a correlation payload."""

        fused = self._fusion_engine.fuse(entities)
        intelligence_bundle = self._intelligence_engine.analyze(
            entities,
            mode=self.policy.name,
            target=self.target,
            anomalies=fused.get("anomalies", []) if isinstance(fused.get("anomalies"), list) else [],
            relation_map=fused.get("relationship_map", {}) if isinstance(fused.get("relationship_map"), dict) else {},
        )
        fused["intelligence_bundle"] = intelligence_bundle
        fused["risk_summary"] = intelligence_bundle.get("risk_summary", {})
        fused["confidence_distribution"] = intelligence_bundle.get("confidence_distribution", {})
        return fused

    def generate_report(self, fused_data: dict[str, Any]) -> dict[str, Any]:
        """Generate presentation-layer payloads from fused entities."""

        advisory = {
            "next_steps": self._advisor.recommend_next_steps(fused_data),
            "overall_confidence": self._advisor.estimate_overall_confidence(fused_data),
            "priorities": self._advisor.prioritize_findings(fused_data),
        }
        payload = self._report_manager.generate(
            target=self.target,
            mode=self.mode,
            fused_data=fused_data,
            advisory=advisory,
            lifecycle=self.lifecycle.as_dict(),
        )
        return payload

    def _build_context(self, *, existing_entities: list[BaseEntity]) -> dict[str, Any]:
        source_profile = str(self.config.get("source_profile", self.policy.name)).strip().lower()
        proxy_settings = build_proxy_settings(self.config)
        try:
            proxy_url = proxy_settings.resolve_proxy_url()
        except RuntimeError as exc:
            LOGGER.warning("Proxy/Tor settings failed to resolve: %s", exc)
            proxy_url = None

        max_platforms_value = self.config.get("max_platforms")
        max_platforms = int(max_platforms_value) if isinstance(max_platforms_value, int) else None

        return {
            "mode": self.mode,
            "timeout": int(self.config.get("timeout", self.policy.timeout)),
            "max_workers": int(self.config.get("max_workers", self.policy.max_workers)),
            "source_profile": source_profile,
            "max_platforms": max_platforms,
            "proxy_url": proxy_url,
            "include_ct": bool(self.config.get("include_ct", True)),
            "include_rdap": bool(self.config.get("include_rdap", True)),
            "max_subdomains": int(self.config.get("max_subdomains", 250)),
            "recon_mode": str(self.config.get("recon_mode", "hybrid")).strip().lower() or "hybrid",
            "depth": int(self.config.get("depth", self.policy.enrichment_depth)),
            "profile_target": str(self.config.get("profile_target", self.target)).strip(),
            "surface_target": str(self.config.get("surface_target", self.target)).strip(),
            "existing_entities": list(existing_entities),
        }

    def _target_for_capability(self, capability_id: str) -> str:
        if self.mode != "fusion":
            return self.target
        profile_target = str(self.config.get("profile_target", self.target)).strip()
        surface_target = str(self.config.get("surface_target", self.target)).strip()
        if capability_id == "domain_enumeration":
            return surface_target or self.target
        return profile_target or self.target

    def _filter_targets(self) -> list[str]:
        if self.mode != "fusion":
            return [self.target]
        profile_target = str(self.config.get("profile_target", self.target)).strip()
        surface_target = str(self.config.get("surface_target", self.target)).strip()
        values = [item for item in [profile_target, surface_target] if item]
        seen: set[str] = set()
        deduped: list[str] = []
        for item in values:
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(item)
        return deduped

    def _safe_engine_health(self) -> dict[str, Any]:
        if not hasattr(self._engine, "health_check"):
            return {}
        try:
            snapshot = self._engine.health_check()
            return snapshot if isinstance(snapshot, dict) else {}
        except Exception as exc:  # pragma: no cover - defensive boundary
            LOGGER.warning("Engine health snapshot failed: %s", exc)
            return {}

    def _engine_status_counts(self) -> dict[str, int]:
        counters = {"success": 0, "failed": 0, "timeout": 0}
        for row in self._last_engine_results:
            status = str(row.get("status", "")).strip().lower()
            if status in counters:
                counters[status] += 1
        return counters
