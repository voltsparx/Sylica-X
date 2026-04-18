# Reporter

Reporter is the v10.0 reporting layer for Silica-X.

Use `silica-x doctor` when you want to confirm local OCR/Tor/report-backend readiness before assuming a reporting or extraction failure is caused by the scan itself.

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

Reporter is most visible in HTML, but the same naming and categorization now carry into:

- CLI summaries
- JSON payloads
- CSV exports
- SQLite case stores
- DOCX case documents
- PDF case documents

The closing summary remains the `Reporter Brief` across those surfaces when applicable.

## Attachables and OCR runtime context

Reporter now preserves execution context beyond just findings:

- selected plugins
- selected filters
- attached modules
- OCR/image tooling availability

That means a case can now show not only what was found, but also which attachables were enabled and whether OCR ran through `easyocr`, `pytesseract`, or no usable backend at all.

## OCR diagnostics

Reporter now preserves backend diagnostics so OCR failures are easier to understand:

- whether `Pillow` was available
- whether `easyocr` was importable
- whether `pytesseract` was importable
- whether a reachable `tesseract` binary was found
- which OCR backend the runtime preferred at execution time

If a run records `preferred_engine: none`, the main issue is typically missing OCR dependencies rather than a report-rendering problem. If `pytesseract` is available but `tesseract_binary_found` is false, install or expose the `tesseract` binary before expecting OCR text recovery.

## Theme

Reporter uses the Ember palette as its base: orange-led accents with distinct colors for severity, confidence, and signal classes so the report stays visually understandable.
