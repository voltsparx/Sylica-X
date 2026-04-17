# Core Module Layout

Release: v10.0 (Theme: Ember)

Core modules are grouped by responsibility to keep runtime wiring and ownership clear.

## Runtime + Interface

- `core/interface/` -> CLI and operator-facing modules.
- `core/runner.py` -> existing CLI runtime orchestration.
- `core/prompt_handlers.py` -> prompt command defaults and command rewriting.

## Collection + Analysis

- `core/collect/` -> scanners, network calls, and raw signal collection.
- `core/analyze/` -> correlation, confidence, exposure, and narrative synthesis.

## Extensions + Artifacts

- `core/extensions/` -> plugin/filter discovery and execution wiring.
- `core/artifacts/` -> storage, csv/html/json output, and report generation.
- `core/artifacts/output.py` -> enriched CLI + JSON artifact summaries, Reporter briefs, extension severity rollups, and run logs.
- `core/artifacts/html_report.py` -> Reporter HTML case views with graphs, categorized sections, and payload drill-down.
- `core/artifacts/csv_export.py` -> primary result CSV + companion CSV exports (`issues`, `plugins`, `filters`, `intel`).

## Engines + Foundation

- `core/engines/` -> async/thread/parallel execution helpers.
- `core/engines/engine_result.py` -> standardized engine result schema.
- `core/engines/engine_base.py` -> timeout guard + exception isolation base contract.
- `core/engines/health_monitor.py` -> runtime engine health metrics.
- `core/foundation/` -> low-level shared state, metadata, colors, and credentials.
- `core/intel/` -> prompt recommendations and capability mapping.

## Blueprint-Oriented Orchestration Layer

- `core/execution_policy.py` -> central scan profile definitions.
- `core/engine_manager.py` -> policy-driven engine selection.
- `core/lifecycle.py` -> scan lifecycle event tracking.
- `core/orchestrator.py` -> policy -> capabilities -> filters -> fusion -> report flow.
- `core/domain/` -> immutable entity contracts.
- `core/capabilities/` -> tool-agnostic capability interfaces and implementations.
- `core/adapters/` -> scanner/domain adapters that normalize into entities.
- `core/filters/` -> stateless entity filter pipeline.
- `core/fusion/` -> relationship and confidence fusion engine.
- `core/intelligence/` -> strategic next-step advisor.
- `core/reporting/` -> presentation-only payload renderers.
- `core/security/` -> proxy and credential vault wrappers.
- `core/utils/` -> centralized orchestration logger.
