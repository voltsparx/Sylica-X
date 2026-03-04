#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"

RUNNER_BUILD=0
RUNNER_NO_INSTALL=0
RUNNER_FORCE_TOR_SERVICE=0
RUNNER_PROMPT=0
RUNNER_STOP=0
RUNNER_STOP_DOCKER=0
RUNNER_SERVICE="silica-x"
RUNNER_PROFILE=""
RUNNER_SERVICE_SET=0
RUNNER_PROFILE_SET=0
SILICA_ARGS=()
COMPOSE_VARIANT=""

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
  ./${SCRIPT_NAME} [runner-options] [silica-args...]
  ./${SCRIPT_NAME} [runner-options] -- [silica-args...]

Runner options (reserved for this script):
  --runner-help              Show this help message.
  --runner-build             Build service image before running.
  --runner-stop              Stop/remove Silica containers.
  --runner-stop-docker       Stop/remove Silica containers and stop Docker Desktop.
  --runner-use-tor-service   Force Tor service container (silica-x-tor).
  --runner-service <name>    Override compose service (default: silica-x).
  --runner-profile <name>    Override compose profile (default: auto).
  --runner-no-install        Never install missing Docker components.
  --runner-prompt            Force Silica prompt mode (ignore silica-args).

Silica args:
  Any argument not prefixed with --runner- is passed to silica-x.
  If no silica args are passed, silica-x starts in prompt mode.
  If silica args include --tor (without --no-tor), this script auto-selects
  service 'silica-x-tor' and profile 'tor' unless you override it.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} profile alice --html
  ./${SCRIPT_NAME} --runner-stop
  ./${SCRIPT_NAME} --runner-stop-docker
  ./${SCRIPT_NAME} --runner-build --runner-use-tor-service profile alice --tor --html
  ./${SCRIPT_NAME} -- --help
EOF
}

ask_yes_no() {
  local question="$1"
  local default_yes="${2:-1}"
  local suffix='[Y/n]'
  local reply=''

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
  local normalized
  normalized="$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

format_gib_from_bytes() {
  local bytes="$1"
  awk -v value="$bytes" 'BEGIN { printf "%.2f", value / 1073741824 }'
}

format_gib_from_kb() {
  local kb="$1"
  awk -v value="$kb" 'BEGIN { printf "%.2f", value / 1048576 }'
}

parse_args() {
  while (($#)); do
    case "$1" in
      --runner-help)
        show_help
        exit 0
        ;;
      --runner-build)
        RUNNER_BUILD=1
        ;;
      --runner-stop)
        RUNNER_STOP=1
        ;;
      --runner-stop-docker)
        RUNNER_STOP=1
        RUNNER_STOP_DOCKER=1
        ;;
      --runner-use-tor-service)
        RUNNER_FORCE_TOR_SERVICE=1
        ;;
      --runner-no-install)
        RUNNER_NO_INSTALL=1
        ;;
      --runner-prompt)
        RUNNER_PROMPT=1
        ;;
      --runner-service)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --runner-service"
        RUNNER_SERVICE="$1"
        RUNNER_SERVICE_SET=1
        ;;
      --runner-profile)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --runner-profile"
        RUNNER_PROFILE="$1"
        RUNNER_PROFILE_SET=1
        ;;
      --)
        shift
        while (($#)); do
          SILICA_ARGS+=("$1")
          shift
        done
        break
        ;;
      *)
        SILICA_ARGS+=("$1")
        ;;
    esac
    shift
  done
}

configure_mode_and_service() {
  if [[ "$RUNNER_PROMPT" -eq 1 ]]; then
    SILICA_ARGS=()
  fi

  if [[ "$RUNNER_FORCE_TOR_SERVICE" -eq 1 ]]; then
    RUNNER_SERVICE="silica-x-tor"
    if [[ "$RUNNER_PROFILE_SET" -eq 0 ]]; then
      RUNNER_PROFILE="tor"
    fi
  fi

  if [[ "$RUNNER_SERVICE" == "silica-x-tor" && "$RUNNER_PROFILE_SET" -eq 0 && -z "$RUNNER_PROFILE" ]]; then
    RUNNER_PROFILE="tor"
  fi

  if [[ "$RUNNER_SERVICE_SET" -eq 0 && "$RUNNER_FORCE_TOR_SERVICE" -eq 0 ]]; then
    local wants_tor=0
    local disables_tor=0
    local arg
    for arg in "${SILICA_ARGS[@]}"; do
      if [[ "$arg" == "--tor" ]]; then
        wants_tor=1
      elif [[ "$arg" == "--no-tor" ]]; then
        disables_tor=1
      fi
    done
    if [[ "$wants_tor" -eq 1 && "$disables_tor" -eq 0 ]]; then
      RUNNER_SERVICE="silica-x-tor"
      if [[ "$RUNNER_PROFILE_SET" -eq 0 ]]; then
        RUNNER_PROFILE="tor"
      fi
    fi
  fi
}

check_compose_file() {
  [[ -f "$COMPOSE_FILE" ]] || die "Missing compose file: $COMPOSE_FILE"
}

check_resources() {
  local min_mem_bytes=$((2 * 1024 * 1024 * 1024))
  local min_disk_kb=$((4 * 1024 * 1024))
  local mem_bytes=0
  local disk_kb=0

  mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || printf '0')"
  if [[ "$mem_bytes" =~ ^[0-9]+$ ]] && (( mem_bytes < min_mem_bytes )); then
    warn "Low RAM detected: $(format_gib_from_bytes "$mem_bytes") GiB available."
    if ! ask_yes_no "Continue anyway?" 0; then
      die "Aborted due to low memory."
    fi
  fi

  disk_kb="$(df -Pk "$REPO_ROOT" | awk 'NR==2 {print $4}')"
  if [[ "$disk_kb" =~ ^[0-9]+$ ]] && (( disk_kb < min_disk_kb )); then
    warn "Low disk space detected: $(format_gib_from_kb "$disk_kb") GiB free on repo filesystem."
    if ! ask_yes_no "Continue anyway?" 0; then
      die "Aborted due to low disk space."
    fi
  fi
}

install_homebrew() {
  info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

install_docker_macos() {
  if ! command -v brew >/dev/null 2>&1; then
    if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
      die "Homebrew is required to auto-install Docker on macOS."
    fi
    if ask_yes_no "Homebrew is not installed. Install it now?" 1; then
      install_homebrew
    else
      die "Docker installation canceled."
    fi
  fi

  info "Installing Docker Desktop..."
  brew install --cask docker
}

install_compose_macos() {
  if ! command -v brew >/dev/null 2>&1; then
    die "Homebrew is required to install Docker Compose."
  fi
  info "Installing Docker Compose..."
  brew install docker-compose
}

wait_for_docker() {
  local attempts="${1:-90}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

ensure_docker_command() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi
  if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
    die "Docker is not installed. Remove --runner-no-install to allow guided install."
  fi
  if ask_yes_no "Docker is not installed. Install Docker Desktop now?" 1; then
    install_docker_macos
    return
  fi
  die "Docker is required."
}

start_docker_daemon() {
  if docker info >/dev/null 2>&1; then
    return
  fi

  warn "Docker daemon is not reachable. Attempting to start Docker Desktop."
  open -a Docker >/dev/null 2>&1 || true

  if wait_for_docker 90; then
    return
  fi

  die "Docker daemon is still unavailable. Open Docker Desktop manually and rerun."
}

detect_compose_variant() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_VARIANT="plugin"
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_VARIANT="legacy"
    return 0
  fi
  return 1
}

ensure_compose_available() {
  if detect_compose_variant; then
    return
  fi
  if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
    die "Docker Compose is not available. Remove --runner-no-install for guided install."
  fi
  if ask_yes_no "Docker Compose is missing. Install it now?" 1; then
    install_compose_macos
    detect_compose_variant || die "Docker Compose install completed but command is still unavailable."
    return
  fi
  die "Docker Compose is required."
}

compose_exec_with_profile() {
  local profile="${1:-}"
  shift
  local action="$1"
  shift

  if [[ "$COMPOSE_VARIANT" == "plugin" ]]; then
    local cmd=(docker compose -f "$COMPOSE_FILE")
    if [[ -n "$profile" ]]; then
      cmd+=(--profile "$profile")
    fi
    cmd+=("$action" "$@")
    (cd "$REPO_ROOT" && "${cmd[@]}")
    return
  fi

  if [[ -n "$profile" ]]; then
    (cd "$REPO_ROOT" && COMPOSE_PROFILES="$profile" docker-compose -f "$COMPOSE_FILE" "$action" "$@")
  else
    (cd "$REPO_ROOT" && docker-compose -f "$COMPOSE_FILE" "$action" "$@")
  fi
}

compose_exec() {
  compose_exec_with_profile "$RUNNER_PROFILE" "$@"
}

ensure_output_dirs() {
  mkdir -p \
    "${REPO_ROOT}/output/data" \
    "${REPO_ROOT}/output/html" \
    "${REPO_ROOT}/output/cli" \
    "${REPO_ROOT}/output/logs"
}

stop_silica_compose_stack() {
  if ! command -v docker >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    warn "Docker CLI is not available. Nothing to stop."
    return
  fi

  if ! detect_compose_variant; then
    warn "Docker Compose command is unavailable. Skipping compose shutdown."
    return
  fi

  info "Stopping Silica compose services..."
  if ! compose_exec_with_profile "" down --remove-orphans; then
    warn "Compose down reported an issue for default profile."
  fi
  if ! compose_exec_with_profile "tor" down --remove-orphans; then
    warn "Compose down reported an issue for tor profile."
  fi
}

stop_docker_host() {
  info "Stopping Docker Desktop..."
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'quit app "Docker"' >/dev/null 2>&1 || true
  fi
  sleep 2
  if command -v pkill >/dev/null 2>&1; then
    pkill -f "Docker Desktop" >/dev/null 2>&1 || true
    pkill -f "com.docker.backend" >/dev/null 2>&1 || true
  fi
  info "Docker Desktop stop requested."
}

perform_shutdown() {
  if [[ "${#SILICA_ARGS[@]}" -gt 0 ]]; then
    warn "Ignoring forwarded Silica args during shutdown."
  fi

  stop_silica_compose_stack

  if [[ "$RUNNER_STOP_DOCKER" -eq 1 ]]; then
    stop_docker_host
  else
    info "Silica containers stopped. Docker daemon left running."
  fi
}

run_silica() {
  if [[ "$RUNNER_BUILD" -eq 1 ]]; then
    info "Building image for service: $RUNNER_SERVICE"
    compose_exec build "$RUNNER_SERVICE"
  fi

  if [[ "${#SILICA_ARGS[@]}" -eq 0 ]]; then
    info "Starting Silica-X in prompt mode via Docker service: $RUNNER_SERVICE"
    compose_exec run --rm "$RUNNER_SERVICE"
    return
  fi

  info "Running Silica-X via Docker service: $RUNNER_SERVICE"
  compose_exec run --rm "$RUNNER_SERVICE" "${SILICA_ARGS[@]}"
}

main() {
  parse_args "$@"
  configure_mode_and_service
  check_compose_file
  if [[ "$RUNNER_STOP" -eq 1 || "$RUNNER_STOP_DOCKER" -eq 1 ]]; then
    perform_shutdown
    return
  fi
  check_resources
  ensure_docker_command
  start_docker_daemon
  ensure_compose_available
  ensure_output_dirs
  run_silica
}

main "$@"
