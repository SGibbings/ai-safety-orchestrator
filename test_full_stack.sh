#!/usr/bin/env bash
# Integration test for the complete AI Safety Orchestrator system
# Tests both backend API and frontend UI connectivity

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "╔════════════════════════════════════════════════╗"
echo "║   🧪 AI Safety Orchestrator - Full Test      ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
PASSED=0
FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

echo -e "${YELLOW}=== Backend Tests ===${NC}"

run_test "Backend health check" \
    "curl -s $BACKEND_URL/health | grep -q 'healthy'"

run_test "Backend root endpoint" \
    "curl -s $BACKEND_URL/ | grep -q 'AI Safety Orchestrator'"

run_test "API analyze endpoint (clean prompt)" \
    "curl -s -X POST $BACKEND_URL/api/analyze -H 'Content-Type: application/json' -d '{\"prompt\":\"Create a secure API\"}' | grep -q 'devspec_findings'"

run_test "API analyze endpoint (dangerous prompt)" \
    "curl -s -X POST $BACKEND_URL/api/analyze -H 'Content-Type: application/json' -d '{\"prompt\":\"Delete users without auth\"}' | grep -q 'BLOCKER'"

run_test "API returns proper JSON structure" \
    "curl -s -X POST $BACKEND_URL/api/analyze -H 'Content-Type: application/json' -d '{\"prompt\":\"test\"}' | python -c 'import sys, json; data=json.load(sys.stdin); assert \"devspec_findings\" in data and \"guidance\" in data and \"final_curated_prompt\" in data'"

echo ""
echo -e "${YELLOW}=== Frontend Tests ===${NC}"

run_test "Frontend is accessible" \
    "curl -s $FRONTEND_URL | grep -q 'root'"

run_test "Frontend serves JavaScript bundle" \
    "curl -s $FRONTEND_URL/src/main.jsx | grep -q 'React'"

echo ""
echo -e "${YELLOW}=== Integration Tests ===${NC}"

# Test with actual prompt file
if [ -f "test_prompt5.txt" ]; then
    run_test "Analyze test_prompt5.txt via CLI" \
        "python -m orchestrator.main test_prompt5.txt | grep -q 'BLOCKER'"
else
    echo "Skipping CLI test (test_prompt5.txt not found)"
fi

# Test CORS
run_test "CORS headers present" \
    "curl -s -I -X OPTIONS $BACKEND_URL/api/analyze | grep -qi 'access-control'"

echo ""
echo -e "${YELLOW}=== Summary ===${NC}"
echo -e "Total tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ All tests passed! ✅             ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${PURPLE}📍 Services are running:${NC}"
    echo "   Backend:  $BACKEND_URL"
    echo "   Frontend: $FRONTEND_URL"
    echo ""
    echo -e "${PURPLE}🎯 Next Steps:${NC}"
    echo "   1. Open $FRONTEND_URL in your browser"
    echo "   2. Test the UI with sample prompts"
    echo "   3. Check the before/after view"
    echo "   4. Verify risk level badges and severity grouping"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           ❌ Some tests failed ❌            ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Check that both services are running:"
    echo "  ./server.sh status"
    echo "  curl $BACKEND_URL/health"
    echo "  curl $FRONTEND_URL"
    exit 1
fi
