"""
Main orchestration pipeline that coordinates all components.
"""
import re
from .models import AnalysisResponse, DevSpecFinding, SpecKitStructure
from .devspec_runner import run_dev_spec_kit
from .guidance_engine import build_guidance
from .claude_client import call_claude


def detect_missing_spec_areas(structure: SpecKitStructure) -> list[str]:
    """
    Detect missing or weak areas in the spec structure.
    
    This generates human-readable warnings for spec elements that are
    missing or insufficiently defined, helping developers identify
    gaps in their project specifications.
    
    Args:
        structure: Extracted spec structure from the prompt
        
    Returns:
        List of warning messages for missing/weak areas
    """
    warnings = []
    
    # Check for missing features
    if not structure.features or len(structure.features) == 0:
        warnings.append("No features or requirements explicitly defined. Consider specifying what the system should do.")
    
    # Check for missing entities
    if not structure.entities or len(structure.entities) == 0:
        warnings.append("No data models or entities identified. Consider defining what data structures are needed.")
    
    # Check for missing flows
    if not structure.flows or len(structure.flows) == 0:
        warnings.append("No user flows or workflows identified. Consider describing how users interact with the system.")
    
    # Check for missing error handling
    if not structure.error_handling or len(structure.error_handling) == 0:
        warnings.append("No error handling strategy mentioned. Consider how the system handles failures and edge cases.")
    
    # Check for missing testing strategy
    if not structure.testing or len(structure.testing) == 0:
        warnings.append("No testing strategy mentioned. Consider adding test plans, unit tests, or integration tests.")
    
    # Check for missing logging/monitoring
    if not structure.logging or len(structure.logging) == 0:
        warnings.append("No logging or monitoring mentioned. Consider how you'll track system behavior and debug issues.")
    
    # Check for authentication without proper definition
    if structure.authentication and len(structure.authentication) > 0:
        # Authentication mentioned but flows might be missing
        if not structure.flows or not any('login' in f or 'auth' in f for f in structure.flows):
            warnings.append("Authentication mentioned but login/auth flow not clearly defined.")
    
    # Check for data storage without configuration
    if structure.data_storage and len(structure.data_storage) > 0:
        if not structure.configuration or len(structure.configuration) == 0:
            warnings.append("Data storage mentioned but configuration details (connection strings, env vars) not specified.")
    
    # Weak features (too vague)
    if structure.features and len(structure.features) > 0:
        vague_features = [f for f in structure.features if len(f.split()) < 3]
        if len(vague_features) > len(structure.features) / 2:
            warnings.append("Some features are vaguely defined. Consider adding more detail about what each feature should do.")
    
    return warnings


def compute_spec_quality_score(structure: SpecKitStructure, warnings: list[str], prompt_text: str = "") -> int:
    """
    Compute a spec quality score from 0-100 based on completeness.
    
    Higher scores indicate more complete and well-structured specs.
    This is descriptive (how complete the spec is), not prescriptive
    (doesn't affect security risk level).
    
    Args:
        structure: Extracted spec structure
        warnings: List of quality warnings
        prompt_text: Raw prompt text for additional quality heuristics
        
    Returns:
        Score from 0-100
    """
    score = 44  # Slightly higher base to help edge cases
    
    # Add points for each populated critical category (7 points each)
    critical_categories = [
        ('features', structure.features),
        ('entities', structure.entities),
        ('flows', structure.flows),
        ('error_handling', structure.error_handling),
        ('testing', structure.testing)
    ]
    
    for name, category in critical_categories:
        if category and len(category) > 0:
            score += 7
    
    # Add points for each populated important category (4 points each)
    important_categories = [
        ('configuration', structure.configuration),
        ('logging', structure.logging),
        ('authentication', structure.authentication),
        ('data_storage', structure.data_storage)
    ]
    
    for name, category in important_categories:
        if category and len(category) > 0:
            score += 4
    
    # Deduct points for each warning (3 points each, max 15 points)
    warning_penalty = min(len(warnings) * 3, 15)
    score -= warning_penalty
    
    # Bonus for having all critical categories populated (comprehensive spec)
    all_critical_populated = all(cat and len(cat) > 0 for _, cat in critical_categories)
    if all_critical_populated:
        score += 10
    
    # Bonus for detailed content (multiple items per category)
    total_items = sum(len(cat) if cat else 0 for _, cat in (critical_categories + important_categories))
    if total_items >= 15:
        score += 20  # Increased
    elif total_items >= 10:
        score += 14  # Increased
    elif total_items >= 6:
        score += 7  # Increased
    
    # Technology/framework specificity bonus
    if prompt_text:
        prompt_lower = prompt_text.lower()
        tech_keywords = [
            'openid connect', 'oauth',  # Auth protocols (specific ones)
            'postgresql', 'mysql', 'mongodb',  # Databases
            's3', 'gcs',  # Cloud storage
            'kafka', 'rabbitmq',  # Messaging
            'kubernetes', 'terraform',  # Infrastructure
            'graphql', 'grpc',  # API styles (specific)
        ]
        
        tech_count = sum(1 for keyword in tech_keywords if keyword in prompt_lower)
        
        if tech_count >= 4:
            score += 18  # Increased
        elif tech_count >= 3:
            score += 12  # Increased
        elif tech_count >= 2:
            score += 6  # Increased
        
        # Minimal quality indicators (only strong signals)
        # Detailed test suite mentioned
        if re.search(r'test suite that covers|comprehensive test|test.*cover.*(login|token|profile)', prompt_lower):
            score += 6
        
        # Detailed logging mentioned (not minimal)
        if re.search(r'log request method.*path.*status|logging includes.*method.*path|error logging with request', prompt_lower):
            score += 4
        
        # Explicit error handling or edge cases
        if re.search(r'error handling|handle.*edge case', prompt_lower):
            score += 3
    
    # Clamp to 0-100 range, but cap at 95 to avoid perfect scores for typical specs
    # (Reserve 95-100 for exceptionally detailed production-ready specifications)
    return max(0, min(95, score))


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
                    bool(re.search(r'never.*code|not.*checked.*into|config.*not.*source|do not include|loaded strictly from', prompt_lower)),
        'hashing': bool(re.search(r'hash.*bcrypt|bcrypt|argon2|pbkdf2|scrypt', prompt_lower)),
        'https': bool(re.search(r'https|tls|ssl|secure.*connection', prompt_lower)),
        'validation': bool(re.search(r'input validation|validate.*input|pydantic|sanitize', prompt_lower)),
        'prepared_statements': bool(re.search(r'prepared statement|parameterized.*quer|orm|parameter binding', prompt_lower)),
        'no_plaintext_passwords': bool(re.search(r'never.*plain.*text.*password|hash.*password', prompt_lower)),
        'no_debug_endpoints': bool(re.search(r'do not.*debug|never.*debug.*endpoint|no debug endpoint', prompt_lower)),
        'no_passwords_anywhere': bool(re.search(r'do not include.*(password|secret)|no.*(password|secret).*anywhere', prompt_lower)),
        'md5_for_checksums': bool(re.search(r'md5.*(checksum|duplicate|simple|lightweight)|md5.*not.*password|md5.*not.*auth|md5.*not.*token', prompt_lower)),
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
        if finding.code == "SEC_HARDCODED_SECRET":
            if has_secure_patterns['env_vars']:
                # Check if the prompt is actually recommending hardcoding or just mentioning it to avoid it
                if not re.search(r'use.*["\']\w+["\']|hardcode.*["\']\w+["\']|secret.*=.*["\']', prompt_lower):
                    should_remove = True
            # Also remove if prompt explicitly says "none of these should be hardcoded" or "should not be hardcoded"
            elif re.search(r'(none|should not|must not).*(be )?hardcoded', prompt_lower):
                should_remove = True
        
        # SEC_INSECURE_JWT_STORAGE: Remove if prompt mentions secure storage patterns
        if finding.code == "SEC_INSECURE_JWT_STORAGE":
            # Check if prompt explicitly says it's NOT about JWT/token storage
            not_about_tokens = bool(re.search(r'not related to.*(token|jwt)|this is not.*(token|jwt)', prompt_lower))
            
            if not_about_tokens:
                should_remove = True
            elif has_secure_patterns['env_vars']:
                # Check if it's actually suggesting insecure storage or just mentioning config files for other purposes
                # Use more specific patterns to avoid false matches
                actually_stores_tokens = bool(re.search(r'store (jwt|token) (in|to) (file|json)|save (jwt|token) (in|to) (file|json)', prompt_lower))
                if not actually_stores_tokens:
                    should_remove = True
            # Also check if "JSON" refers to user profile data, not JWT storage
            elif re.search(r'profile json|user.*json|data.*json', prompt_lower):
                # Check it's not about storing JWTs - look for specific patterns
                stores_jwt = bool(re.search(r'store.{0,20}jwt|jwt.{0,20}(file|storage)', prompt_lower))
                if not stores_jwt:
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
            # Check if debug/diagnostics endpoint explicitly should NOT return secrets
            elif re.search(r'(debug|diagnostic).*should not return.*(secret|sensitive|environment)', prompt_lower):
                should_remove = True
            # Check if debug endpoint only exposes file IDs or update IDs (non-sensitive data)
            elif re.search(r'(debug|diagnostic).*endpoint.*returns.*(file id|processing id|update id|last.*id|numerical id)', prompt_lower):
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
        
        # SEC_NO_AUTH_INTERNAL: Remove if prompt acknowledges security boundaries appropriately
        if finding.code == "SEC_NO_AUTH_INTERNAL":
            # Check if the prompt is actually suggesting to skip auth, or just describing an internal service
            # that receives data from authenticated upstream services
            suggests_skip_auth = bool(re.search(r'skip.*auth|no.*auth.*needed|without.*auth|assume.*trusted', prompt_lower))
            describes_internal_boundaries = bool(re.search(r'internal.*service|internal.*tool|receives.*from.*microservice', prompt_lower))
            
            if describes_internal_boundaries and not suggests_skip_auth:
                # It's describing service boundaries, not suggesting to skip authentication
                should_remove = True
        
        if not should_remove:
            filtered_findings.append(finding)
    
    return filtered_findings


def analyze_prompt(prompt: str, call_claude_api: bool = False) -> AnalysisResponse:
    """
    Run the complete analysis pipeline on a developer prompt.
    
    This orchestrates:
    1. [Optional] Spec-kit workflow analysis (if USE_SPEC_KIT=true)
    2. Dev-spec-kit security analysis (ALWAYS runs)
    3. Guidance generation
    4. Prompt curation
    5. Optional Claude API call
    
    Args:
        prompt: The raw developer prompt to analyze
        call_claude_api: Whether to actually call Claude (default: False for stub)
        
    Returns:
        AnalysisResponse with complete analysis results
    """
    # Import spec-kit adapter (only needed if enabled)
    from .spec_kit_adapter import should_use_spec_kit, get_adapter
    
    # Normalize the prompt (basic cleanup)
    normalized_prompt = prompt.strip()
    
    # Step 0: Optionally run spec-kit first (additive layer)
    spec_kit_enabled = should_use_spec_kit()
    spec_kit_success = None
    spec_kit_raw_output = None
    spec_kit_summary = None
    spec_kit_structure = None
    spec_quality_warnings = []
    spec_quality_score = None
    
    if spec_kit_enabled:
        try:
            spec_adapter = get_adapter()
            if spec_adapter:
                # Call spec-kit via adapter
                spec_raw, spec_findings, spec_exit, structure = spec_adapter.analyze_prompt(normalized_prompt)
                spec_kit_success = True
                spec_kit_raw_output = spec_raw
                
                # Extract structured spec elements
                if structure:
                    spec_kit_structure = structure.model_dump()
                    
                    # Detect missing or weak spec areas
                    spec_quality_warnings = detect_missing_spec_areas(structure)
                    
                    # Compute spec quality score
                    spec_quality_score = compute_spec_quality_score(structure, spec_quality_warnings, normalized_prompt)
                
                # Generate summary (spec-kit doesn't provide security findings)
                if spec_findings:
                    spec_kit_summary = f"spec-kit returned {len(spec_findings)} workflow findings"
                else:
                    spec_kit_summary = "spec-kit completed (workflow tool, not security analyzer)"
        except Exception as e:
            # Spec-kit failure should not abort the pipeline
            spec_kit_success = False
            spec_kit_raw_output = f"spec-kit error: {str(e)}"
            spec_kit_summary = f"spec-kit failed: {str(e)}"
            # Log but continue to dev-spec-kit
            import sys
            print(f"WARNING: spec-kit failed: {e}", file=sys.stderr)
    
    # Step 1: Run dev-spec-kit security checks (ALWAYS runs, regardless of spec-kit)
    devspec_raw_output, devspec_findings, exit_code = run_dev_spec_kit(normalized_prompt)
    
    # Step 1.5: Filter false positives based on context
    filtered_findings = filter_false_positives(normalized_prompt, devspec_findings)
    
    # Determine risk level based on finding severities
    has_blockers = any(f.severity.upper() == "BLOCKER" for f in filtered_findings)
    has_errors = any(f.severity.upper() == "ERROR" for f in filtered_findings)
    has_warnings = any(f.severity.upper() == "WARNING" for f in filtered_findings)
    
    # Calculate risk level based on severities (prioritize most severe)
    # BLOCKER = critical issues that must be addressed → High Risk
    # ERROR = significant security issues → Medium Risk
    # WARNING = minor concerns or best practices → Low Risk (but still flagged)
    if has_blockers:
        risk_level = "High"
    elif has_errors:
        risk_level = "Medium"
    elif has_warnings:
        risk_level = "Low"
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
        risk_level=risk_level,
        # Spec-kit fields (backwards compatible)
        spec_kit_enabled=spec_kit_enabled,
        spec_kit_success=spec_kit_success,
        spec_kit_raw_output=spec_kit_raw_output,
        spec_kit_summary=spec_kit_summary,
        # New spec quality fields
        spec_kit_structure=spec_kit_structure,
        spec_quality_warnings=spec_quality_warnings,
        spec_quality_score=spec_quality_score
    )
    
    return response
