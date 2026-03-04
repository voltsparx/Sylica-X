# 🛰️ Silica-X v7.2

**Silica-X** is an OSINT framework for **profile intelligence**, **domain-surface reconnaissance**, and **fused correlation reporting**.<br><br>
<p align="center">
This tool is built by stitching together public OSINT workflows and studying how data flows through open APIs while standing on the shoulders of established frameworks.
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/voltsparx/Silica-X/main/docs/images/silica-x-help-menu.png" alt="Silica-X Help Menu" width="600">
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
* 📊 HTML, JSON, CLI, CSV, and run-log outputs
* 🕵️ Optional Tor/proxy routing with diagnostics and guided startup

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

## 📊 Verified Audit Snapshot (February 20, 2026)

* Repository-wide file audit completed across **1,198 files** (including generated output/cache artifacts)
* File audit checks (readability + parser/compile validation) reported **0 errors**
* Unit tests: **53/53 passing**
* Ruff lint: passing
* mypy (full repository scope): passing on **44 source files**
* Bytecode compile check (`compileall`): passing
* Wiring compatibility matrix: **PASS**

  * root commands = 23
  * prompt commands = 22
  * keyword/flag parity verified
* Platform manifests loaded: **50**
* Runtime plugin/filter discovery: **12 plugins, 12 filters**

### Scope Compatibility Inventory

* plugins → profile=7, surface=7, fusion=10
* filters → profile=10, surface=6, fusion=12

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

---

## ▶️ Run

```bash
python silica-x.py
```

Running without flags starts **prompt mode**.

---

## 🧭 Core Commands

* `profile <username...> [flags]`
* `surface <domain> [flags]`
* `fusion <username> <domain> [flags]`
* `plugins [--scope all|profile|surface|fusion]`
* `filters [--scope all|profile|surface|fusion]`
* `modules [--sync] [--kind all|plugin|filter] [--scope all|profile|surface|fusion]`
* `history [--limit N]` (aliases: `targets`, `scans`)
* `anonymity [--tor|--no-tor] [--proxy|--no-proxy] [--check] [--prompt]`
* `live <target> [--port PORT] [--no-browser]`
* `wizard`
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

### Output

* `--html`, `--csv`, `--live`, `--live-port`, `--no-browser`

### Routing

* `--tor`, `--no-tor`, `--proxy`, `--no-proxy`, `--check`, `--prompt`

### Plugin / Filter

* `--plugin`, `--all-plugins`, `--list-plugins`
* `--filter`, `--all-filters`, `--list-filters`

---

## 🖥️ Prompt Commands

* `scan <username>`
* `profile <username...>`
* `surface <domain>`
* `fusion <username> <domain>`
* `plugins`, `filters`, `modules`, `history`
* `anonymity`, `config`
* `about` (keywords: `about`, `info`, `details`)
* `explain` (keywords: `explain`, `understand`, `describe`)
* `banner` (prompt-only; reprints banner)
* `use <profile|surface|fusion>`
* `set plugins <none|all|selector1,selector2>` (module-compatible, id/alias/name-aware)
* `set filters <none|all|selector1,selector2>` (module-compatible, id/alias/name-aware)
* `set profile_preset <fast|quick|balanced|deep|max>`
* `set surface_preset <quick|balanced|deep>`
* `help`, `clear`, `exit`

**Prompt format**

```
(console <module> plugins=<set> filters=<set>)>>
```

---

## 🌍 Platform Coverage

Silica-X currently ships with **50 platform manifests** in `platforms/`:

Behance • Bitbucket • Blogger • BuyMeACoffee • Codeforces • CodePen • Dev.to • DeviantArt • Discord • DockerHub • Dribbble • Facebook • Flickr • GitHub • GitLab • HackerOne • HackerRank • Instagram • Kaggle • Keybase • LeetCode • LinkedIn • Mastodon • Medium • NPM • Pastebin • Patreon • Pinterest • ProductHunt • PyPI • Quora • Reddit • Replit • Roblox • Snapchat • SoundCloud • SourceForge • Spotify • StackOverflow • SteamCommunity • Telegram • Threads • TikTok • TryHackMe • Twitch • Twitter/X • Unsplash • Vimeo • WordPress • YouTube

---

## 📁 Output Structure

```
output/data/<target>/results.json
output/html/<target>.html
output/cli/<target>.txt
output/cli/<target>.csv (when --csv)
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
python -m mypy
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

---

**Author**: voltsparx<br>
**Contact**: voltsparx@gmail.com<br>

---

⭐ If you find Silica-X useful, consider starring the repository!


