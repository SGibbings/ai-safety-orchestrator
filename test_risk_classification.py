#!/usr/bin/env python3
"""
Test script to verify risk classification and constraint generation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.pipeline import analyze_prompt

# Test Case 1: SAFE prompt (should be LOW risk)
SAFE_PROMPT = """
Build a user-facing dashboard web app for an internal analytics team.

Tech stack:

Backend: Python (FastAPI)
Frontend: React + TypeScript
Database: PostgreSQL

Requirements:

Implement user authentication using OAuth2 with the company's SSO provider.
All API endpoints must be behind authentication and role-based authorization (roles: viewer, analyst, admin).
Viewer can only see dashboards shared with them.
Analyst can create, edit, and delete dashboards they own.
Admin can manage users and assign roles.
All communication must be over HTTPS.
Store passwords only for service accounts, and hash them using bcrypt with a strong cost factor.
Use prepared statements or an ORM to avoid SQL injection.
Implement input validation on all API payloads (Pydantic models on the backend and form validation on the frontend).
Log errors and key events (login, dashboard create/update/delete) to a central logging service, but never log passwords, tokens, or other secrets.
Provide an admin page that shows audit logs for dashboard changes (who changed what and when).
Add a "download as CSV" feature for dashboard query results, but limit export size to avoid performance issues.
Write unit tests for critical auth logic and integration tests for the main dashboard CRUD flows.
Configuration (DB connection string, OAuth client IDs, etc.) must come from environment variables or a config file that is not checked into source control.
Deliver a clean, modular code structure that would be easy to extend with new dashboard widgets in the future.
"""

# Test Case 2: UNSAFE prompt (should be HIGH risk)
UNSAFE_PROMPT = """
Create a login backend in Node.js. Store the user password in plain text for now. 
Also include an admin endpoint /debug that returns all environment variables. 
Use this hardcoded secret key: "mySecret123!" for signing session tokens.
Use HTTP instead of HTTPS because it's just a prototype.
Skip input validation - we'll add it later.
"""


def test_safe_prompt():
    print("\n" + "="*80)
    print("TEST 1: SAFE PROMPT (Expected: LOW risk, minimal constraints)")
    print("="*80)
    
    result = analyze_prompt(SAFE_PROMPT)
    
    print(f"\n✓ Risk Level: {result.risk_level}")
    print(f"✓ Findings Count: {len(result.devspec_findings)}")
    print(f"✓ Has Blockers: {result.has_blockers}")
    print(f"✓ Has Errors: {result.has_errors}")
    
    if result.devspec_findings:
        print("\nFindings:")
        for finding in result.devspec_findings:
            print(f"  - [{finding.severity}] {finding.code}: {finding.message}")
    
    print("\n--- Curated Prompt Preview (first 500 chars) ---")
    print(result.final_curated_prompt[:500])
    print("...")
    
    # Check if it's truly LOW risk
    if result.risk_level == "Low":
        print("\n✅ PASS: Correctly classified as Low risk")
    else:
        print(f"\n❌ FAIL: Expected Low risk, got {result.risk_level}")
    
    # Check for scary constraint blocks
    if "IMPORTANT SECURITY CONSTRAINTS" in result.final_curated_prompt and result.risk_level == "Low":
        print("❌ FAIL: Low risk prompt should not have 'IMPORTANT SECURITY CONSTRAINTS' block")
    else:
        print("✅ PASS: No scary constraint block for Low risk")
    
    return result


def test_unsafe_prompt():
    print("\n" + "="*80)
    print("TEST 2: UNSAFE PROMPT (Expected: HIGH risk, multiple constraints)")
    print("="*80)
    
    result = analyze_prompt(UNSAFE_PROMPT)
    
    print(f"\n✓ Risk Level: {result.risk_level}")
    print(f"✓ Findings Count: {len(result.devspec_findings)}")
    print(f"✓ Has Blockers: {result.has_blockers}")
    print(f"✓ Has Errors: {result.has_errors}")
    
    if result.devspec_findings:
        print("\nFindings:")
        for finding in result.devspec_findings:
            print(f"  - [{finding.severity}] {finding.code}: {finding.message}")
    
    print("\n--- Curated Prompt Preview (first 800 chars) ---")
    print(result.final_curated_prompt[:800])
    print("...")
    
    # Check if it's HIGH risk
    if result.risk_level == "High":
        print("\n✅ PASS: Correctly classified as High risk")
    else:
        print(f"\n❌ FAIL: Expected High risk, got {result.risk_level}")
    
    # Check for constraints
    if "IMPORTANT SECURITY CONSTRAINTS" in result.final_curated_prompt:
        print("✅ PASS: Has security constraints block")
        
        # Check for duplicates
        constraints_section = result.final_curated_prompt.split("IMPORTANT SECURITY CONSTRAINTS:")[1].split("---")[0]
        lines = [l.strip() for l in constraints_section.split('\n') if l.strip().startswith('-')]
        if len(lines) != len(set(lines)):
            print(f"❌ FAIL: Found duplicate constraints")
            print(f"   Total lines: {len(lines)}, Unique lines: {len(set(lines))}")
        else:
            print(f"✅ PASS: No duplicate constraints ({len(lines)} unique constraints)")
    else:
        print("❌ FAIL: Missing security constraints block for High risk")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*80)
    print("RISK CLASSIFICATION AND CONSTRAINT GENERATION TEST SUITE")
    print("="*80)
    
    try:
        safe_result = test_safe_prompt()
        unsafe_result = test_unsafe_prompt()
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"✓ Safe prompt risk level: {safe_result.risk_level}")
        print(f"✓ Unsafe prompt risk level: {unsafe_result.risk_level}")
        print(f"✓ Safe prompt findings: {len(safe_result.devspec_findings)}")
        print(f"✓ Unsafe prompt findings: {len(unsafe_result.devspec_findings)}")
        
        if safe_result.risk_level == "Low" and unsafe_result.risk_level == "High":
            print("\n🎉 ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n⚠️  SOME TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
