"""
Test suite for the 5 demo prompts used for system calibration.

These tests ensure that the risk classification, spec quality scoring,
and curated prompt generation all work correctly for presentation demos.
"""
import pytest
import json
import subprocess
from pathlib import Path


@pytest.fixture(scope="module")
def api_endpoint():
    """Get the API endpoint URL."""
    return "http://localhost:8000/api/analyze"


def call_api(api_endpoint: str, prompt_file: str) -> dict:
    """Call the analysis API with a prompt file."""
    filepath = Path(f"test_prompts/{prompt_file}")
    prompt_text = filepath.read_text().strip()
    
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", api_endpoint,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"prompt": prompt_text})],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"API call failed: {result.stderr}")
    
    return json.loads(result.stdout)


# ============================================================================
# P1: Low Risk, Good Quality
# ============================================================================

def test_demo_1_low_risk_good_quality(api_endpoint):
    """
    P1: Low risk, good quality spec.
    
    Expected:
    - Risk: Low
    - Quality: 75-95
    - Findings: 0 BLOCKER, 0 ERROR, 0-2 WARNING
    - Curated: No critical/quality sections, just notes if warnings exist
    """
    response = call_api(api_endpoint, "demo_1_low_good.txt")
    
    risk = response.get("risk_level")
    quality = response.get("spec_quality_score")
    findings = response.get("devspec_findings", [])
    curated = response.get("final_curated_prompt", "")
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    
    # Risk classification
    assert risk == "Low", f"P1 should be Low risk, got {risk}"
    
    # Quality score
    assert 75 <= quality <= 95, f"P1 quality should be 75-95, got {quality}"
    
    # Findings
    assert len(blockers) == 0, f"P1 should have 0 BLOCKERs, got {len(blockers)}"
    assert len(errors) == 0, f"P1 should have 0 ERRORs, got {len(errors)}"
    assert len(warnings) <= 2, f"P1 should have 0-2 WARNINGs, got {len(warnings)}"
    
    # Curated prompt should not have critical/quality sections
    assert "CRITICAL SECURITY ISSUES" not in curated, "P1 should not have critical issues section"
    assert "Quality and Design Concerns" not in curated, "P1 should not have quality concerns section"


# ============================================================================
# P2: Medium Risk (Warnings Only)
# ============================================================================

def test_demo_2_medium_risk_warnings(api_endpoint):
    """
    P2: Medium risk from accumulated warnings.
    
    Expected:
    - Risk: Medium
    - Quality: 45-70
    - Findings: 0 BLOCKER, 0 ERROR, 3+ WARNING
    - Curated: Should have "Quality and Design Concerns" section
    """
    response = call_api(api_endpoint, "demo_2_medium_warnings.txt")
    
    risk = response.get("risk_level")
    quality = response.get("spec_quality_score")
    findings = response.get("devspec_findings", [])
    curated = response.get("final_curated_prompt", "")
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    
    # Risk classification
    assert risk == "Medium", f"P2 should be Medium risk, got {risk}"
    
    # Quality score (lower due to vagueness and missing details)
    assert 45 <= quality <= 70, f"P2 quality should be 45-70, got {quality}"
    
    # Findings
    assert len(blockers) == 0, f"P2 should have 0 BLOCKERs, got {len(blockers)}"
    assert len(errors) == 0, f"P2 should have 0 ERRORs, got {len(errors)}"
    assert len(warnings) >= 3, f"P2 should have 3+ WARNINGs, got {len(warnings)}"
    
    # Curated prompt should have quality concerns section
    assert "Quality and Design Concerns" in curated, "P2 should have quality concerns section"
    assert "CRITICAL SECURITY ISSUES" not in curated, "P2 should not have critical issues section"
    
    # Should mention the specific concerns
    assert any(code in ["SEC_AUTH_DEFERRED", "ARCH_VAGUE_DATABASE", "QUAL_NO_TESTING"] 
               for code in [f["code"] for f in warnings]), "P2 should have expected warning codes"


# ============================================================================
# P3: High Risk (Multiple Vulnerabilities)
# ============================================================================

def test_demo_3_high_risk_multiple_vulns(api_endpoint):
    """
    P3: High risk from multiple critical vulnerabilities.
    
    Expected:
    - Risk: High
    - Quality: 55-85
    - Findings: 1+ BLOCKER, possibly ERRORs/WARNINGs
    - Curated: Should have "CRITICAL SECURITY ISSUES" section
    """
    response = call_api(api_endpoint, "demo_3_high_vulns.txt")
    
    risk = response.get("risk_level")
    quality = response.get("spec_quality_score")
    findings = response.get("devspec_findings", [])
    curated = response.get("final_curated_prompt", "")
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    blocker_codes = [f["code"] for f in blockers]
    
    # Risk classification
    assert risk == "High", f"P3 should be High risk, got {risk}"
    
    # Quality score (middle tier)
    assert 55 <= quality <= 85, f"P3 quality should be 55-85, got {quality}"
    
    # Findings
    assert len(blockers) >= 1, f"P3 should have 1+ BLOCKERs, got {len(blockers)}"
    
    # Expected BLOCKERs from P3 prompt
    expected_blockers = ["SEC_HTTP_FOR_AUTH", "SEC_HARDCODED_SECRET", "SEC_DEBUG_DUMPS_CONFIG"]
    found_expected = [code for code in expected_blockers if code in blocker_codes]
    assert len(found_expected) >= 2, f"P3 should have at least 2 of {expected_blockers}, got {blocker_codes}"
    
    # Curated prompt should have critical issues section
    assert "CRITICAL SECURITY ISSUES" in curated or "⚠️" in curated, "P3 should have critical issues section"
    assert "Quality and Design Concerns" not in curated, "P3 should not have quality concerns section"


# ============================================================================
# P4: Low Risk, Tiny/Minimal Spec
# ============================================================================

def test_demo_4_low_risk_tiny_spec(api_endpoint):
    """
    P4: Low risk, minimal/tiny spec.
    
    Expected:
    - Risk: Low (no escalation despite 3 warnings - minimal spec exemption)
    - Quality: 35-60 (low due to brevity)
    - Findings: 0 BLOCKER, 0 ERROR, possibly 3 WARNINGs
    - Curated: Minimal notes, no critical/quality sections
    """
    response = call_api(api_endpoint, "demo_4_low_tiny.txt")
    
    risk = response.get("risk_level")
    quality = response.get("spec_quality_score")
    findings = response.get("devspec_findings", [])
    curated = response.get("final_curated_prompt", "")
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    
    # Risk classification (should be Low despite warnings due to minimal spec)
    assert risk == "Low", f"P4 should be Low risk (minimal spec exemption), got {risk}"
    
    # Quality score (low due to brevity and lack of detail)
    assert 35 <= quality <= 60, f"P4 quality should be 35-60, got {quality}"
    
    # Findings
    assert len(blockers) == 0, f"P4 should have 0 BLOCKERs, got {len(blockers)}"
    assert len(errors) == 0, f"P4 should have 0 ERRORs, got {len(errors)}"
    # May have warnings but they don't escalate due to minimal spec exemption
    
    # Curated prompt should not have critical/quality sections
    assert "CRITICAL SECURITY ISSUES" not in curated, "P4 should not have critical issues section"
    assert "Quality and Design Concerns" not in curated, "P4 should not have quality concerns section"


# ============================================================================
# P5: High Risk, High Quality (Detailed with Fatal Flaw)
# ============================================================================

def test_demo_5_high_risk_detailed(api_endpoint):
    """
    P5: High risk, high quality spec (detailed but with critical flaw).
    
    Expected:
    - Risk: High
    - Quality: 85-100 (high due to detail)
    - Findings: 1+ BLOCKER (payout dump), possibly ERRORs
    - Curated: Should have "CRITICAL SECURITY ISSUES" section
    """
    response = call_api(api_endpoint, "demo_5_high_detailed.txt")
    
    risk = response.get("risk_level")
    quality = response.get("spec_quality_score")
    findings = response.get("devspec_findings", [])
    curated = response.get("final_curated_prompt", "")
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    blocker_codes = [f["code"] for f in blockers]
    
    # Risk classification
    assert risk == "High", f"P5 should be High risk, got {risk}"
    
    # Quality score (highest tier due to comprehensive detail)
    assert 85 <= quality <= 100, f"P5 quality should be 85-100, got {quality}"
    
    # Findings
    assert len(blockers) >= 1, f"P5 should have 1+ BLOCKERs, got {len(blockers)}"
    
    # Expected BLOCKER from P5 prompt (debug payout dump)
    assert "SEC_DEBUG_PAYOUT_DUMP" in blocker_codes, \
        f"P5 should have SEC_DEBUG_PAYOUT_DUMP, got {blocker_codes}"
    
    # Curated prompt should have critical issues section
    assert "CRITICAL SECURITY ISSUES" in curated or "⚠️" in curated, "P5 should have critical issues section"
    assert "Quality and Design Concerns" not in curated, "P5 should not have quality concerns section"
    
    # Should mention the payout/financial data exposure
    assert "payout" in curated.lower() or "financial" in curated.lower(), \
        "P5 curated should mention payout/financial data issue"


# ============================================================================
# Cross-Cutting Tests
# ============================================================================

def test_quality_score_ordering(api_endpoint):
    """
    Test that quality scores follow expected ordering:
    P1/P5 (high detail) > P3 (moderate) > P2 (vague) > P4 (minimal)
    """
    responses = {}
    for label, filename in [
        ("P1", "demo_1_low_good.txt"),
        ("P2", "demo_2_medium_warnings.txt"),
        ("P3", "demo_3_high_vulns.txt"),
        ("P4", "demo_4_low_tiny.txt"),
        ("P5", "demo_5_high_detailed.txt")
    ]:
        response = call_api(api_endpoint, filename)
        responses[label] = response.get("spec_quality_score")
    
    # P1 and P5 should be highest tier (both detailed, secure specs)
    assert responses["P1"] >= 75, f"P1 quality should be ≥75, got {responses['P1']}"
    assert responses["P5"] >= 85, f"P5 quality should be ≥85, got {responses['P5']}"
    
    # P4 should be lowest (minimal spec)
    assert responses["P4"] <= 60, f"P4 quality should be ≤60, got {responses['P4']}"
    
    # P2 should be lower than P1 and P3 (vague, missing details)
    assert responses["P2"] < responses["P1"], f"P2 ({responses['P2']}) should be < P1 ({responses['P1']})"
    assert responses["P2"] < responses["P3"], f"P2 ({responses['P2']}) should be < P3 ({responses['P3']})"
    
    print(f"✓ Quality score ordering correct: P1={responses['P1']}, P2={responses['P2']}, "
          f"P3={responses['P3']}, P4={responses['P4']}, P5={responses['P5']}")


def test_curated_prompt_consistency(api_endpoint):
    """
    Test that curated prompts are consistent with risk levels:
    - High risk → CRITICAL section
    - Medium (warnings) → Quality Concerns section
    - Low risk → No critical/quality sections
    """
    test_cases = [
        ("demo_1_low_good.txt", "Low", False, False),
        ("demo_2_medium_warnings.txt", "Medium", False, True),
        ("demo_3_high_vulns.txt", "High", True, False),
        ("demo_4_low_tiny.txt", "Low", False, False),
        ("demo_5_high_detailed.txt", "High", True, False)
    ]
    
    for filename, expected_risk, should_have_critical, should_have_quality in test_cases:
        response = call_api(api_endpoint, filename)
        risk = response.get("risk_level")
        curated = response.get("final_curated_prompt", "")
        
        has_critical = "CRITICAL SECURITY ISSUES" in curated or "⚠️" in curated
        has_quality = "Quality and Design Concerns" in curated
        
        assert risk == expected_risk, f"{filename}: Risk should be {expected_risk}, got {risk}"
        
        if should_have_critical:
            assert has_critical, f"{filename}: Should have CRITICAL section"
        else:
            assert not has_critical, f"{filename}: Should NOT have CRITICAL section"
        
        if should_have_quality:
            assert has_quality, f"{filename}: Should have Quality Concerns section"
        else:
            assert not has_quality, f"{filename}: Should NOT have Quality Concerns section"
    
    print("✓ All curated prompts consistent with risk levels")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
