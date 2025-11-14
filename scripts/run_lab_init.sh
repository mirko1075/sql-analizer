#!/usr/bin/env bash
# Run any lab DB initialization scripts found in the repository (recursive search)
# Supports shell scripts and .sql files. Uses psql when available or docker exec fallback.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/run/logs"
mkdir -p "$LOG_DIR"
LAB_LOG="$LOG_DIR/lab-db-init.log"

NONINTERACTIVE=0
if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
  NONINTERACTIVE=1
fi

echo "Searching repository for lab DB init scripts and SQL files..." | tee -a "$LAB_LOG"

# Find candidate scripts (recursive). Avoid node_modules and .git
mapfile -t found < <(find "$ROOT_DIR" -type f \( -iname '*init*.sh' -o -iname '*init*_db*.sh' -o -iname 'init_db.sh' -o -iname '*create*db*.sh' -o -iname '*.sql' \) -not -path '*/node_modules/*' -not -path '*/.git/*' | sort)

if [[ ${#found[@]} -eq 0 ]]; then
  echo "No lab DB init scripts or SQL files found. Searched repo recursively." | tee -a "$LAB_LOG"
  exit 0
fi

echo "Found candidate init files:" | tee -a "$LAB_LOG"
for f in "${found[@]}"; do
  echo " - $f" | tee -a "$LAB_LOG"
done

if [[ $NONINTERACTIVE -eq 0 ]]; then
  read -p "Run lab DB initialization now? This may execute heavy SQL (y/N): " yn
  case "$yn" in
    [Yy]*) ;;
    *) echo "Skipping lab DB init." | tee -a "$LAB_LOG"; exit 0 ;;
  esac
fi

echo "Starting lab DB init — output -> $LAB_LOG" | tee -a "$LAB_LOG"

# helper: run SQL file via psql or docker exec
run_sql_file() {
  local sqlfile="$1"
  echo "Applying SQL file: $sqlfile" | tee -a "$LAB_LOG"
  if command -v psql >/dev/null 2>&1; then
    PGPASSWORD=${PGPASSWORD:-ai_core} psql -h localhost -p 5440 -U ai_core -d ai_core -f "$sqlfile" >> "$LAB_LOG" 2>&1
    return $?
  fi
  if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^local-postgres-dev$'; then
    docker cp "$sqlfile" local-postgres-dev:/tmp/$(basename "$sqlfile")
    docker exec local-postgres-dev bash -lc "PGPASSWORD=ai_core psql -U ai_core -d ai_core -f /tmp/$(basename "$sqlfile")" >> "$LAB_LOG" 2>&1
    return $?
  fi
  echo "No psql or docker postgres available to apply $sqlfile" | tee -a "$LAB_LOG"
  return 2
}

for f in "${found[@]}"; do
  echo "=== Processing $f ===" | tee -a "$LAB_LOG"
  case "${f##*.}" in
    sh)
      if [[ -x "$f" ]]; then
        "$f" >> "$LAB_LOG" 2>&1
      else
        bash "$f" >> "$LAB_LOG" 2>&1
      fi
      rc=$?
      ;;
    bash)
      bash "$f" >> "$LAB_LOG" 2>&1
      rc=$?
      ;;
    sql)
      run_sql_file "$f"
      rc=$?
      ;;
    *)
      # try executing as shell first, otherwise skip
      if [[ -x "$f" ]]; then
        "$f" >> "$LAB_LOG" 2>&1
        rc=$?
      else
        echo "Skipping unknown file type: $f" | tee -a "$LAB_LOG"
        rc=0
      fi
      ;;
  esac

  if [[ $rc -ne 0 ]]; then
    echo "Initialization step $f failed with exit code $rc. See $LAB_LOG" | tee -a "$LAB_LOG" >&2
    exit $rc
  fi
  echo "=== Completed $f (rc=$rc) ===" | tee -a "$LAB_LOG"
done

echo "Lab DB initialization completed successfully." | tee -a "$LAB_LOG"
exit 0
