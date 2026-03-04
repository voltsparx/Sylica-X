"""Prompt intelligence helpers for command recommendations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class PromptEngine:
    """Suggest prompt actions based on command history."""

    history: list[str] = field(default_factory=list)

    def _normalized_commands(self) -> list[str]:
        normalized: list[str] = []
        for item in self.history:
            raw = str(item or "").strip().lower()
            if not raw:
                continue
            normalized.append(raw.split()[0])
        return normalized

    def suggest_next(self, *, limit: int = 3) -> list[str]:
        commands = self._normalized_commands()
        if not commands:
            return ["profile <username>", "surface <domain>", "fusion <username> <domain>"]

        last = commands[-1]
        counter = Counter(commands)
        suggestions: list[str] = []

        if last in {"profile", "scan", "persona", "social"}:
            suggestions.extend(["plugins --scope profile", "filters --scope profile", "fusion <username> <domain>"])
        elif last in {"surface", "domain", "asset"}:
            suggestions.extend(["plugins --scope surface", "filters --scope surface", "fusion <username> <domain>"])
        elif last in {"fusion", "full", "combo"}:
            suggestions.extend(["history --limit 10", "anonymity --check", "wizard"])
        else:
            suggestions.extend(["profile <username>", "surface <domain>", "fusion <username> <domain>"])

        if counter.get("anonymity", 0) == 0:
            suggestions.append("anonymity --check")
        if counter.get("history", 0) == 0:
            suggestions.append("history --limit 10")

        unique: list[str] = []
        seen: set[str] = set()
        for suggestion in suggestions:
            if suggestion in seen:
                continue
            seen.add(suggestion)
            unique.append(suggestion)
        return unique[: max(1, limit)]

    def workflow_templates(self) -> list[str]:
        return ["quick", "balanced", "deep", "fusion-full"]
