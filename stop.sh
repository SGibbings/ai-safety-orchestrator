#!/usr/bin/env bash
# Shutdown script for AI Safety Orchestrator

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}"
echo "╔════════════════════════════════════════════════╗"
echo "║   🛡️  AI Safety Orchestrator - Shutdown      ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "Stopping services..."

# Stop backend
if [ -f "/tmp/ai-safety-orchestrator.pid" ]; then
    echo "Stopping backend..."
    ./server.sh stop
else
    echo "Backend not running"
fi

# Stop frontend
if [ -f "/tmp/ui-dev.pid" ]; then
    UI_PID=$(cat /tmp/ui-dev.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $UI_PID)..."
        kill $UI_PID 2>/dev/null || true
        rm /tmp/ui-dev.pid
    else
        echo "Frontend not running (stale PID)"
        rm /tmp/ui-dev.pid
    fi
else
    echo "Frontend not running"
fi

echo ""
echo -e "${RED}✅ All services stopped${NC}"
