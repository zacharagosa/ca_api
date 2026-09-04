#!/bin/bash
# ==============================================================================
# restart_demo.sh - Restarts the Gaming Analytics Demo
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/stop_demo.sh"
sleep 2
"${SCRIPT_DIR}/start_demo.sh"
