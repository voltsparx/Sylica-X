# Reporter

Reporter is the v10.0 reporting layer for Silica-X.

## Goals

- make cases readable without losing raw detail
- group related signals together
- show quick graphs and severity summaries
- keep raw plugin/filter payloads available for drill-down
- end every case with a short `Reporter Brief`

## Reporter sections

- case triage snapshot
- extension signal overview
- operational graphs
- found identities and reliability issues
- correlation and surface intelligence
- vulnerability findings
- plugin and filter intelligence
- OCR/media sections when present
- intelligence scoring and guidance
- Reporter Brief

## Artifact formats

Reporter is most visible in HTML, but the same naming and categorization now carry into CLI summaries as `Reporter Brief`.

## Theme

Reporter uses the Ember palette as its base: orange-led accents with distinct colors for severity, confidence, and signal classes so the report stays visually understandable.
