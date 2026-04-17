# Extensions

Silica-X uses plugins and filters as scope-aware intelligence layers.

## Plugins

Plugins enrich findings, run secondary intelligence passes, or attach specialized data to the current case. Examples include public-media reconnaissance, post-text analysis, stego-style probes, and OCR extraction.

## Filters

Filters suppress noise, rank findings, classify exposure, or reshape signals into a more triage-friendly form.

## Scope control

Extensions are not applied blindly. Silica-X checks compatibility with the active scope, such as:

- `profile`
- `surface`
- `fusion`
- `ocr`

## Operator guidance

- Keep the extension set minimal for baseline scans.
- Add media/OCR plugins when the target case is content-heavy.
- Prefer Reporter output to validate whether a plugin or filter is adding useful signal.
