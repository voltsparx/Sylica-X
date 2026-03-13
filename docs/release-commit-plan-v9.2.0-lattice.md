# Silica-X v9.2.0 "Lattice" Commit Plan

Use this grouping to keep history readable and simplify rollback/cherry-pick paths.

## Commit 1: Core runtime and wiring

Suggested message:
`feat(core): harden runner, parser, and extension wiring for v9.2.0 lattice`

Suggested files:

- `core/runner.py`
- `core/interface/cli_parsers.py`
- `core/interface/explain.py`
- `core/interface/help_menu.py`
- `core/extensions/signal_forge.py`
- `core/intel/capability_matrix.py`
- `core/artifacts/output.py`
- `core/artifacts/html_report.py`
- `core/output.py`
- `core/intel_pack.py`

## Commit 2: Crypto plugin lane

Suggested message:
`feat(plugins): add crypto plugin lane with integrated execution support`

Suggested files:

- `plugins/crypto/` (all new plugin files)
- `requirements.txt`
- `requirements-dev.txt`

## Commit 3: Tests and validation expansion

Suggested message:
`test: expand coverage for extension registry, runner cli, and crypto plugins`

Suggested files:

- `tests/test_extensions_registry.py`
- `tests/test_runner_cli.py`
- `tests/test_crypto_plugins.py`

## Commit 4: Documentation and release assets

Suggested message:
`docs: publish v9.2.0 lattice usage, release notes, and checklist`

Suggested files:

- `README.md`
- `docs/Usage.txt`
- `docs/orchestration-architecture.md` (if changed)
- `docs/silica-capability-scan.md` (if changed)
- `docs/ocr-image-scan-infrastructure.md`
- `docs/release-checklist-v9.2.0-lattice.md`
- `docs/release-notes-v9.2.0-lattice.md`
- `docs/release-commit-plan-v9.2.0-lattice.md`

## Tag and release

After commits and CI green:

1. `git tag -a v9.2.0 -m "Silica-X v9.2.0 Lattice"`
2. `git push origin <branch> --follow-tags`
3. Create GitHub release using `docs/release-notes-v9.2.0-lattice.md`
