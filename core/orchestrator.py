"""Central orchestration brain for policy-driven capability execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.capabilities import build_capability_registry
from core.domain import BaseEntity
from core.engine_manager import get_engine
from core.execution_policy import ExecutionPolicy, load_execution_policy
from core.filters import FilterPipeline, build_filter_registry
from core.fusion import FusionEngine
from core.intelligence import StrategicAdvisor
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
        self._advisor = StrategicAdvisor()
        self._report_manager = ReportManager()

    async def run(self) -> dict[str, Any]:
        """Execute full orchestration lifecycle and return presentation payloads."""

        self.lifecycle.mark("policy", "loaded", profile=self.policy.name, engine=self.policy.engine_type)

        entities = await self.execute_capabilities()
        self.lifecycle.mark("capabilities", "completed", count=len(entities))

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
            task_factories.append(
                lambda capability=capability, capability_target=capability_target: capability.execute(
                    capability_target,
                    context,
                )
            )
        runtime_context = {"max_workers": self.policy.max_workers, "timeout": self.policy.timeout}

        raw_results = await self._engine.run(task_factories, runtime_context)
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
            correlation_entities = await correlation_capability.execute(correlation_target, correlation_context)
            entities.extend(entity for entity in correlation_entities if isinstance(entity, BaseEntity))

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

        return self._fusion_engine.fuse(entities)

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
