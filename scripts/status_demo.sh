#!/bin/bash
# ==============================================================================
# status_demo.sh - Checks health and status of the Gaming Analytics Demo
# ==============================================================================

echo "================================================================="
echo "🔍 Checking Gaming Analytics Demo Status"
echo "================================================================="

BACKEND_PID=$(lsof -ti :8080 2>/dev/null || true)
FRONTEND_PID=$(lsof -ti :5173 2>/dev/null || true)

# Backend Check
if [ -n "${BACKEND_PID}" ]; then
    echo "⚙️  Backend Flask Server:  RUNNING (PID: ${BACKEND_PID}, Port: 8080)"
    if curl -s -f http://127.0.0.1:8080/api/models >/dev/null 2>&1; then
        echo "   Status: 🟢 Healthy (API responding)"
    else
        echo "   Status: 🟡 Port listening but /api/models not responding yet"
    fi
else
    echo "⚙️  Backend Flask Server:  🔴 STOPPED (Port 8080 free)"
fi

echo ""

# Frontend Check
if [ -n "${FRONTEND_PID}" ]; then
    echo "🖥️  Frontend Vite Server: RUNNING (PID: ${FRONTEND_PID}, Port: 5173)"
    if curl -s -f http://127.0.0.1:5173 >/dev/null 2>&1; then
        echo "   Status: 🟢 Healthy (UI responding)"
    else
        echo "   Status: 🟡 Port listening but HTTP not responding yet"
    fi
else
    echo "🖥️  Frontend Vite Server: 🔴 STOPPED (Port 5173 free)"
fi

echo ""
echo "================================================================="
if [ -n "${BACKEND_PID}" ] && [ -n "${FRONTEND_PID}" ]; then
    echo "🟢 Status: ALL SERVICES ACTIVE"
    echo "🌐 Frontend UI:  http://aragosa.c.googlers.com:5173"
    echo "                 http://localhost:5173"
    echo "⚙️  Backend API:  http://aragosa.c.googlers.com:8080"
    echo "                 http://localhost:8080"
else
    echo "🟡 Status: INCOMPLETE (Run 'bash scripts/start_demo.sh' to start)"
fi
echo "================================================================="
