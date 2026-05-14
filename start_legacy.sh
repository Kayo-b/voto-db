#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -f "$ROOT_DIR/backend/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
elif [[ -f "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  echo "Python virtualenv nao encontrado (.venv/bin/python, backend/venv/bin/python ou venv/bin/python)."
  exit 1
fi

if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/backend/.env"
  set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8001}"

echo "Starting legacy backend only..."
echo "Starting backend.main_v2:app on http://127.0.0.1:${BACKEND_PORT}"
exec "$PYTHON_BIN" -m uvicorn backend.main_v2:app --host 127.0.0.1 --port "$BACKEND_PORT"
