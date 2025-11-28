#!/bin/bash

echo "Iniciando VotoDB..."

echo "Iniciando PostgreSQL..."
cd ~/projects/voto-db
./postgres.sh status > /dev/null 2>&1
if [ $? -ne 0 ]; then
    ./postgres.sh restart
    echo "PostgreSQL iniciado"
else
    echo "PostgreSQL já está rodando"
fi

sleep 2

echo "Iniciando Backend API..."
cd ~/projects/voto-db/backend
../.venv/bin/python main_v2.py > /tmp/voto-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend iniciado (PID: $BACKEND_PID)"

sleep 3

echo "Iniciando Frontend React..."
cd ~/projects/voto-db/frontend
npm start

echo "Encerrando serviços..."
kill $BACKEND_PID 2>/dev/null
echo "Sistema encerrado"