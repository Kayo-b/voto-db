#!/bin/bash
# Quick start script - just the working legacy backend for testing

echo "Starting legacy backend only..."

cd "$(dirname "$0")/backend"

# Check if venv exists
if [ ! -f "./venv/bin/python" ]; then
    echo "Virtual environment not found at ./venv/bin/python"
    exit 1
fi

# Start legacy backend
echo "Starting main_v2.py on port 8001..."
./venv/bin/python -m uvicorn main_v2:app --host 0.0.0.0 --port 8001 --reload