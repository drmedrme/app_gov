#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Port configuration
API_PORT="${API_PORT:-4825}"

# Install dependencies if needed
if ! python3 -c "import flask, lxml, requests" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -q flask lxml requests --break-system-packages 2>/dev/null || \
    pip install -q flask lxml requests
fi

# Kill any existing process on the port
if lsof -ti :"$API_PORT" >/dev/null 2>&1; then
    echo "Killing existing process on port $API_PORT..."
    kill $(lsof -ti :"$API_PORT") 2>/dev/null || true
    sleep 1
fi

echo "Starting app_gov on port $API_PORT..."
echo "  http://localhost:$API_PORT"
echo ""
echo "Environment:"
echo "  CH_ENVIRONMENT=${CH_ENVIRONMENT:-test}"
echo "  CH_PRESENTER_ID=${CH_PRESENTER_ID:-(not set)}"
echo ""

exec python3 app.py
