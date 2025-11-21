#!/bin/bash
# Start both backend and frontend services

# Kill any existing processes
pkill -f "uvicorn" || true
pkill -f "vite" || true

# Start backend in background
cd /workspaces/ai-safety-orchestrator
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &

# Wait a moment for backend to start
sleep 2

# Start frontend
cd /workspaces/ai-safety-orchestrator/ui
npm run dev -- --host 0.0.0.0
