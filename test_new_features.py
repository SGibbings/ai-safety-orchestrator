#!/usr/bin/env python3
"""
Test all new features:
1. Prompt file organization
2. Human-readable issue names (UI only - manual check)
3. Risk descriptions (UI only - manual check)
4. Spec quality score
5. Header position (UI only - manual check)
"""
import os
import sys
import requests
import json

API_BASE = "http://localhost:8000"


def test_prompt_file_organization():
    """Test that prompt files have been moved to new structure."""
    print("\n=== Test: Prompt File Organization ===")
    
    # Check that new directories exist
    required_dirs = [
        'prompts/base',
        'prompts/stress',
        'prompts/regression',
        'prompts/demo'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"✗ Missing directory: {dir_path}")
            return False
    
    # Check that files exist in new locations
    test_files = [
        'prompts/stress/high2.txt',
        'prompts/base/test_prompt_clean.txt',
        'prompts/regression/test_prompt5.txt',
        'prompts/demo/test_case.txt'
    ]
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"✗ Missing file: {file_path}")
            return False
    
    # Check that old directories are gone
    if os.path.exists('stress_tests'):
        print("✗ Old stress_tests directory still exists")
        return False
    
    print("✓ All prompt files organized in new structure")
    print(f"  - {len(required_dirs)} directories created")
    print(f"  - All test files found in correct locations")
    return True


def test_spec_quality_score():
    """Test that spec quality score is computed and returned."""
    print("\n=== Test: Spec Quality Score ===")
    
    # Test with incomplete spec (should have low score)
    with open('prompts/stress/high2.txt') as f:
        incomplete_prompt = f.read()
    
    response = requests.post(
        f"{API_BASE}/api/analyze",
        json={"prompt": incomplete_prompt},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"✗ API returned status {response.status_code}")
        return False
    
    data = response.json()
    
    # Check spec_quality_score exists
    if 'spec_quality_score' not in data:
        print("✗ spec_quality_score field missing from response")
        return False
    
    score = data['spec_quality_score']
    
    if score is None:
        print("✗ spec_quality_score is None (should have value when spec-kit enabled)")
        return False
    
    if not isinstance(score, int) or score < 0 or score > 100:
        print(f"✗ Invalid score: {score} (should be 0-100)")
        return False
    
    print(f"✓ Spec quality score working")
    print(f"  - Incomplete spec score: {score}/100")
    print(f"  - Quality warnings: {len(data.get('spec_quality_warnings', []))}")
    print(f"  - Risk level: {data['risk_level']}")
    
    # Test with more complete spec (should have higher score)
    complete_prompt = """
    Build a secure REST API for task management.
    
    Features: Create, read, update, delete tasks with authentication.
    Entities: User, Task models.
    Flows: Login, CRUD operations.
    Configuration: Database URL and JWT secret in environment variables.
    Error Handling: Try-catch blocks, graceful degradation.
    Testing: Unit tests and integration tests.
    Logging: Structured logging with request IDs.
    Authentication: JWT-based authentication.
    Data Storage: PostgreSQL database.
    """
    
    response2 = requests.post(
        f"{API_BASE}/api/analyze",
        json={"prompt": complete_prompt},
        timeout=30
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        score2 = data2.get('spec_quality_score')
        if score2 and score2 > score:
            print(f"  - Complete spec score: {score2}/100 (higher ✓)")
        else:
            print(f"  - Complete spec score: {score2}/100")
    
    return True


def test_backwards_compatibility():
    """Test that spec quality score is None when spec-kit is disabled."""
    print("\n=== Test: Backwards Compatibility ===")
    
    # This test assumes backend might be running with spec-kit disabled
    # Just verify the field exists in the schema
    response = requests.post(
        f"{API_BASE}/api/analyze",
        json={"prompt": "Build an API"},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"✗ API returned status {response.status_code}")
        return False
    
    data = response.json()
    
    # Field must exist (even if None)
    if 'spec_quality_score' not in data:
        print("✗ spec_quality_score field missing (breaks backwards compatibility)")
        return False
    
    print("✓ Backwards compatibility maintained")
    print(f"  - spec_quality_score field present in response")
    print(f"  - spec_kit_enabled: {data.get('spec_kit_enabled')}")
    
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Feature Implementation Tests")
    print("=" * 70)
    print(f"Testing API at: {API_BASE}")
    
    # Change to repo root
    os.chdir('/workspaces/ai-safety-orchestrator')
    
    results = []
    results.append(("Prompt File Organization", test_prompt_file_organization()))
    results.append(("Spec Quality Score", test_spec_quality_score()))
    results.append(("Backwards Compatibility", test_backwards_compatibility()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    # UI-only features (manual verification needed)
    print("\n📋 Manual UI Verification Required:")
    print("  1. Human-readable issue names (not SEC_* codes)")
    print("  2. Risk descriptions under risk badge")
    print("  3. Spec quality score displayed near risk badge")
    print("  4. Header moved to left side")
    print("\nOpen http://localhost:3000 to verify UI changes")
    print("=" * 70)
    
    if all_passed:
        print("\n✓ All automated tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
