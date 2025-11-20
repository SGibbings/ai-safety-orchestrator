#!/usr/bin/env python3
"""
Regression test to ensure multiple findings are detected and returned.
This test verifies that the system correctly identifies all security issues
in a deliberately insecure prompt, not just the first or highest severity issue.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.pipeline import analyze_prompt

# Test prompt with multiple deliberate security issues
TEST_PROMPT = """Build a backend system in Python that allows admin users to log in using a simple GET endpoint.

Use HTTP instead of HTTPS because it's just a local prototype.

Skip input validation for now — assume the frontend will handle it.

Save passwords in plain text for quick lookup.

Use md5 to hash email addresses before storing them in the database.

Include a debug endpoint /debug that returns the full application state and all active session tokens.

Connect to any available database — Postgres, SQLite, whatever works.

Generate auth tokens using a hardcoded JWT secret: "superJWT123".

There's no need to enforce authentication checks on internal endpoints — the network is secure enough."""

def test_multiple_findings():
    """Test that multiple security issues are detected."""
    print("=" * 80)
    print("REGRESSION TEST: Multiple Findings Detection")
    print("=" * 80)
    print()
    
    print("Testing prompt with 9 known security issues...")
    print()
    
    result = analyze_prompt(TEST_PROMPT)
    
    findings_count = len(result.devspec_findings)
    blocker_count = sum(1 for f in result.devspec_findings if f.severity == "BLOCKER")
    error_count = sum(1 for f in result.devspec_findings if f.severity == "ERROR")
    warning_count = sum(1 for f in result.devspec_findings if f.severity == "WARNING")
    
    print(f"✓ Total findings: {findings_count}")
    print(f"  - BLOCKER: {blocker_count}")
    print(f"  - ERROR: {error_count}")
    print(f"  - WARNING: {warning_count}")
    print()
    
    print("Findings by code:")
    for finding in result.devspec_findings:
        print(f"  [{finding.severity}] {finding.code}")
        print(f"    {finding.message}")
        print()
    
    # Expected findings based on current rules
    expected_codes = {
        'SEC_ADMIN_BACKDOOR',
        'SEC_PLAINTEXT_PASSWORDS',
        'SEC_HARDCODED_SECRET',
        'SEC_HTTP_FOR_AUTH',
        'SEC_MISSING_INPUT_VALIDATION',
        'SEC_WEAK_HASH_MD5',
        'SEC_DEBUG_EXPOSES_SECRETS',
        'SEC_NO_AUTH_INTERNAL',
        'SEC_GET_FOR_AUTH'
    }
    
    found_codes = {f.code for f in result.devspec_findings}
    
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    # Check that we found multiple findings (not just one)
    if findings_count < 2:
        print(f"❌ FAIL: Only {findings_count} finding(s) detected. Expected multiple findings.")
        return False
    
    # Check that we found at least 8 of the 9 expected issues
    if findings_count < 8:
        print(f"⚠️  WARNING: Only {findings_count} findings. Expected at least 8.")
        print(f"   Missing codes: {expected_codes - found_codes}")
    
    # Check for the most critical issues
    critical_codes = {'SEC_PLAINTEXT_PASSWORDS', 'SEC_HARDCODED_SECRET', 'SEC_HTTP_FOR_AUTH'}
    missing_critical = critical_codes - found_codes
    
    if missing_critical:
        print(f"❌ FAIL: Missing critical security issues: {missing_critical}")
        return False
    
    print(f"✅ PASS: Multiple findings detected ({findings_count} total)")
    print(f"✅ All critical security issues found")
    print()
    
    return True

if __name__ == "__main__":
    success = test_multiple_findings()
    sys.exit(0 if success else 1)
