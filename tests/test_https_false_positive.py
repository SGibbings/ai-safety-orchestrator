"""
Regression test for HTTPS false positive detection.

This validates that the SEC_HTTP_FOR_AUTH rule correctly distinguishes
between HTTP and HTTPS usage, avoiding false positives when HTTPS is mentioned.

Issue: The pattern 'use http' was matching 'use HTTPS' because it was
case-insensitive without word boundaries.

Fix: Added word boundaries and checks for HTTPS/TLS/SSL to avoid false positives.
"""
import pytest
import json
import subprocess
from pathlib import Path


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


def test_https_does_not_trigger_http_blocker(api_endpoint):
    """
    Test that mentioning HTTPS does not trigger SEC_HTTP_FOR_AUTH.
    
    This was a false positive where 'use HTTPS' was matching the pattern
    'use http' (case-insensitive).
    """
    prompt = """
    Build a FastAPI microservice for employee profiles. All endpoints must use HTTPS.
    Load JWT_SECRET, DB_URL, and SESSION_KEY from environment variables.
    Passwords must be hashed with bcrypt.
    Add structured logging, detailed error handling, and full unit tests for profile CRUD.
    Include a /health endpoint only—no debug endpoints.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    blockers = [f for f in findings if f.get("severity") == "BLOCKER"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    print(f"BLOCKER findings: {len(blockers)}")
    if blockers:
        print(f"BLOCKER codes: {[f['code'] for f in blockers]}")
    
    # Should NOT trigger SEC_HTTP_FOR_AUTH
    assert len(http_findings) == 0, (
        f"False positive: SEC_HTTP_FOR_AUTH triggered when prompt says 'use HTTPS'.\n"
        f"  This should not trigger the HTTP blocker.\n"
        f"  Findings: {[f['code'] for f in http_findings]}"
    )
    
    # Should NOT have BLOCKER from HTTP
    http_blockers = [f for f in blockers if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    assert len(http_blockers) == 0, (
        f"False positive BLOCKER: SEC_HTTP_FOR_AUTH should not be BLOCKER when HTTPS is used."
    )


def test_http_without_https_triggers_blocker(api_endpoint):
    """
    Test that explicitly using HTTP (without HTTPS) triggers SEC_HTTP_FOR_AUTH.
    
    This validates the rule still catches actual HTTP usage.
    """
    prompt = """
    Build a FastAPI microservice. Use HTTP for authentication endpoints.
    Passwords hashed with bcrypt.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    
    # SHOULD trigger SEC_HTTP_FOR_AUTH
    assert len(http_findings) > 0, (
        f"SEC_HTTP_FOR_AUTH should trigger when prompt says 'use HTTP' for auth.\n"
        f"  All findings: {[f['code'] for f in findings]}"
    )
    
    # Should be BLOCKER severity
    assert http_findings[0].get("severity") == "BLOCKER", (
        f"SEC_HTTP_FOR_AUTH should be BLOCKER severity, got {http_findings[0].get('severity')}"
    )


def test_https_with_tls_mentioned(api_endpoint):
    """
    Test that HTTPS with TLS/SSL mentioned doesn't trigger false positive.
    """
    prompt = """
    Build an API with JWT authentication.
    All endpoints use HTTPS with TLS 1.3.
    Passwords hashed with bcrypt.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    
    # Should NOT trigger SEC_HTTP_FOR_AUTH
    assert len(http_findings) == 0, (
        f"False positive: SEC_HTTP_FOR_AUTH triggered when HTTPS/TLS mentioned.\n"
        f"  Findings: {[f['code'] for f in http_findings]}"
    )


def test_ssl_certificates_no_false_positive(api_endpoint):
    """
    Test that mentioning SSL certificates doesn't trigger false positive.
    """
    prompt = """
    Build an authentication API.
    Configure SSL certificates for secure connections.
    Use JWT tokens with proper expiration.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    
    # Should NOT trigger SEC_HTTP_FOR_AUTH
    assert len(http_findings) == 0, (
        f"False positive: SEC_HTTP_FOR_AUTH triggered when SSL mentioned.\n"
        f"  Findings: {[f['code'] for f in http_findings]}"
    )


def test_word_boundary_http_in_compound_words(api_endpoint):
    """
    Test that HTTP in compound words (like HTTP-only cookies) doesn't trigger.
    
    Actually, this might be a gray area. Let's see what happens.
    """
    prompt = """
    Build an API with authentication.
    Set HTTP-only cookies for session tokens.
    Use secure HTTPS connections.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    
    # Should NOT trigger because HTTPS is mentioned
    assert len(http_findings) == 0, (
        f"False positive: SEC_HTTP_FOR_AUTH triggered despite HTTPS being mentioned.\n"
        f"  Findings: {[f['code'] for f in http_findings]}"
    )


def test_http_for_protocol_name_not_usage(api_endpoint):
    """
    Test that mentioning HTTP as a protocol name (not usage) doesn't trigger.
    
    Example: "Migrate from HTTP to HTTPS"
    """
    prompt = """
    Upgrade the API from HTTP to HTTPS.
    All authentication now requires secure connections.
    Use JWT tokens with bcrypt passwords.
    """
    
    response = call_api(api_endpoint, prompt.strip())
    
    findings = response.get("devspec_findings", [])
    http_findings = [f for f in findings if f.get("code") == "SEC_HTTP_FOR_AUTH"]
    
    print(f"\nRisk: {response.get('risk_level')}")
    print(f"SEC_HTTP_FOR_AUTH findings: {len(http_findings)}")
    
    # Should NOT trigger because HTTPS is mentioned (migration context)
    assert len(http_findings) == 0, (
        f"False positive: SEC_HTTP_FOR_AUTH triggered in migration context.\n"
        f"  Findings: {[f['code'] for f in http_findings]}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
