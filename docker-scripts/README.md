# Docker Runner Scripts

Release: v9.0 (Theme: Lattice)

These scripts wrap `docker/docker-compose.yml` and provide guided setup for:

- Docker install checks
- Docker daemon startup checks
- Docker Compose availability checks
- Basic host resource checks (RAM + disk)
- Prompt-safe argument forwarding to Silica-X
- Clean shutdown of Silica containers (and optional Docker host stop)

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

# stop Silica containers
./docker-scripts/run-docker-linux.sh --runner-stop

# stop Silica containers + Docker daemon/desktop
./docker-scripts/run-docker-linux.sh --runner-stop-docker

# pass --help directly to Silica
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
- `--runner-stop`
- `--runner-stop-docker`
- `--runner-use-tor-service`
- `--runner-service <name>`
- `--runner-profile <name>`
- `--runner-no-install`
- `--runner-prompt`

All non-`--runner-*` args are forwarded to `silica-x.py`.
No forwarded args starts Silica prompt mode.

## Shutdown Behavior

- `--runner-stop`:
  Stops/removes Silica compose services using `down --remove-orphans` for default and `tor` profiles.
- `--runner-stop-docker`:
  Runs `--runner-stop` behavior, then attempts to stop Docker on the host.
- Termux note:
  If `DOCKER_HOST` points to a remote daemon, remote daemon shutdown is not automated.
