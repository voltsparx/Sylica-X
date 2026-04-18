#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

TOR_CONFIG="${SCRIPT_DIR}/torrc.silica_x"
TOR_DATA_DIR="${TOR_DATA_DIR:-/tmp/tor-data}"
NO_INSTALL=0
TOR_ARGS=()

info() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

die() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

show_help() {
  cat <<EOF
Usage:
  ./${SCRIPT_NAME} [wrapper-options] [tor-args...]
  ./${SCRIPT_NAME} [wrapper-options] -- [tor-args...]

Wrapper options:
  --help               Show this help.
  --config <path>      Tor config file path (default: docker/torrc.silica_x).
  --data-dir <path>    Tor data dir (default: /tmp/tor-data).
  --no-install         Never install Tor automatically.

Any other args are forwarded to the Tor process.
EOF
}

ask_yes_no() {
  local question="$1"
  local default_yes="${2:-1}"
  local suffix='[Y/n]'
  local reply=''
  local normalized=''

  if [[ "$default_yes" -eq 0 ]]; then
    suffix='[y/N]'
  fi

  if [[ ! -t 0 || ! -t 1 ]]; then
    return 1
  fi

  read -r -p "${question} ${suffix} " reply || true
  if [[ -z "$reply" ]]; then
    [[ "$default_yes" -eq 1 ]]
    return
  fi

  normalized="$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

parse_args() {
  while (($#)); do
    case "$1" in
      --help)
        show_help
        exit 0
        ;;
      --config)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --config"
        TOR_CONFIG="$1"
        ;;
      --data-dir)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --data-dir"
        TOR_DATA_DIR="$1"
        ;;
      --no-install)
        NO_INSTALL=1
        ;;
      --)
        shift
        while (($#)); do
          TOR_ARGS+=("$1")
          shift
        done
        break
        ;;
      *)
        TOR_ARGS+=("$1")
        ;;
    esac
    shift
  done
}

install_homebrew() {
  info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

install_tor_macos() {
  if ! command -v brew >/dev/null 2>&1; then
    if [[ "$NO_INSTALL" -eq 1 ]]; then
      die "Homebrew is required to auto-install Tor on macOS."
    fi
    if ask_yes_no "Homebrew is not installed. Install it now?" 1; then
      install_homebrew
    else
      die "Tor installation canceled."
    fi
  fi

  info "Installing Tor via Homebrew..."
  brew install tor
}

ensure_tor() {
  if command -v tor >/dev/null 2>&1; then
    return
  fi

  if [[ "$NO_INSTALL" -eq 1 ]]; then
    die "Tor is not installed. Remove --no-install to allow guided install."
  fi

  if ask_yes_no "Tor is not installed. Install it now?" 1; then
    install_tor_macos
    command -v tor >/dev/null 2>&1 || die "Tor install completed but binary is still unavailable."
    return
  fi

  die "Tor is required."
}

start_tor() {
  mkdir -p "$TOR_DATA_DIR"

  if [[ -f "$TOR_CONFIG" ]]; then
    info "Starting Tor with config: $TOR_CONFIG"
    exec tor --DataDirectory "$TOR_DATA_DIR" -f "$TOR_CONFIG" "${TOR_ARGS[@]}"
  fi

  warn "Config file not found at '$TOR_CONFIG'. Starting Tor with inline defaults."
  exec tor \
    --DataDirectory "$TOR_DATA_DIR" \
    --SocksPort 127.0.0.1:9050 \
    --ClientOnly 1 \
    --AvoidDiskWrites 1 \
    "${TOR_ARGS[@]}"
}

main() {
  parse_args "$@"
  ensure_tor
  start_tor
}

main "$@"
