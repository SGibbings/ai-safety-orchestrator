"""
Regression tests for dev progression scenarios.

These tests validate that the risk classification pipeline correctly tracks
how security risk and spec quality evolve as a developer iteratively refines
their API design across 6 realistic scenarios.

Test Scenarios (same developer, same project):
1. Low risk, high score (75-95): Comprehensive spec with tests, logging, security
2. Low risk, lower score (50-70): Minimal spec, defers tests
3. Medium risk (65-85): Introduces PII logging (ERROR)
4. Medium risk (70-90): Weak password hashing SHA-256 (ERROR)
5. High risk (70-90): Logs raw passwords (BLOCKER)
6. High risk (45-70): Debug endpoints exposing config + 100 user records (BLOCKER)
"""
import pytest
import json
import subprocess
from pathlib import Path


# Test data: (filename, expected_risk, min_score, max_score, description)
DEV_PROGRESSION_TESTS = [
    (
        "dev_progress_1_low_high.txt",
        "Low",
        75, 95,
        "Comprehensive FastAPI spec with JWT, bcrypt, tests, detailed logging"
    ),
    (
        "dev_progress_2_low_lower.txt",
        "Low",
        50, 70,
        "Same API but defers tests and minimal logging"
    ),
    (
        "dev_progress_3_medium_pii.txt",
        "Medium",
        65, 85,
        "Introduces PII logging (user emails)"
    ),
    (
        "dev_progress_4_medium_hash.txt",
        "Medium",
        70, 90,
        "Switches to SHA-256 password hashing (weak)"
    ),
    (
        "dev_progress_5_high_password.txt",
        "High",
        70, 90,
        "Logs raw passwords in failed login attempts"
    ),
    (
        "dev_progress_6_high_debug.txt",
        "High",
        45, 70,
        "Adds debug endpoints exposing config + 100 user emails"
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
    "filename,expected_risk,min_score,max_score,description",
    DEV_PROGRESSION_TESTS,
    ids=[f"dev_progress_{i+1}" for i in range(len(DEV_PROGRESSION_TESTS))]
)
def test_dev_progression_prompt(
    test_prompts_dir,
    api_endpoint,
    filename,
    expected_risk,
    min_score,
    max_score,
    description
):
    """
    Test a dev progression prompt against expected risk level and quality score.
    
    Validates:
    1. Risk level matches expected (Low/Medium/High)
    2. Quality score falls within expected range (±10 tolerance for spec-kit variability)
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
    assert "spec_quality_score" in response, "Response missing spec_quality_score"
    
    actual_risk = response["risk_level"]
    actual_score = response["spec_quality_score"]
    
    # Validate risk level (strict)
    assert actual_risk == expected_risk, (
        f"Risk level mismatch for {description}:\n"
        f"  Expected: {expected_risk}\n"
        f"  Got: {actual_risk}"
    )
    
    # Validate quality score (with tolerance for spec-kit extraction variability)
    # Allow ±10 points flexibility since spec-kit categorization can vary
    tolerance = 10
    assert (min_score - tolerance) <= actual_score <= (max_score + tolerance), (
        f"Quality score significantly out of range for {description}:\n"
        f"  Expected: {min_score}-{max_score} (±{tolerance} tolerance)\n"
        f"  Got: {actual_score}"
    )


def test_dev_progression_1_no_issues(test_prompts_dir, api_endpoint):
    """Verify Prompt 1 (comprehensive spec) has no high-severity findings."""
    with open(test_prompts_dir / "dev_progress_1_low_high.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have no ERROR or BLOCKER findings
    high_severity = [f for f in findings if f.get("severity") in ["ERROR", "BLOCKER"]]
    assert len(high_severity) == 0, \
        f"Comprehensive spec should have no high-severity findings, got: {high_severity}"


def test_dev_progression_2_no_issues(test_prompts_dir, api_endpoint):
    """Verify Prompt 2 (minimal but secure) has no high-severity findings."""
    with open(test_prompts_dir / "dev_progress_2_low_lower.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have no ERROR or BLOCKER findings
    high_severity = [f for f in findings if f.get("severity") in ["ERROR", "BLOCKER"]]
    assert len(high_severity) == 0, \
        f"Minimal but secure spec should have no high-severity findings, got: {high_severity}"


def test_dev_progression_3_pii_logging(test_prompts_dir, api_endpoint):
    """Verify Prompt 3 detects PII logging (emails) as ERROR."""
    with open(test_prompts_dir / "dev_progress_3_medium_pii.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have PII logging detected as ERROR
    finding_codes = [f["code"] for f in findings]
    assert any("PII" in code or "EMAIL" in code for code in finding_codes), \
        f"Should detect PII logging (emails), got codes: {finding_codes}"
    
    # Should be ERROR severity (not BLOCKER)
    pii_findings = [f for f in findings if "PII" in f["code"] or "EMAIL" in f["code"]]
    assert all(f.get("severity") == "ERROR" for f in pii_findings), \
        "PII logging should be ERROR severity"


def test_dev_progression_4_weak_hashing(test_prompts_dir, api_endpoint):
    """Verify Prompt 4 detects SHA-256 password hashing as ERROR."""
    with open(test_prompts_dir / "dev_progress_4_medium_hash.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have weak password hashing detected
    finding_codes = [f["code"] for f in findings]
    assert any("SHA256" in code or "WEAK" in code for code in finding_codes), \
        f"Should detect SHA-256 password hashing, got codes: {finding_codes}"
    
    # Should be ERROR severity (not BLOCKER)
    hash_findings = [f for f in findings if "SHA256" in f["code"] or "HASH" in f["code"]]
    assert all(f.get("severity") == "ERROR" for f in hash_findings), \
        "Weak password hashing should be ERROR severity"


def test_dev_progression_5_password_logging(test_prompts_dir, api_endpoint):
    """Verify Prompt 5 detects raw password logging as BLOCKER."""
    with open(test_prompts_dir / "dev_progress_5_high_password.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have password logging detected
    finding_codes = [f["code"] for f in findings]
    assert any("PASSWORD" in code or "LOGS" in code for code in finding_codes), \
        f"Should detect password logging, got codes: {finding_codes}"
    
    # Should have at least one BLOCKER
    severities = [f.get("severity") for f in findings]
    assert "BLOCKER" in severities, \
        f"Password logging should be BLOCKER severity, got: {severities}"


def test_dev_progression_6_debug_endpoints(test_prompts_dir, api_endpoint):
    """Verify Prompt 6 detects debug endpoints exposing config and bulk data."""
    with open(test_prompts_dir / "dev_progress_6_high_debug.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have debug config dump detected
    finding_codes = [f["code"] for f in findings]
    assert any("DEBUG" in code and "CONFIG" in code for code in finding_codes), \
        f"Should detect debug config endpoint, got codes: {finding_codes}"
    
    # Should have bulk data exposure detected
    assert any("BULK" in code or "100" in str(f) for f in findings for code in [f["code"]]), \
        f"Should detect bulk data exposure (100 user emails), got codes: {finding_codes}"
    
    # Should have at least one BLOCKER
    severities = [f.get("severity") for f in findings]
    blocker_count = severities.count("BLOCKER")
    assert blocker_count >= 1, \
        f"Debug endpoints should have at least 1 BLOCKER, got {blocker_count}"


def test_risk_progression_consistency(test_prompts_dir, api_endpoint):
    """
    Test that risk level increases as security issues are introduced.
    
    Progression:
    - Prompts 1-2: Low risk (no issues)
    - Prompts 3-4: Medium risk (ERROR only)
    - Prompts 5-6: High risk (BLOCKER present)
    """
    expected_progression = [
        ("dev_progress_1_low_high.txt", "Low"),
        ("dev_progress_2_low_lower.txt", "Low"),
        ("dev_progress_3_medium_pii.txt", "Medium"),
        ("dev_progress_4_medium_hash.txt", "Medium"),
        ("dev_progress_5_high_password.txt", "High"),
        ("dev_progress_6_high_debug.txt", "High"),
    ]
    
    for filename, expected_risk in expected_progression:
        with open(test_prompts_dir / filename) as f:
            prompt = f.read()
        
        response = call_api(api_endpoint, prompt)
        actual_risk = response["risk_level"]
        
        assert actual_risk == expected_risk, (
            f"Risk progression broken at {filename}:\n"
            f"  Expected: {expected_risk}\n"
            f"  Got: {actual_risk}"
        )


def test_quality_score_decreases_with_incomplete_specs(test_prompts_dir, api_endpoint):
    """
    Test that quality score reflects spec completeness.
    
    Prompt 1 (comprehensive) should score higher than Prompt 2 (minimal).
    """
    # Get scores
    with open(test_prompts_dir / "dev_progress_1_low_high.txt") as f:
        prompt1 = f.read()
    
    with open(test_prompts_dir / "dev_progress_2_low_lower.txt") as f:
        prompt2 = f.read()
    
    response1 = call_api(api_endpoint, prompt1)
    response2 = call_api(api_endpoint, prompt2)
    
    score1 = response1["spec_quality_score"]
    score2 = response2["spec_quality_score"]
    
    assert score1 > score2, (
        f"Comprehensive spec (Prompt 1) should score higher than minimal spec (Prompt 2):\n"
        f"  Prompt 1: {score1}\n"
        f"  Prompt 2: {score2}"
    )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])
