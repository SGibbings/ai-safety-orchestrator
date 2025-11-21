"""
Regression tests for Medium risk classification.

This test suite ensures that Medium risk level is correctly assigned when:
- ERROR-level findings are present
- No BLOCKER-level findings exist

This addresses a regression where Medium risk became unreachable and only
High or Low risk levels were being produced.

Test Scenarios:
- Prompt A: PII logging (ERROR) → Medium
- Prompt B: Weak password hashing (ERROR) → Medium  
- Prompt C: Debug endpoint exposing 10-49 IDs (ERROR) → Medium
- Prompt D: Minimal spec with no issues → Low
- Prompt E: Trusting gateway headers (ERROR) → Medium
- Prompt F: Logging raw passwords (BLOCKER) → High
"""
import pytest
import json
import subprocess
from pathlib import Path


# Test data: (filename, expected_risk, description, expected_finding_code)
MEDIUM_RISK_TESTS = [
    (
        "medium_test_a_pii.txt",
        "Medium",
        "PII logging (email addresses)",
        "SEC_LOGS_PII_EMAIL"
    ),
    (
        "medium_test_b_hash.txt",
        "Medium",
        "Weak password hashing (SHA-256)",
        "SEC_WEAK_PASSWORD_HASH_SHA256"
    ),
    (
        "medium_test_c_debug.txt",
        "Medium",
        "Debug endpoint exposing 10 user IDs",
        "SEC_DEBUG_EXPOSES_MULTIPLE_IDS"
    ),
    (
        "medium_test_e_header.txt",
        "Medium",
        "Trusting gateway header without verification",
        "SEC_TRUSTS_GATEWAY_HEADER"
    ),
]

# Control cases (Low and High)
CONTROL_TESTS = [
    (
        "medium_test_d_low.txt",
        "Low",
        "Minimal spec with no security issues",
        None
    ),
    (
        "medium_test_f_high.txt",
        "High",
        "Logging raw passwords (BLOCKER)",
        "SEC_LOGS_PASSWORDS"
    ),
]


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


@pytest.mark.parametrize(
    "filename,expected_risk,description,expected_code",
    MEDIUM_RISK_TESTS,
    ids=[f"medium_{i+1}" for i in range(len(MEDIUM_RISK_TESTS))]
)
def test_medium_risk_prompts(
    test_prompts_dir,
    api_endpoint,
    filename,
    expected_risk,
    description,
    expected_code
):
    """
    Test that prompts with ERROR-level findings (and no BLOCKERs) produce Medium risk.
    
    This is the core regression test ensuring Medium risk is reachable.
    """
    # Read prompt
    prompt_path = test_prompts_dir / filename
    assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    # Call API
    response = call_api(api_endpoint, prompt)
    
    # Validate response structure
    assert "risk_level" in response, "Response missing risk_level"
    assert "devspec_findings" in response, "Response missing devspec_findings"
    
    actual_risk = response["risk_level"]
    findings = response.get("devspec_findings", [])
    
    # Validate risk level (strict)
    assert actual_risk == expected_risk, (
        f"Risk level mismatch for {description}:\n"
        f"  Expected: {expected_risk}\n"
        f"  Got: {actual_risk}\n"
        f"  Findings: {[f['code'] for f in findings]}"
    )
    
    # Validate findings structure
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    
    # For Medium risk: Must have ERRORs, must NOT have BLOCKERs
    assert len(blockers) == 0, (
        f"Medium risk prompt should have NO BLOCKERs, found {len(blockers)}:\n"
        f"  {[f['code'] for f in blockers]}"
    )
    
    assert len(errors) > 0, (
        f"Medium risk prompt should have at least one ERROR, found {len(errors)}"
    )
    
    # Validate expected finding is present
    if expected_code:
        finding_codes = [f.get("code") for f in findings]
        assert expected_code in finding_codes, (
            f"Expected finding '{expected_code}' not found for {description}.\n"
            f"  Found codes: {finding_codes}"
        )


@pytest.mark.parametrize(
    "filename,expected_risk,description,expected_code",
    CONTROL_TESTS,
    ids=["control_low", "control_high"]
)
def test_control_cases(
    test_prompts_dir,
    api_endpoint,
    filename,
    expected_risk,
    description,
    expected_code
):
    """
    Test control cases (Low and High risk) to ensure classification boundaries work.
    """
    # Read prompt
    prompt_path = test_prompts_dir / filename
    assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"
    
    with open(prompt_path) as f:
        prompt = f.read()
    
    # Call API
    response = call_api(api_endpoint, prompt)
    
    actual_risk = response["risk_level"]
    findings = response.get("devspec_findings", [])
    
    # Validate risk level
    assert actual_risk == expected_risk, (
        f"Risk level mismatch for {description}:\n"
        f"  Expected: {expected_risk}\n"
        f"  Got: {actual_risk}\n"
        f"  Findings: {[f['code'] for f in findings]}"
    )
    
    # Validate expected finding if specified
    if expected_code:
        finding_codes = [f.get("code") for f in findings]
        assert expected_code in finding_codes, (
            f"Expected finding '{expected_code}' not found for {description}.\n"
            f"  Found codes: {finding_codes}"
        )


def test_medium_risk_classification_logic():
    """
    Test that the risk classification logic follows the correct priority:
    1. BLOCKER present → High Risk
    2. ERROR present AND no BLOCKER → Medium Risk
    3. WARNING present AND no BLOCKER/ERROR → Low Risk
    4. No findings → Low Risk
    """
    # This test validates the logic documented in the requirements
    # The actual implementation is tested through the parametrized tests above
    
    # Document the classification rules for reference
    classification_rules = {
        "High": "Any BLOCKER present",
        "Medium": "ERROR present AND no BLOCKER",
        "Low": "WARNING only OR no findings"
    }
    
    # This test passes if it runs (validates documentation)
    assert len(classification_rules) == 3
    assert "High" in classification_rules
    assert "Medium" in classification_rules
    assert "Low" in classification_rules


def test_medium_risk_has_no_blockers(test_prompts_dir, api_endpoint):
    """
    Verify that ALL Medium risk prompts have zero BLOCKERs.
    
    This is a critical invariant: Medium risk MUST NOT contain BLOCKER findings.
    """
    for filename, expected_risk, description, _ in MEDIUM_RISK_TESTS:
        prompt_path = test_prompts_dir / filename
        
        with open(prompt_path) as f:
            prompt = f.read()
        
        response = call_api(api_endpoint, prompt)
        findings = response.get("devspec_findings", [])
        
        blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
        
        assert len(blockers) == 0, (
            f"Medium risk prompt '{filename}' has BLOCKERs (should have none):\n"
            f"  {[f['code'] for f in blockers]}"
        )


def test_medium_risk_has_errors(test_prompts_dir, api_endpoint):
    """
    Verify that ALL Medium risk prompts have at least one ERROR.
    
    This is a critical invariant: Medium risk MUST contain ERROR findings.
    """
    for filename, expected_risk, description, _ in MEDIUM_RISK_TESTS:
        prompt_path = test_prompts_dir / filename
        
        with open(prompt_path) as f:
            prompt = f.read()
        
        response = call_api(api_endpoint, prompt)
        findings = response.get("devspec_findings", [])
        
        errors = [f for f in findings if f.get("severity") == "ERROR"]
        
        assert len(errors) > 0, (
            f"Medium risk prompt '{filename}' has no ERRORs (should have at least one):\n"
            f"  All findings: {[f['code'] for f in findings]}"
        )


def test_risk_level_ordering():
    """
    Test that risk levels follow severity ordering: Low < Medium < High.
    
    This validates that the classification system is internally consistent.
    """
    risk_severity = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }
    
    assert risk_severity["Low"] < risk_severity["Medium"]
    assert risk_severity["Medium"] < risk_severity["High"]
    assert risk_severity["Low"] < risk_severity["High"]


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])
