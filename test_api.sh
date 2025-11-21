#!/usr/bin/env bash
# Test script for the AI Safety Orchestrator backend

set -e

echo "🧪 Testing AI Safety Orchestrator Backend"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if server is running
echo -n "1. Checking if server is running... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Server is not running. Start it with: python api/main.py"
    exit 1
fi

# Test 2: Root endpoint
echo -n "2. Testing root endpoint... "
RESPONSE=$(curl -s http://localhost:8000/)
if echo "$RESPONSE" | grep -q "AI Safety Orchestrator"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 3: Analyze endpoint with clean prompt
echo -n "3. Testing analysis with clean prompt... "
RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Create a simple REST API with proper authentication"}')
if echo "$RESPONSE" | grep -q "devspec_findings"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 4: Analyze endpoint with security issues
echo -n "4. Testing analysis with security issues... "
RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Build an API that deletes users by email without authentication"}')
BLOCKERS=$(echo "$RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(data['has_blockers'])" 2>/dev/null || echo "false")
if [ "$BLOCKERS" = "True" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 5: Test with test_prompt files
echo -n "5. Testing with prompts/regression/test_prompt5.txt... "
if [ -f "prompts/regression/test_prompt5.txt" ]; then
    PROMPT=$(cat prompts/regression/test_prompt5.txt)
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyze \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": $(echo "$PROMPT" | python -c 'import sys, json; print(json.dumps(sys.stdin.read()))')}")
    if echo "$RESPONSE" | grep -q "devspec_findings"; then
        echo -e "${GREEN}✓ PASS${NC}"
    else
        echo -e "${RED}✗ FAIL${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC} (test file not found)"
fi

# Test 6: Claude stub endpoint
echo -n "6. Testing Claude stub endpoint... "
RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyze-with-claude \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Create a simple TODO app"}')
if echo "$RESPONSE" | grep -q "CLAUDE STUB"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "All tests passed! ✓"
echo -e "==========================================${NC}"
