#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.yml"

RUNNER_BUILD=0
RUNNER_PULL=0
RUNNER_NO_CACHE=0
RUNNER_UPGRADE=0
RUNNER_UPGRADE_HOST=0
RUNNER_NO_INSTALL=0
RUNNER_FORCE_TOR_SERVICE=0
RUNNER_PROMPT=0
RUNNER_STOP=0
RUNNER_STOP_DOCKER=0
RUNNER_SHOW_CONTEXTS=0
RUNNER_DIAGNOSE=0
RUNNER_SERVICE="silica-x"
RUNNER_PROFILE=""
RUNNER_PYTHON_VERSION=""
RUNNER_CONTEXT=""
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
  --runner-pull              Build with --pull to refresh base layers.
  --runner-no-cache          Build with --no-cache.
  --runner-upgrade           Upgrade container runtime (implies --runner-build --runner-pull --runner-no-cache).
  --runner-upgrade-host      Upgrade host Docker CLI/Compose packages.
  --runner-stop              Stop/remove Silica containers.
  --runner-stop-docker       Stop/remove Silica containers and stop local Docker daemon.
  --runner-show-contexts     List Docker contexts and exit.
  --runner-diagnose          Run non-interactive environment diagnostics and exit.
  --runner-context <name>    Use a specific Docker context.
  --runner-use-tor-service   Force Tor service container (silica-x-tor).
  --runner-service <name>    Override compose service (default: silica-x).
  --runner-profile <name>    Override compose profile (default: auto).
  --runner-python-version <v>  Override Docker build arg PYTHON_VERSION (e.g., 3.13).
  --runner-no-install        Never install missing Docker components.
  --runner-prompt            Force Silica prompt mode (ignore silica-args).

Silica args:
  Any argument not prefixed with --runner- is passed to silica-x.
  If no silica args are passed, silica-x starts in prompt mode.
  If silica args include --tor (without --no-tor), this script auto-selects
  service 'silica-x-tor' and profile 'tor' unless you override it.

Termux note:
  Android/Termux generally uses Docker CLI with a remote Docker daemon.
  This script can prompt for DOCKER_HOST when no local daemon is reachable.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} profile alice --html
  ./${SCRIPT_NAME} --runner-stop
  ./${SCRIPT_NAME} --runner-stop-docker
  ./${SCRIPT_NAME} --runner-upgrade-host --runner-upgrade
  ./${SCRIPT_NAME} --runner-show-contexts
  ./${SCRIPT_NAME} --runner-diagnose
  ./${SCRIPT_NAME} --runner-use-tor-service profile alice --tor --html
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

format_kb_to_gb() {
  local kb="$1"
  awk -v value="$kb" 'BEGIN { printf "%.2f", value / 1048576 }'
}

docker_cmd() {
  local cmd=(docker)
  if [[ -n "$RUNNER_CONTEXT" ]]; then
    cmd+=(--context "$RUNNER_CONTEXT")
  fi
  cmd+=("$@")
  "${cmd[@]}"
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
      --runner-pull)
        RUNNER_PULL=1
        ;;
      --runner-no-cache)
        RUNNER_NO_CACHE=1
        ;;
      --runner-upgrade)
        RUNNER_UPGRADE=1
        ;;
      --runner-upgrade-host)
        RUNNER_UPGRADE_HOST=1
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
      --runner-show-contexts)
        RUNNER_SHOW_CONTEXTS=1
        ;;
      --runner-diagnose)
        RUNNER_DIAGNOSE=1
        ;;
      --runner-context)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --runner-context"
        RUNNER_CONTEXT="$1"
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
      --runner-python-version)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --runner-python-version"
        RUNNER_PYTHON_VERSION="$1"
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
  local min_mem_kb=$((2 * 1024 * 1024))
  local min_disk_kb=$((4 * 1024 * 1024))
  local mem_kb=0
  local disk_kb=0

  if [[ -r /proc/meminfo ]]; then
    mem_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
    if [[ "$mem_kb" =~ ^[0-9]+$ ]] && (( mem_kb < min_mem_kb )); then
      warn "Low RAM detected: $(format_kb_to_gb "$mem_kb") GiB available."
      if ! ask_yes_no "Continue anyway?" 0; then
        die "Aborted due to low memory."
      fi
    fi
  fi

  disk_kb="$(df -Pk "$REPO_ROOT" | awk 'NR==2 {print $4}')"
  if [[ "$disk_kb" =~ ^[0-9]+$ ]] && (( disk_kb < min_disk_kb )); then
    warn "Low disk space detected: $(format_kb_to_gb "$disk_kb") GiB free on repo filesystem."
    if ! ask_yes_no "Continue anyway?" 0; then
      die "Aborted due to low disk space."
    fi
  fi
}

diagnose_runner() {
  local failures=0
  local min_mem_kb=$((2 * 1024 * 1024))
  local min_disk_kb=$((4 * 1024 * 1024))
  local mem_kb=0
  local disk_kb=0
  local docker_cli='missing'
  local daemon_state='unavailable'
  local compose_state='missing'
  local context_state='n/a'
  local cli_version='n/a'
  local termux_state='unknown'

  diag_line() {
    printf '  %-24s %s\n' "$1" "$2"
  }

  if [[ -n "${TERMUX_VERSION:-}" || -d "/data/data/com.termux/files/home" ]]; then
    termux_state='detected'
  else
    termux_state='not-detected'
  fi

  info "Runner diagnostics"
  printf '%s\n' '----------------------------------------'
  diag_line "script" "$SCRIPT_NAME"
  diag_line "repo_root" "$REPO_ROOT"
  diag_line "termux_context" "$termux_state"
  diag_line "docker_host_env" "${DOCKER_HOST:-not-set}"
  diag_line "compose_file" "$COMPOSE_FILE"
  if [[ -f "$COMPOSE_FILE" ]]; then
    diag_line "compose_file_status" "ok"
  else
    diag_line "compose_file_status" "missing"
    failures=$((failures + 1))
  fi
  diag_line "service" "$RUNNER_SERVICE"
  diag_line "profile" "${RUNNER_PROFILE:-auto}"
  diag_line "requested_context" "${RUNNER_CONTEXT:-default/auto}"

  if command -v docker >/dev/null 2>&1; then
    docker_cli='present'
    cli_version="$(docker --version 2>/dev/null || printf 'unknown')"
    context_state="$(docker context show 2>/dev/null || printf 'unknown')"
    if docker_cmd info >/dev/null 2>&1; then
      daemon_state='reachable'
    else
      daemon_state='unreachable'
      failures=$((failures + 1))
    fi
    if docker_cmd compose version >/dev/null 2>&1; then
      compose_state='plugin'
    elif command -v docker-compose >/dev/null 2>&1; then
      compose_state='legacy'
    else
      compose_state='missing'
      failures=$((failures + 1))
    fi
  else
    failures=$((failures + 1))
  fi

  diag_line "docker_cli" "$docker_cli"
  diag_line "docker_cli_version" "$cli_version"
  diag_line "docker_context_active" "$context_state"
  diag_line "docker_daemon" "$daemon_state"
  diag_line "compose_support" "$compose_state"

  if [[ -r /proc/meminfo ]]; then
    mem_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
  fi
  if [[ "$mem_kb" =~ ^[0-9]+$ ]] && [[ "$mem_kb" -gt 0 ]]; then
    diag_line "memory_total" "$(format_kb_to_gb "$mem_kb") GiB"
    if (( mem_kb < min_mem_kb )); then
      diag_line "memory_status" "low (< 2 GiB)"
      failures=$((failures + 1))
    else
      diag_line "memory_status" "ok"
    fi
  else
    diag_line "memory_status" "unknown"
  fi

  disk_kb="$(df -Pk "$REPO_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')"
  if [[ "$disk_kb" =~ ^[0-9]+$ ]] && [[ "$disk_kb" -gt 0 ]]; then
    diag_line "disk_free" "$(format_kb_to_gb "$disk_kb") GiB"
    if (( disk_kb < min_disk_kb )); then
      diag_line "disk_status" "low (< 4 GiB)"
      failures=$((failures + 1))
    else
      diag_line "disk_status" "ok"
    fi
  else
    diag_line "disk_status" "unknown"
  fi

  if (( failures == 0 )); then
    info "Diagnostics passed."
    return 0
  fi

  warn "Diagnostics found ${failures} issue(s) that may block execution."
  return 1
}

ensure_termux_context() {
  if [[ -z "${TERMUX_VERSION:-}" && ! -d "/data/data/com.termux/files/home" ]]; then
    warn "TERMUX_VERSION not detected. Continuing anyway."
  fi
}

install_termux_packages() {
  command -v pkg >/dev/null 2>&1 || die "Termux pkg command not found."
  info "Installing required Termux packages..."
  pkg update -y
  pkg install -y docker openssh
}

install_compose_termux() {
  command -v pkg >/dev/null 2>&1 || die "Termux pkg command not found."
  info "Installing Docker Compose for Termux..."
  pkg install -y docker-compose
}

upgrade_docker_host_termux() {
  command -v pkg >/dev/null 2>&1 || die "Termux pkg command not found."
  info "Upgrading Docker packages on Termux..."
  pkg update -y
  pkg upgrade -y docker docker-compose || pkg upgrade -y
}

ensure_docker_command() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi
  if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
    die "Docker CLI is not installed. Remove --runner-no-install to allow guided install."
  fi
  if ask_yes_no "Docker CLI is missing. Install docker + openssh packages now?" 1; then
    install_termux_packages
    return
  fi
  die "Docker CLI is required."
}

configure_remote_docker_host() {
  local remote_host=''

  if ! ask_yes_no "Configure DOCKER_HOST for a remote Docker daemon now?" 1; then
    return 1
  fi

  read -r -p "Enter DOCKER_HOST (e.g., ssh://user@host or tcp://127.0.0.1:2375): " remote_host || true
  [[ -n "$remote_host" ]] || return 1

  export DOCKER_HOST="$remote_host"
  info "DOCKER_HOST set for this session: $DOCKER_HOST"

  if ask_yes_no "Persist DOCKER_HOST in ~/.bashrc?" 0; then
    if [[ -f "$HOME/.bashrc" ]] && grep -q '^export DOCKER_HOST=' "$HOME/.bashrc"; then
      sed -i "s|^export DOCKER_HOST=.*|export DOCKER_HOST=\"${remote_host}\"|" "$HOME/.bashrc"
    else
      printf '\nexport DOCKER_HOST="%s"\n' "$remote_host" >> "$HOME/.bashrc"
    fi
    info "Saved DOCKER_HOST in ~/.bashrc"
  fi

  return 0
}

wait_for_docker() {
  local attempts="${1:-45}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if docker_cmd info >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

auto_select_context() {
  [[ -n "$RUNNER_CONTEXT" ]] && return 1
  command -v docker >/dev/null 2>&1 || return 1

  local contexts=()
  local ctx=""
  mapfile -t contexts < <(docker context ls --format '{{.Name}}' 2>/dev/null || true)
  for ctx in "${contexts[@]}"; do
    [[ -n "$ctx" ]] || continue
    [[ "$ctx" == "default" ]] && continue
    if docker --context "$ctx" info >/dev/null 2>&1; then
      RUNNER_CONTEXT="$ctx"
      info "Using reachable Docker context: $RUNNER_CONTEXT"
      return 0
    fi
  done
  return 1
}

show_contexts() {
  command -v docker >/dev/null 2>&1 || die "Docker command is not available."
  info "Available Docker contexts:"
  docker context ls
}

ensure_docker_connection() {
  if docker_cmd info >/dev/null 2>&1; then
    return
  fi

  if auto_select_context; then
    return
  fi

  warn "Docker daemon is not reachable."

  if command -v dockerd >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
    warn "Attempting to start local dockerd (root mode)."
    nohup dockerd >/tmp/dockerd-termux.log 2>&1 &
    if wait_for_docker 30; then
      return
    fi
  fi

  warn "Termux commonly uses Docker CLI against a remote daemon."
  if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
    die "Set DOCKER_HOST to a reachable daemon and rerun."
  fi
  if configure_remote_docker_host && wait_for_docker 20; then
    return
  fi

  die "Unable to connect to Docker daemon. Configure a working DOCKER_HOST and rerun."
}

detect_compose_variant() {
  if docker_cmd compose version >/dev/null 2>&1; then
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
    install_compose_termux
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
    local cmd=(docker)
    if [[ -n "$RUNNER_CONTEXT" ]]; then
      cmd+=(--context "$RUNNER_CONTEXT")
    fi
    cmd+=(compose -f "$COMPOSE_FILE")
    if [[ -n "$profile" ]]; then
      cmd+=(--profile "$profile")
    fi
    cmd+=("$action" "$@")
    (cd "$REPO_ROOT" && "${cmd[@]}")
    return
  fi

  (
    if [[ -n "$profile" ]]; then
      export COMPOSE_PROFILES="$profile"
    else
      unset COMPOSE_PROFILES
    fi
    if [[ -n "$RUNNER_CONTEXT" ]]; then
      export DOCKER_CONTEXT="$RUNNER_CONTEXT"
    fi
    cd "$REPO_ROOT"
    docker-compose -f "$COMPOSE_FILE" "$action" "$@"
  )
}

compose_exec() {
  compose_exec_with_profile "$RUNNER_PROFILE" "$@"
}

ensure_output_dirs() {
  mkdir -p \
    "${REPO_ROOT}/output/json" \
    "${REPO_ROOT}/output/html" \
    "${REPO_ROOT}/output/cli" \
    "${REPO_ROOT}/output/csv" \
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
  if [[ -n "${DOCKER_HOST:-}" ]]; then
    warn "DOCKER_HOST is set to '$DOCKER_HOST'. Remote daemon shutdown is not automated."
    return
  fi
  if command -v pkill >/dev/null 2>&1 && pgrep -x dockerd >/dev/null 2>&1; then
    if pkill -x dockerd >/dev/null 2>&1; then
      info "Local dockerd process stopped."
    else
      warn "Failed to stop local dockerd process."
    fi
    return
  fi
  info "No local dockerd process detected."
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
  if [[ "$RUNNER_UPGRADE" -eq 1 ]]; then
    RUNNER_BUILD=1
    RUNNER_PULL=1
    RUNNER_NO_CACHE=1
  fi

  if [[ "$RUNNER_PULL" -eq 1 && "$RUNNER_BUILD" -eq 0 ]]; then
    RUNNER_BUILD=1
  fi

  if [[ "$RUNNER_BUILD" -eq 1 ]]; then
    info "Building image for service: $RUNNER_SERVICE"
    local build_args=(build)
    if [[ "$RUNNER_PULL" -eq 1 ]]; then
      build_args+=(--pull)
    fi
    if [[ "$RUNNER_NO_CACHE" -eq 1 ]]; then
      build_args+=(--no-cache)
    fi
    if [[ -n "$RUNNER_PYTHON_VERSION" ]]; then
      build_args+=(--build-arg "PYTHON_VERSION=${RUNNER_PYTHON_VERSION}")
    fi
    build_args+=("$RUNNER_SERVICE")
    compose_exec "${build_args[@]}"
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

  if [[ "$RUNNER_DIAGNOSE" -eq 1 ]]; then
    diagnose_runner
    return
  fi

  if [[ "$RUNNER_SHOW_CONTEXTS" -eq 1 ]]; then
    command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install Docker to list contexts."
    show_contexts
    return
  fi

  check_compose_file
  if [[ "$RUNNER_STOP" -eq 1 || "$RUNNER_STOP_DOCKER" -eq 1 ]]; then
    perform_shutdown
    return
  fi
  ensure_termux_context
  check_resources
  ensure_docker_command
  if [[ "$RUNNER_UPGRADE_HOST" -eq 1 ]]; then
    upgrade_docker_host_termux
  fi
  ensure_docker_connection
  ensure_compose_available
  ensure_output_dirs
  run_silica
}

main "$@"
