#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

usage() {
  cat <<EOF
Usage: devctl.sh <command>

Commands:
  setup                Prepare environment (venv, install deps) and optionally init lab DB
  start-local          Start backend and services locally (no Docker)
  start-all            Start backend, services and frontend together (no LabDB init)
  start-all-with-lab   Start stack and run LabDB init (prompt or --yes)
  stop-local           Stop local processes started by scripts
  lab-init             Run lab DB initialization scripts
  stress-db            Run heavy DB queries (stress test) - use with caution
  docker-up            Start docker-compose stacks
  docker-down          Stop docker-compose stacks
  logs                 Tail backend log
  status               Show docker and local pid status
  help                 Show this help

Examples:
  ./scripts/devctl.sh start-all
  ./scripts/devctl.sh start-all-with-lab --yes
  ./scripts/devctl.sh stress-db
EOF
}

# simple helper to wait for a TCP port
wait_for_port() {
  local host=$1 port=$2 timeout=${3:-20}
  for i in $(seq 1 $timeout); do
    if nc -z "$host" "$port" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# frontend smoke test
smoke_frontend() {
  local url=${1:-http://localhost:5173}
  for i in {1..15}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "Frontend responding at $url"
      return 0
    fi
    sleep 1
  done
  echo "Frontend did not respond at $url" >&2
  return 1
}

if [ "$#" -ge 1 ]; then
  cmd="$1"
  shift
  case "$cmd" in
    setup)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    start-local)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    start-all)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      bash "$SCRIPTS_DIR/start-frontend-local.sh" || true
      # wait for backend (8000) and frontend (5173) then smoke-test
      echo "Waiting for backend on port 8000..."
      if wait_for_port localhost 8000 20; then
        echo "Backend is up"
      else
        echo "Backend failed to start within timeout" >&2
      fi
      echo "Waiting for frontend on port 5173..."
      if wait_for_port localhost 5173 20; then
        echo "Frontend port open; running smoke test..."
        smoke_frontend || echo "Frontend smoke test failed" >&2
      else
        echo "Frontend port not open within timeout" >&2
      fi
      exit 0
      ;;
    start-all-with-lab)
      # Accept --yes to pass to lab-init
      LAB_YES=0
      if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
        LAB_YES=1
      fi
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      if [[ $LAB_YES -eq 1 ]]; then
        bash "$SCRIPTS_DIR/run_lab_init.sh" --yes || true
      else
        bash "$SCRIPTS_DIR/run_lab_init.sh" || true
      fi
      # quick schema validation: check presence of expected table(s)
      echo "Validating DB schema (simple checks)..."
      if command -v psql >/dev/null 2>&1; then
        PGPASSWORD=${PGPASSWORD:-ai_core} psql -h localhost -p 5440 -U ai_core -d ai_core -c "SELECT 1" >/dev/null 2>&1 && echo "DB reachable" || echo "DB check failed"
      else
        echo "psql not available; skipping detailed DB validation"
      fi
      # start frontend and run health checks
      bash "$SCRIPTS_DIR/start-frontend-local.sh" || true
      echo "Waiting for backend on port 8000..."
      if wait_for_port localhost 8000 20; then
        echo "Backend is up"
      else
        echo "Backend failed to start within timeout" >&2
      fi
      echo "Waiting for frontend on port 5173..."
      if wait_for_port localhost 5173 20; then
        echo "Frontend port open; running smoke test..."
        smoke_frontend || echo "Frontend smoke test failed" >&2
      else
        echo "Frontend port not open within timeout" >&2
      fi
      exit 0
      ;;
    stop-local)
      bash "$SCRIPTS_DIR/stop-local.sh" --local "$@"
      exit 0
      ;;
    lab-init)
      bash "$SCRIPTS_DIR/run_lab_init.sh" "$@"
      exit 0
      ;;
    stress-db)
      bash "$SCRIPTS_DIR/stress-db.sh" "$@"
      exit 0
      ;;
    docker-up)
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d "$@"
      exit 0
      ;;
    docker-down)
      docker compose -f "$ROOT_DIR/docker-compose.yml" down "$@"
      exit 0
      ;;
    logs)
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      exit 0
      ;;
    status)
      echo "Docker containers:"
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      echo
      echo "Local PIDs (run/*.pid):"
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      exit 0
      ;;
    help|--help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
fi

# Interactive menu
echo "Developer Control (devctl)"
PS3="Choose an action: "
options=("setup" "start-docker" "start-local" "start-all" "start-all-with-lab" "stop-docker" "stop-local" "lab-init" "stress-db" "logs" "status" "exit")
select opt in "${options[@]}"; do
  case $opt in
    setup)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      break
      ;;
    "start-docker")
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d
      break
      ;;
    "start-local")
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      break
      ;;
    "start-all")
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      bash "$SCRIPTS_DIR/start-frontend-local.sh"
      break
      ;;
    "start-all-with-lab")
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      bash "$SCRIPTS_DIR/run_lab_init.sh"
      bash "$SCRIPTS_DIR/start-frontend-local.sh"
      break
      ;;
    "stop-docker")
      docker compose -f "$ROOT_DIR/docker-compose.yml" down
      break
      ;;
    "stop-local")
      bash "$SCRIPTS_DIR/stop-local.sh" --local
      break
      ;;
    "lab-init")
      bash "$SCRIPTS_DIR/run_lab_init.sh"
      break
      ;;
    "stress-db")
      bash "$SCRIPTS_DIR/stress-db.sh"
      break
      ;;
    logs)
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      break
      ;;
    status)
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      break
      ;;
    exit)
      echo "Goodbye"
      break
      ;;
    *) echo "Invalid option" ;;
  esac
done
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

usage() {
  cat <<EOF
Usage: devctl.sh <command>

Commands:
  setup        Prepare environment (venv, install deps) and optionally init lab DB
  start-local  Start backend and services locally (no Docker)
  start-all    Start backend, services and frontend together (no LabDB init)
  stop-local   Stop local processes started by scripts
  lab-init     Run lab DB initialization scripts
  stress-db    Run heavy DB queries (stress test) - use with caution
  docker-up    Start docker-compose stacks
  docker-down  Stop docker-compose stacks
  logs         Tail backend logs
  status       Show docker and local pid status
  help         Show this help

Examples:
  ./scripts/devctl.sh setup --lab --yes
  ./scripts/devctl.sh start-local
  ./scripts/devctl.sh stop-local
EOF
}

if [ "$#" -ge 1 ]; then
  cmd="$1"
  shift
  case "$cmd" in
    setup)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    start-local)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    start-all)
      # Start backend+services first
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      # Then start frontend
      bash "$SCRIPTS_DIR/start-frontend-local.sh" || true
      exit 0
      ;;
    stop-local)
      bash "$SCRIPTS_DIR/stop-local.sh" --local "$@"
      exit 0
      ;;
    lab-init)
      bash "$SCRIPTS_DIR/run_lab_init.sh" "$@"
      exit 0
      ;;
    stress-db)
      bash "$SCRIPTS_DIR/stress-db.sh" "$@"
      exit 0
      ;;
    docker-up)
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d "$@"
      exit 0
      ;;
    docker-down)
      docker compose -f "$ROOT_DIR/docker-compose.yml" down "$@"
      exit 0
      ;;
    logs)
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      exit 0
      ;;
    status)
      echo "Docker containers:"
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      echo
      echo "Local PIDs (run/*.pid):"
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      exit 0
      ;;
    help|--help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
fi

# Interactive menu
echo "Developer Control (devctl)"
PS3="Choose an action: "
options=("setup" "start-docker" "start-local" "stop-docker" "stop-local" "lab-init" "logs" "status" "exit")
select opt in "${options[@]}"; do
  case $opt in
    setup)
      echo "Running setup-and-run-local (automated local setup + run)..."
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      break
      ;;
    "start-docker")
      echo "Starting docker compose stack..."
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d
      break
      ;;
    "start-local")
      echo "Starting selected local services interactively..."
      bash "$SCRIPTS_DIR/run-batch.sh"
      break
      ;;
    "stop-docker")
      echo "Stopping docker compose stacks..."
      docker compose -f "$ROOT_DIR/docker-compose.yml" down
      break
      ;;
    "stop-local")
      echo "Stopping local processes started by run scripts..."
      bash "$SCRIPTS_DIR/stop-local.sh" --local
      break
      ;;
    "lab-init")
      echo "Running lab DB initialization scripts (interactive)..."
      bash "$SCRIPTS_DIR/run_lab_init.sh"
      break
      ;;
    logs)
      echo "Tailing backend log..."
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      break
      ;;
    status)
      echo "Docker containers:"
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      echo
      echo "Local PIDs (run/*.pid):"
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      break
      ;;
    exit)
      echo "Goodbye"
      break
      ;;
    *) echo "Invalid option. Run devctl and choose one of the menu items." ;;
  esac
done
#!/usr/bin/env bash
# Interactive developer control script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<EOF
Usage: devctl.sh <command>

Commands:
  setup        Prepare environment (venv, install deps) and optionally init lab DB
  start-local  Start backend and services locally (no Docker)
  stop-local   Stop local processes started by scripts
  lab-init     Run lab DB initialization scripts
  docker-up    Start docker-compose stacks
  docker-down  Stop docker-compose stacks
  logs         Tail backend logs
  help         Show this help

Examples:
  ./scripts/devctl.sh setup --lab --yes
  ./scripts/devctl.sh start-local
  ./scripts/devctl.sh stop-local
EOF
}

cmd=${1:-help}
shift || true

case "$cmd" in
  setup)
    "$SCRIPT_DIR/setup-and-run-local.sh" "$@" || true
    ;;
  start-local)
    "$SCRIPT_DIR/setup-and-run-local.sh" "$@" || true
    ;;
  stop-local)
    "$SCRIPT_DIR/stop-local.sh" --local "$@"
    ;;
  lab-init)
    "$SCRIPT_DIR/run_lab_init.sh" "$@"
    ;;
  docker-up)
    docker compose -f "$ROOT_DIR/docker-compose.yml" up -d "$@"
    ;;
  docker-down)
    "$SCRIPT_DIR/stop-local.sh" "$@"
    ;;
  logs)
    tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
#!/usr/bin/env bash
# Central developer control script
# Provides an interactive menu to run common tasks (setup, start, stop, init lab DB, logs)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
LEGACY_DIR="$SCRIPTS_DIR/legacy"

usage() {
  cat <<EOF
devctl - developer control script

Options:
  1) setup    - create venv, install deps, start local DB/redis, start backend+scheduler
  2) start-docker - start full stack via docker-compose
  3) start-local  - start local services (uses legacy setup/run scripts)
  4) stop-docker  - stop docker compose stacks
  5) stop-local   - stop local processes started by scripts
  6) lab-init     - run lab DB init scripts
  7) logs        - tail backend log
  8) status      - show docker ps and run/*.pid
  9) help/exit
EOF
}

echo "Developer Control (devctl)"

PS3="Choose an action: "
options=("setup" "start-docker" "start-local" "stop-docker" "stop-local" "lab-init" "logs" "status" "exit")
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

usage() {
  cat <<EOF
Usage: devctl.sh <command>

Commands:
  setup        Prepare environment (venv, install deps) and optionally init lab DB
  start-local  Start backend and services locally (no Docker)
  stop-local   Stop local processes started by scripts
  lab-init     Run lab DB initialization scripts
  docker-up    Start docker-compose stacks
  docker-down  Stop docker-compose stacks
  logs         Tail backend logs
  status       Show docker and local pid status
  help         Show this help

Examples:
  ./scripts/devctl.sh setup --lab --yes
  ./scripts/devctl.sh start-local
  ./scripts/devctl.sh stop-local
EOF
}

if [ "$#" -ge 1 ]; then
  cmd="$1"
  shift
  case "$cmd" in
    setup)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    start-local)
      bash "$SCRIPTS_DIR/setup-and-run-local.sh" "$@" || true
      exit 0
      ;;
    stop-local)
      bash "$SCRIPTS_DIR/stop-local.sh" --local "$@"
      exit 0
      ;;
    lab-init)
      bash "$SCRIPTS_DIR/run_lab_init.sh" "$@"
      exit 0
      ;;
    docker-up)
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d "$@"
      exit 0
      ;;
    docker-down)
      docker compose -f "$ROOT_DIR/docker-compose.yml" down "$@"
      exit 0
      ;;
    logs)
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      exit 0
      ;;
    status)
      echo "Docker containers:"
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      echo
      echo "Local PIDs (run/*.pid):"
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      exit 0
      ;;
    help|--help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
fi

# Interactive menu
echo "Developer Control (devctl)"
PS3="Choose an action: "
options=("setup" "start-docker" "start-local" "stop-docker" "stop-local" "lab-init" "logs" "status" "exit")
select opt in "${options[@]}"; do
  case $opt in
    setup)
      echo "Running setup-and-run-local (automated local setup + run)..."
      bash "$SCRIPTS_DIR/setup-and-run-local.sh"
      break
      ;;
    "start-docker")
      echo "Starting docker compose stack..."
      docker compose -f "$ROOT_DIR/docker-compose.yml" up -d
      break
      ;;
    "start-local")
      echo "Starting selected local services interactively..."
      bash "$SCRIPTS_DIR/run-batch.sh"
      break
      ;;
    "stop-docker")
      echo "Stopping docker compose stacks..."
      docker compose -f "$ROOT_DIR/docker-compose.yml" down
      break
      ;;
    "stop-local")
      echo "Stopping local processes started by run scripts..."
      bash "$SCRIPTS_DIR/stop-local.sh" --local
      break
      ;;
    "lab-init")
      echo "Running lab DB initialization scripts (interactive)..."
      bash "$SCRIPTS_DIR/run_lab_init.sh"
      break
      ;;
    logs)
      echo "Tailing backend log..."
      tail -n 200 -f "$ROOT_DIR/run/logs/backend.log"
      break
      ;;
    status)
      echo "Docker containers:"
      docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
      echo
      echo "Local PIDs (run/*.pid):"
      ls -la "$ROOT_DIR/run"/*.pid 2>/dev/null || echo "No pidfiles"
      break
      ;;
    exit)
      echo "Goodbye"
      break
      ;;
    *) echo "Invalid option. Run devctl and choose one of the menu items." ;;
  esac
done
