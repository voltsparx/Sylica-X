# Tor Wrappers

Release: v10.0 (Theme: Ember)

This folder now contains Tor wrapper scripts for container and host OS usage.

Container runtime notes:
- Docker images now default to Python `3.13` slim-bookworm.
- Build arg `PYTHON_VERSION` is supported via compose and runner scripts.
- Docker runners support host upgrade and context routing flags (`--runner-upgrade-host`, `--runner-show-contexts`, `--runner-context`).

## Files

- `tor-wrapper.sh`
  Container-only wrapper used by `docker/Dockerfile.tor`.
- `tor-wrapper-linux.sh`
- `tor-wrapper-macos.sh`
- `tor-wrapper-termux.sh`
- `tor-wrapper-windows.ps1`

## Host Usage

Linux:

```bash
chmod +x docker/tor-wrapper-linux.sh
./docker/tor-wrapper-linux.sh
./docker/tor-wrapper-linux.sh --data-dir /tmp/tor-data -- --Log "notice stdout"
```

macOS:

```bash
chmod +x docker/tor-wrapper-macos.sh
./docker/tor-wrapper-macos.sh
```

Termux:

```bash
chmod +x docker/tor-wrapper-termux.sh
./docker/tor-wrapper-termux.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\tor-wrapper-windows.ps1
powershell -ExecutionPolicy Bypass -File .\docker\tor-wrapper-windows.ps1 --data-dir "$env:TEMP\tor-data"
```

## Common Options

- `--help`
- `--config <path>`
- `--data-dir <path>`
- `--no-install`

Any non-wrapper args are passed directly to Tor.

