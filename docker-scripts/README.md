# Docker Runner Scripts

Release: v10.0 (Theme: Ember)

These scripts wrap `docker/docker-compose.yml` and provide guided setup for:

- Docker install checks
- Docker daemon startup checks
- Docker Compose availability checks
- Basic host resource checks (RAM + disk)
- Prompt-safe argument forwarding to Silica-X
- Clean shutdown of Sylica containers (and optional Docker host stop)
- Runtime upgrade controls (`--runner-upgrade`, `--runner-pull`, `--runner-no-cache`)
- Host Docker/Desktop upgrade control (`--runner-upgrade-host`)
- Docker context support (`--runner-show-contexts`, `--runner-context <name>`)
- Non-interactive diagnostics (`--runner-diagnose`)
- Python base version override for builds (`--runner-python-version <version>`)

## Scripts

- `run-docker-windows.ps1`
- `run-docker-linux.sh`
- `run-docker-macos.sh`
- `run-docker-termux.sh`

## Quick Start

Unix shells:

```bash
chmod +x docker-scripts/run-docker-linux.sh docker-scripts/run-docker-macos.sh docker-scripts/run-docker-termux.sh
```

Examples:

```bash
# prompt mode
./docker-scripts/run-docker-linux.sh

# direct command/flag mode
./docker-scripts/run-docker-linux.sh profile alice --html

# force tor service image
./docker-scripts/run-docker-linux.sh --runner-use-tor-service profile alice --tor --html

# stop Sylica containers
./docker-scripts/run-docker-linux.sh --runner-stop

# stop Sylica containers + Docker daemon/desktop
./docker-scripts/run-docker-linux.sh --runner-stop-docker

# force runtime upgrade build (pull latest base layers, no cache)
./docker-scripts/run-docker-linux.sh --runner-upgrade

# upgrade host Docker engine/Desktop and then rebuild runtime
./docker-scripts/run-docker-linux.sh --runner-upgrade-host --runner-upgrade

# list available contexts and use a specific one
./docker-scripts/run-docker-linux.sh --runner-show-contexts
./docker-scripts/run-docker-linux.sh --runner-context remote-lab profile alice --html

# run compatibility diagnostics
./docker-scripts/run-docker-linux.sh --runner-diagnose

# pin Docker build Python runtime
./docker-scripts/run-docker-linux.sh --runner-build --runner-python-version 3.13 profile alice --html

# pass --help directly to Sylica
./docker-scripts/run-docker-linux.sh -- --help
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1
powershell -ExecutionPolicy Bypass -File .\docker-scripts\run-docker-windows.ps1 profile alice --html
```

## Runner Flags

Script-only flags are namespaced with `--runner-`:

- `--runner-help`
- `--runner-build`
- `--runner-pull`
- `--runner-no-cache`
- `--runner-upgrade`
- `--runner-upgrade-host`
- `--runner-stop`
- `--runner-stop-docker`
- `--runner-show-contexts`
- `--runner-diagnose`
- `--runner-context <name>`
- `--runner-use-tor-service`
- `--runner-service <name>`
- `--runner-profile <name>`
- `--runner-python-version <version>`
- `--runner-no-install`
- `--runner-prompt`

All non-`--runner-*` args are forwarded to `silica-x.py`.
No forwarded args starts Sylica prompt mode.

## Shutdown Behavior

- `--runner-stop`:
  Stops/removes Sylica compose services using `down --remove-orphans` for default and `tor` profiles.
- `--runner-stop-docker`:
  Runs `--runner-stop` behavior, then attempts to stop Docker on the host.
- Termux note:
  If `DOCKER_HOST` points to a remote daemon, remote daemon shutdown is not automated.

