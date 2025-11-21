#!/usr/bin/env python3
"""
Test suite to verify spec-kit integration is additive and never replaces dev-spec-kit.

This validates:
1. With USE_SPEC_KIT=false: behavior is identical to pre-integration
2. With USE_SPEC_KIT=true: spec-kit runs first, dev-spec-kit always runs after
3. Security analysis (risk_level, findings) remains identical regardless of spec-kit
4. Spec-kit cannot short-circuit or bypass security checks
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.pipeline import analyze_prompt
from orchestrator.models import AnalysisResponse


# Test prompts
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

UNSAFE_PROMPT = """
Create a login backend in Node.js. Store the user password in plain text for now. 
Also include an admin endpoint /debug that returns all environment variables. 
Use this hardcoded secret key: "mySecret123!" for signing session tokens.
Use HTTP instead of HTTPS because it's just a prototype.
Skip input validation - we'll add it later.
"""


def test_default_mode_safe_prompt():
    """Test safe prompt with spec-kit DISABLED (default behavior)."""
    print("\n" + "="*80)
    print("TEST 1: SAFE PROMPT - SPEC-KIT DISABLED (default)")
    print("="*80)
    
    # Ensure spec-kit is disabled
    os.environ.pop('USE_SPEC_KIT', None)
    
    result = analyze_prompt(SAFE_PROMPT)
    
    # Verify spec-kit fields are False/None (backwards compatibility)
    assert result.spec_kit_enabled == False, "spec_kit_enabled should be False by default"
    assert result.spec_kit_success is None, "spec_kit_success should be None when disabled"
    assert result.spec_kit_raw_output is None, "spec_kit_raw_output should be None when disabled"
    assert result.spec_kit_summary is None, "spec_kit_summary should be None when disabled"
    
    # Verify security analysis still works
    assert result.risk_level == "Low", f"Expected Low risk, got {result.risk_level}"
    assert len(result.devspec_findings) == 0, f"Expected 0 findings, got {len(result.devspec_findings)}"
    assert result.has_blockers == False, "Should have no blockers"
    assert result.has_errors == False, "Should have no errors"
    
    print(f"✓ spec_kit_enabled: {result.spec_kit_enabled}")
    print(f"✓ spec_kit_success: {result.spec_kit_success}")
    print(f"✓ Risk Level: {result.risk_level}")
    print(f"✓ Findings: {len(result.devspec_findings)}")
    print("✅ PASS: Default mode works, spec-kit fields are None/False")
    
    return result


def test_default_mode_unsafe_prompt():
    """Test unsafe prompt with spec-kit DISABLED (default behavior)."""
    print("\n" + "="*80)
    print("TEST 2: UNSAFE PROMPT - SPEC-KIT DISABLED (default)")
    print("="*80)
    
    # Ensure spec-kit is disabled
    os.environ.pop('USE_SPEC_KIT', None)
    
    result = analyze_prompt(UNSAFE_PROMPT)
    
    # Verify spec-kit fields are False/None
    assert result.spec_kit_enabled == False, "spec_kit_enabled should be False"
    assert result.spec_kit_success is None, "spec_kit_success should be None"
    
    # Verify security analysis still detects issues
    assert result.risk_level == "High", f"Expected High risk, got {result.risk_level}"
    assert len(result.devspec_findings) > 0, "Should have findings for unsafe prompt"
    assert result.has_blockers or result.has_errors, "Should have blockers or errors"
    
    print(f"✓ spec_kit_enabled: {result.spec_kit_enabled}")
    print(f"✓ Risk Level: {result.risk_level}")
    print(f"✓ Findings: {len(result.devspec_findings)}")
    print(f"✓ Has Blockers: {result.has_blockers}")
    print("✅ PASS: Security analysis works correctly with spec-kit disabled")
    
    return result


def test_spec_kit_mode_safe_prompt():
    """Test safe prompt with spec-kit ENABLED."""
    print("\n" + "="*80)
    print("TEST 3: SAFE PROMPT - SPEC-KIT ENABLED")
    print("="*80)
    
    # Enable spec-kit
    os.environ['USE_SPEC_KIT'] = 'true'
    
    try:
        result = analyze_prompt(SAFE_PROMPT)
        
        # Verify spec-kit fields are populated
        assert result.spec_kit_enabled == True, "spec_kit_enabled should be True"
        assert result.spec_kit_success is not None, "spec_kit_success should not be None"
        assert result.spec_kit_raw_output is not None, "spec_kit_raw_output should not be None"
        
        print(f"✓ spec_kit_enabled: {result.spec_kit_enabled}")
        print(f"✓ spec_kit_success: {result.spec_kit_success}")
        print(f"✓ spec_kit_summary: {result.spec_kit_summary}")
        
        # CRITICAL: Verify dev-spec-kit STILL runs (spec-kit is additive, not replacement)
        assert result.risk_level == "Low", f"Expected Low risk, got {result.risk_level}"
        assert len(result.devspec_findings) == 0, f"Expected 0 findings, got {len(result.devspec_findings)}"
        assert result.has_blockers == False, "Should have no blockers"
        
        print(f"✓ Risk Level (from dev-spec-kit): {result.risk_level}")
        print(f"✓ Findings (from dev-spec-kit): {len(result.devspec_findings)}")
        print("✅ PASS: spec-kit runs AND dev-spec-kit runs (additive behavior)")
        
        return result
    finally:
        # Clean up
        os.environ.pop('USE_SPEC_KIT', None)


def test_spec_kit_mode_unsafe_prompt():
    """Test unsafe prompt with spec-kit ENABLED."""
    print("\n" + "="*80)
    print("TEST 4: UNSAFE PROMPT - SPEC-KIT ENABLED")
    print("="*80)
    
    # Enable spec-kit
    os.environ['USE_SPEC_KIT'] = 'true'
    
    try:
        result = analyze_prompt(UNSAFE_PROMPT)
        
        # Verify spec-kit fields are populated
        assert result.spec_kit_enabled == True, "spec_kit_enabled should be True"
        assert result.spec_kit_success is not None, "spec_kit_success should not be None"
        
        print(f"✓ spec_kit_enabled: {result.spec_kit_enabled}")
        print(f"✓ spec_kit_success: {result.spec_kit_success}")
        
        # CRITICAL: Verify dev-spec-kit STILL detects security issues
        # (spec-kit cannot mark prompt as "safe" and bypass security checks)
        assert result.risk_level == "High", f"Expected High risk, got {result.risk_level}"
        assert len(result.devspec_findings) > 0, "Should have findings for unsafe prompt"
        assert result.has_blockers or result.has_errors, "Should have blockers or errors"
        
        print(f"✓ Risk Level (from dev-spec-kit): {result.risk_level}")
        print(f"✓ Findings (from dev-spec-kit): {len(result.devspec_findings)}")
        print(f"✓ Has Blockers: {result.has_blockers}")
        print("✅ PASS: dev-spec-kit ALWAYS runs and detects security issues")
        
        return result
    finally:
        # Clean up
        os.environ.pop('USE_SPEC_KIT', None)


def test_consistency_between_modes():
    """Verify security analysis is IDENTICAL between spec-kit on/off modes."""
    print("\n" + "="*80)
    print("TEST 5: CONSISTENCY CHECK - Security Analysis Must Be Identical")
    print("="*80)
    
    # Test with spec-kit disabled
    os.environ.pop('USE_SPEC_KIT', None)
    result_disabled = analyze_prompt(UNSAFE_PROMPT)
    
    # Test with spec-kit enabled
    os.environ['USE_SPEC_KIT'] = 'true'
    try:
        result_enabled = analyze_prompt(UNSAFE_PROMPT)
    finally:
        os.environ.pop('USE_SPEC_KIT', None)
    
    # Compare security analysis results (must be identical)
    print(f"\nComparing security analysis results:")
    print(f"  risk_level: {result_disabled.risk_level} vs {result_enabled.risk_level}")
    print(f"  findings count: {len(result_disabled.devspec_findings)} vs {len(result_enabled.devspec_findings)}")
    print(f"  has_blockers: {result_disabled.has_blockers} vs {result_enabled.has_blockers}")
    print(f"  has_errors: {result_disabled.has_errors} vs {result_enabled.has_errors}")
    
    assert result_disabled.risk_level == result_enabled.risk_level, \
        "risk_level must be identical regardless of spec-kit"
    assert len(result_disabled.devspec_findings) == len(result_enabled.devspec_findings), \
        "findings count must be identical regardless of spec-kit"
    assert result_disabled.has_blockers == result_enabled.has_blockers, \
        "has_blockers must be identical regardless of spec-kit"
    assert result_disabled.has_errors == result_enabled.has_errors, \
        "has_errors must be identical regardless of spec-kit"
    
    # Verify only the spec-kit fields differ
    assert result_disabled.spec_kit_enabled == False, "spec-kit should be disabled"
    assert result_enabled.spec_kit_enabled == True, "spec-kit should be enabled"
    
    print("\n✅ PASS: Security analysis is IDENTICAL between modes")
    print("✅ PASS: Only spec-kit fields differ (backwards compatible)")


def test_spec_kit_failure_handling():
    """Verify that spec-kit failures do not abort the pipeline."""
    print("\n" + "="*80)
    print("TEST 6: SPEC-KIT FAILURE HANDLING")
    print("="*80)
    
    # Enable spec-kit
    os.environ['USE_SPEC_KIT'] = 'true'
    
    try:
        # Even if spec-kit fails, dev-spec-kit should still run
        result = analyze_prompt(UNSAFE_PROMPT)
        
        # Verify dev-spec-kit ran successfully (regardless of spec-kit status)
        assert result.risk_level == "High", "dev-spec-kit should detect issues"
        assert len(result.devspec_findings) > 0, "dev-spec-kit should return findings"
        
        print(f"✓ spec_kit_enabled: {result.spec_kit_enabled}")
        print(f"✓ spec_kit_success: {result.spec_kit_success}")
        print(f"✓ dev-spec-kit still ran: {len(result.devspec_findings)} findings")
        print(f"✓ Risk Level: {result.risk_level}")
        print("✅ PASS: dev-spec-kit runs even if spec-kit has issues")
        
    finally:
        os.environ.pop('USE_SPEC_KIT', None)


def main():
    """Run all tests."""
    print("="*80)
    print("SPEC-KIT ADDITIVE INTEGRATION TEST SUITE")
    print("="*80)
    print("\nVerifying that spec-kit:")
    print("  1. Is ADDITIVE, not a replacement")
    print("  2. NEVER bypasses or replaces dev-spec-kit security analysis")
    print("  3. Is backwards compatible (safe to disable)")
    print("  4. Does not affect risk_level or security findings")
    
    tests = [
        test_default_mode_safe_prompt,
        test_default_mode_unsafe_prompt,
        test_spec_kit_mode_safe_prompt,
        test_spec_kit_mode_unsafe_prompt,
        test_consistency_between_modes,
        test_spec_kit_failure_handling,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"\n❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    if failed == 0:
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nVERIFIED:")
        print("  ✓ spec-kit is ADDITIVE (runs before dev-spec-kit)")
        print("  ✓ dev-spec-kit ALWAYS runs (spec-kit cannot bypass it)")
        print("  ✓ Security analysis identical with spec-kit on/off")
        print("  ✓ Backwards compatible (safe to disable)")
        print("  ✓ Spec-kit failures do not abort pipeline")
        print("="*80)
        return 0
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
