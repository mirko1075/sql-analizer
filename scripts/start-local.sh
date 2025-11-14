#!/usr/bin/env bash
# Start the full development stack (internal postgres, redis, backend, frontend)
# Usage: ./scripts/start-local.sh [--lab-db]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILES=(
  "$ROOT_DIR/docker-compose.yml"
)

# Optional lab database compose
if [[ "${1:-}" == "--lab-db" ]]; then
  COMPOSE_FILES+=("$ROOT_DIR/lab-database/docker-compose.yml")
fi

echo "Using compose files: ${COMPOSE_FILES[*]}"

COMPOSE_CMD=(docker compose)

# Build and start
for f in "${COMPOSE_FILES[@]}"; do
  COMPOSE_CMD+=( -f "$f" )
done

echo "Building and starting services..."
"${COMPOSE_CMD[@]}" up --build -d

echo "All done. To view logs:"
echo "  ${COMPOSE_CMD[*]} logs -f"
echo "To stop: ${COMPOSE_CMD[*]} down"
