#!/bin/bash
# ==============================================================================
# stop_demo.sh - Stops the Gaming Analytics Demo (Backend + Frontend)
# ==============================================================================

echo "================================================================="
echo "🛑 Stopping Looker Gaming Analytics Demo Environment"
echo "================================================================="

kill_port_process() {
    local port=$1
    local name=$2
    local pids=$(lsof -ti :${port} 2>/dev/null || true)
    if [ -n "${pids}" ]; then
        echo "🔹 Stopping ${name} on port ${port} (PID: ${pids})..."
        kill -15 ${pids} 2>/dev/null || true
        sleep 1
        # Force kill if still lingering
        pids_left=$(lsof -ti :${port} 2>/dev/null || true)
        if [ -n "${pids_left}" ]; then
            echo "   Force killing remaining PID(s): ${pids_left}"
            kill -9 ${pids_left} 2>/dev/null || true
        fi
        echo "   ✅ Stopped ${name}."
    else
        echo "   ℹ️  ${name} (port ${port}) is not running."
    fi
}

# Stop backend and frontend by port
kill_port_process 8080 "Backend Flask Server"
kill_port_process 5173 "Frontend Vite Server"

# Also kill any lingering python server.py processes if running outside port
pkill -f "python server.py" 2>/dev/null || true

echo "================================================================="
echo "✅ All demo services have been stopped."
echo "================================================================="
