#!/usr/bin/env python3
"""
Integration tests for spec-kit adapter.

These tests verify that the spec-kit integration works correctly
and remains isolated from the rest of the codebase.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.spec_kit_adapter import (
    SpecKitAdapter,
    should_use_spec_kit,
    get_adapter
)


def test_adapter_initialization():
    """Test that the adapter can be initialized."""
    print("Testing adapter initialization...")
    adapter = SpecKitAdapter()
    
    assert adapter is not None, "Adapter should be created"
    assert adapter.spec_kit_path is not None, "Adapter should have spec_kit_path"
    print(f"  ✓ Adapter initialized with path: {adapter.spec_kit_path}")


def test_availability_check():
    """Test that the adapter can check if spec-kit is available."""
    print("\nTesting availability check...")
    adapter = SpecKitAdapter()
    
    is_available = adapter.is_available()
    print(f"  ✓ spec-kit available: {is_available}")
    
    # Check prerequisites
    success, message = adapter.check_prerequisites()
    print(f"  ✓ Prerequisites: {message}")


def test_environment_flag():
    """Test that the USE_SPEC_KIT environment variable works."""
    print("\nTesting environment flag...")
    
    # Test default (should be False)
    os.environ.pop('USE_SPEC_KIT', None)
    assert should_use_spec_kit() == False, "Default should be False"
    print("  ✓ Default behavior: use dev-spec-kit (not spec-kit)")
    
    # Test enabled
    os.environ['USE_SPEC_KIT'] = 'true'
    assert should_use_spec_kit() == True, "Should be True when set to 'true'"
    print("  ✓ USE_SPEC_KIT=true enables spec-kit")
    
    # Clean up
    os.environ.pop('USE_SPEC_KIT', None)


def test_get_adapter():
    """Test the get_adapter() helper function."""
    print("\nTesting get_adapter() helper...")
    
    # Should return None by default
    os.environ.pop('USE_SPEC_KIT', None)
    adapter = get_adapter()
    assert adapter is None, "Should return None when disabled"
    print("  ✓ Returns None when USE_SPEC_KIT is not set")
    
    # Should return adapter when enabled
    os.environ['USE_SPEC_KIT'] = 'true'
    adapter = get_adapter()
    assert adapter is not None, "Should return adapter when enabled"
    assert isinstance(adapter, SpecKitAdapter), "Should return SpecKitAdapter instance"
    print("  ✓ Returns SpecKitAdapter when USE_SPEC_KIT=true")
    
    # Clean up
    os.environ.pop('USE_SPEC_KIT', None)


def test_analyze_prompt_compatibility():
    """Test that analyze_prompt maintains API compatibility."""
    print("\nTesting analyze_prompt() API compatibility...")
    adapter = SpecKitAdapter()
    
    test_prompt = "Build a secure login system"
    raw_output, findings, exit_code = adapter.analyze_prompt(test_prompt)
    
    assert isinstance(raw_output, str), "Should return string output"
    assert isinstance(findings, list), "Should return list of findings"
    assert isinstance(exit_code, int), "Should return integer exit code"
    
    # spec-kit doesn't do security analysis, so findings should be empty
    assert len(findings) == 0, "spec-kit doesn't provide security findings"
    assert "WARNING" in raw_output, "Should warn that spec-kit is not a security analyzer"
    
    print("  ✓ API signature matches dev-spec-kit")
    print("  ✓ Returns appropriate warning about spec-kit's purpose")


def test_isolation():
    """Test that spec-kit is properly isolated."""
    print("\nTesting isolation...")
    
    # Ensure spec-kit is not imported anywhere except the adapter
    import orchestrator.pipeline
    import orchestrator.devspec_runner
    
    # These modules should NOT import spec_kit_adapter by default
    assert not hasattr(orchestrator.pipeline, 'SpecKitAdapter'), \
        "pipeline should not import SpecKitAdapter"
    assert not hasattr(orchestrator.devspec_runner, 'SpecKitAdapter'), \
        "devspec_runner should not import SpecKitAdapter"
    
    print("  ✓ spec-kit is isolated to adapter module")
    print("  ✓ No accidental coupling detected")


def main():
    """Run all tests."""
    print("="*80)
    print("SPEC-KIT INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        test_adapter_initialization,
        test_availability_check,
        test_environment_flag,
        test_get_adapter,
        test_analyze_prompt_compatibility,
        test_isolation,
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
            failed += 1
    
    print("\n" + "="*80)
    if failed == 0:
        print("✅ ALL TESTS PASSED")
        print("="*80)
        return 0
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
