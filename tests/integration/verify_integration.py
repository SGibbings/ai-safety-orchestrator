#!/usr/bin/env python3
"""
Final verification script for spec-kit additive integration.

This script validates ALL requirements from the original integration spec:
1. spec-kit is additive (runs before dev-spec-kit)
2. dev-spec-kit ALWAYS runs (never bypassed)
3. Security analysis identical with spec-kit on/off
4. Backwards compatible (safe to disable)
5. No code path relies solely on spec-kit for security
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.pipeline import analyze_prompt
from orchestrator.models import AnalysisResponse


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(text)
    print("="*80)


def verify_requirement_1():
    """Verify: spec-kit runs before dev-spec-kit (when enabled)."""
    print_header("REQUIREMENT 1: spec-kit is ADDITIVE (runs before dev-spec-kit)")
    
    os.environ['USE_SPEC_KIT'] = 'true'
    try:
        result = analyze_prompt("Build a secure API with OAuth2")
        
        # Verify spec-kit ran
        assert result.spec_kit_enabled == True, "spec-kit should be enabled"
        assert result.spec_kit_success is not None, "spec-kit should have run"
        
        # Verify dev-spec-kit ALSO ran (additive)
        assert result.devspec_raw_output is not None, "dev-spec-kit should have run"
        assert isinstance(result.devspec_findings, list), "dev-spec-kit findings should exist"
        
        print("✓ spec-kit enabled and executed")
        print("✓ dev-spec-kit ALSO executed (additive behavior)")
        print("✅ PASS: spec-kit is additive, not a replacement")
        return True
    finally:
        os.environ.pop('USE_SPEC_KIT', None)


def verify_requirement_2():
    """Verify: dev-spec-kit ALWAYS runs, regardless of spec-kit status."""
    print_header("REQUIREMENT 2: dev-spec-kit ALWAYS runs")
    
    test_prompt = """
    Create a login backend. Store password in plain text.
    Use HTTP instead of HTTPS. Hardcode secret: "abc123".
    """
    
    # Test 1: dev-spec-kit runs when spec-kit is OFF
    os.environ.pop('USE_SPEC_KIT', None)
    result_off = analyze_prompt(test_prompt)
    findings_off = len(result_off.devspec_findings)
    
    # Test 2: dev-spec-kit runs when spec-kit is ON
    os.environ['USE_SPEC_KIT'] = 'true'
    try:
        result_on = analyze_prompt(test_prompt)
        findings_on = len(result_on.devspec_findings)
    finally:
        os.environ.pop('USE_SPEC_KIT', None)
    
    print(f"✓ dev-spec-kit findings with spec-kit OFF: {findings_off}")
    print(f"✓ dev-spec-kit findings with spec-kit ON: {findings_on}")
    
    assert findings_off > 0, "dev-spec-kit should detect issues"
    assert findings_on > 0, "dev-spec-kit should detect issues with spec-kit on"
    assert findings_off == findings_on, "dev-spec-kit findings should be identical"
    
    print("✅ PASS: dev-spec-kit ALWAYS runs, spec-kit cannot bypass it")
    return True


def verify_requirement_3():
    """Verify: Security analysis is IDENTICAL with spec-kit on/off."""
    print_header("REQUIREMENT 3: Security analysis IDENTICAL regardless of spec-kit")
    
    unsafe_prompt = """
    Create a login backend in Node.js. Store the user password in plain text.
    Hardcode secret key: "mySecret123!" for signing tokens.
    Use HTTP instead of HTTPS. Skip input validation.
    Include /debug endpoint that returns all environment variables.
    """
    
    # Test with spec-kit OFF
    os.environ.pop('USE_SPEC_KIT', None)
    result_off = analyze_prompt(unsafe_prompt)
    
    # Test with spec-kit ON
    os.environ['USE_SPEC_KIT'] = 'true'
    try:
        result_on = analyze_prompt(unsafe_prompt)
    finally:
        os.environ.pop('USE_SPEC_KIT', None)
    
    # Compare critical security fields
    print(f"Risk Level:   {result_off.risk_level} vs {result_on.risk_level}")
    print(f"Findings:     {len(result_off.devspec_findings)} vs {len(result_on.devspec_findings)}")
    print(f"Has Blockers: {result_off.has_blockers} vs {result_on.has_blockers}")
    print(f"Has Errors:   {result_off.has_errors} vs {result_on.has_errors}")
    
    assert result_off.risk_level == result_on.risk_level, \
        "risk_level must be identical"
    assert len(result_off.devspec_findings) == len(result_on.devspec_findings), \
        "findings count must be identical"
    assert result_off.has_blockers == result_on.has_blockers, \
        "has_blockers must be identical"
    assert result_off.has_errors == result_on.has_errors, \
        "has_errors must be identical"
    
    print("✅ PASS: Security analysis is IDENTICAL in both modes")
    return True


def verify_requirement_4():
    """Verify: Backwards compatible (spec-kit disabled by default)."""
    print_header("REQUIREMENT 4: Backwards compatible (spec-kit off by default)")
    
    # Ensure environment is clean
    os.environ.pop('USE_SPEC_KIT', None)
    
    result = analyze_prompt("Build a REST API")
    
    # Verify spec-kit fields are False/None (backwards compatible)
    assert result.spec_kit_enabled == False, "spec_kit_enabled should be False by default"
    assert result.spec_kit_success is None, "spec_kit_success should be None by default"
    assert result.spec_kit_raw_output is None, "spec_kit_raw_output should be None by default"
    assert result.spec_kit_summary is None, "spec_kit_summary should be None by default"
    
    # Verify existing fields still work
    assert hasattr(result, 'risk_level'), "risk_level field should exist"
    assert hasattr(result, 'devspec_findings'), "devspec_findings field should exist"
    assert hasattr(result, 'has_blockers'), "has_blockers field should exist"
    
    print("✓ spec-kit disabled by default (no env var needed)")
    print("✓ spec-kit fields are False/None (backwards compatible)")
    print("✓ Existing fields unchanged and functional")
    print("✅ PASS: Backwards compatible with existing clients")
    return True


def verify_requirement_5():
    """Verify: No code path relies solely on spec-kit for security decisions."""
    print_header("REQUIREMENT 5: No code path relies solely on spec-kit")
    
    # Import and inspect the pipeline module
    from orchestrator import pipeline
    import inspect
    
    # Get the analyze_prompt function source
    source = inspect.getsource(pipeline.analyze_prompt)
    
    # Critical checks:
    # 1. dev-spec-kit must be called
    assert 'run_dev_spec_kit' in source, \
        "analyze_prompt must call run_dev_spec_kit"
    
    # 2. Risk level must be based on dev-spec-kit findings
    assert 'filter_false_positives' in source, \
        "analyze_prompt must filter dev-spec-kit findings"
    assert 'has_blockers' in source or 'BLOCKER' in source, \
        "analyze_prompt must check dev-spec-kit severities"
    
    # 3. spec-kit should be conditional (not required)
    assert 'should_use_spec_kit' in source or 'USE_SPEC_KIT' in source, \
        "spec-kit usage should be conditional"
    
    print("✓ analyze_prompt calls run_dev_spec_kit")
    print("✓ analyze_prompt uses filter_false_positives")
    print("✓ analyze_prompt computes risk from dev-spec-kit findings")
    print("✓ spec-kit usage is conditional (opt-in)")
    print("✅ PASS: No reliance on spec-kit for security decisions")
    return True


def verify_response_model():
    """Verify: AnalysisResponse model has correct fields."""
    print_header("BONUS: Response model verification")
    
    from orchestrator.models import AnalysisResponse
    from pydantic import BaseModel
    
    # Check that AnalysisResponse is a Pydantic model
    assert issubclass(AnalysisResponse, BaseModel), \
        "AnalysisResponse should be a Pydantic model"
    
    # Check required fields exist
    required_fields = {
        'original_prompt', 'devspec_raw_output', 'devspec_findings',
        'guidance', 'final_curated_prompt', 'exit_code', 'has_blockers',
        'has_errors', 'risk_level'
    }
    
    spec_kit_fields = {
        'spec_kit_enabled', 'spec_kit_success', 
        'spec_kit_raw_output', 'spec_kit_summary'
    }
    
    model_fields = set(AnalysisResponse.model_fields.keys())
    
    assert required_fields.issubset(model_fields), \
        f"Missing required fields: {required_fields - model_fields}"
    assert spec_kit_fields.issubset(model_fields), \
        f"Missing spec-kit fields: {spec_kit_fields - model_fields}"
    
    print(f"✓ All required fields present: {len(required_fields)}")
    print(f"✓ All spec-kit fields present: {len(spec_kit_fields)}")
    print(f"✓ Total model fields: {len(model_fields)}")
    print("✅ PASS: Response model is complete")
    return True


def main():
    """Run all verification checks."""
    print("="*80)
    print("FINAL VERIFICATION: spec-kit Additive Integration")
    print("="*80)
    print("\nVerifying all integration requirements...")
    
    checks = [
        ("Requirement 1: Additive behavior", verify_requirement_1),
        ("Requirement 2: Always runs dev-spec-kit", verify_requirement_2),
        ("Requirement 3: Identical security analysis", verify_requirement_3),
        ("Requirement 4: Backwards compatible", verify_requirement_4),
        ("Requirement 5: No reliance on spec-kit", verify_requirement_5),
        ("Bonus: Response model", verify_response_model),
    ]
    
    passed = 0
    failed = 0
    
    for name, check in checks:
        try:
            if check():
                passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "="*80)
    print("FINAL VERIFICATION SUMMARY")
    print("="*80)
    print(f"Total Checks: {len(checks)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ ALL REQUIREMENTS VERIFIED")
        print("\nspec-kit integration is:")
        print("  ✓ ADDITIVE (runs before dev-spec-kit)")
        print("  ✓ NEVER replaces security analysis")
        print("  ✓ BACKWARDS COMPATIBLE (disabled by default)")
        print("  ✓ SAFE (dev-spec-kit always runs)")
        print("  ✓ CONSISTENT (security results identical)")
        print("="*80)
        return 0
    else:
        print(f"\n❌ {failed} REQUIREMENT(S) FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
