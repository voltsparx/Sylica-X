# Silica-X Hybrid Architecture

Silica-X now exposes a native hybrid console/runtime model that combines three local source-study patterns into the existing framework:

- `metasploit-ui`: console prompt rhythm, startup banner cadence, rotating spinner feedback, and command-recovery patterns.
- `amass-registry`: registry, dispatcher, and session-manager topology for runtime inventory thinking.
- `bbot-event-flow`: event-driven scan lifecycle and parallel workload lane ideas.

This is implemented as part of Silica-X itself, not as a bundled copy of those frameworks.

## Native Lanes

1. `console-dispatch`
   Prompt UX, banner, help flow, command hints, and boot inventory display.
2. `registry-session`
   Module catalog, plugin/filter discovery, presets, selector management, and runtime state.
3. `event-flow`
   Scanner lifecycle, collection orchestration, and queue-like execution handoff.
4. `fusion-graph`
   Correlation, confidence scoring, graph fusion, and analyst reporting.

## Native Engine Set

- `async`
- `thread`
- `process`
- `hybrid`
- `fusion`

## Silica-X Ownership

The hybrid architecture is surfaced through:

- `core/intel/hybrid_architecture.py`
- `core/interface/loading.py`
- `core/runner.py`
- `core/interface/banner.py`
- `intel/runtime-inventory.json`

At runtime, the framework writes the hybrid architecture snapshot into the inventory report so the console and intel layer both treat it as a first-class part of Silica-X.
