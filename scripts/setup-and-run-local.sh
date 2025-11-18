#!/usr/bin/env bash
# Automated local setup + run for Backend + local Postgres + Redis (best-effort)
# Creates .venv, installs backend deps, fixes data permissions (prompt for sudo),
# initializes & starts Postgres on port 5440 (if initdb/pg_ctl available) or tries systemctl,
# starts redis-server if available, then starts uvicorn backend and scheduler.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PID_DIR="$ROOT_DIR/run"
LOG_DIR="$PID_DIR/logs"
PGDATA="$ROOT_DIR/data/internal-db-local"

mkdir -p "$PID_DIR" "$LOG_DIR" "$PGDATA"

echo "== Local setup: Backend + Postgres (local) + Redis =="

# 1) Create and activate venv
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "Installing backend requirements..."
pip install --upgrade pip
if [[ -f "$ROOT_DIR/backend/requirements.txt" ]]; then
  pip install -r "$ROOT_DIR/backend/requirements.txt"
else
  echo "No backend/requirements.txt found; ensure dependencies are installed manually." >&2
fi

# 2) Fix permissions for data dirs (if created by Docker)
fix_permissions() {
  for d in data data/redis data/mysql data/internal-db; do
    if [[ -e "$ROOT_DIR/$d" && ! -w "$ROOT_DIR/$d" ]]; then
      echo "Found $d but not writable by current user. Attempting sudo chown to fix..."
      if command -v sudo >/dev/null 2>&1; then
        sudo chown -R "$(id -u):$(id -g)" "$ROOT_DIR/$d" || true
      else
        echo "sudo not available; please run: sudo chown -R \\$(id -u):\\$(id -g) $ROOT_DIR/$d" >&2
      fi
    fi
  done
}

fix_permissions

# 3) Start Postgres local
start_postgres_local() {
  echo "== Starting local Postgres (internal DB) on port 5440 =="
  if command -v pg_ctl >/dev/null 2>&1 && command -v initdb >/dev/null 2>&1; then
    if [[ ! -f "$PGDATA/PG_VERSION" ]]; then
      echo "Initializing Postgres data directory at $PGDATA"
      initdb -D "$PGDATA" --username=ai_core --encoding=UTF8 || true
    fi
    echo "Starting postgres with pg_ctl..."
    pg_ctl -D "$PGDATA" -o "-p 5440" -l "$LOG_DIR/postgres.log" start || true
    # Wait for ready
    for i in {1..10}; do
      if pg_isready -p 5440 >/dev/null 2>&1; then
        echo "Postgres ready on 5440"
        return 0
      fi
      sleep 1
    done
    echo "Postgres did not become ready in time; check $LOG_DIR/postgres.log" >&2
    return 1
  fi

  # Try systemctl-managed postgres
  if systemctl --user is-active --quiet postgresql 2>/dev/null || systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "Starting system Postgres service"
    sudo systemctl start postgresql || true
    for i in {1..10}; do
      if pg_isready >/dev/null 2>&1; then
        echo "System Postgres ready"
        return 0
      fi
      sleep 1
    done
  fi

  echo "No local Postgres toolchain found. You can install PostgreSQL or run the DB in Docker."
  return 2
    echo "No local Postgres toolchain found. Attempting Docker fallback."
    if command -v docker >/dev/null 2>&1; then
      echo "Starting postgres:14 docker container on port 5440"
      docker rm -f local-postgres-dev >/dev/null 2>&1 || true
      docker run --name local-postgres-dev -e POSTGRES_USER=ai_core -e POSTGRES_PASSWORD=ai_core -e POSTGRES_DB=ai_core -p 5440:5432 -v "$PGDATA":/var/lib/postgresql/data -d postgres:14 || true
      for i in {1..15}; do
        if pg_isready -h localhost -p 5440 >/dev/null 2>&1; then
          echo "Docker Postgres ready on 5440"
          return 0
        fi
        sleep 1
      done
      echo "Docker Postgres did not become ready in time; check 'docker logs local-postgres-dev'" >&2
      return 1
    fi

    echo "No Docker available either; please install PostgreSQL or Docker." >&2
    return 2
}

start_postgres_local || echo "Postgres local start returned non-zero"

# 4) Start redis if available
start_redis_local() {
  echo "== Starting local Redis on port 6379 =="
  if command -v redis-server >/dev/null 2>&1; then
    REDIS_DIR="$ROOT_DIR/data/redis"
    mkdir -p "$REDIS_DIR"
    redis-server --dir "$REDIS_DIR" --port 6379 > "$LOG_DIR/redis.log" 2>&1 &
    echo $! > "$PID_DIR/redis.pid"
    # Wait a bit
    sleep 1
    if nc -z localhost 6379 >/dev/null 2>&1; then
      echo "Redis started on 6379"
      return 0
    fi
    echo "Redis did not start cleanly; check $LOG_DIR/redis.log" >&2
    return 1
  fi
  echo "redis-server not found; skipping local redis (you can use Docker mode or install redis)."
  return 2
    echo "redis-server not found; attempting Docker fallback."
    if command -v docker >/dev/null 2>&1; then
      docker rm -f local-redis-dev >/dev/null 2>&1 || true
      docker run --name local-redis-dev -p 6379:6379 -v "$ROOT_DIR/data/redis":/data -d redis:7-alpine || true
      for i in {1..10}; do
        if nc -z localhost 6379 >/dev/null 2>&1; then
          echo "Docker Redis ready on 6379"
          return 0
        fi
        sleep 1
      done
      echo "Docker Redis did not become ready in time; check 'docker logs local-redis-dev'" >&2
      return 1
    fi

    echo "No Docker available either; please install redis or Docker." >&2
    return 2
}

start_redis_local || true

# 5) Start backend (uvicorn) with PYTHONPATH and limited reload-dir to avoid scanning data/
echo "== Starting backend (uvicorn) =="
export PYTHONPATH="$ROOT_DIR"
if command -v uvicorn >/dev/null 2>&1; then
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$PID_DIR/backend.pid"
else
  echo "uvicorn not installed in venv; try 'pip install uvicorn[standard]'" >&2
fi

# 6) Start scheduler
echo "== Starting scheduler (collectors) =="
nohup python3 backend/services/scheduler.py > "$LOG_DIR/scheduler.log" 2>&1 &
echo $! > "$PID_DIR/scheduler.pid"

echo "== Setup complete =="
echo "PIDs in $PID_DIR; logs in $LOG_DIR"
echo "Check backend logs: tail -f $LOG_DIR/backend.log"
