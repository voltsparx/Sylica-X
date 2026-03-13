# Silica-X v9.2.0 "Lattice" Release Checklist

Date: 2026-03-14

## 1) Release Gate

- [x] Versioned branding aligned to `v9.2.0` and theme `Lattice` in primary docs.
- [x] Core usage docs updated (`README.md`, `docs/Usage.txt`).
- [x] OCR roadmap note clearly marked as future-scope (`v9.5`/`v10.0` planning lane).
- [x] New plugin/filter/quicktest flows documented.
- [x] Legal-use disclaimer present in README.

## 2) Quality Gate (Last Verified Snapshot)

- [x] `python -m pytest -q` -> PASS (`160 passed`)
- [x] `python -m ruff check .` -> PASS
- [x] `python -m mypy` -> PASS
- [x] `python -m compileall -q core filters plugins tests silica-x.py` -> PASS

## 3) Wiring/Compatibility Gate

- [x] Prompt + flag command surfaces aligned.
- [x] Plugin/filter selector wiring with compatibility checks enabled.
- [x] Quiet/flag execution behavior and prompt startup inventory behavior documented.
- [x] Output lanes available: CLI, JSON, CSV, HTML, logs.

## 4) Packaging/Repo Gate

- [x] Runtime dependencies updated in `requirements.txt`.
- [x] Dev dependencies updated in `requirements-dev.txt`.
- [x] New crypto plugin tree included under `plugins/crypto/`.
- [x] Tests added for crypto/plugin wiring paths.
- [x] Release ZIP prepared in `release-assets/`.
- [x] SHA256 checksum generated and recorded in release notes.

## 5) Pre-Publish Manual Sanity (Recommended Before Tag Push)

- [ ] Run one final local smoke:
  - `python -m pytest -q`
  - `python -m ruff check .`
  - `python -m mypy`
- [ ] Execute one prompt quicktest and one flag quicktest:
  - `python silica-x.py quicktest --seed 7 --html --csv`
  - `python silica-x.py` then run `quicktest --seed 7`
- [ ] Open generated HTML report once and verify table rendering.
- [ ] Verify `.github/workflows` status is green on the target branch.

## 6) Release Decision

Current state: `READY TO PUBLISH` after final manual sanity in section 5.

## 7) Suggested Publish Sequence

1. Commit grouped changes (see `docs/release-commit-plan-v9.2.0-lattice.md`).
2. Push branch and confirm CI is green.
3. Create annotated tag `v9.2.0`.
4. Publish release with notes from `docs/release-notes-v9.2.0-lattice.md`.
