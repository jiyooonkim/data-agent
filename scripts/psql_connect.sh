#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="data-agent-postgres"
DB_NAME="postgres"
DB_USER="data_agent"

if [[ "${1:-}" == "--admin" ]]; then
  DB_USER="postgres"
  shift
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Postgres container is not running: $CONTAINER_NAME" >&2
  exit 1
fi

if [[ -t 0 && -t 1 ]]; then
  exec docker exec -it "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" "$@"
fi

exec docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" "$@"
