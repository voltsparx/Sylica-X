# Silica-X v7.0

Silica-X is an OSINT framework for profile intelligence, domain-surface reconnaissance, and fused correlation reporting.

## Disclaimer

- Legal and authorized use only.
- You are responsible for compliance with local laws and platform Terms of Service.
- Do not use this framework for harassment, stalking, or unauthorized collection.

## Highlights

- Profile scan workflow (`profile`, `scan`, `persona`, `social`)
- Domain surface workflow (`surface`, `domain`, `asset`)
- Fusion workflow (`fusion`, `full`, `combo`)
- Pluggable intelligence system (`core/signal_forge.py` + `plugins/`)
- Pluggable filtering system (`core/signal_sieve.py` + `filters/`)
- Prompt mode with keyword shortcuts, metasploit-style context prompt, and session defaults
- Explain system (`--explain`, `explain`) for command/plugin/filter onboarding
- HTML, JSON, CLI, CSV, and run-log outputs
- Optional Tor/proxy routing with diagnostics and guided startup

## Engineering Upgrades Included

- Parser construction split into `core/cli_parsers.py`
- Shared prompt presets/keywords split into `core/cli_config.py`
- Prompt command handlers split into `core/prompt_handlers.py`
- Centralized about/description renderer in `core/about.py`
- Centralized explain renderer in `core/explain.py`
- Native async engine (`core/async_engine.py`) with adaptive batch concurrency
- Native thread engine (`core/thread_engine.py`) with shared executor + adaptive batch concurrency
- TLS verification enabled by default in scan collectors
- Tor routing uses `socks5h://127.0.0.1:9050` (DNS over Tor)
- Proxy validation supports `HTTP_PROXY` and `HTTPS_PROXY` with scheme checks
- Domain CT/RDAP collectors run concurrently with connector pooling
- Profile scanner reuses tuned async connector limits + DNS cache
- CI pipeline with tests + Ruff + mypy on Python 3.11/3.12/3.13
- Full-repository mypy scope enabled

## Verified Audit Snapshot (February 20, 2026)

- Repository-wide file audit completed across 1,198 files (including generated output/cache artifacts).
- File audit checks (readability + parser/compile validation) reported 0 errors.
- Unit tests: 49/49 passing.
- Ruff lint: passing.
- mypy (full repository scope): passing on 44 source files.
- Bytecode compile check (`compileall`): passing.
- Wiring compatibility matrix: PASS (`root` commands=23, `prompt` commands=22, keyword/flag parity verified).
- Platform manifests loaded: 47.
- Runtime plugin/filter discovery: 6 plugins, 6 filters.
- Scope compatibility inventory:
  - plugins: profile=4, surface=3, fusion=6
  - filters: profile=6, surface=1, fusion=6

## Installation

```bash
git clone https://github.com/voltsparx/Silica-X.git
cd Silica-X
pip install -r requirements.txt
```

Optional developer tooling:

```bash
pip install -r requirements-dev.txt
```

## Run

```bash
python silica-x.py
```

Running without flags starts prompt mode.

## Core Commands

- `profile <username...> [flags]`
- `surface <domain> [flags]`
- `fusion <username> <domain> [flags]`
- `plugins [--scope all|profile|surface|fusion]`
- `filters [--scope all|profile|surface|fusion]`
- `history [--limit N]` (aliases: `targets`, `scans`)
- `anonymity [--tor|--no-tor] [--proxy|--no-proxy] [--check] [--prompt]`
- `live <target> [--port PORT] [--no-browser]`
- `wizard`
- `keywords`
- `about`
- `explain`
- `help`

## Key Flags

- Global:
  - `--about` (print framework description and exit)
  - `--explain` (print plain-language command/plugin/filter guide and exit)
  - `--about` and `--explain` must be used alone (not combined with another command)
- Runtime:
  - `--preset`, `--profile-preset`, `--surface-preset`
  - `--timeout`, `--max-concurrency`, `--max-subdomains`
- Output:
  - `--html`, `--csv`, `--live`, `--live-port`, `--no-browser`
- Routing:
  - `--tor`, `--no-tor`, `--proxy`, `--no-proxy`, `--check`, `--prompt`
- Plugin/filter:
  - `--plugin`, `--all-plugins`, `--list-plugins`
  - `--filter`, `--all-filters`, `--list-filters`

## Prompt Commands

- `scan <username>`
- `profile <username...>`
- `surface <domain>`
- `fusion <username> <domain>`
- `plugins`, `filters`, `history`
- `anonymity`, `config`
- `about` (keywords: `about`, `info`, `details`)
- `explain` (keywords: `explain`, `understand`, `describe`)
- `banner` (prompt-only; reprints banner)
- `use <profile|surface|fusion>`
- `set plugins <none|all|id1,id2>` (module-compatible, alias-aware)
- `set filters <none|all|id1,id2>` (module-compatible, alias-aware)
- `set profile_preset <quick|balanced|deep>`
- `set surface_preset <quick|balanced|deep>`
- `help`, `clear` (screen only; banner stays hidden until `banner`), `exit`
- Prompt format: `(console <module> plugins=<set> filters=<set>)>>`

## Platform Coverage

Silica-X currently ships with 47 platform manifests in `platforms/`:

- Behance
- Bitbucket
- Blogger
- BuyMeACoffee
- Codeforces
- CodePen
- Dev.to
- Discord
- DockerHub
- Dribbble
- Facebook
- Flickr
- GitHub
- GitLab
- HackerOne
- HackerRank
- Instagram
- Kaggle
- Keybase
- LeetCode
- LinkedIn
- Medium
- NPM
- Pastebin
- Patreon
- Pinterest
- ProductHunt
- PyPI
- Quora
- Reddit
- Replit
- Roblox
- Snapchat
- SoundCloud
- SourceForge
- Spotify
- StackOverflow
- SteamCommunity
- Telegram
- TikTok
- TryHackMe
- Twitch
- Twitter/X
- Unsplash
- Vimeo
- WordPress
- YouTube

## Output Structure

- `output/data/<target>/results.json`
- `output/html/<target>.html`
- `output/cli/<target>.txt`
- `output/cli/<target>.csv` (when `--csv`)
- `output/logs/<target>_<timestamp>.txt`
- `output/logs/framework.log.txt`

## Examples

```bash
python silica-x.py --about
python silica-x.py --explain
python silica-x.py anonymity --check
python silica-x.py plugins --scope all
python silica-x.py filters --scope all
python silica-x.py profile alice --tor --plugin orbit_link_matrix --filter contact_canonicalizer --html
python silica-x.py surface example.com --plugin header_hardening_probe --filter exposure_tier_matrix --html
python silica-x.py fusion alice example.com --all-plugins --all-filters --html
python silica-x.py history --limit 20
```

## Docker

```bash
docker compose run --rm silica-x help
docker compose run --rm silica-x profile alice --html
```

Compose profile:

- read-only root filesystem
- non-root runtime
- dropped Linux capabilities
- no-new-privileges
- writable output volume (`./output:/app/output`)

## Quality Gates

Unit tests:

```bash
python -m unittest discover -s tests -v
```

Lint:

```bash
python -m ruff check .
```

Type checking:

```bash
python -m mypy
```

Repository compile pass:

```bash
python -m compileall -q core filters plugins tests silica-x.py
```

CI workflow:

- `.github/workflows/ci.yml`

## Author

- voltsparx
