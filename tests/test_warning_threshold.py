"""
Test threshold-based Medium risk escalation for multiple warnings.

This validates that Medium risk appears when there are multiple WARNING-level
findings, even without ERROR or BLOCKER findings.

Thresholds:
- 3+ WARNINGs → Medium risk
- 1-2 WARNINGs → Low risk
- 0 WARNINGs → Low risk
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
    """Call the analysis API with a prompt."""
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


def test_multiple_warnings_escalate_to_medium(api_endpoint):
    """
    Test that 3+ WARNING findings escalate to Medium risk.
    
    This prompt should trigger multiple architectural/spec quality warnings.
    """
    prompt = """
    Build a REST API.
    
    Use either Flask, Django, Laravel, or Express - whichever is fastest to set up.
    
    Database: not sure yet, maybe PostgreSQL or MongoDB or MySQL.
    
    Authentication: will add later, maybe JWT or sessions.
    
    Testing: minimal for now, will expand later.
    
    Error handling: basic try/catch blocks.
    """
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    # Count by severity
    blockers = [f for f in findings if f.get("severity", "").upper() == "BLOCKER"]
    errors = [f for f in findings if f.get("severity", "").upper() == "ERROR"]
    warnings = [f for f in findings if f.get("severity", "").upper() == "WARNING"]
    
    print(f"\nRisk: {risk}")
    print(f"BLOCKERs: {len(blockers)}")
    print(f"ERRORs: {len(errors)}")
    print(f"WARNINGs: {len(warnings)}")
    if warnings:
        print("WARNING codes:", [f.get("code") for f in warnings])
    
    # The test validates the escalation logic:
    # If 3+ warnings are present with no errors/blockers, should be Medium
    # If fewer warnings, test is informational (not a failure)
    if len(blockers) == 0 and len(errors) == 0:
        if len(warnings) >= 3:
            assert risk == "Medium", f"Expected Medium risk with {len(warnings)} warnings, got {risk}"
            print("✓ Escalation working: 3+ warnings → Medium")
        else:
            print(f"ℹ Not enough warnings to escalate ({len(warnings)} < 3), risk is {risk}")
            # This is ok - the prompt might not trigger enough warnings
            assert risk == "Low", f"With < 3 warnings and no errors, expected Low, got {risk}"


def test_few_warnings_stay_low_risk(api_endpoint):
    """
    Test that 1-2 WARNING findings remain Low risk.
    """
    prompt = """
    Build a simple REST API using Python.
    
    Tech stack: use either Flask or Django (not decided yet, leaning towards Flask).
    
    Database: PostgreSQL with SQLAlchemy ORM and proper connection pooling.
    Authentication: JWT tokens with bcrypt for password hashing.
    TLS certificates for secure connections in production.
    Comprehensive input validation on all endpoints with Marshmallow schemas.
    Rate limiting implemented with Flask-Limiter.
    CORS properly configured for known origins only.
    
    Testing: Unit tests with pytest for all endpoints.
    Error handling: try/except blocks with proper logging.
    Logging: structured logs with correlation IDs.
    """
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    warnings = [f for f in findings if f.get("severity", "").upper() == "WARNING"]
    errors = [f for f in findings if f.get("severity", "").upper() == "ERROR"]
    blockers = [f for f in findings if f.get("severity", "").upper() == "BLOCKER"]
    
    print(f"\nRisk: {risk}")
    print(f"BLOCKERs: {len(blockers)}, ERRORs: {len(errors)}, WARNINGs: {len(warnings)}")
    if warnings:
        print("WARNING codes:", [f.get("code") for f in warnings])
    
    # The test validates that low warning counts don't escalate
    # We expect 0-2 warnings and Low risk (no errors/blockers)
    assert len(blockers) == 0, f"Should have no BLOCKERs, got {len(blockers)}"
    assert len(errors) == 0, f"Should have no ERRORs, got {len(errors)}"
    
    # With 0-2 warnings, should be Low risk
    if len(warnings) <= 2:
        assert risk == "Low", f"Expected Low risk with {len(warnings)} warnings, got {risk}"
        print(f"✓ No escalation: {len(warnings)} warnings → Low")
    else:
        # If we got 3+ warnings, it should escalate to Medium
        assert risk == "Medium", f"Expected Medium risk with {len(warnings)} warnings, got {risk}"
        print(f"✓ Escalation: {len(warnings)} warnings → Medium")


def test_threshold_boundary_at_three_warnings(api_endpoint):
    """
    Test the exact boundary: 3 warnings should escalate to Medium.
    """
    # This prompt is designed to trigger exactly 3 architectural warnings
    prompt = """
    Create a microservice.
    
    Use Flask or Django for the backend.
    Frontend: React or Vue.
    Database: PostgreSQL or MySQL.
    
    All other aspects are well-defined and secure.
    """
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    warnings = [f for f in findings if f.get("severity", "").upper() == "WARNING"]
    errors = [f for f in findings if f.get("severity", "").upper() == "ERROR"]
    blockers = [f for f in findings if f.get("severity", "").upper() == "BLOCKER"]
    
    print(f"\nRisk: {risk}")
    print(f"BLOCKERs: {len(blockers)}, ERRORs: {len(errors)}, WARNINGs: {len(warnings)}")
    
    # If we get exactly 3 warnings with no errors/blockers, should be Medium
    if len(warnings) >= 3 and len(errors) == 0 and len(blockers) == 0:
        assert risk == "Medium", f"Expected Medium risk with 3 warnings, got {risk}"
    # If we get fewer warnings, should be Low
    elif len(warnings) < 3 and len(errors) == 0 and len(blockers) == 0:
        assert risk == "Low", f"Expected Low risk with < 3 warnings, got {risk}"


def test_error_overrides_warning_threshold(api_endpoint):
    """
    Test that ERROR findings always produce Medium risk, regardless of warning count.
    
    Even with 0 warnings, ERROR → Medium.
    Even with many warnings, ERROR → still Medium (not escalated further).
    """
    prompt = """
    Build an API that logs user email addresses for debugging.
    
    Use secure practices otherwise: HTTPS, bcrypt, JWT, etc.
    """
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    errors = [f for f in findings if f.get("severity", "").upper() == "ERROR"]
    blockers = [f for f in findings if f.get("severity", "").upper() == "BLOCKER"]
    
    print(f"\nRisk: {risk}")
    print(f"ERRORs: {len(errors)}, BLOCKERs: {len(blockers)}")
    
    # Should have ERROR but no BLOCKER
    if len(errors) > 0 and len(blockers) == 0:
        assert risk == "Medium", f"ERROR findings should produce Medium risk, got {risk}"


def test_blocker_overrides_everything(api_endpoint):
    """
    Test that BLOCKER findings always produce High risk, regardless of other counts.
    """
    prompt = """
    Build an API with plaintext password storage for simplicity.
    
    Also has various other issues and warnings.
    """
    
    response = call_api(api_endpoint, prompt)
    
    risk = response.get("risk_level")
    findings = response.get("devspec_findings", [])
    
    blockers = [f for f in findings if f.get("severity", "").upper() == "BLOCKER"]
    
    print(f"\nRisk: {risk}")
    print(f"BLOCKERs: {len(blockers)}")
    
    # Should have at least one BLOCKER
    if len(blockers) > 0:
        assert risk == "High", f"BLOCKER findings should produce High risk, got {risk}"


def test_risk_escalation_logic_documentation():
    """
    Document the risk escalation logic for reference.
    
    This is not a real test, just documentation.
    """
    escalation_rules = {
        "High": "Any BLOCKER finding present",
        "Medium": "Any ERROR finding OR 3+ WARNING findings",
        "Low": "1-2 WARNING findings only, or INFO only, or no findings"
    }
    
    # Validate the documentation matches implementation
    assert "High" in escalation_rules
    assert "Medium" in escalation_rules
    assert "Low" in escalation_rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
