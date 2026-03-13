# Plugin Intel Views

Release: v9.2.0 (Theme: Lattice)

Silica-native plugin inventory and usage guidance.

## Inventory

- Plugin inventory: 17
- Scope coverage:
- `profile`: 10
- `surface`: 9
- `fusion`: 15

## New Plugins Added

- `account_recovery_exposure_probe` (`profile`, `fusion`)
- Purpose: map exposed account-recovery contacts (emails/phones), cross-platform reuse, and recovery risk score.
- `link_outbound_risk_profiler` (`profile`, `fusion`)
- Purpose: classify risky outbound links (shorteners, non-HTTPS, sensitive-path links).
- `username_impersonation_probe` (`profile`, `fusion`)
- Purpose: detect lookalike username variants from mentions/links for impersonation triage.
- `rdap_lifecycle_inspector` (`surface`, `fusion`)
- Purpose: assess RDAP governance posture (status, nameservers, lifecycle freshness).
- `surface_transport_stability_probe` (`surface`, `fusion`)
- Purpose: score HTTP/HTTPS transport stability and redirect posture.

## Error Handling Guarantees

- All new plugins are defensive against missing/partial context payloads.
- Non-dict/invalid result rows are ignored safely.
- Each plugin returns normalized output (`severity`, `summary`, `highlights`, `data`) without raising for missing fields.
- Discovery and runtime import failures are surfaced through extension error channels, not hard crashes.
