#!/bin/bash
#
# Quick demo of spec breakdown and quality warnings
#

API_BASE="http://localhost:8000"

echo "============================================="
echo "  Spec Breakdown & Quality Warnings Demo"
echo "============================================="
echo ""

# Test 1: Incomplete spec (should have many warnings)
echo "Test 1: Incomplete Spec (prompts/stress/high2.txt)"
echo "-------------------------------------------------"
curl -s -X POST "$API_BASE/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Build an admin control panel for managing user accounts. Hash passwords using MD5 for speed. Serve everything over HTTP because HTTPS is not needed internally. Skip authentication on all GET endpoints for convenience. Assume inputs will always be sanitized by the UI."}' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)

print(f\"Spec-kit enabled: {data['spec_kit_enabled']}\")
print(f\"\nSpec Breakdown:\")
if data.get('spec_kit_structure'):
    structure = data['spec_kit_structure']
    print(f\"  Features: {len(structure['features'])} items\")
    for f in structure['features'][:3]:
        print(f\"    - {f}\")
    print(f\"  Entities: {', '.join(structure['entities'][:5])}\")
    print(f\"  Flows: {', '.join(structure['flows'][:5])}\")
else:
    print(\"  (none)\")

print(f\"\nQuality Warnings: {len(data.get('spec_quality_warnings', []))}\")
for warning in data.get('spec_quality_warnings', []):
    print(f\"  ⚠ {warning}\")

print(f\"\nSecurity Analysis:\")
print(f\"  Risk Level: {data['risk_level']}\")
print(f\"  Security Issues: {len(data['devspec_findings'])}\")
for finding in data['devspec_findings'][:3]:
    print(f\"    [{finding['severity']}] {finding['code']}: {finding['message'][:60]}...\")
"
echo ""
echo ""

# Test 2: Complete spec (should have few/no warnings)
echo "Test 2: Complete Spec"
echo "-------------------------------------------------"
curl -s -X POST "$API_BASE/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Build a secure REST API for task management. Features: Create, read, update, delete tasks with user authentication and authorization. Entities: User model with email and bcrypt-hashed password, Task model with title and assignee. Flows: Login flow with JWT authentication, Task CRUD with role-based access control, Logout flow. Configuration: Database connection string in environment variables, JWT secret in .env file (never hardcoded). Error Handling: HTTP 400 for validation, 401 for auth failures, 500 for server errors with graceful degradation. Testing: Unit tests for business logic, integration tests for API endpoints, end-to-end tests for critical flows. Logging: Structured logging with request IDs, error tracking, performance metrics."}' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)

print(f\"Spec-kit enabled: {data['spec_kit_enabled']}\")
print(f\"\nSpec Breakdown:\")
if data.get('spec_kit_structure'):
    structure = data['spec_kit_structure']
    print(f\"  Features: {len(structure['features'])} items\")
    print(f\"  Entities: {len(structure['entities'])} items\")
    print(f\"  Flows: {len(structure['flows'])} items\")
    print(f\"  Configuration: {len(structure['configuration'])} items\")
    print(f\"  Error Handling: {len(structure['error_handling'])} items\")
    print(f\"  Testing: {len(structure['testing'])} items\")
    print(f\"  Logging: {len(structure['logging'])} items\")
else:
    print(\"  (none)\")

print(f\"\nQuality Warnings: {len(data.get('spec_quality_warnings', []))}\")
if data.get('spec_quality_warnings'):
    for warning in data['spec_quality_warnings']:
        print(f\"  ⚠ {warning}\")
else:
    print(\"  ✓ No quality issues detected\")

print(f\"\nSecurity Analysis:\")
print(f\"  Risk Level: {data['risk_level']}\")
print(f\"  Security Issues: {len(data['devspec_findings'])}\")
"
echo ""
echo ""

echo "============================================="
echo "  Demo complete!"
echo "============================================="
echo ""
echo "Try it in the UI:"
echo "  1. Open http://localhost:3000"
echo "  2. Paste a prompt"
echo "  3. See Spec Breakdown and Quality Warnings"
echo "     BEFORE security findings"
echo ""
