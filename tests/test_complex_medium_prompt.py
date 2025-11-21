"""
Regression test for complex Medium risk classification.

This test validates that realistic, complex prompts with ERROR-level findings
(but no BLOCKERs) correctly produce Medium risk classification.

Test Scenario:
A financial profile API with:
- Gateway header trust (ERROR)
- Debug endpoint with 25 records (ERROR)
- Partial PII logging (controlled)
- Good security practices (encrypted data, HTTPS, env secrets)

This prompt should produce Medium risk, not High.
"""
import pytest
import json
import subprocess
from pathlib import Path


@pytest.fixture(scope="module")
def test_prompts_dir():
    """Get the test prompts directory path."""
    return Path(__file__).parent.parent / "test_prompts"


@pytest.fixture(scope="module")
def api_endpoint():
    """Get the API endpoint URL."""
    return "http://localhost:8000/api/analyze"


def call_api(api_endpoint: str, prompt: str) -> dict:
    """
    Call the analysis API with a prompt.
    
    Args:
        api_endpoint: API URL
        prompt: Prompt text to analyze
        
    Returns:
        API response as dict
    """
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", api_endpoint,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"prompt": prompt})],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"API call failed: {result.stderr}")
    
    return json.loads(result.stdout)


def test_complex_financial_medium_risk(test_prompts_dir, api_endpoint):
    """
    Test that complex financial API prompt produces Medium risk.
    
    This is a realistic enterprise scenario with:
    - Multiple security considerations
    - Some good practices (HTTPS, encryption, env vars)
    - Some concerning practices (gateway header trust, debug endpoint)
    
    Expected:
    - Risk: Medium (not High, not Low)
    - ERROR findings present
    - NO BLOCKER findings
    - Quality score in reasonable range
    """
    # Read the complex prompt
    prompt_path = test_prompts_dir / "complex_financial_medium.txt"
    assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    # Call API
    response = call_api(api_endpoint, prompt)
    
    # Validate response structure
    assert "risk_level" in response, "Response missing risk_level"
    assert "devspec_findings" in response, "Response missing devspec_findings"
    assert "spec_quality_score" in response, "Response missing spec_quality_score"
    
    actual_risk = response["risk_level"]
    findings = response.get("devspec_findings", [])
    score = response.get("spec_quality_score", 0)
    
    # Group findings by severity
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    
    # CRITICAL ASSERTION 1: Must have ZERO BLOCKERs
    assert len(blockers) == 0, (
        f"Complex medium prompt must have NO BLOCKERs.\n"
        f"  Expected: 0 BLOCKERs\n"
        f"  Got: {len(blockers)} BLOCKERs\n"
        f"  BLOCKER findings: {[f['code'] for f in blockers]}\n"
        f"  This indicates a false positive BLOCKER is triggering.\n"
        f"  Review security rules to make patterns more specific."
    )
    
    # CRITICAL ASSERTION 2: Must have at least one ERROR
    assert len(errors) >= 1, (
        f"Complex medium prompt must have ERROR findings.\n"
        f"  Expected: At least 1 ERROR\n"
        f"  Got: {len(errors)} ERRORs\n"
        f"  All findings: {[f['code'] for f in findings]}"
    )
    
    # CRITICAL ASSERTION 3: Risk level must be Medium
    assert actual_risk == "Medium", (
        f"Risk level mismatch for complex financial prompt:\n"
        f"  Expected: Medium\n"
        f"  Got: {actual_risk}\n"
        f"  Findings: {len(blockers)} BLOCKER, {len(errors)} ERROR, {len(warnings)} WARNING\n"
        f"  If High: check for false BLOCKER triggers\n"
        f"  If Low: check that ERROR findings are present"
    )
    
    # Validate specific expected findings
    finding_codes = [f.get("code") for f in findings]
    
    # Should detect gateway header trust
    assert "SEC_TRUSTS_GATEWAY_HEADER" in finding_codes, (
        f"Expected SEC_TRUSTS_GATEWAY_HEADER finding not present.\n"
        f"  Found codes: {finding_codes}"
    )
    
    # Validate quality score is in reasonable range for a mostly-good spec
    # This prompt has good practices (HTTPS, encryption, env vars) but some issues
    # Higher scores (70-100) indicate well-structured specs with security concerns
    assert 55 <= score <= 100, (
        f"Quality score out of expected range for complex medium prompt:\n"
        f"  Expected: 55-100 (good spec with some issues)\n"
        f"  Got: {score}"
    )


def test_complex_prompt_no_false_blocker_triggers(test_prompts_dir, api_endpoint):
    """
    Verify that complex enterprise scenarios don't trigger false BLOCKER findings.
    
    Common false positives to avoid:
    - "internal gateway" + "no additional verification" → should NOT trigger SEC_NO_AUTH_INTERNAL
    - "debug endpoint" with moderate data → should be ERROR not BLOCKER
    - "partial PII" in logs → should be WARNING/ERROR not BLOCKER
    """
    prompt_path = test_prompts_dir / "complex_financial_medium.txt"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    blocker_codes = [f.get("code") for f in blockers]
    
    # Specific false positives to check
    false_positive_blockers = {
        "SEC_NO_AUTH_INTERNAL": "Should not trigger on gateway header trust scenarios",
        "SEC_DEBUG_EXPOSES_SECRETS": "Debug endpoint shows metadata, not secrets",
        "SEC_LOGS_PII_EMAIL": "Logs partial identifier (last 4 chars), not full PII"
    }
    
    for blocker_code, reason in false_positive_blockers.items():
        assert blocker_code not in blocker_codes, (
            f"False positive BLOCKER detected: {blocker_code}\n"
            f"  Reason: {reason}\n"
            f"  All BLOCKER codes: {blocker_codes}\n"
            f"  Review pattern specificity in security-check.new.sh"
        )


def test_error_findings_are_accurate(test_prompts_dir, api_endpoint):
    """
    Verify that ERROR findings in complex prompt are accurate and relevant.
    
    Expected ERRORs:
    - SEC_TRUSTS_GATEWAY_HEADER: trusting x-employee-id without verification
    - Possibly SEC_DEBUG_EXPOSES_MULTIPLE_IDS: 25 payroll job IDs
    """
    prompt_path = test_prompts_dir / "complex_financial_medium.txt"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    error_codes = [f.get("code") for f in errors]
    
    # Must have gateway header trust error
    assert "SEC_TRUSTS_GATEWAY_HEADER" in error_codes, (
        f"Expected SEC_TRUSTS_GATEWAY_HEADER not found in ERROR findings.\n"
        f"  ERROR codes: {error_codes}\n"
        f"  Prompt explicitly trusts x-employee-id header from gateway."
    )
    
    # All ERRORs should be legitimate
    # (This is a smoke test - specific codes may vary as rules evolve)
    assert len(errors) > 0, "At least one ERROR finding should be present"


def test_medium_risk_is_stable_across_variations(api_endpoint):
    """
    Test that slight variations of the complex prompt still produce Medium risk.
    
    This ensures the classification is robust, not fragile to wording changes.
    """
    variations = [
        # Variation 1: Different header name
        """
        I'm updating our FastAPI service that processes payroll data.
        The service trusts the "x-user-id" header forwarded by our gateway to identify users.
        No additional verification is performed beyond checking the header exists.
        Add a /debug/activity endpoint that returns the last 20 job IDs and durations.
        """,
        
        # Variation 2: Different record count
        """
        Our internal API processes employee data behind an HTTPS proxy.
        The service will trust the "x-authenticated-user" header sent by our load balancer.
        We're adding a /debug/metrics endpoint that shows the 30 most recent transaction IDs.
        Input validation is partially implemented.
        """,
    ]
    
    for i, prompt in enumerate(variations, 1):
        response = call_api(api_endpoint, prompt.strip())
        
        risk = response.get("risk_level")
        findings = response.get("devspec_findings", [])
        
        blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
        errors = [f for f in findings if f.get("severity") == "ERROR"]
        
        # Each variation should be Medium risk
        assert risk == "Medium", (
            f"Variation {i} produced {risk} instead of Medium.\n"
            f"  BLOCKERs: {len(blockers)}\n"
            f"  ERRORs: {len(errors)}\n"
            f"  This indicates classification is fragile to wording changes."
        )


def test_classification_logic_invariants(test_prompts_dir, api_endpoint):
    """
    Test the fundamental invariants of risk classification logic.
    
    Invariants:
    1. If ANY BLOCKER → High risk
    2. If NO BLOCKER but ERROR exists → Medium risk
    3. If NO BLOCKER/ERROR but WARNING → Low risk
    4. If no findings → Low risk
    """
    prompt_path = test_prompts_dir / "complex_financial_medium.txt"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    warnings = [f for f in findings if f.get("severity") == "WARNING"]
    
    # Invariant: No BLOCKER + ERROR present → MUST be Medium
    if len(blockers) == 0 and len(errors) > 0:
        assert risk == "Medium", (
            f"Classification logic violation:\n"
            f"  Condition: 0 BLOCKER, {len(errors)} ERROR\n"
            f"  Expected: Medium\n"
            f"  Got: {risk}\n"
            f"  This violates the core classification logic."
        )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])
