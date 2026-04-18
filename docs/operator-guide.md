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
- diagnose local readiness with `silica-x doctor`

## Output strategy

Silica-X can emit CLI, JSON, CSV, HTML, SQL, DOCX, PDF, and log outputs in the same run. The HTML output is now the Reporter case view, designed for quick triage and visual review, while DOCX/PDF/SQL provide richer handoff and persistence options.

Use `out-type` when you want to persist a run in a different artifact mix:

```bash
silica-x out-type cli,json,html,sql,docx,pdf
```

## Attachables and config

Prompt mode now treats plugins, filters, and modules as attachables you can enable per session:

```text
enable plugin threat_conductor
enable filter contact_canonicalizer
enable module source-pack-01-module-1
config
```

Direct CLI runs keep the explicit flags:

- `--plugin <name>,<name>`
- `--filter <name>,<name>`
- `--module <name>,<name>`

Silica-X validates attachables before execution. Unknown selectors, incompatible module scopes, and extension-control conflicts are blocked before the run starts, and the CLI points back to `plugins --scope ...`, `filters --scope ...`, or `modules --scope ...` when you need a compatible selection.

## Execution review

Before execution, both prompt mode and direct flag mode now show the resolved configuration first:

- active scope and target
- selected plugins, filters, and modules
- output types and output root
- relevant runtime knobs such as preset, timeout, and worker count

In direct mode, press Enter to continue or `Ctrl+C` to cancel before execution. In prompt mode, press Enter to continue or `c` to cancel that configured command while keeping the console open.

## Example commands

```bash
silica-x profile alice --html
silica-x surface example.com --plugin header_hardening_probe --html
silica-x fusion alice example.com --filter signal_lane_fusion --module source-pack-01-module-1 --html
silica-x ocr ./images/poster.png --plugin ocr_extractor --filter ocr_signal_classifier --out-type json,html,docx,pdf
```

## Recommended mental model

1. Start with the workflow that matches the target.
2. Add plugins, filters, and modules only when they meaningfully improve triage.
3. Review the printed configuration before launch, then confirm the run.
4. Review Reporter output before diving into raw JSON or SQL.
5. Use history and logs to compare runs over time.
