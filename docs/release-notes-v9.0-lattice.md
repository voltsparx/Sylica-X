# Silica-X v9.0 "Lattice" Release Notes

Release date: 2026-03-05

## Release Asset and SHA256

- Asset: `silica-x-v9.0-lattice-major-snapshot-release-20260305-035351.zip`
- Size: `1,260,307 bytes`
- SHA256: `C464EB79EE098C017277EDD34F4C46DCFE7B129E68AB9152837E561D50E66A7E`

Verification:

```powershell
Get-FileHash -Algorithm SHA256 .\silica-x-v9.0-lattice-major-snapshot-release-20260305-035351.zip
```

```bash
sha256sum silica-x-v9.0-lattice-major-snapshot-release-20260305-035351.zip
```

## Overview

`v9.0` focuses on control-plane maturity, stronger extension orchestration, richer report outputs, and clearer operator UX while keeping the existing Silica-X architecture.

## Major Additions

- Prompt + flag workflows aligned for plugin/filter/module selection by name.
- Improved compatibility and conflict handling across plugin/filter combinations.
- Guided extension control modes (`auto`, `manual`, `hybrid`) with better execution alignment.
- Expanded quicktest flow with template-driven synthetic victims and report generation coverage.
- Crypto plugin lane integrated under `plugins/crypto/` with practical scan-time usage paths.

## Reporting and Output

- Rich multi-format artifacts:
  - CLI summary output
  - JSON run payloads
  - CSV main and companion exports
  - HTML visual reports with table-oriented intelligence views
  - run logs
- Improved intelligence rendering for entities, contacts, scoring, and correlation/fusion summaries.

## UX and Operator Experience

- Prompt startup inventory now reports loaded ecosystem counts (plugins, filters, platforms, catalog/framework).
- Explain/help surfaces improved for onboarding and operational clarity.
- Quiet behavior preserved for flag-driven execution where banner/loading noise should stay minimal.

## Engineering and Reliability

- Parser, prompt handler, explain/help, and capability-matrix wiring refinements.
- Requirements refreshed for runtime and development lanes.
- Test coverage extended for extension registry and crypto plugin paths.
- Verified quality snapshot:
  - `pytest`: 160 passing
  - `ruff`: pass
  - `mypy`: pass
  - compile smoke: pass

## Documentation

- Updated:
  - `README.md`
  - `docs/Usage.txt`
  - `docs/orchestration-architecture.md`
  - `docs/silica-capability-scan.md`
- Added:
  - `docs/release-checklist-v9.0-lattice.md`
  - `docs/release-commit-plan-v9.0-lattice.md`
- OCR/image infrastructure document remains roadmap-scoped for upcoming versions (`v9.5`/`v10.0`).

## Notes for Upgraders

- Reinstall dependencies to align crypto/runtime changes:
  - `pip install -r requirements.txt`
  - `pip install -r requirements-dev.txt` (optional)
- Use `--list-plugins` and `--list-filters` after upgrade to review available inventory and scopes.
