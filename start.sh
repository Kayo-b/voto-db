#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/backend/.env"
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL nao definido. Tentando iniciar PostgreSQL local..."
  if ./postgres.sh start; then
    if ./postgres.sh verify-schema >/dev/null 2>&1; then
      export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/votodb"
      echo "Usando PostgreSQL local em ${DATABASE_URL}"
    else
      echo "Schema PostgreSQL local esta desatualizado para o backend atual. Usando launcher padrao."
    fi
  else
    echo "Nao foi possivel iniciar PostgreSQL. Continuando com o launcher padrao."
  fi
fi

exec "$ROOT_DIR/run_app.sh" "$@"
