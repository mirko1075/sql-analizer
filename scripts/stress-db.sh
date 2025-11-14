#!/usr/bin/env bash
set -euo pipefail

# Run heavy queries against the local Postgres to stress DB (use with caution)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/run"
LOG_DIR="$PID_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

SQL_FILE="$ROOT_DIR/tests/heavy-queries.sql"
STRESS_LOG="$LOG_DIR/stress-db.log"

if [[ ! -f "$SQL_FILE" ]]; then
  echo "No heavy SQL file found at $SQL_FILE" >&2
  exit 1
fi

echo "Starting DB stress run; output -> $STRESS_LOG"
echo "Timestamp: $(date)" > "$STRESS_LOG"

# Try psql against localhost:5440 database ai_core
if command -v psql >/dev/null 2>&1; then
  echo "Running via local psql..." >> "$STRESS_LOG"
  PGPASSWORD=${PGPASSWORD:-ai_core} psql -h localhost -p 5440 -U ai_core -d ai_core -f "$SQL_FILE" >> "$STRESS_LOG" 2>&1 || (
    echo "psql run failed; see $STRESS_LOG" >&2; exit 2
  )
  echo "Stress run complete." >> "$STRESS_LOG"
  exit 0
fi

# Otherwise try docker exec into local-postgres-dev
if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -q '^local-postgres-dev$'; then
    echo "Running via docker exec local-postgres-dev..." >> "$STRESS_LOG"
    docker cp "$SQL_FILE" local-postgres-dev:/tmp/stress.sql
    docker exec local-postgres-dev bash -lc "PGPASSWORD=ai_core psql -U ai_core -d ai_core -f /tmp/stress.sql" >> "$STRESS_LOG" 2>&1 || (
      echo "docker psql run failed; see $STRESS_LOG" >&2; exit 3
    )
    echo "Stress run complete (docker)." >> "$STRESS_LOG"
    exit 0
  fi
fi

echo "No psql found and no local-postgres-dev container running. Cannot run stress tests." >> "$STRESS_LOG"
echo "See $STRESS_LOG for details." >&2
exit 1
