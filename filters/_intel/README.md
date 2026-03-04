# Filter Intel Views

Release: v9.0 (Theme: Lattice)

Silica-native filter inventory and triage guidance.

## Inventory

- Filter inventory: 17
- Scope coverage:
- `profile`: 14
- `surface`: 9
- `fusion`: 17

## New Filters Added

- `triage_priority_filter` (`profile`, `surface`, `fusion`)
- Purpose: converts issue/plugin signals into one actionable triage priority.
- `contact_quality_filter` (`profile`, `fusion`)
- Purpose: ranks contacts by quality and flags disposable contact channels.
- `link_hygiene_filter` (`profile`, `fusion`)
- Purpose: prioritizes risky links (non-HTTPS/shortener/suspicious-query).
- `subdomain_attack_path_filter` (`surface`, `fusion`)
- Purpose: ranks subdomains by attack-path relevance and takeover signal.
- `evidence_consistency_filter` (`profile`, `surface`, `fusion`)
- Purpose: finds contradictions across confidence, issues, and intelligence risk.

## Error Handling Guarantees

- All new filters are defensive against missing/partial context payloads.
- Non-dict rows and missing optional plugin payloads are handled safely.
- Filters always return normalized output (`severity`, `summary`, `highlights`, `data`) even on sparse input.
- Discovery and runtime import failures are surfaced in filter error channels, not hard crashes.
