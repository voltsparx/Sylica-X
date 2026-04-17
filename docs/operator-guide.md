# Operator Guide

Silica-X is centered around a small set of operator workflows that share the same reporting and extension system.

## Main commands

- `profile <username...>` scans usernames and public profile signals.
- `surface <domain>` inspects domain and surface intelligence.
- `fusion <username> <domain>` correlates identity and surface evidence.
- `orchestrate <profile|surface|fusion> <target>` runs the policy-led orchestration path directly.
- `ocr <image-paths...> [--url ...]` runs dedicated OCR image scanning.
- `plugins`, `filters`, `modules`, `history`, `wizard`, `anonymity`, `live`, `about`, `explain`, and `help` round out the operator surface.

## Package naming

- install with `pip install silica-x`
- run with `silica-x`
- import with `import silica_x`

## Output strategy

Silica-X can emit CLI, JSON, CSV, HTML, and log outputs in the same run. The HTML output is now the Reporter case view, designed for quick triage and visual review.

## Example commands

```bash
silica-x profile alice --html
silica-x surface example.com --plugin header_hardening_probe --html
silica-x fusion alice example.com --filter signal_lane_fusion --html
silica-x ocr ./images/poster.png --plugin ocr_extractor --filter ocr_signal_classifier --html
```

## Recommended mental model

1. Start with the workflow that matches the target.
2. Add plugins and filters only when they meaningfully improve triage.
3. Review Reporter output before diving into raw JSON.
4. Use history and logs to compare runs over time.
