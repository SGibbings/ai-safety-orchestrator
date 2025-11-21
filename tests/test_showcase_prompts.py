"""
Regression tests for showcase prompts.

These tests validate that the risk classification pipeline correctly
identifies risk levels and quality scores for representative AI prompts
across different security profiles.

Test Cases:
- Prompt 1: Medium risk (config.json secrets)
- Prompt 2: Low risk (clean microservice)
- Prompt 3: Medium risk (SHA-256 passwords)
- Prompt 4: High risk (debug config dump)
- Prompt 5: High risk (bulk data exposure)
"""
import pytest
import json
import subprocess
from pathlib import Path


# Test data: (filename, expected_risk, min_score, max_score, description)
SHOWCASE_TESTS = [
    (
        "showcase_1_medium.txt",
        "Medium",
        50, 75,
        "FastAPI with JWT secret in config.json + debug endpoint"
    ),
    (
        "showcase_2_low.txt",
        "Low",
        40, 60,
        "Clean Node.js/Express microservice with bearer tokens"
    ),
    (
        "showcase_3_medium.txt",
        "Medium",
        60, 80,
        "Go auth service with SHA-256 password hashing"
    ),
    (
        "showcase_4_high.txt",
        "High",
        40, 70,
        "Django with /debug/config endpoint exposing settings"
    ),
    (
        "showcase_5_high.txt",
        "High",
        50, 70,
        "Flask upload service with bulk data exposure (100 files)"
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
    SHOWCASE_TESTS,
    ids=[f"prompt_{i+1}" for i in range(len(SHOWCASE_TESTS))]
)
def test_showcase_prompt(
    test_prompts_dir,
    api_endpoint,
    filename,
    expected_risk,
    min_score,
    max_score,
    description
):
    """
    Test a showcase prompt against expected risk level and quality score.
    
    Validates:
    1. Risk level matches expected (Low/Medium/High)
    2. Quality score falls within expected range
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
    
    # Validate risk level
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


def test_showcase_prompt_1_findings(test_prompts_dir, api_endpoint):
    """Verify Prompt 1 detects config.json secrets and debug endpoint."""
    with open(test_prompts_dir / "showcase_1_medium.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have at least SEC_SECRETS_IN_CONFIG_FILE (ERROR)
    finding_codes = [f["code"] for f in findings]
    assert any("SEC_SECRETS_IN_CONFIG_FILE" in code or "SECRET" in code for code in finding_codes), \
        f"Should detect secrets in config.json, got codes: {finding_codes}"


def test_showcase_prompt_2_clean(test_prompts_dir, api_endpoint):
    """Verify Prompt 2 has no security findings (clean microservice)."""
    with open(test_prompts_dir / "showcase_2_low.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have no ERROR or BLOCKER findings
    high_severity = [f for f in findings if f.get("severity") in ["ERROR", "BLOCKER"]]
    assert len(high_severity) == 0, \
        f"Clean microservice should have no high-severity findings, got: {high_severity}"


def test_showcase_prompt_3_weak_hashing(test_prompts_dir, api_endpoint):
    """Verify Prompt 3 detects SHA-256 password hashing."""
    with open(test_prompts_dir / "showcase_3_medium.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have SEC_WEAK_PASSWORD_HASH_SHA256 (ERROR)
    finding_codes = [f["code"] for f in findings]
    assert any("SHA256" in code or "WEAK" in code for code in finding_codes), \
        f"Should detect SHA-256 password hashing, got codes: {finding_codes}"


def test_showcase_prompt_4_debug_dump(test_prompts_dir, api_endpoint):
    """Verify Prompt 4 detects debug config dump."""
    with open(test_prompts_dir / "showcase_4_high.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have SEC_DEBUG_DUMPS_CONFIG (BLOCKER)
    finding_codes = [f["code"] for f in findings]
    assert any("DEBUG_DUMPS_CONFIG" in code or "CONFIG" in code for code in finding_codes), \
        f"Should detect debug config dump, got codes: {finding_codes}"
    
    # Should have at least one BLOCKER
    severities = [f.get("severity") for f in findings]
    assert "BLOCKER" in severities, f"Debug config dump should be BLOCKER severity, got: {severities}"


def test_showcase_prompt_5_bulk_exposure(test_prompts_dir, api_endpoint):
    """Verify Prompt 5 detects bulk data exposure (100+ records)."""
    with open(test_prompts_dir / "showcase_5_high.txt") as f:
        prompt = f.read()
    
    response = call_api(api_endpoint, prompt)
    findings = response.get("devspec_findings", [])
    
    # Should have SEC_DEBUG_EXPOSES_BULK_DATA (BLOCKER)
    finding_codes = [f["code"] for f in findings]
    assert any("BULK" in code or "DEBUG_EXPOSES" in code for code in finding_codes), \
        f"Should detect bulk data exposure (100 files), got codes: {finding_codes}"
    
    # Should have at least one BLOCKER
    severities = [f.get("severity") for f in findings]
    assert "BLOCKER" in severities, f"Bulk data exposure should be BLOCKER severity, got: {severities}"


def test_all_prompts_have_quality_scores(test_prompts_dir, api_endpoint):
    """Verify all showcase prompts return quality scores."""
    for filename, _, _, _, desc in SHOWCASE_TESTS:
        with open(test_prompts_dir / filename) as f:
            prompt = f.read()
        
        response = call_api(api_endpoint, prompt)
        score = response.get("spec_quality_score")
        
        assert score is not None, f"{desc} should have a quality score"
        assert isinstance(score, (int, float)), f"{desc} quality score should be numeric"
        assert 0 <= score <= 100, f"{desc} quality score should be 0-100, got {score}"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])
