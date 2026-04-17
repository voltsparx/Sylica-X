# Architecture

Silica-X is a policy-driven OSINT runtime rather than a single collector.

## Execution shape

1. Interface layer normalizes flag-mode, prompt-mode, or wizard input.
2. Execution policy selects the engine profile and runtime controls.
3. Collectors and adapters gather profile, surface, OCR, and media signals.
4. Plugins enrich and filters reduce noise or prioritize risk.
5. Fusion and intelligence layers correlate entities and build guidance.
6. Reporter and other artifact writers render the case for operators and automation.

## Important runtime slices

- `core/interface/` handles CLI UX, explain surfaces, wizard flow, and prompt wiring.
- `core/collect/` handles profile, surface, OCR, and media acquisition.
- `core/engines/` handles async, threaded, parallel, and specialized engine lanes.
- `core/extensions/` provides plugin and filter discovery plus scope control.
- `core/analyze/`, `core/fusion/`, and `core/intelligence/` shape meaning from collected signals.
- `core/artifacts/` renders JSON, CSV, CLI, HTML Reporter, and logs.

## v10.0 focus

The v10.0 refresh emphasizes:

- clearer engine specialization
- first-class media and OCR lanes
- stronger artifact design through Reporter
- cleaner docs and website alignment
