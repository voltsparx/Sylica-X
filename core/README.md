# Core Module Layout

Core modules are grouped by responsibility so runtime wiring and ownership are easier to follow.

- `core/interface/`
  - CLI and operator-facing modules.
  - Files: `about.py`, `banner.py`, `cli_config.py`, `cli_parsers.py`, `cli_ui.py`, `explain.py`, `help_menu.py`, `live_server.py`
- `core/collect/`
  - Collection, scanning, and network access modules.
  - Files: `anonymity.py`, `domain_intel.py`, `extractor.py`, `http_resilience.py`, `network.py`, `platform_schema.py`, `scanner.py`
- `core/analyze/`
  - Correlation, exposure, confidence, and summarization modules.
  - Files: `confidence.py`, `correlator.py`, `exposure.py`, `narrative.py`, `profile_summary.py`
- `core/extensions/`
  - Plugin/filter execution and schema modules.
  - Files: `plugin_manager.py`, `signal_forge.py`, `signal_sieve.py`, `forge_schema.py`, `sieve_schema.py`, `selector_keys.py`
- `core/artifacts/`
  - Output, storage, and report-generation modules.
  - Files: `csv_export.py`, `html_report.py`, `output.py`, `reporting.py`, `storage.py`
- `core/foundation/`
  - Shared primitives and state/security support.
  - Files: `colors.py`, `credential_manager.py`, `metadata.py`, `security_manager.py`, `session_state.py`, `utils.py`
- `core/engines/`
  - Async, thread, parallel, fusion, and scheduler execution engines.
  - Files: `async_engine.py`, `thread_engine.py`, `parallel_engine.py`, `fusion_engine.py`, `scheduler.py`
- `core/intel/`
  - Prompt recommendations, advisor scoring, and capability/source mapping.
  - Files: `prompt_engine.py`, `advisor.py`, `capability_matrix.py`
- `core/` (root)
  - Runtime orchestration and prompt glue.
  - Files: `runner.py`, `prompt_handlers.py`
