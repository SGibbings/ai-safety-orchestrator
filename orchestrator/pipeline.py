"""
Main orchestration pipeline that coordinates all components.
"""
import re
from .models import AnalysisResponse, DevSpecFinding
from .devspec_runner import run_dev_spec_kit
from .guidance_engine import build_guidance
from .claude_client import call_claude


def filter_false_positives(prompt: str, findings: list[DevSpecFinding]) -> list[DevSpecFinding]:
    """
    Filter out likely false positives based on context analysis.
    
    This function checks if the prompt explicitly follows security best practices,
    and removes findings that contradict the secure patterns detected.
    
    Args:
        prompt: The normalized prompt text
        findings: List of findings from dev-spec-kit
        
    Returns:
        Filtered list of findings with false positives removed
    """
    prompt_lower = prompt.lower()
    filtered_findings = []
    
    # Build a profile of security best practices mentioned in the prompt
    has_secure_patterns = {
        'env_vars': bool(re.search(r'environment variables|env vars?|\.env\s*file', prompt_lower)) and 
                    bool(re.search(r'never.*code|not.*checked.*into|config.*not.*source|do not include', prompt_lower)),
        'hashing': bool(re.search(r'hash.*bcrypt|bcrypt|argon2|pbkdf2|scrypt', prompt_lower)),
        'https': bool(re.search(r'https|tls|ssl|secure.*connection', prompt_lower)),
        'validation': bool(re.search(r'input validation|validate.*input|pydantic|sanitize', prompt_lower)),
        'prepared_statements': bool(re.search(r'prepared statement|parameterized.*quer|orm|parameter binding', prompt_lower)),
        'no_plaintext_passwords': bool(re.search(r'never.*plain.*text.*password|hash.*password', prompt_lower)),
        'no_debug_endpoints': bool(re.search(r'do not.*debug|never.*debug.*endpoint|no debug endpoint', prompt_lower)),
        'no_passwords_anywhere': bool(re.search(r'do not include.*(password|secret)|no.*(password|secret).*anywhere', prompt_lower)),
        'md5_for_checksums': bool(re.search(r'md5.*checksum|md5.*duplicate', prompt_lower)),
    }
    
    # Detect negation patterns (e.g., "do NOT expose", "never log", "skip validation")
    def has_negation_context(code: str) -> bool:
        """Check if the finding code's keywords appear in a negation context."""
        if code == "SEC_DEBUG_EXPOSES_SECRETS":
            return bool(re.search(r'(do not|don\'t|never|must not).*expose.*(debug|environment|config)', prompt_lower)) or \
                   bool(re.search(r'but (do )?not.*debug.*endpoint', prompt_lower))
        elif code == "SEC_MISSING_INPUT_VALIDATION":
            # Check if validation is mentioned positively, not skipped
            if has_secure_patterns['validation']:
                # Make sure it's not "skip validation" or "without validation"
                return not bool(re.search(r'skip.*validation|without.*validation|no.*validation', prompt_lower))
        return False
    
    for finding in findings:
        should_remove = False
        
        # SEC_HARDCODED_SECRET: Remove if prompt explicitly mentions using env vars/config files
        if finding.code == "SEC_HARDCODED_SECRET" and has_secure_patterns['env_vars']:
            # Check if the prompt is actually recommending hardcoding or just mentioning it to avoid it
            if not re.search(r'use.*["\']\w+["\']|hardcode.*["\']\w+["\']|secret.*=.*["\']', prompt_lower):
                should_remove = True
        
        # SEC_INSECURE_JWT_STORAGE: Remove if prompt mentions secure storage patterns
        if finding.code == "SEC_INSECURE_JWT_STORAGE" and has_secure_patterns['env_vars']:
            # Check if it's actually suggesting insecure storage or just mentioning config files for other purposes
            if not re.search(r'save.*token.*file|store.*jwt.*json|token.*in.*file', prompt_lower):
                should_remove = True
        
        # SEC_PLAINTEXT_PASSWORDS: Remove if prompt explicitly mentions password hashing OR says no passwords anywhere
        if finding.code == "SEC_PLAINTEXT_PASSWORDS":
            if has_secure_patterns['hashing'] or has_secure_patterns['no_passwords_anywhere']:
                should_remove = True
        
        # SEC_DEBUG_EXPOSES_SECRETS: Remove if prompt explicitly says NOT to expose debug info
        # OR if debug endpoint only returns non-sensitive data (IDs, not tokens/secrets)
        if finding.code == "SEC_DEBUG_EXPOSES_SECRETS":
            if has_secure_patterns['no_debug_endpoints']:
                should_remove = True
            # Check if debug endpoint only exposes file IDs or similar non-sensitive data
            elif re.search(r'debug.*endpoint.*returns.*(file id|processing id|last.*processed)', prompt_lower):
                # Downgrade to warning instead of removing entirely
                # For now, remove the BLOCKER but we should ideally downgrade severity
                should_remove = True
        
        # SEC_MISSING_INPUT_VALIDATION: Remove if prompt explicitly requires validation
        if finding.code == "SEC_MISSING_INPUT_VALIDATION" and has_negation_context(finding.code):
            should_remove = True
        
        # SEC_WEAK_HASH_MD5: Remove if MD5 is used for checksums/duplicates (not password hashing)
        if finding.code == "SEC_WEAK_HASH_MD5":
            if has_secure_patterns['md5_for_checksums']:
                # MD5 for file checksums/duplicate detection is acceptable
                should_remove = True
        
        # SEC_NO_TLS_FOR_AUTH: Remove if there's no authentication in the prompt
        if finding.code == "SEC_NO_TLS_FOR_AUTH":
            # Check if auth is actually mentioned in a positive way (implementing auth, not just forbidding secrets)
            has_auth_implementation = bool(re.search(r'implement.*auth|login.*endpoint|auth.*flow|session.*management|jwt|oauth|sso', prompt_lower))
            # If only mentions passwords/secrets in "do not include" context, it's not auth
            only_negative_mentions = bool(re.search(r'do not include.*password|no.*password.*anywhere', prompt_lower))
            
            if not has_auth_implementation or only_negative_mentions:
                # No authentication implementation mentioned, so TLS warning is not relevant
                should_remove = True
        
        if not should_remove:
            filtered_findings.append(finding)
    
    return filtered_findings


def analyze_prompt(prompt: str, call_claude_api: bool = False) -> AnalysisResponse:
    """
    Run the complete analysis pipeline on a developer prompt.
    
    This orchestrates:
    1. Dev-spec-kit security analysis
    2. Guidance generation
    3. Prompt curation
    4. Optional Claude API call
    
    Args:
        prompt: The raw developer prompt to analyze
        call_claude_api: Whether to actually call Claude (default: False for stub)
        
    Returns:
        AnalysisResponse with complete analysis results
    """
    # Normalize the prompt (basic cleanup)
    normalized_prompt = prompt.strip()
    
    # Step 1: Run dev-spec-kit security checks
    devspec_raw_output, devspec_findings, exit_code = run_dev_spec_kit(normalized_prompt)
    
    # Step 1.5: Filter false positives based on context
    filtered_findings = filter_false_positives(normalized_prompt, devspec_findings)
    
    # Determine risk level based on finding severities
    has_blockers = any(f.severity.upper() == "BLOCKER" for f in filtered_findings)
    has_errors = any(f.severity.upper() == "ERROR" for f in filtered_findings)
    has_warnings = any(f.severity.upper() == "WARNING" for f in filtered_findings)
    
    # Calculate risk level based on severities
    if has_blockers or has_errors:
        risk_level = "High"
    elif has_warnings:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    # Step 2: Generate guidance and curated prompt
    guidance_items, final_curated_prompt = build_guidance(normalized_prompt, filtered_findings, risk_level)
    
    # Step 3: Optionally call Claude
    claude_output = None
    if call_claude_api:
        claude_output = call_claude(final_curated_prompt)
    
    # Build the complete response (use filtered findings for stats, but keep original devspec output for transparency)
    response = AnalysisResponse(
        original_prompt=prompt,
        normalized_prompt=normalized_prompt,
        devspec_raw_output=devspec_raw_output,
        devspec_findings=filtered_findings,  # Use filtered findings
        guidance=guidance_items,
        final_curated_prompt=final_curated_prompt,
        claude_output=claude_output,
        exit_code=exit_code,
        has_blockers=has_blockers,
        has_errors=has_errors,
        risk_level=risk_level
    )
    
    return response
