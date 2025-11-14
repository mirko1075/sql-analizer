#!/usr/bin/env bash
set -euo pipefail

# Start the frontend (Vite) in dev mode, write logs and pidfile in run/
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/run"
LOG_DIR="$PID_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

FRONTEND_DIR="$ROOT_DIR/frontend"
FRONTEND_LOG="$LOG_DIR/frontend.log"
FRONTEND_PID="$PID_DIR/frontend.pid"

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "No frontend directory found at $FRONTEND_DIR" >&2
  exit 1
fi

pushd "$FRONTEND_DIR" >/dev/null

# Ensure node deps are installed (best-effort)
if [[ ! -d "node_modules" ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "Installing frontend dependencies (npm install)..."
    npm install --silent || echo "npm install failed; ensure dependencies installed manually"
  else
    echo "npm not found; please install Node and run 'npm install' in $FRONTEND_DIR" >&2
  fi
fi

echo "Starting frontend dev server (vite) -> $FRONTEND_LOG"
nohup npm run dev >"$FRONTEND_LOG" 2>&1 &
echo $! > "$FRONTEND_PID"
popd >/dev/null
echo "Frontend started (pid $(cat $FRONTEND_PID)); logs: $FRONTEND_LOG"
