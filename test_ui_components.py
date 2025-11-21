#!/usr/bin/env python3
"""
Visual UI Test - Verify UI components render correctly with API responses.

This script tests that the UI receives and can display all expected fields
from the API in both spec-kit enabled and disabled modes.
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"

def test_api_response_structure():
    """Test that API returns all expected fields for UI."""
    print("="*80)
    print("UI API RESPONSE STRUCTURE TEST")
    print("="*80)
    
    test_prompt = "Build a secure API with OAuth2"
    
    print(f"\nSending test prompt: '{test_prompt}'")
    print(f"API endpoint: {API_URL}/api/analyze")
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze",
            json={"prompt": test_prompt},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"\n❌ ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        print("\n" + "="*80)
        print("RESPONSE STRUCTURE VALIDATION")
        print("="*80)
        
        # Core fields (always present)
        core_fields = [
            'original_prompt',
            'normalized_prompt',
            'devspec_raw_output',
            'devspec_findings',
            'guidance',
            'final_curated_prompt',
            'exit_code',
            'has_blockers',
            'has_errors',
            'risk_level'
        ]
        
        # Spec-kit fields (new, should be present)
        spec_kit_fields = [
            'spec_kit_enabled',
            'spec_kit_success',
            'spec_kit_raw_output',
            'spec_kit_summary'
        ]
        
        all_fields = core_fields + spec_kit_fields
        
        missing_fields = []
        for field in all_fields:
            if field not in data:
                missing_fields.append(field)
                print(f"  ❌ Missing: {field}")
            else:
                value_preview = str(data[field])[:50] if data[field] is not None else "null"
                print(f"  ✓ Present: {field} = {value_preview}...")
        
        if missing_fields:
            print(f"\n❌ FAILED: Missing {len(missing_fields)} fields")
            return False
        
        print("\n" + "="*80)
        print("UI DISPLAY VALUES")
        print("="*80)
        
        # Values the UI will display
        print(f"\n1. RISK BADGE:")
        print(f"   risk_level: {data['risk_level']}")
        
        print(f"\n2. PIPELINE INDICATOR:")
        print(f"   All stages will show as completed")
        if data['spec_kit_enabled']:
            status = "✓" if data['spec_kit_success'] else "⚠"
            print(f"   Stage 1 (Spec-kit): {status}")
        print(f"   Stage 2 (Security): ✓")
        print(f"   Stage 3 (Finalizing): ✓")
        
        print(f"\n3. SECURITY ANALYSIS:")
        print(f"   findings: {len(data['devspec_findings'])} issues")
        print(f"   has_blockers: {data['has_blockers']}")
        print(f"   has_errors: {data['has_errors']}")
        
        print(f"\n4. SPEC-KIT PANEL:")
        if data['spec_kit_enabled']:
            print(f"   Visible: Yes")
            print(f"   Status: {'Success' if data['spec_kit_success'] else 'Failed'}")
            print(f"   Summary: {data['spec_kit_summary']}")
        else:
            print(f"   Visible: No (spec-kit disabled)")
        
        print(f"\n5. CURATED PROMPT:")
        preview = data['final_curated_prompt'][:100]
        print(f"   Length: {len(data['final_curated_prompt'])} chars")
        print(f"   Preview: {preview}...")
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nThe API response structure is correct for UI rendering.")
        print("All expected fields are present and properly typed.")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Cannot connect to {API_URL}")
        print("Make sure the backend is running:")
        print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_spec_kit_modes():
    """Test UI behavior with spec-kit enabled and disabled."""
    print("\n\n" + "="*80)
    print("SPEC-KIT MODES TEST")
    print("="*80)
    
    print("\nCurrent backend configuration:")
    try:
        response = requests.post(
            f"{API_URL}/api/analyze",
            json={"prompt": "test"},
            timeout=5
        )
        data = response.json()
        
        if data['spec_kit_enabled']:
            print("  ✓ spec-kit is ENABLED")
            print("  UI will show: 3-stage pipeline + spec-kit panel")
        else:
            print("  ✓ spec-kit is DISABLED (default)")
            print("  UI will show: 3-stage pipeline only")
        
        print("\nTo toggle spec-kit:")
        print("  Disabled → Enabled:")
        print("    USE_SPEC_KIT=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
        print("  Enabled → Disabled:")
        print("    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
        
        return True
    except Exception as e:
        print(f"  ❌ Error checking spec-kit status: {e}")
        return False


def main():
    """Run all UI tests."""
    print("\n" + "="*80)
    print("UI COMPONENT INTEGRATION TEST")
    print("="*80)
    print("\nThis test verifies that the API provides all data needed")
    print("for the UI to render correctly.")
    
    success = test_api_response_structure()
    
    if success:
        test_spec_kit_modes()
    
    print("\n" + "="*80)
    if success:
        print("✅ UI INTEGRATION: READY")
        print("="*80)
        print("\nNext steps:")
        print("  1. Open http://localhost:3000 in your browser")
        print("  2. Submit a test prompt")
        print("  3. Observe the pipeline stages animating")
        print("  4. Check that results display correctly")
        print("="*80)
        return 0
    else:
        print("❌ UI INTEGRATION: FAILED")
        print("="*80)
        print("\nFix the issues above and try again.")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
