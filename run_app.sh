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
  echo "Python virtualenv nao encontrado (.venv/bin/python, venv/bin/python ou backend/venv/bin/python)."
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

BACKEND_PORT_EXPLICIT=false
FRONTEND_PORT_EXPLICIT=false
[[ -n "${BACKEND_PORT+x}" ]] && BACKEND_PORT_EXPLICIT=true
[[ -n "${FRONTEND_PORT+x}" ]] && FRONTEND_PORT_EXPLICIT=true

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export PYTHONPATH="${PYTHONPATH:-$ROOT_DIR/backend}"

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"; then
      return 0
    fi
  elif command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
  else
    if "$PYTHON_BIN" - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
try:
    s.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
raise SystemExit(0)
PY
    then
      return 1
    fi
    return 0
  fi
  return 1
}

resolve_free_port() {
  local requested_port="$1"
  local label="$2"
  local explicit_override="$3"
  local candidate="$requested_port"

  if [[ "$explicit_override" == "true" ]]; then
    if port_in_use "$candidate"; then
      echo "Porta do ${label} (${candidate}) ja esta em uso."
      echo "Escolha outra porta para ${label^^}_PORT ou finalize o processo atual."
      exit 1
    fi
    echo "$candidate"
    return 0
  fi

  if ! port_in_use "$candidate"; then
    echo "$candidate"
    return 0
  fi

  while port_in_use "$candidate"; do
    candidate=$((candidate + 1))
  done

  echo "Porta padrao do ${label} (${requested_port}) ocupada. Usando ${candidate}." >&2
  echo "$candidate"
}

# Use local SQLite by default so run_app works without PostgreSQL.
if [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="sqlite:///./tmp/local_run.db"
  echo "DATABASE_URL nao definido. Usando SQLite local em ./tmp/local_run.db"
fi

mkdir -p "$ROOT_DIR/tmp"

init_schema() {
  "$PYTHON_BIN" - <<'PY'
from backend.database.connection import create_tables

create_tables()
print("Schema do banco inicializado com sucesso.")
PY
}

echo "Inicializando schema do banco..."
if ! init_schema; then
  if [[ "${RUN_APP_STRICT_DB:-false}" == "true" ]]; then
    echo "Falha ao inicializar banco com DATABASE_URL atual e RUN_APP_STRICT_DB=true."
    exit 1
  fi
  echo "Falha ao inicializar banco atual. Tentando fallback para SQLite local..."
  export DATABASE_URL="sqlite:///./tmp/local_run.db"
  init_schema
fi

BACKEND_PORT="$(resolve_free_port "$BACKEND_PORT" "backend" "$BACKEND_PORT_EXPLICIT")"
FRONTEND_PORT="$(resolve_free_port "$FRONTEND_PORT" "frontend" "$FRONTEND_PORT_EXPLICIT")"
export REACT_APP_API_URL="${REACT_APP_API_URL:-http://127.0.0.1:${BACKEND_PORT}}"

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

sleep 1
if ! kill -0 "$BACK_PID" 2>/dev/null; then
  echo "Backend encerrou ao iniciar. Verifique logs acima."
  exit 1
fi

echo "Iniciando frontend em http://127.0.0.1:${FRONTEND_PORT}"
echo "Frontend apontando para API em ${REACT_APP_API_URL}"
BROWSER=none PORT="$FRONTEND_PORT" npm --prefix frontend start &
FRONT_PID=$!

echo "Aplicacao iniciada. Pressione Ctrl+C para parar."
wait
