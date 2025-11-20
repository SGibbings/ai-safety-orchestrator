#!/usr/bin/env bash
# Management script for the SpecAlign API server

set -e

API_PORT=8000
PID_FILE="/tmp/ai-safety-orchestrator.pid"
LOG_FILE="/tmp/ai-safety-orchestrator.log"

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Server is already running (PID: $PID)"
            return 0
        else
            rm "$PID_FILE"
        fi
    fi
    
    echo "Starting SpecAlign API server..."
    cd "$(dirname "$0")"
    
    # Start the server in the background
    nohup python api/main.py > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Server started successfully (PID: $PID)"
        echo "📝 Logs: $LOG_FILE"
        echo "🌐 API: http://localhost:$API_PORT"
        echo "📚 Docs: http://localhost:$API_PORT/docs"
    else
        echo "❌ Server failed to start. Check logs: $LOG_FILE"
        rm "$PID_FILE"
        exit 1
    fi
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Server is not running (no PID file found)"
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping server (PID: $PID)..."
        kill "$PID"
        sleep 1
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Force stopping..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        
        rm "$PID_FILE"
        echo "✅ Server stopped"
    else
        echo "Server is not running (stale PID file)"
        rm "$PID_FILE"
    fi
}

status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Server is running (PID: $PID)"
            echo "🌐 API: http://localhost:$API_PORT"
            echo "📚 Docs: http://localhost:$API_PORT/docs"
            echo "📝 Logs: $LOG_FILE"
            return 0
        else
            echo "❌ Server is not running (stale PID file)"
            rm "$PID_FILE"
            return 1
        fi
    else
        echo "❌ Server is not running"
        return 1
    fi
}

restart_server() {
    stop_server
    sleep 1
    start_server
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
        exit 1
    fi
}

case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "SpecAlign Server Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the API server"
        echo "  stop     - Stop the API server"
        echo "  restart  - Restart the API server"
        echo "  status   - Check server status"
        echo "  logs     - Show and follow server logs"
        exit 1
        ;;
esac
