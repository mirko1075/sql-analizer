#!/usr/bin/env bash
# Run multiple services either via Docker or locally (no Docker)
# Interactive script: asks which mode and which services to start

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/run/logs"

mkdir -p "$RUN_DIR" "$LOG_DIR"

ask_yes_no() {
  local prompt="$1"
  local def=${2:-y}
  local resp
  while true; do
    read -r -p "$prompt [y/n] (default: $def): " resp
    resp=${resp:-$def}
    case "$resp" in
      [Yy]*) return 0 ;; 
      [Nn]*) return 1 ;; 
      *) echo "Please answer y or n." ;; 
    esac
  done
}

echo "Select mode:"
select MODE in "docker" "local"; do
  case $MODE in
    docker) echo "Using Docker mode"; break ;; 
    local) echo "Using LOCAL mode (no Docker)"; break ;; 
    *) echo "Choose 1 or 2" ;; 
  esac
done

SERVICES=("internal-db" "redis" "backend" "scheduler" "mysql-lab" "postgres-lab")
declare -A START

for s in "${SERVICES[@]}"; do
  if ask_yes_no "Start $s?" y; then
    START[$s]=1
  else
    START[$s]=0
  fi
done

if [[ "$MODE" == "docker" ]]; then
  # Build compose command with optional lab db
  COMPOSE_FILES=("$ROOT_DIR/docker-compose.yml")
  if [[ ${START[mysql-lab]} -eq 1 || ${START[postgres-lab]} -eq 1 ]]; then
    COMPOSE_FILES+=("$ROOT_DIR/lab-database/docker-compose.yml")
  fi

  COMPOSE_CMD=(docker compose)
  for f in "${COMPOSE_FILES[@]}"; do
    COMPOSE_CMD+=( -f "$f" )
  done

  echo "Running: ${COMPOSE_CMD[*]} up --build -d"
  "${COMPOSE_CMD[@]}" up --build -d
  echo "Docker compose started. Use '${COMPOSE_CMD[*]} logs -f' to stream logs." 
  exit 0
fi

# Local mode: try to start services using local binaries
echo "Starting selected services locally. Logs will be in $LOG_DIR"

# Helper to start a background command and record pid/log
start_bg() {
  local name="$1"; shift
  local logfile="$LOG_DIR/${name}.log"
  echo "Starting $name -> log: $logfile"
  nohup "$@" > "$logfile" 2>&1 &
  echo $! > "$RUN_DIR/${name}.pid"
}

if [[ ${START[internal-db]} -eq 1 ]]; then
  echo "-- internal Postgres --"
  # Prefer systemctl if available and service exists
  if command -v pg_ctl >/dev/null 2>&1; then
    PGDATA="$ROOT_DIR/data/internal-db-local"
    mkdir -p "$PGDATA"
    if [[ ! -f "$PGDATA/PG_VERSION" ]]; then
      echo "Initializing Postgres data directory at $PGDATA (initdb)..."
      initdb -D "$PGDATA" --username=ai_core --encoding=UTF8 || true
    fi
    # Start postgres on port 5440
    echo "Starting Postgres on port 5440"
    start_bg postgres pg_ctl -D "$PGDATA" -o "-p 5440" -l "$LOG_DIR/postgres.log" start
    sleep 1
  elif systemctl status postgresql >/dev/null 2>&1; then
    echo "Using system postgres service"
    sudo systemctl start postgresql
  else
    echo "No local Postgres tools found (initdb/pg_ctl). Install PostgreSQL or use Docker mode. Skipping internal-db."
  fi
fi

if [[ ${START[redis]} -eq 1 ]]; then
  echo "-- redis --"
  if command -v redis-server >/dev/null 2>&1; then
    REDIS_DIR="$ROOT_DIR/data/redis-local"
    mkdir -p "$REDIS_DIR"
    start_bg redis redis-server --dir "$REDIS_DIR" --port 6379
  else
    echo "redis-server not found. Install redis or run in Docker mode. Skipping redis."
  fi
fi

if [[ ${START[backend]} -eq 1 ]]; then
  echo "-- backend (FastAPI) --"
  # Activate project's venv if present
  if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$ROOT_DIR/.venv/bin/activate"
  elif [[ -f "$ROOT_DIR/venv/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$ROOT_DIR/venv/bin/activate"
  fi

  # Ensure uvicorn is available
  if ! command -v uvicorn >/dev/null 2>&1; then
    echo "uvicorn not found in PATH. Try: pip install -r backend/requirements.txt" 
  else
    start_bg backend uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  fi
fi

if [[ ${START[scheduler]} -eq 1 ]]; then
  echo "-- scheduler / collectors --"
  # Start scheduler which will run the collectors and analyzer
  start_bg scheduler python3 backend/services/scheduler.py
fi

if [[ ${START[mysql-lab]} -eq 1 ]]; then
  echo "-- MySQL lab DB --"
  if command -v mysqld >/dev/null 2>&1; then
    MYSQL_DATADIR="$ROOT_DIR/data/mysql-local"
    mkdir -p "$MYSQL_DATADIR"
    if [[ ! -d "$MYSQL_DATADIR/mysql" && ! -f "$MYSQL_DATADIR/ibdata1" ]]; then
      echo "Initializing MySQL datadir (mysqld --initialize-insecure)"
      mysqld --initialize-insecure --datadir="$MYSQL_DATADIR" || true
    fi
    echo "Starting mysqld on port 3307"
    start_bg mysql-lab mysqld --datadir="$MYSQL_DATADIR" --port=3307
  else
    echo "mysqld not found. Install MySQL server or use Docker mode. Skipping mysql-lab."
  fi
fi

if [[ ${START[postgres-lab]} -eq 1 ]]; then
  echo "-- Postgres lab DB --"
  if command -v pg_ctl >/dev/null 2>&1; then
    PGLAB="$ROOT_DIR/data/pg-lab-local"
    mkdir -p "$PGLAB"
    if [[ ! -f "$PGLAB/PG_VERSION" ]]; then
      echo "Initializing Postgres lab data directory at $PGLAB (initdb)..."
      initdb -D "$PGLAB" || true
    fi
    echo "Starting Postgres lab on port 5433"
    start_bg pg-lab pg_ctl -D "$PGLAB" -o "-p 5433" -l "$LOG_DIR/pg-lab.log" start
  else
    echo "pg_ctl/initdb not found. Use Docker mode for postgres-lab. Skipping."
  fi
fi

echo "Started selected local services. PIDs are in $RUN_DIR/*.pid. Logs are in $LOG_DIR/*.log"
echo "Use 'tail -f $LOG_DIR/backend.log' to follow logs, or './scripts/stop-local.sh' to stop Docker stacks. For local services, kill PIDs from run/*.pid or use the provided stop-local script to stop docker stacks only." 
