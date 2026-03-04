# 🛰️ Silica-X v9.0

**Release Theme**: Lattice

**Silica-X** is an OSINT framework for **profile intelligence**, **domain-surface reconnaissance**, and **fused correlation reporting**.<br><br>
<p align="center">
This tool is built by stitching together public OSINT workflows and studying how data flows through open APIs while standing on the shoulders of established frameworks. Also added my own ideas, architectures, features, etc..., too.....
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/voltsparx/Silica-X/main/docs/images/silica-x-menu.png" alt="Silica-X Menu" width="600">
</p>

---

## ⚠️ Disclaimer

* Legal and authorized use only
* You are responsible for compliance with local laws and platform Terms of Service
* Do not use this framework for harassment, stalking, or unauthorized collection

---

## ✨ Highlights

* 🔎 Profile scan workflow (`profile`, `scan`, `persona`, `social`)
* 🌐 Domain surface workflow (`surface`, `domain`, `asset`)
* 🔗 Fusion workflow (`fusion`, `full`, `combo`)
* 🧩 Pluggable intelligence system (`core/extensions/signal_forge.py` + `plugins/`)
* 🧹 Pluggable filtering system (`core/extensions/signal_sieve.py` + `filters/`)
* 🧱 External module catalog system (`modules/catalog.py` + `modules/*.json`)
* 🌌 Signal fusion connector layer (`core/collect/source_fusion.py` + `signal_*` plugin/filter pair)
* 🖥️ Prompt mode with keyword shortcuts, metasploit-style context prompt, and session defaults
* 📖 Explain system (`--explain`, `explain`) for command/plugin/filter onboarding
* 📦 Prompt startup inventory shows loaded plugin/filter/platform/module/framework counts
* 📊 HTML, JSON, CLI, CSV, and run-log outputs
* 🕵️ Optional Tor/proxy routing with diagnostics and guided startup

---

## 📘 Documentation Index

* [Usage Guide](docs/Usage.txt)
* [Orchestration Architecture](docs/orchestration-architecture.md)
* [Capability Scan Report](docs/silica-capability-scan.md)
* [OCR/Image Infrastructure Plan](docs/ocr-image-scan-infrastructure.md)
* [Release Checklist v9.0 Lattice](docs/release-checklist-v9.0-lattice.md)
* [Release Notes v9.0 Lattice](docs/release-notes-v9.0-lattice.md)
* [Release Commit Plan v9.0 Lattice](docs/release-commit-plan-v9.0-lattice.md)

---

## 🛠️ Engineering Upgrades Included

* Parser construction split into `core/interface/cli_parsers.py`
* Shared prompt presets/keywords split into `core/interface/cli_config.py`
* Prompt command handlers split into `core/prompt_handlers.py`
* Centralized about/description renderer in `core/interface/about.py`
* Centralized explain renderer in `core/interface/explain.py`
* ⚡ Native async engine (`core/engines/async_engine.py`) with adaptive batch concurrency
* 🧵 Native thread engine (`core/engines/thread_engine.py`) with shared executor + adaptive batch concurrency
* 🧠 Hybrid parallel orchestration engine (`core/engines/parallel_engine.py`) for async + thread + CPU execution
* 🔗 Fusion analytics engine (`core/engines/fusion_engine.py`) with confidence scoring, anomaly flags, and graph output
* 🧩 Async plugin manager (`core/extensions/plugin_manager.py`) with chaining support and dependency checks
* 🌐 Shared resilient HTTP layer (`core/collect/http_resilience.py`) with retry/backoff and `Retry-After` handling
* 💡 Prompt intelligence + advisor modules (`core/intel/prompt_engine.py`, `core/intel/advisor.py`)
* 📁 Categorized core layout (`core/interface/`, `core/collect/`, `core/analyze/`, `core/extensions/`, `core/artifacts/`, `core/foundation/`, `core/engines/`, `core/intel/`)
* 🔐 Credential + security managers (`core/foundation/credential_manager.py`, `core/foundation/security_manager.py`)
* 📈 Reporting/scheduler/CLI helpers (`core/artifacts/reporting.py`, `core/engines/scheduler.py`, `core/interface/cli_ui.py`)
* 🗺️ Capability-source map integration (`core/intel/capability_matrix.py`)
* 🧬 Silica capability intel generated under `intel/` (`baseline/`, `features/`, `plans/`, `wiring/`)
* 🧩 Plugin/filter intel views generated in `plugins/_intel/` and `filters/_intel/`
* 🌌 Signal fusion connector layer with normalized signal extraction (`core/collect/source_fusion.py`)
* 🔒 TLS verification enabled by default in scan collectors
* 🧅 Tor routing uses `socks5h://127.0.0.1:9050` (DNS over Tor)
* 🌍 Proxy validation supports `HTTP_PROXY` and `HTTPS_PROXY` with scheme checks
* 🔄 Domain CT/RDAP collectors run concurrently with connector pooling
* 🌐 Profile scanner reuses tuned async connector limits + DNS cache
* 🧪 CI pipeline with tests + Ruff + mypy on Python 3.11/3.12/3.13
* 📦 Full-repository mypy scope enabled

---

## 📊 Verified Audit Snapshot (March 5, 2026)

* Repository-wide file audit completed across **1,198 files** (including generated output/cache artifacts)
* File audit checks (readability + parser/compile validation) reported **0 errors**
* Unit tests: **160/160 passing**
* Ruff lint: passing
* mypy (full repository scope): passing (no issues found)
* Bytecode compile check (`compileall`): passing
* Wiring compatibility matrix: **PASS**

  * root commands = 23
  * prompt commands = 22
  * keyword/flag parity verified
* Platform manifests loaded: **71**
* Runtime plugin/filter discovery: **20 plugins, 17 filters**

### Scope Compatibility Inventory

* plugins → profile=13, surface=12, fusion=18
* filters → profile=14, surface=9, fusion=17

---

## 🚀 Installation

```bash
git clone https://github.com/voltsparx/Silica-X.git
cd Silica-X
pip install -r requirements.txt
```

### Optional developer tooling

```bash
pip install -r requirements-dev.txt
```

Crypto plugin runtime note:

* `cryptography` is included in `requirements.txt` and required for `crypto_aes_attachment`.
* `crypto_xor_attachment` and `crypto_rot13_attachment` run without external system binaries.

OCR roadmap dependency note:

* Planned OCR lane depends on `pytesseract` + `Pillow` and a host Tesseract installation.

---

## ▶️ Run

```bash
python silica-x.py
```

Running without flags starts **prompt mode**.

---

## 📚 Documentation Tables

<table>
  <thead>
    <tr>
      <th>Mode</th>
      <th>Command</th>
      <th>Aliases</th>
      <th>Primary Purpose</th>
      <th>High-Value Flags</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Flag/Prompt</td><td><code>profile &lt;username...&gt;</code></td><td><code>scan</code>, <code>persona</code>, <code>social</code></td><td>Username/profile reconnaissance</td><td><code>--preset</code>, <code>--plugin</code>, <code>--filter</code>, <code>--html</code>, <code>--csv</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>surface &lt;domain&gt;</code></td><td><code>domain</code>, <code>asset</code></td><td>Domain surface exposure collection</td><td><code>--preset</code>, <code>--ct</code>, <code>--rdap</code>, <code>--plugin</code>, <code>--filter</code>, <code>--html</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>fusion &lt;username&gt; &lt;domain&gt;</code></td><td><code>full</code>, <code>combo</code></td><td>Combined profile + surface intelligence</td><td><code>--profile-preset</code>, <code>--surface-preset</code>, <code>--plugin</code>, <code>--filter</code>, <code>--html</code>, <code>--csv</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>orchestrate &lt;mode&gt; &lt;target&gt;</code></td><td><code>orch</code></td><td>Policy-driven orchestration pipeline</td><td><code>--profile</code>, <code>--source-profile</code>, <code>--min-confidence</code>, <code>--json</code>, <code>--html</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>quicktest</code></td><td><code>qtest</code>, <code>smoke</code></td><td>Offline synthetic victim test run with full artifact generation</td><td><code>--template</code>, <code>--seed</code>, <code>--list-templates</code>, <code>--json</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>plugins</code></td><td>-</td><td>List plugin inventory</td><td><code>--scope all|profile|surface|fusion</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>filters</code></td><td>-</td><td>List filter inventory</td><td><code>--scope all|profile|surface|fusion</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>modules</code></td><td>-</td><td>List/sync/query module catalog</td><td><code>--sync</code>, <code>--kind</code>, <code>--search</code>, <code>--tag</code>, <code>--stats-only</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>history</code></td><td><code>targets</code>, <code>scans</code></td><td>Show local scan history</td><td><code>--limit</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>anonymity</code></td><td>-</td><td>Inspect/configure routing state</td><td><code>--tor</code>, <code>--proxy</code>, <code>--check</code>, <code>--prompt</code></td></tr>
    <tr><td>Flag</td><td><code>live &lt;target&gt;</code></td><td>-</td><td>Launch local dashboard for a saved target</td><td><code>--port</code>, <code>--no-browser</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>wizard</code></td><td>-</td><td>Guided interactive workflow</td><td><code>--profile-preset</code>, <code>--surface-preset</code>, <code>--extension-control</code>, <code>--plugin</code>, <code>--filter</code>, <code>--tor</code>, <code>--proxy</code></td></tr>
    <tr><td>Flag/Prompt</td><td><code>keywords</code></td><td>-</td><td>Show keyword-to-command map</td><td>-</td></tr>
    <tr><td>Flag/Prompt</td><td><code>about</code>, <code>explain</code>, <code>help</code></td><td>-</td><td>Documentation and metadata</td><td><code>--about</code>, <code>--explain</code> (global)</td></tr>
  </tbody>
</table>

<br>

<table>
  <thead>
    <tr>
      <th>Prompt Control</th>
      <th>Example</th>
      <th>Behavior</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Module switch</td><td><code>use fusion</code> or <code>select module fusion</code></td><td>Changes active prompt context.</td></tr>
    <tr><td>Plugin set</td><td><code>set plugins threat_conductor,signal_fusion_core</code></td><td>Sets module-compatible plugins by id/alias/title.</td></tr>
    <tr><td>Filter set</td><td><code>set filters triage_priority_filter,link_hygiene_filter</code></td><td>Sets module-compatible filters by id/alias/title.</td></tr>
    <tr><td>Incremental plugin edits</td><td><code>add plugins x</code> / <code>remove plugins x</code></td><td>Adds/removes specific plugins while preserving compatibility checks.</td></tr>
    <tr><td>Incremental filter edits</td><td><code>add filters x</code> / <code>remove filters x</code></td><td>Adds/removes specific filters while preserving compatibility checks.</td></tr>
    <tr><td>Preset defaults</td><td><code>set profile_preset deep</code>, <code>set surface_preset quick</code></td><td>Updates prompt defaults for later commands.</td></tr>
    <tr><td>Extension control</td><td><code>set extension_control hybrid</code></td><td>Controls auto/manual/hybrid selection behavior.</td></tr>
    <tr><td>Quick smoke run</td><td><code>quicktest --seed 7</code></td><td>Runs synthetic end-to-end flow from prompt mode.</td></tr>
  </tbody>
</table>

<br>

<table>
  <thead>
    <tr>
      <th>Artifact</th>
      <th>Path Pattern</th>
      <th>Contains</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Primary JSON</td><td><code>output/data/&lt;target&gt;/results.json</code></td><td>Structured run payload (results, issues, plugins/filters, intelligence, summary).</td></tr>
    <tr><td>HTML Report</td><td><code>output/html/&lt;target&gt;.html</code></td><td>Visual dashboard report with tables/cards/correlation/guidance.</td></tr>
    <tr><td>CLI Report</td><td><code>output/cli/&lt;target&gt;.txt</code></td><td>Readable text report with scoring and extension summaries.</td></tr>
    <tr><td>CSV Main</td><td><code>output/cli/&lt;target&gt;.csv</code></td><td>Core flattened rows.</td></tr>
    <tr><td>CSV Companions</td><td><code>*.issues.csv</code>, <code>*.plugins.csv</code>, <code>*.filters.csv</code>, <code>*.intel-entities.csv</code>, <code>*.intel-contacts.csv</code></td><td>Detailed slices for downstream analysis.</td></tr>
    <tr><td>Run Logs</td><td><code>output/logs/&lt;target&gt;_&lt;timestamp&gt;.txt</code>, <code>output/logs/framework.log.txt</code></td><td>Per-run and framework lifecycle logs.</td></tr>
  </tbody>
</table>

<br>

<table>
  <thead>
    <tr>
      <th>Quicktest Template ID</th>
      <th>Victim Label</th>
      <th>Username</th>
      <th>Domain</th>
      <th>Default Selection</th>
    </tr>
  </thead>
  <tbody>
    <tr><td><code>atlas-mercier</code></td><td>Atlas Mercier</td><td><code>atlas_mercier</code></td><td><code>atlaslab.dev</code></td><td rowspan="5">Random when no <code>--template</code> is provided.</td></tr>
    <tr><td><code>noor-akhtar</code></td><td>Noor Akhtar</td><td><code>noor_akhtar</code></td><td><code>nordelta-ops.net</code></td></tr>
    <tr><td><code>juno-harbor</code></td><td>Juno Harbor</td><td><code>juno_harbor</code></td><td><code>harbor-grid.io</code></td></tr>
    <tr><td><code>raven-ion</code></td><td>Raven Ion</td><td><code>raven_ion</code></td><td><code>ionrelay.cloud</code></td></tr>
    <tr><td><code>maya-cipher</code></td><td>Maya Cipher</td><td><code>maya_cipher</code></td><td><code>ciphertrail.ai</code></td></tr>
  </tbody>
</table>

<br>

<table>
  <thead>
    <tr>
      <th>Smoke Suite (2026-03-05)</th>
      <th>Status</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>
    <tr><td><code>python -m pytest -q</code></td><td>PASS</td><td>160 tests passed.</td></tr>
    <tr><td><code>python -m ruff check .</code></td><td>PASS</td><td>No lint errors.</td></tr>
    <tr><td><code>python -m mypy</code></td><td>PASS</td><td>No type errors found (repository scope).</td></tr>
    <tr><td><code>python -m compileall -q core filters plugins tests silica-x.py</code></td><td>PASS</td><td>Bytecode compile smoke passed.</td></tr>
    <tr><td>CLI matrix (about/explain/help/keywords/plugins/filters/modules/history)</td><td>PASS</td><td>All returned exit code 0.</td></tr>
    <tr><td>Command-path matrix (profile/surface/fusion/orchestrate via <code>--list-plugins/--list-filters</code>, plus <code>anonymity --check</code>)</td><td>PASS</td><td>All returned exit code 0 without external collection.</td></tr>
    <tr><td>Quicktest matrix (<code>quicktest</code>, <code>qtest</code>, <code>smoke</code>, prompt quicktest)</td><td>PASS</td><td>All produced expected artifacts and exit code 0.</td></tr>
    <tr><td><code>live</code> command</td><td>SKIPPED</td><td>Long-running server mode; verified manually in targeted runs.</td></tr>
  </tbody>
</table>

---

## 🧭 Core Commands

* `profile <username...> [flags]`
* `surface <domain> [flags]`
* `fusion <username> <domain> [flags]`
* `orchestrate <profile|surface|fusion> <target> [--secondary-target ...] [flags]`
* `plugins [--scope all|profile|surface|fusion]`
* `filters [--scope all|profile|surface|fusion]`
* `modules [--sync] [--kind all|plugin|filter] [--scope all|profile|surface|fusion]`
* `history [--limit N]` (aliases: `targets`, `scans`)
* `anonymity [--tor|--no-tor] [--proxy|--no-proxy] [--check] [--prompt]`
* `live <target> [--port PORT] [--no-browser]`
* `wizard [--profile-phase|--no-profile-phase] [--surface-phase|--no-surface-phase] [--fusion-phase|--no-fusion-phase] [--profile-preset ...] [--surface-preset ...] [--extension-control ...] [--plugin ...] [--filter ...] [--html|--no-html] [--csv|--no-csv] [--ct|--no-ct] [--rdap|--no-rdap] [--sync-modules]`
* `capability-pack` (alias: `intel`)
* `keywords`
* `about`
* `explain`
* `help`

---

## 🎛️ Key Flags

### Global

* `--about` → print framework description and exit
* `--explain` → print plain-language command/plugin/filter guide and exit
* `--about` and `--explain` must be used alone

### Runtime

* `--preset`, `--profile-preset`, `--surface-preset`
* `--timeout`, `--max-concurrency`, `--max-subdomains`
* `--max-workers`, `--source-profile`, `--max-platforms`, `--min-confidence`

### Output

* `--html`, `--csv`, `--live`, `--live-port`, `--no-browser`

### Routing

* `--tor`, `--no-tor`, `--proxy`, `--no-proxy`, `--check`, `--prompt`

### Plugin / Filter

* `--plugin`, `--all-plugins`, `--list-plugins`
* `--filter`, `--all-filters`, `--list-filters`
* `--extension-control auto|manual|hybrid`
* Plugin inventory lists cryptography plugins in a separate `Cryptography Plugin Set` section

---

## 🧙 Wizard Workflow

`wizard` supports both fully guided operation and flag-seeded operation.

When you provide wizard flags, those values are used directly.  
When flags are omitted, wizard prompts for the missing decisions.

Wizard supports:

* Phase toggles: `--profile-phase|--no-profile-phase`, `--surface-phase|--no-surface-phase`, `--fusion-phase|--no-fusion-phase`
* Targets: `--usernames <a,b,c>`, `--domain <domain>`
* Runtime control: `--profile-preset`, `--surface-preset`, `--extension-control auto|manual|hybrid`
* Extension selection: `--plugin`, `--all-plugins`, `--list-plugins`, `--filter`, `--all-filters`, `--list-filters`
* Output toggles: `--html|--no-html`, `--csv|--no-csv`
* Surface toggles: `--ct|--no-ct`, `--rdap|--no-rdap`
* Catalog refresh: `--sync-modules`

Wizard includes extension compatibility preflight across selected scopes.  
If selectors conflict or are incompatible, wizard stops before scanning and prints recovery hints.

Example:

```bash
python silica-x.py wizard \
  --profile-phase --surface-phase --fusion-phase \
  --usernames alice,bob --domain example.com \
  --profile-preset deep --surface-preset balanced \
  --extension-control hybrid \
  --plugin threat_conductor --filter triage_priority_filter \
  --html --csv --ct --rdap
```

---

## 🔐 Crypto Plugin Operations

Crypto plugin set:

* `crypto_aes_attachment`
* `crypto_xor_attachment`
* `crypto_rot13_attachment`

Selection:

```bash
python silica-x.py profile alice --plugin crypto_aes_attachment --html
python silica-x.py fusion alice example.com --plugin crypto_xor_attachment --filter signal_lane_fusion --html
```

Runtime behavior:

* Crypto plugins are discoverable under `plugins/crypto/` and listed in a dedicated `Cryptography Plugin Set`.
* Crypto payload sources are scope-aware and collected from results/correlation/issues/domain/intelligence context.
* Scan mode config drives crypto depth:
  * `fast`: smaller payload budget
  * `balanced`: baseline payload budget
  * `deep` / `max`: larger payload budget + strict mode enabled
* Reports include crypto configuration details (`crypto_profile`) and source coverage (`source_summary`) so selected behavior is transparent in CLI/HTML outputs.

---

## 🖼️ OCR/Image Infrastructure

OCR/image intelligence is documented as an architecture track and implementation guide (currently roadmap-level, not enabled as a built-in runtime plugin set yet).  
Planned availability target: `v9.5` or `v10.0`.

Reference docs:

* [OCR/Image Infrastructure Plan](docs/ocr-image-scan-infrastructure.md)
* [Self-Structuring Note](self-structuring/ocr-n-image/ocr-n-image-scan-infrastructure.txt)

---

## 🖥️ Prompt Commands

* `scan <username>`
* `profile <username...>`
* `surface <domain>`
* `fusion <username> <domain>`
* `orchestrate <profile|surface|fusion> <target> [--secondary-target ...]`
* `plugins`, `filters`, `modules`, `history`
* `anonymity`, `config`
* `about` (keywords: `about`, `info`, `details`)
* `explain` (keywords: `explain`, `understand`, `describe`)
* `banner` (prompt-only; reprints banner)
* `use <profile|surface|fusion>`
* `select module <profile|surface|fusion>` (alias for `use`)
* `set plugins <none|all|selector1,selector2>` (module-compatible, id/alias/name-aware)
* `set filters <none|all|selector1,selector2>` (module-compatible, id/alias/name-aware)
* `select plugins <selector1,selector2>` / `select filters <selector1,selector2>` (name-based aliases)
* `add plugins <selector1,selector2>` / `remove plugins <selector1,selector2>` (incremental controls)
* `add filters <selector1,selector2>` / `remove filters <selector1,selector2>` (incremental controls)
* `set profile_preset <fast|quick|balanced|deep|max>`
* `set surface_preset <quick|balanced|deep>`
* `help`, `clear`, `exit`

**Prompt format**

```
(console <module> ec=<mode> plugins=<set> filters=<set>)>>
```

---

## 🌍 Platform Coverage

Silica-X currently ships with **71 platform manifests** in `platforms/`.  
Representative set:

Behance • Bitbucket • Blogger • BuyMeACoffee • Codeforces • CodePen • Dev.to • DeviantArt • Discord • DockerHub • Dribbble • Facebook • Flickr • GitHub • GitLab • HackerOne • HackerRank • Instagram • Kaggle • Keybase • LeetCode • LinkedIn • Mastodon • Medium • NPM • Pastebin • Patreon • Pinterest • ProductHunt • PyPI • Quora • Reddit • Replit • Roblox • Snapchat • SoundCloud • SourceForge • Spotify • StackOverflow • SteamCommunity • Telegram • Threads • TikTok • TryHackMe • Twitch • Twitter/X • Unsplash • Vimeo • WordPress • YouTube

---

## 📁 Output Structure

```
output/data/<target>/results.json
output/html/<target>.html
output/cli/<target>.txt
output/cli/<target>.csv (when --csv)
output/cli/<target>.issues.csv (when --csv)
output/cli/<target>.plugins.csv (when --csv)
output/cli/<target>.filters.csv (when --csv)
output/cli/<target>.intel-entities.csv (when --csv)
output/cli/<target>.intel-contacts.csv (when --csv)
output/logs/<target>_<timestamp>.txt
output/logs/framework.log.txt
```

---

## 🧪 Examples

```bash
python silica-x.py --about
python silica-x.py --explain
python silica-x.py anonymity --check
python silica-x.py plugins --scope all
python silica-x.py filters --scope all
python silica-x.py modules --sync --kind plugin --scope profile --limit 30
python silica-x.py profile alice --tor --plugin orbit_link_matrix --filter contact_canonicalizer --html
python silica-x.py surface example.com --plugin header_hardening_probe --filter exposure_tier_matrix --html
python silica-x.py fusion alice example.com --all-plugins --all-filters --html
python silica-x.py fusion alice example.com --plugin signal_fusion_core --filter signal_lane_fusion --html
python silica-x.py history --limit 20
```

---

## 🐳 Docker

```bash
docker compose -f docker/docker-compose.yml run --rm silica-x help
docker compose -f docker/docker-compose.yml run --rm silica-x profile alice --html
```

### Tor-enabled compose profile

```bash
docker compose -f docker/docker-compose.yml --profile tor run --rm silica-x-tor anonymity --check
docker compose -f docker/docker-compose.yml --profile tor run --rm silica-x-tor profile alice --tor --html
```

`silica-x-tor` is built from `docker/Dockerfile.tor`, includes `tor`, and uses a container-safe Tor config (`/etc/tor/torrc.silica`) that writes under `/tmp`.
Host-side Tor wrapper scripts for Linux/macOS/Termux/Windows are documented in `docker/README.md`.

### Cross-platform Docker runners

Use `docker-scripts/` for guided setup + launch (install checks, daemon checks, resource checks, prompt support):

```bash
chmod +x docker-scripts/run-docker-linux.sh docker-scripts/run-docker-macos.sh docker-scripts/run-docker-termux.sh

# Linux
./docker-scripts/run-docker-linux.sh
./docker-scripts/run-docker-linux.sh profile alice --html
./docker-scripts/run-docker-linux.sh --runner-stop
./docker-scripts/run-docker-linux.sh --runner-stop-docker

# macOS
./docker-scripts/run-docker-macos.sh
./docker-scripts/run-docker-macos.sh profile alice --tor --html
./docker-scripts/run-docker-macos.sh --runner-stop
./docker-scripts/run-docker-macos.sh --runner-stop-docker

# Termux
./docker-scripts/run-docker-termux.sh
./docker-scripts/run-docker-termux.sh profile alice --html
./docker-scripts/run-docker-termux.sh --runner-stop
./docker-scripts/run-docker-termux.sh --runner-stop-docker

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1 profile alice --html
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1 --runner-stop
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1 --runner-stop-docker
```

Detailed runner options are documented in `docker-scripts/README.md`.

Runner behavior:

* Script-only flags are namespaced as `--runner-*` to avoid collisions with Silica flags.
* Any non-`--runner-*` args are forwarded to `silica-x.py` (flag mode).
* No forwarded args starts Silica prompt mode automatically.
* `--runner-stop` cleanly tears down Silica containers when finished.
* `--runner-stop-docker` also stops the local Docker daemon/Desktop (when supported).
* Use `--` if you want to pass args like `--help` directly to Silica.
* If forwarded args include `--tor` (without `--no-tor`), runners auto-switch to `silica-x-tor`.

### Compose Security Profile

* read-only root filesystem
* non-root runtime
* dropped Linux capabilities
* no-new-privileges
* writable output volume (`../output:/app/output` in `docker/docker-compose.yml`)

---

## 🧪 Quality Gates

### Unit tests

```bash
python -m pytest -q
```

### Lint

```bash
python -m ruff check .
```

### Type checking

```bash
python -m mypy --follow-imports=skip core/intelligence core/artifacts core/reporting core/analyze core/adapters core/runner.py
```

### Repository compile pass

```bash
python -m compileall -q core filters modules plugins tests silica-x.py
```

### Capability source scan

```bash
python -c "from core.intel.capability_matrix import write_capability_report; print(write_capability_report())"
```

Writes a capability summary to `docs/silica-capability-scan.md`.

```bash
python silica-x.py capability-pack
# same as: python silica-x.py intel
```

Generates/refreshes:
- `intel/baseline/`
- `intel/features/`
- `intel/plans/`
- `intel/wiring/`
- `intel/index.json`
- `plugins/_intel/index.json`
- `plugins/_intel/plans/*.json`
- `filters/_intel/index.json`
- `filters/_intel/plans/*.json`
- `modules/index.json`
- `modules/plugin-modules.json`
- `modules/filter-modules.json`

### CI workflow

* `.github/workflows/ci.yml`
* Gates: unittest, Ruff, targeted mypy on critical runtime paths, compile smoke.

---

**Author**: voltsparx<br>
**Contact**: voltsparx@gmail.com<br>

---

⭐ If you find Silica-X useful, consider starring the repository!
