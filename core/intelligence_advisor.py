"""Intelligence advisor for workflow recommendations and confidence estimation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from core.intel.prompt_engine import PromptEngine
from core.intel.capability_matrix import (
    DEFAULT_CAPABILITY_PACK_ROOT,
    DEFAULT_SOURCE_MAP_PATH,
    build_capability_pack,
    load_source_map,
    recommend_capability_priorities,
    recommend_focus_modules,
)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


@dataclass
class IntelligenceAdvisor:
    """Provides recommendations from local run history and research map insights."""

    history: Sequence[dict[str, Any] | str] = field(default_factory=list)
    source_map_path: str = str(DEFAULT_SOURCE_MAP_PATH)
    capability_index_path: str = str(DEFAULT_CAPABILITY_PACK_ROOT / "index.json")
    auto_build_capability_pack: bool = False

    def _history_commands(self) -> list[str]:
        commands: list[str] = []
        for entry in self.history:
            if isinstance(entry, str):
                token = entry.strip().lower().split()
                if token:
                    commands.append(token[0])
                continue
            if isinstance(entry, dict):
                command = str(entry.get("command") or entry.get("mode") or "").strip().lower()
                if command:
                    commands.append(command)
        return commands

    def recommend_next(self) -> list[str]:
        """Recommend next actions and learning targets."""

        commands = self._history_commands()
        prompt_engine = PromptEngine(history=commands)
        suggestions = prompt_engine.suggest_next(limit=4)

        dominant_scope = "profile"
        if commands:
            normalized: list[str] = []
            for command in commands:
                if command in {"scan", "persona", "social"}:
                    normalized.append("profile")
                elif command in {"domain", "asset"}:
                    normalized.append("surface")
                elif command in {"full", "combo"}:
                    normalized.append("fusion")
                else:
                    normalized.append(command)
            dominant_scope = Counter(normalized).most_common(1)[0][0]
            if dominant_scope not in {"profile", "surface", "fusion"}:
                dominant_scope = "profile"

        source_map = load_source_map(self.source_map_path)
        research = recommend_focus_modules(dominant_scope, source_map)
        capability_hints = recommend_capability_priorities(
            dominant_scope,
            capability_index_path=self.capability_index_path,
        )
        if not capability_hints and self.auto_build_capability_pack:
            with suppress(Exception):
                build_capability_pack()
            capability_hints = recommend_capability_priorities(
                dominant_scope,
                capability_index_path=self.capability_index_path,
            )

        merged = [*suggestions, *research, *capability_hints]
        unique: list[str] = []
        seen: set[str] = set()
        for item in merged:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique

    def estimate_confidence(self, fused_results: dict[str, Any]) -> float:
        """Estimate normalized confidence score from fused intelligence artifacts."""

        if not isinstance(fused_results, dict):
            return 0.0

        if "confidence_score" in fused_results:
            return max(0.0, min(1.0, _safe_float(fused_results.get("confidence_score")) / 100.0))

        profile = fused_results.get("profile", {}) if isinstance(fused_results.get("profile"), dict) else {}
        risk = fused_results.get("risk", {}) if isinstance(fused_results.get("risk"), dict) else {}
        found_profiles = _safe_float(profile.get("found_profiles"), 0.0)
        avg_confidence = _safe_float(profile.get("average_confidence"), 0.0)
        risk_score = _safe_float(risk.get("risk_score"), 0.0)
        overlap = _safe_float(profile.get("identity_overlap_score"), 0.0)

        raw = avg_confidence * 0.55 + overlap * 0.35 + min(found_profiles, 10.0) * 2.5 - risk_score * 0.3
        return max(0.0, min(1.0, raw / 100.0))

