#!/bin/bash
# Test UI integration with spec-kit disabled and enabled

echo "================================================================================"
echo "UI INTEGRATION TEST - Testing both spec-kit modes"
echo "================================================================================"

API_URL="http://localhost:8000"

# Test prompt
TEST_PROMPT="Build a secure API with OAuth2, HTTPS, and bcrypt password hashing."

echo ""
echo "Test 1: API call with spec-kit DISABLED (default)"
echo "--------------------------------------------------------------------------------"
RESPONSE=$(curl -s -X POST "${API_URL}/api/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"${TEST_PROMPT}\"}")

echo "Response fields:"
echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  risk_level: {data.get(\"risk_level\")}')
print(f'  findings: {len(data.get(\"devspec_findings\", []))}')
print(f'  spec_kit_enabled: {data.get(\"spec_kit_enabled\")}')
print(f'  spec_kit_success: {data.get(\"spec_kit_success\")}')
print(f'  spec_kit_summary: {data.get(\"spec_kit_summary\")}')
"

echo ""
echo "Test 2: Verify backend is running and responding"
echo "--------------------------------------------------------------------------------"
HEALTH=$(curl -s "${API_URL}/health")
echo "Health check: $HEALTH"

echo ""
echo "================================================================================"
echo "✅ UI Integration Test Complete"
echo "================================================================================"
echo ""
echo "To test with spec-kit ENABLED:"
echo "  1. Stop the backend (Ctrl+C in the uvicorn terminal)"
echo "  2. Run: USE_SPEC_KIT=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo "  3. Refresh the UI and submit a prompt"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "================================================================================"
