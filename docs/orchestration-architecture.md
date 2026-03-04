# Orchestration Architecture (Layered)

Silica-X now includes an additive layered architecture aligned with `structure.txt`.

## Core Flow

1. `core.execution_policy.load_execution_policy()` resolves profile policy.
2. `core.engine_manager.get_engine()` selects backend (`async`, `thread`, `process`, `hybrid`).
3. `core.orchestrator.Orchestrator.execute_capabilities()` runs enabled capabilities.
4. `core.filters.FilterPipeline` applies policy-selected refinement filters.
5. `core.fusion.FusionEngine` fuses entities and builds relationship graph.
6. `core.intelligence.StrategicAdvisor` generates recommendations and priorities.
7. `core.reporting` renders CLI summary, JSON payload, and HTML text.

## Data Contract

All capability outputs are normalized into immutable entities from `core/domain/entities.py`.
No raw scanner dictionaries move beyond adapters.

## Layer Guarantees

- Orchestrator has no tool-specific implementation.
- Capabilities call adapters, not collectors directly.
- Fusion depends only on entities.
- Reporting is presentation-only.
- Security utilities are isolated under `core/security`.
