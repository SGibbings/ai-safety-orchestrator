#!/usr/bin/env bash
# Startup script for SpecAlign (Backend + Frontend)

set -e

GREEN='\033[0;32m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "╔════════════════════════════════════════════════╗"
echo "║          SpecAlign - Startup                   ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if we're in the right directory
if [ ! -f "server.sh" ] || [ ! -d "ui" ]; then
    echo "❌ Error: Must run from repository root"
    exit 1
fi

echo ""
echo -e "${YELLOW}[1/3] Starting Backend API...${NC}"
./server.sh start

echo ""
echo -e "${YELLOW}[2/3] Checking Backend Health...${NC}"
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo "❌ Backend health check failed"
    exit 1
fi

echo ""
echo -e "${YELLOW}[3/3] Starting Frontend UI...${NC}"
cd ui

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
npm run dev > /tmp/ui-dev.log 2>&1 &
UI_PID=$!
echo $UI_PID > /tmp/ui-dev.pid

# Wait for frontend to be ready
echo "Waiting for frontend to start..."
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
done

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is ready${NC}"
else
    echo "⚠️  Frontend may still be starting..."
fi

cd ..

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 Startup Complete! 🎉            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${PURPLE}📍 Services:${NC}"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Frontend UI:  http://localhost:3000"
echo ""
echo -e "${PURPLE}📝 Next Steps:${NC}"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Enter a developer prompt"
echo "   3. Click 'Analyze Prompt' to see security analysis"
echo ""
echo -e "${PURPLE}🛠️  Management:${NC}"
echo "   Stop backend:  ./server.sh stop"
echo "   Stop frontend: kill \$(cat /tmp/ui-dev.pid)"
echo "   View logs:     ./server.sh logs (backend)"
echo "                  tail -f /tmp/ui-dev.log (frontend)"
echo ""
