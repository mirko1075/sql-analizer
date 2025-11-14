#!/usr/bin/env bash
# Stop and remove containers for the development stack, or stop local processes started by run-batch.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  echo "Usage: $0 [--lab-db] [--local] [--force]"
  echo "  --lab-db   Include lab-database compose files (for Docker mode)"
  echo "  --local    Stop local processes started by scripts/run-batch.sh (reads run/*.pid)"
  echo "  --force    When used with --local, force kill PIDs even if cwd check fails (use with care)"
  exit 1
}

LOCAL_MODE=0
FORCE=0
LAB_DB=0

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --local) LOCAL_MODE=1; shift ;;
    --force) FORCE=1; shift ;;
    --lab-db) LAB_DB=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if [[ $LOCAL_MODE -eq 0 ]]; then
  # Docker compose shutdown (existing behavior)
  COMPOSE_FILES=("$ROOT_DIR/docker-compose.yml")
  if [[ $LAB_DB -eq 1 ]]; then
    COMPOSE_FILES+=("$ROOT_DIR/lab-database/docker-compose.yml")
  fi

  COMPOSE_CMD=(docker compose)
  for f in "${COMPOSE_FILES[@]}"; do
    COMPOSE_CMD+=( -f "$f" )
  done

  echo "Bringing down services defined in: ${COMPOSE_FILES[*]}"
  "${COMPOSE_CMD[@]}" down --volumes --remove-orphans

  echo "Containers stopped and removed. Volumes removed for the stacks above."
  exit 0
fi

# Local stop mode: read run/*.pid and terminate processes safely
PID_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/run/logs"

if [[ ! -d "$PID_DIR" ]]; then
  echo "No run directory found at $PID_DIR — nothing to stop." >&2
  exit 0
fi

echo "Stopping local services using PID files in: $PID_DIR"

shopt -s nullglob
for pidfile in "$PID_DIR"/*.pid; do
  name=$(basename "$pidfile" .pid)
  pid=$(cat "$pidfile" 2>/dev/null || true)

  if [[ -z "$pid" ]]; then
    echo "[skip] $name: empty pid file, removing";
    rm -f "$pidfile"
    continue
  fi

  if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "[skip] $name: pid '$pid' is not numeric, removing pidfile"
    rm -f "$pidfile"
    continue
  fi

  if [[ ! -d "/proc/$pid" ]]; then
    echo "[stale] $name: PID $pid not running, removing pidfile"
    rm -f "$pidfile"
    continue
  fi

  # Safety check: ensure process cwd is inside the repo root
  proc_cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
  if [[ -z "$proc_cwd" ]]; then
    echo "[warn] $name: cannot determine cwd for PID $pid"
  fi

  if [[ "$proc_cwd" != "" && "$proc_cwd" == "$ROOT_DIR"* ]]; then
    echo "[ok] $name: PID $pid seems to belong to this project (cwd: $proc_cwd). Stopping..."
  else
    if [[ $FORCE -eq 1 ]]; then
      echo "[force] $name: PID $pid cwd '$proc_cwd' outside project, but --force given — stopping"
    else
      echo "[skip] $name: PID $pid cwd '$proc_cwd' outside project — skipping (use --force to override)"
      continue
    fi
  fi

  # Attempt graceful termination
  if kill -TERM "$pid" 2>/dev/null; then
    echo "Sent SIGTERM to $pid, waiting up to 5s..."
    for i in {1..5}; do
      if [[ ! -d "/proc/$pid" ]]; then
        break
      fi
      sleep 1
    done
  else
    echo "Failed to send SIGTERM to $pid (might have exited)"
  fi

  # If still running, escalate
  if [[ -d "/proc/$pid" ]]; then
    echo "PID $pid still running — sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
    sleep 1
  fi

  if [[ ! -d "/proc/$pid" ]]; then
    echo "Stopped $name (PID $pid). Removing pidfile."
    rm -f "$pidfile"
  else
    echo "Failed to stop $name (PID $pid). Leaving pidfile for manual inspection."
  fi
done

echo "Local stop complete. Check $LOG_DIR for logs, and run: ps aux | grep -E \"(uvicorn|postgres|mysqld|redis-server|python)\" to find leftovers."

