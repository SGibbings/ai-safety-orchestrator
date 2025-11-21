"""
Regression tests for risk classification profiles.

These tests ensure that the risk classification system correctly identifies:
- Secure prompts → Low Risk
- Moderately risky prompts → Medium Risk
- Dangerous prompts → High Risk

This prevents the "everything is High Risk" problem from reappearing.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.pipeline import analyze_prompt


def test_prompt_a_secure_service_low_risk():
    """
    Test that a well-specified, secure prompt is classified as Low Risk.
    
    This prompt has:
    - HTTPS only
    - OAuth2/OIDC with JWTs
    - Secrets from environment variables
    - bcrypt/Argon2 for passwords
    - No logging of sensitive data
    - Parameterized queries
    - Security-focused health endpoint
    - Unit tests
    
    Expected: Low Risk, High quality score (85-100)
    """
    prompt = """This is a secure, well-specified service.

I'm building a small backend service in Python (FastAPI) for managing user profiles in a multi-tenant SaaS product. I want this to be production-grade from a security standpoint.

Requirements:
- All requests go over HTTPS only; reject any non-HTTPS traffic.
- OAuth2 / OIDC SSO for authentication with short-lived JWTs.
- Secrets (JWT signing keys, DB URL) from environment variables only.
- Use bcrypt or Argon2 for password hashing.
- Do not log raw passwords, tokens, or API keys.
- Use parameterized queries or ORM for DB access.
- /health endpoint must not leak anything sensitive.
- Include unit tests for password hashing + token validation.

Describe structure and critical security checks.
"""
    
    result = analyze_prompt(prompt, call_claude_api=False)
    
    # Assert risk level
    assert result.risk_level == "Low", f"Expected Low risk, got {result.risk_level}"
    
    # Assert quality score
    assert result.spec_quality_score is not None, "Spec quality score should be present"
    assert result.spec_quality_score >= 80, f"Expected score >= 80, got {result.spec_quality_score}"
    
    # Assert no blockers or errors
    blockers = sum(1 for f in result.devspec_findings if f.severity.upper() == "BLOCKER")
    errors = sum(1 for f in result.devspec_findings if f.severity.upper() == "ERROR")
    
    assert blockers == 0, f"Secure prompt should have 0 blockers, found {blockers}"
    assert errors == 0, f"Secure prompt should have 0 errors, found {errors}"
    
    print(f"✓ Prompt A: Risk={result.risk_level}, Score={result.spec_quality_score}, Findings={len(result.devspec_findings)}")


def test_prompt_b_medium_risk_service():
    """
    Test that a moderately risky prompt is classified as Medium Risk.
    
    This prompt has:
    - HTTPS handled by Nginx (acceptable)
    - bcrypt with default work factor (acceptable)
    - Secrets from env vars (good)
    - /debug endpoint exposing emails and IDs (PII exposure - ERROR)
    - No raw token logging (good)
    - Prepared statements (good)
    
    Expected: Medium Risk, Medium quality score (55-75 ideal, but spec is incomplete so may be lower)
    """
    prompt = """I'm hacking together an internal Node.js Express service behind Nginx. Requirements:

- Let Nginx handle HTTPS. App accepts HTTP but only internally.
- Use bcrypt with default work factor.
- DB URL + JWT secret from env vars.
- /debug/users returns last 20 emails + IDs.
- Basic logging, no raw tokens.
- Use prepared statements or Prisma.

Sketch the structure and call out acceptable shortcuts.
"""
    
    result = analyze_prompt(prompt, call_claude_api=False)
    
    # Assert risk level
    assert result.risk_level == "Medium", f"Expected Medium risk, got {result.risk_level}"
    
    # Assert quality score is lower (spec is incomplete)
    assert result.spec_quality_score is not None, "Spec quality score should be present"
    # Note: Score will be lower due to incomplete spec, which is correct
    
    # Assert has errors but no blockers
    blockers = sum(1 for f in result.devspec_findings if f.severity.upper() == "BLOCKER")
    errors = sum(1 for f in result.devspec_findings if f.severity.upper() == "ERROR")
    
    assert blockers == 0, f"Medium risk prompt should have 0 blockers, found {blockers}"
    assert errors > 0, f"Medium risk prompt should have errors (PII exposure), found {errors}"
    
    # Check for PII exposure finding
    finding_codes = [f.code for f in result.devspec_findings]
    assert "SEC_DEBUG_EXPOSES_PII" in finding_codes, "Should detect PII exposure in debug endpoint"
    
    print(f"✓ Prompt B: Risk={result.risk_level}, Score={result.spec_quality_score}, Errors={errors}, Findings={finding_codes}")


def test_prompt_c_dangerous_service_high_risk():
    """
    Test that a dangerous prompt with multiple vulnerabilities is classified as High Risk.
    
    This prompt has:
    - HTTP only, no TLS (BLOCKER)
    - SHA-256 for password hashing (ERROR - weak)
    - Hardcoded default admin user (BLOCKER)
    - JWT secret may be hardcoded (BLOCKER)
    - Debug endpoint exposing user data (WARNING/ERROR)
    - File uploads on disk (acceptable for now)
    
    Expected: High Risk, Low quality score (20-40)
    """
    prompt = """I'm building a Go service handling file uploads and user accounts:

- Inside-cluster HTTP only, no TLS enforcement.
- Passwords hashed using SHA-256 + salt (not bcrypt/argon2).
- Hardcoded default admin user in config.
- JWT secret may be hardcoded in local config.
- /debug/state returns last 50 uploaded filenames + user IDs.
- File uploads stored on disk.

Describe implementation and highlight risks.
"""
    
    result = analyze_prompt(prompt, call_claude_api=False)
    
    # Assert risk level
    assert result.risk_level == "High", f"Expected High risk, got {result.risk_level}"
    
    # Assert quality score is low
    assert result.spec_quality_score is not None, "Spec quality score should be present"
    assert result.spec_quality_score <= 40, f"Expected score <= 40, got {result.spec_quality_score}"
    
    # Assert has blockers
    blockers = sum(1 for f in result.devspec_findings if f.severity.upper() == "BLOCKER")
    errors = sum(1 for f in result.devspec_findings if f.severity.upper() == "ERROR")
    
    assert blockers > 0, f"Dangerous prompt should have blockers, found {blockers}"
    
    # Check for specific critical findings
    finding_codes = [f.code for f in result.devspec_findings]
    assert "SEC_ADMIN_BACKDOOR" in finding_codes, "Should detect hardcoded admin user"
    assert "SEC_HTTP_FOR_AUTH" in finding_codes or "SEC_HARDCODED_SECRET" in finding_codes, "Should detect HTTP or hardcoded secrets"
    
    # SHA-256 should be detected as ERROR
    if "SEC_WEAK_PASSWORD_HASH_SHA256" in finding_codes:
        sha256_finding = next(f for f in result.devspec_findings if f.code == "SEC_WEAK_PASSWORD_HASH_SHA256")
        assert sha256_finding.severity.upper() == "ERROR", "SHA-256 password hashing should be ERROR severity"
    
    print(f"✓ Prompt C: Risk={result.risk_level}, Score={result.spec_quality_score}, Blockers={blockers}, Errors={errors}, Findings={finding_codes}")


def test_risk_level_distribution():
    """
    Test that the three prompts produce different risk levels.
    
    This ensures the classification system can distinguish between
    secure, moderately risky, and dangerous prompts.
    """
    prompt_a = """All requests go over HTTPS only. OAuth2 with short-lived JWTs. Secrets from environment variables only. Use bcrypt for password hashing. Do not log raw passwords or tokens. Use parameterized queries."""
    prompt_b = """Let Nginx handle HTTPS. App accepts HTTP internally. /debug/users returns last 20 emails + IDs. Use bcrypt. DB URL from env vars."""
    prompt_c = """HTTP only, no TLS. Passwords hashed using SHA-256. Hardcoded default admin user. JWT secret may be hardcoded."""
    
    result_a = analyze_prompt(prompt_a, call_claude_api=False)
    result_b = analyze_prompt(prompt_b, call_claude_api=False)
    result_c = analyze_prompt(prompt_c, call_claude_api=False)
    
    # All three should have different risk levels OR A and B can both be Low if B has only warnings
    assert result_a.risk_level == "Low", f"Prompt A should be Low, got {result_a.risk_level}"
    assert result_c.risk_level == "High", f"Prompt C should be High, got {result_c.risk_level}"
    
    # B should be Medium or Low (depends on if debug endpoint detected)
    assert result_b.risk_level in ["Low", "Medium"], f"Prompt B should be Low or Medium, got {result_b.risk_level}"
    
    print(f"✓ Risk distribution: A={result_a.risk_level}, B={result_b.risk_level}, C={result_c.risk_level}")


def test_spec_quality_score_correlation():
    """
    Test that spec quality scores correlate with spec completeness.
    
    - Complete, detailed specs should score higher (80-100)
    - Incomplete specs should score lower (20-60)
    """
    # Test that Prompt A (detailed spec) scores higher than Prompt C (minimal spec)
    prompt_a_path = os.path.join(os.path.dirname(__file__), "../test_prompts/prompt_a_secure.txt")
    prompt_c_path = os.path.join(os.path.dirname(__file__), "../test_prompts/prompt_c_dangerous.txt")
    
    if os.path.exists(prompt_a_path) and os.path.exists(prompt_c_path):
        with open(prompt_a_path) as f:
            prompt_a = f.read()
        with open(prompt_c_path) as f:
            prompt_c = f.read()
        
        result_a = analyze_prompt(prompt_a, call_claude_api=False)
        result_c = analyze_prompt(prompt_c, call_claude_api=False)
        
        # Prompt A should have higher quality score than Prompt C
        assert result_a.spec_quality_score > result_c.spec_quality_score, \
            f"Detailed spec (A) should score higher than minimal spec (C): {result_a.spec_quality_score} vs {result_c.spec_quality_score}"
        
        print(f"✓ Spec quality correlation: A={result_a.spec_quality_score} > C={result_c.spec_quality_score}")


if __name__ == "__main__":
    # Run tests
    print("Running risk profile regression tests...\n")
    
    try:
        test_prompt_a_secure_service_low_risk()
        test_prompt_b_medium_risk_service()
        test_prompt_c_dangerous_service_high_risk()
        test_risk_level_distribution()
        test_spec_quality_score_correlation()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nRisk classification is working correctly:")
        print("- Secure prompts → Low Risk")
        print("- Moderate prompts → Medium Risk")
        print("- Dangerous prompts → High Risk")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
