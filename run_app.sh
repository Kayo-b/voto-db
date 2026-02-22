#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -f "$ROOT_DIR/backend/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
else
  echo "Python virtualenv nao encontrado (.venv/bin/python ou backend/venv/bin/python)."
  exit 1
fi

if [[ ! -f "$ROOT_DIR/frontend/package.json" ]]; then
  echo "Frontend nao encontrado em frontend/."
  exit 1
fi

if [[ ! -d "$ROOT_DIR/backend" ]]; then
  echo "Backend nao encontrado em backend/."
  exit 1
fi

if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/backend/.env"
  set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export PYTHONPATH="${PYTHONPATH:-$ROOT_DIR/backend}"

cleanup() {
  echo ""
  echo "Encerrando frontend e backend..."
  [[ -n "${FRONT_PID:-}" ]] && kill "$FRONT_PID" 2>/dev/null || true
  [[ -n "${BACK_PID:-}" ]] && kill "$BACK_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Iniciando backend em http://127.0.0.1:${BACKEND_PORT}"
"$PYTHON_BIN" -m uvicorn backend.main_v2:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACK_PID=$!

echo "Iniciando frontend em http://127.0.0.1:${FRONTEND_PORT}"
PORT="$FRONTEND_PORT" npm --prefix frontend start &
FRONT_PID=$!

echo "Aplicacao iniciada. Pressione Ctrl+C para parar."
wait
