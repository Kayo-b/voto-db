#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CONTAINER_NAME="votodb-postgres"
DEFAULT_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/votodb"

if [[ -f "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -f "$ROOT_DIR/backend/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
elif [[ -f "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  PYTHON_BIN="python3"
fi

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker nao encontrado."
    exit 1
  fi
}

container_exists() {
  docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

container_running() {
  docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

ensure_database_env() {
  export DATABASE_URL="${DATABASE_URL:-$DEFAULT_DATABASE_URL}"
}

verify_schema() {
  docker exec "$CONTAINER_NAME" psql -U postgres -d votodb -At -c "
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_name = 'votacoes'
      AND column_name IN ('api_votacao_id', 'tipo_votacao', 'sigla_orgao', 'aprovacao');
  " | grep -qx '4'
}

case "${1:-}" in
  start)
    require_docker
    echo "Starting PostgreSQL with Docker..."

    if container_exists; then
      if container_running; then
        echo "Container ${CONTAINER_NAME} already running."
      else
        docker start "$CONTAINER_NAME" >/dev/null
      fi
    else
      docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_DB=votodb \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -p 5432:5432 \
        -v votodb_data:/var/lib/postgresql/data \
        postgres:15 >/dev/null
    fi

    echo "Waiting for PostgreSQL to be ready..."
    for _ in $(seq 1 15); do
      if docker exec "$CONTAINER_NAME" pg_isready -U postgres -d votodb >/dev/null 2>&1; then
        echo "PostgreSQL is running!"
        echo "Connection: ${DEFAULT_DATABASE_URL}"
        exit 0
      fi
      sleep 1
    done

    echo "PostgreSQL failed to start"
    exit 1
    ;;

  stop)
    require_docker
    if ! container_exists; then
      echo "Container ${CONTAINER_NAME} does not exist."
      exit 0
    fi
    if ! container_running; then
      echo "PostgreSQL is already stopped."
      exit 0
    fi
    echo "Stopping PostgreSQL..."
    docker stop "$CONTAINER_NAME" >/dev/null
    ;;

  restart)
    require_docker
    if container_exists; then
      echo "Restarting PostgreSQL..."
      docker restart "$CONTAINER_NAME" >/dev/null
    else
      "$0" start
    fi
    ;;

  logs)
    require_docker
    if ! container_exists; then
      echo "Container ${CONTAINER_NAME} does not exist."
      exit 1
    fi
    docker logs "$CONTAINER_NAME"
    ;;

  shell)
    require_docker
    if ! container_running; then
      echo "PostgreSQL is not running."
      exit 1
    fi
    exec docker exec -it "$CONTAINER_NAME" psql -U postgres -d votodb
    ;;

  status)
    require_docker
    if container_running; then
      echo "PostgreSQL is running"
      docker ps --filter "name=^${CONTAINER_NAME}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
      exit 0
    fi

    if container_exists; then
      echo "PostgreSQL container exists but is stopped"
    else
      echo "PostgreSQL container does not exist"
    fi
    exit 1
    ;;

  init)
    require_docker
    if ! container_running; then
      echo "PostgreSQL is not running. Start it first with ./postgres.sh start"
      exit 1
    fi
    ensure_database_env
    echo "Initializing database..."
    "$PYTHON_BIN" init_database.py
    if verify_schema; then
      echo "PostgreSQL schema looks compatible with the current backend."
      exit 0
    fi
    echo "PostgreSQL schema is older than the current backend models."
    echo "init_database.py created missing tables but did not upgrade existing ones."
    exit 1
    ;;

  stats)
    require_docker
    if ! container_running; then
      echo "PostgreSQL is not running. Start it first with ./postgres.sh start"
      exit 1
    fi
    docker exec "$CONTAINER_NAME" psql -U postgres -d votodb -At -F '|' -c \
      "SELECT 'deputados', COUNT(*) FROM deputados
       UNION ALL SELECT 'proposicoes', COUNT(*) FROM proposicoes
       UNION ALL SELECT 'votacoes', COUNT(*) FROM votacoes
       UNION ALL SELECT 'votos', COUNT(*) FROM votos;" \
      | awk -F'|' '{print $1 ": " $2}'
    ;;

  verify-schema)
    require_docker
    if ! container_running; then
      echo "PostgreSQL is not running."
      exit 1
    fi
    if verify_schema; then
      echo "PostgreSQL schema is compatible with current startup scripts."
      exit 0
    fi
    echo "PostgreSQL schema is outdated for the current backend."
    exit 1
    ;;

  backup)
    require_docker
    if ! container_running; then
      echo "PostgreSQL is not running."
      exit 1
    fi
    backup_file="backup_votodb_$(date +%Y%m%d_%H%M%S).sql"
    echo "Creating database backup..."
    docker exec "$CONTAINER_NAME" pg_dump -U postgres votodb > "$backup_file"
    echo "Backup saved as $backup_file"
    ;;

  *)
    cat <<'EOF'
VotoDB PostgreSQL Management

Usage: ./postgres.sh {start|stop|restart|status|logs|shell|init|stats|backup|verify-schema}

Commands:
  start    - Start PostgreSQL in Docker container
  stop     - Stop PostgreSQL container
  restart  - Restart PostgreSQL container
  status   - Check if PostgreSQL is running
  logs     - Show PostgreSQL logs
  shell    - Connect to PostgreSQL command line
  init     - Initialize VotoDB database schema using PostgreSQL
  stats    - Show PostgreSQL-backed database statistics
  backup   - Create database backup
  verify-schema - Check whether PostgreSQL matches current backend columns
EOF
    exit 1
    ;;
esac
