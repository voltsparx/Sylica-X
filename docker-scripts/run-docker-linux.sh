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
silica_x_ARGS=()
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
  ./${SCRIPT_NAME} [runner-options] [silica_x-args...]
  ./${SCRIPT_NAME} [runner-options] -- [silica_x-args...]

Runner options (reserved for this script):
  --runner-help              Show this help message.
  --runner-build             Build service image before running.
  --runner-pull              Build with --pull to refresh base layers.
  --runner-no-cache          Build with --no-cache.
  --runner-upgrade           Upgrade container runtime (implies --runner-build --runner-pull --runner-no-cache).
  --runner-upgrade-host      Upgrade host Docker engine/components.
  --runner-stop              Stop/remove silica_x containers.
  --runner-stop-docker       Stop/remove silica_x containers and stop Docker daemon.
  --runner-show-contexts     List Docker contexts and exit.
  --runner-diagnose          Run non-interactive environment diagnostics and exit.
  --runner-context <name>    Use a specific Docker context.
  --runner-use-tor-service   Force Tor service container (silica-x-tor).
  --runner-service <name>    Override compose service (default: silica-x).
  --runner-profile <name>    Override compose profile (default: auto).
  --runner-python-version <v>  Override Docker build arg PYTHON_VERSION (e.g., 3.13).
  --runner-no-install        Never install missing Docker components.
  --runner-prompt            Force silica_x prompt mode (ignore silica_x-args).

silica_x args:
  Any argument not prefixed with --runner- is passed to silica-x.
  If no silica_x args are passed, silica-x starts in prompt mode.
  If silica_x args include --tor (without --no-tor), this script auto-selects
  service 'silica-x-tor' and profile 'tor' unless you override it.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} profile alice --html
  ./${SCRIPT_NAME} --runner-stop
  ./${SCRIPT_NAME} --runner-stop-docker
  ./${SCRIPT_NAME} --runner-upgrade-host --runner-upgrade
  ./${SCRIPT_NAME} --runner-show-contexts
  ./${SCRIPT_NAME} --runner-diagnose
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

format_kb_to_gb() {
  local kb="$1"
  awk -v value="$kb" 'BEGIN { printf "%.2f", value / 1048576 }'
}

run_privileged() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi
  die "Root privileges are required for: $*"
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
          silica_x_ARGS+=("$1")
          shift
        done
        break
        ;;
      *)
        silica_x_ARGS+=("$1")
        ;;
    esac
    shift
  done
}

configure_mode_and_service() {
  if [[ "$RUNNER_PROMPT" -eq 1 ]]; then
    silica_x_ARGS=()
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
    for arg in "${silica_x_ARGS[@]}"; do
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

  diag_line() {
    printf '  %-24s %s\n' "$1" "$2"
  }

  info "Runner diagnostics"
  printf '%s\n' '----------------------------------------'
  diag_line "script" "$SCRIPT_NAME"
  diag_line "repo_root" "$REPO_ROOT"
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

install_docker_linux() {
  info "Installing Docker Engine and Compose..."
  if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    if ! run_privileged apt-get install -y docker.io docker-compose-plugin; then
      run_privileged apt-get install -y docker.io docker-compose
    fi
  elif command -v dnf >/dev/null 2>&1; then
    if ! run_privileged dnf install -y docker docker-compose-plugin; then
      run_privileged dnf install -y docker docker-compose
    fi
  elif command -v yum >/dev/null 2>&1; then
    if ! run_privileged yum install -y docker docker-compose-plugin; then
      run_privileged yum install -y docker docker-compose
    fi
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Sy --noconfirm docker docker-compose
  elif command -v zypper >/dev/null 2>&1; then
    run_privileged zypper --non-interactive install docker docker-compose
  else
    die "Unsupported Linux package manager. Install Docker manually and rerun."
  fi
}

install_compose_linux() {
  info "Installing Docker Compose..."
  if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    if ! run_privileged apt-get install -y docker-compose-plugin; then
      run_privileged apt-get install -y docker-compose
    fi
  elif command -v dnf >/dev/null 2>&1; then
    if ! run_privileged dnf install -y docker-compose-plugin; then
      run_privileged dnf install -y docker-compose
    fi
  elif command -v yum >/dev/null 2>&1; then
    if ! run_privileged yum install -y docker-compose-plugin; then
      run_privileged yum install -y docker-compose
    fi
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Sy --noconfirm docker-compose
  elif command -v zypper >/dev/null 2>&1; then
    run_privileged zypper --non-interactive install docker-compose
  else
    die "Unsupported Linux package manager. Install Docker Compose manually and rerun."
  fi
}

upgrade_docker_host_linux() {
  info "Upgrading Docker components on host..."
  if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    run_privileged apt-get install -y --only-upgrade docker.io docker-compose-plugin docker-compose || true
  elif command -v dnf >/dev/null 2>&1; then
    run_privileged dnf upgrade -y docker docker-compose-plugin docker-compose || true
  elif command -v yum >/dev/null 2>&1; then
    run_privileged yum update -y docker docker-compose-plugin docker-compose || true
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Syu --noconfirm docker docker-compose || true
  elif command -v zypper >/dev/null 2>&1; then
    run_privileged zypper --non-interactive update docker docker-compose || true
  else
    warn "Unsupported package manager for auto-upgrade. Upgrade Docker manually."
  fi
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

ensure_docker_command() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi
  if [[ "$RUNNER_NO_INSTALL" -eq 1 ]]; then
    die "Docker is not installed. Remove --runner-no-install to allow guided install."
  fi
  if ask_yes_no "Docker is not installed. Install it now?" 1; then
    install_docker_linux
    return
  fi
  die "Docker is required."
}

start_docker_daemon() {
  if docker_cmd info >/dev/null 2>&1; then
    return
  fi

  if auto_select_context; then
    return
  fi

  warn "Docker daemon is not reachable. Attempting to start it."
  if command -v systemctl >/dev/null 2>&1; then
    run_privileged systemctl start docker || true
    run_privileged systemctl enable docker >/dev/null 2>&1 || true
  elif command -v service >/dev/null 2>&1; then
    run_privileged service docker start || true
  fi

  if wait_for_docker 45; then
    return
  fi

  local target_user="${SUDO_USER:-${USER:-}}"
  if [[ -n "$target_user" ]] && ! id -nG "$target_user" | grep -qw docker; then
    warn "User '$target_user' is not in the docker group."
    if [[ "$RUNNER_NO_INSTALL" -eq 0 ]] && ask_yes_no "Add '$target_user' to docker group now? (re-login required)" 0; then
      run_privileged usermod -aG docker "$target_user" || true
      warn "Group updated. Log out and back in, then rerun."
    fi
  fi

  die "Docker daemon is still unavailable. Start Docker manually and rerun."
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
    install_compose_linux
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

stop_silica_x_compose_stack() {
  if ! command -v docker >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    warn "Docker CLI is not available. Nothing to stop."
    return
  fi

  if ! detect_compose_variant; then
    warn "Docker Compose command is unavailable. Skipping compose shutdown."
    return
  fi

  info "Stopping silica_x compose services..."
  if ! compose_exec_with_profile "" down --remove-orphans; then
    warn "Compose down reported an issue for default profile."
  fi
  if ! compose_exec_with_profile "tor" down --remove-orphans; then
    warn "Compose down reported an issue for tor profile."
  fi
}

stop_docker_host() {
  info "Stopping Docker daemon..."
  if [[ "${EUID:-$(id -u)}" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
    warn "Cannot stop Docker daemon automatically without root/sudo."
    return
  fi
  if command -v systemctl >/dev/null 2>&1; then
    if run_privileged systemctl stop docker; then
      info "Docker daemon stopped."
    else
      warn "Failed to stop Docker via systemctl."
    fi
    return
  fi
  if command -v service >/dev/null 2>&1; then
    if run_privileged service docker stop; then
      info "Docker daemon stopped."
    else
      warn "Failed to stop Docker via service."
    fi
    return
  fi
  warn "No supported service manager found. Stop Docker manually if needed."
}

perform_shutdown() {
  if [[ "${#silica_x_ARGS[@]}" -gt 0 ]]; then
    warn "Ignoring forwarded silica_x args during shutdown."
  fi

  stop_silica_x_compose_stack

  if [[ "$RUNNER_STOP_DOCKER" -eq 1 ]]; then
    stop_docker_host
  else
    info "silica_x containers stopped. Docker daemon left running."
  fi
}

run_silica_x() {
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

  if [[ "${#silica_x_ARGS[@]}" -eq 0 ]]; then
    info "Starting Silica-X in prompt mode via Docker service: $RUNNER_SERVICE"
    compose_exec run --rm "$RUNNER_SERVICE"
    return
  fi

  info "Running Silica-X via Docker service: $RUNNER_SERVICE"
  compose_exec run --rm "$RUNNER_SERVICE" "${silica_x_ARGS[@]}"
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
  check_resources
  ensure_docker_command
  if [[ "$RUNNER_UPGRADE_HOST" -eq 1 ]]; then
    upgrade_docker_host_linux
  fi
  start_docker_daemon
  ensure_compose_available
  ensure_output_dirs
  run_silica_x
}

main "$@"
