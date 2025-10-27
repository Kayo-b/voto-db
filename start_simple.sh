#!/bin/bash
# Simple start script - automatically handles database setup

echo "VotoDB Quick Start"

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if PostgreSQL is needed and available
USE_DB="true"

# Try to start/check PostgreSQL
if command -v docker >/dev/null 2>&1; then
    # Check if container exists
    if docker ps -a --format "{{.Names}}" | grep -q "votodb-postgres"; then
        # Start existing container
        docker start votodb-postgres >/dev/null 2>&1
    else
        # Create new container
        ./postgres.sh start >/dev/null 2>&1
    fi
    
    sleep 3
    
    # Check if it's running
    if docker ps --format "{{.Names}}" | grep -q "votodb-postgres"; then
        echo "PostgreSQL ready"
        export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/votodb"
    else
        echo "Using file cache mode"
        USE_DB="false"
    fi
else
    echo "Docker not available, using file cache mode"
    USE_DB="false"
fi

# Start the appropriate backend
cd "$SCRIPT_DIR/backend"
if [ "$USE_DB" = "true" ]; then
    echo "Starting enhanced backend with PostgreSQL..."
    ./venv/bin/python -m uvicorn main_db:app --host 0.0.0.0 --port 8001 --reload &
else
    echo "Starting legacy backend with file cache..."
    ./venv/bin/python -m uvicorn main_v2:app --host 0.0.0.0 --port 8001 --reload &
fi

sleep 3

# Start frontend
echo "Starting frontend..."
cd "$SCRIPT_DIR/frontend" && npm start