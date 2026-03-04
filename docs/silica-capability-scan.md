# Silica Capability Scan

Frameworks scanned: 8

| Framework | Files | Async | Retry | RateLimit | Cache | Plugins | Parallel | Exports | Tor/Proxy | Tests |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| amass | 243 | 0 | 3 | 1 | 98 | 84 | 14 | 69 | 107 | 0 |
| datasploit | 116 | 2 | 1 | 4 | 8 | 67 | 1 | 42 | 40 | 0 |
| maigret | 146 | 26 | 5 | 9 | 15 | 22 | 6 | 61 | 68 | 20 |
| maigret-1 | 56 | 3 | 1 | 0 | 8 | 12 | 0 | 11 | 25 | 5 |
| recon-ng | 74 | 0 | 1 | 2 | 8 | 17 | 3 | 30 | 26 | 0 |
| sherlock | 87 | 0 | 1 | 2 | 11 | 20 | 1 | 26 | 37 | 18 |
| spiderfoot | 853 | 5 | 6 | 25 | 123 | 735 | 16 | 205 | 335 | 452 |
| theHarvester | 38 | 2 | 3 | 0 | 10 | 6 | 0 | 7 | 13 | 5 |

## Recommendations

- Strengthen retry/backoff/rate-limit strategy in scanner + domain collectors.
- Introduce queryable workspace indexing for historical artifacts and correlation replay.
- Expand plugin/filter orchestration with strict metadata validation and parallel lanes.
- Broaden reporting with richer graphs and analyst-focused export variants.
- Increase coverage around network error paths, plugin failures, and regression fixtures.
