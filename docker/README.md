# Tor Wrappers

This folder now contains Tor wrapper scripts for container and host OS usage.

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
