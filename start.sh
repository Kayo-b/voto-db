#!/bin/bash
# Start backend in background
cd ~/projects/voto-db/backend && ./venv/bin/python -m uvicorn main_v2:app --host 0.0.0.0 --port 8001 --reload &
sleep 5 
# Start frontend in foreground
cd ~/projects/voto-db/frontend && npm start 
