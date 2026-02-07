#!/bin/bash

echo "VotoDB PostgreSQL Management"

case "$1" in
    "start")
        echo "Starting PostgreSQL with Docker..."
        # If container already exists, just start it instead of trying to recreate.
        if docker ps -a --format "{{.Names}}" | grep -q "^votodb-postgres$"; then
            echo "Container votodb-postgres already exists. Starting existing container..."
            docker start votodb-postgres > /dev/null
        else
            docker run -d \
                --name votodb-postgres \
                -e POSTGRES_DB=votodb \
                -e POSTGRES_USER=postgres \
                -e POSTGRES_PASSWORD=postgres \
                -p 5432:5432 \
                -v votodb_data:/var/lib/postgresql/data \
                postgres:15
        fi
        
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
        
        # Test connection
        if docker exec votodb-postgres pg_isready; then
            echo "PostgreSQL is running!"
            echo "Connection: postgresql://postgres:postgres@localhost:5432/votodb"
        else
            echo "PostgreSQL failed to start"
            exit 1
        fi
        ;;
    
    "stop")
        echo "Stopping PostgreSQL..."
        docker stop votodb-postgres
        ;;
    
    "restart")
        echo "Restarting PostgreSQL..."
        docker restart votodb-postgres
        ;;
    
    "logs")
        echo "PostgreSQL logs:"
        docker logs votodb-postgres
        ;;
    
    "shell")
        echo "Connecting to PostgreSQL shell..."
        docker exec -it votodb-postgres psql -U postgres -d votodb
        ;;
    
    "status")
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "votodb-postgres"; then
            echo "PostgreSQL is running"
            docker ps --filter name=votodb-postgres --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        else
            echo "PostgreSQL is not running"
        fi
        ;;
    
    "init")
        echo "Initializing database..."
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        cd "$SCRIPT_DIR"
        ./.venv/bin/python init_database.py
        ;;
    
    "stats")
        echo "Database statistics:"
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        cd "$SCRIPT_DIR"
        ./.venv/bin/python - <<'PY'
from backend.database.connection import SessionLocal
from backend.database.model import Deputado, Proposicao, Votacao, Voto

with SessionLocal() as db:
    print("deputados:", db.query(Deputado).count())
    print("proposicoes:", db.query(Proposicao).count())
    print("votacoes:", db.query(Votacao).count())
    print("votos:", db.query(Voto).count())
PY
        ;;
    
    "backup")
        echo "Creating database backup..."
        docker exec votodb-postgres pg_dump -U postgres votodb > "backup_votodb_$(date +%Y%m%d_%H%M%S).sql"
        echo "Backup saved as backup_votodb_$(date +%Y%m%d_%H%M%S).sql"
        ;;
    
    *)
        echo "VotoDB PostgreSQL Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|shell|init|stats|backup}"
        echo ""
        echo "Commands:"
        echo "  start    - Start PostgreSQL in Docker container"
        echo "  stop     - Stop PostgreSQL container"  
        echo "  restart  - Restart PostgreSQL container"
        echo "  status   - Check if PostgreSQL is running"
        echo "  logs     - Show PostgreSQL logs"
        echo "  shell    - Connect to PostgreSQL command line"
        echo "  init     - Initialize VotoDB database schema"
        echo "  stats    - Show database statistics"
        echo "  backup   - Create database backup"
        echo ""
        echo "Examples:"
        echo "  ./postgres.sh start     # Start database"
        echo "  ./postgres.sh init      # Setup tables"
        echo "  ./postgres.sh status    # Check status"
        ;;
esac
