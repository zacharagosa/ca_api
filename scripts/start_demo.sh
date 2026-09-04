#!/bin/bash
# ==============================================================================
# start_demo.sh - Starts the Gaming Analytics Demo (Backend + Frontend)
# ==============================================================================

set -e

# Resolve script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "================================================================="
echo "🚀 Starting Looker Gaming Analytics Demo Environment"
echo "================================================================="

# 1. Ensure NVM / Node / NPM are available
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
fi

# 2. Check and clean up existing ports if already running
cleanup_port() {
    local port=$1
    local name=$2
    local pids=$(lsof -ti :${port} 2>/dev/null || true)
    if [ -n "${pids}" ]; then
        echo "⚠️  Port ${port} (${name}) is already in use by PID(s): ${pids}"
        echo "   Terminating existing process..."
        kill -9 ${pids} 2>/dev/null || true
        sleep 1
    fi
}

cleanup_port 8080 "Backend Flask Server"
cleanup_port 5173 "Frontend Vite Server"

# 3. Check Virtualenv
if [ ! -d "venv" ] || [ ! -f "venv/bin/python" ]; then
    echo "❌ Python virtual environment 'venv' not found in ${PROJECT_ROOT}!"
    echo "   Please create it using: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# 4. Check Frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    (cd frontend && npm install)
fi

# 5. Start Backend in background (disowned)
echo "🔹 [1/2] Starting Backend Flask API on port 8080..."
nohup ./venv/bin/python server.py > server.log 2>&1 &
BACKEND_PID=$!
disown ${BACKEND_PID} 2>/dev/null || true
echo "   Backend started (PID: ${BACKEND_PID}). Log: server.log"

# 6. Start Frontend in background (disowned)
echo "🔹 [2/2] Starting Frontend Vite Dev Server on port 5173..."
nohup bash -c "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && \. \"$NVM_DIR/nvm.sh\"; cd frontend && npm run dev" > frontend/vite.log 2>&1 &
FRONTEND_PID=$!
disown ${FRONTEND_PID} 2>/dev/null || true
echo "   Frontend started (PID: ${FRONTEND_PID}). Log: frontend/vite.log"

# 7. Wait for services to become healthy
echo ""
echo "⏳ Waiting for services to initialize..."

MAX_RETRIES=20
RETRY_COUNT=0
BACKEND_READY=false
FRONTEND_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if ! $BACKEND_READY; then
        if curl -s -f http://127.0.0.1:8080/api/models >/dev/null 2>&1; then
            BACKEND_READY=true
            echo "   ✅ Backend API is ready (http://127.0.0.1:8080)"
        fi
    fi

    if ! $FRONTEND_READY; then
        if curl -s -f http://127.0.0.1:5173 >/dev/null 2>&1; then
            FRONTEND_READY=true
            echo "   ✅ Frontend UI is ready (http://127.0.0.1:5173)"
        fi
    fi

    if $BACKEND_READY && $FRONTEND_READY; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 1
done

echo ""
echo "================================================================="
echo "🎉 Gaming Analytics Demo is RUNNING!"
echo "================================================================="
echo "🌐 Frontend UI:  http://aragosa.c.googlers.com:5173"
echo "                 http://localhost:5173"
echo "⚙️  Backend API:  http://aragosa.c.googlers.com:8080"
echo "                 http://localhost:8080"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f server.log"
echo "   Frontend: tail -f frontend/vite.log"
echo ""
echo "🛑 To stop:    bash scripts/stop_demo.sh (or npm run stop)"
echo "🔍 To status:  bash scripts/status_demo.sh (or npm run status)"
echo "🔄 To restart: bash scripts/restart_demo.sh (or npm run restart)"
echo "================================================================="
