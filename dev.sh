#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting development environment..."

# 1. Start Backend
echo "Starting Backend..."
./venv/bin/python server.py &

# 2. Start Frontend
echo "Starting Frontend..."
cd frontend && npm run dev &

# Wait for all background processes
wait
