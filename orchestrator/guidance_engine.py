"""
Guidance engine that adds additional constraints and refines prompts
based on dev-spec-kit findings.
"""
from typing import Tuple
from .models import DevSpecFinding, GuidanceItem


def build_guidance(
    prompt: str, 
    findings: list[DevSpecFinding],
    risk_level: str
) -> Tuple[list[GuidanceItem], str]:
    """
    Generate guidance items and a curated prompt based on security findings.
    
    Args:
        prompt: The original developer prompt
        findings: List of findings from dev-spec-kit
        risk_level: Computed risk level (Low, Medium, High)
        
    Returns:
        Tuple of (guidance_items, final_curated_prompt)
    """
    guidance_items = []
    constraints = set()  # Use set to avoid duplicates
    
    # Categorize findings by severity
    blockers = [f for f in findings if f.severity.upper() == "BLOCKER"]
    errors = [f for f in findings if f.severity.upper() == "ERROR"]
    warnings = [f for f in findings if f.severity.upper() == "WARNING"]
    
    # Generate guidance based on findings
    if blockers:
        guidance_items.append(GuidanceItem(
            title="Critical Security Issues Detected",
            detail=f"Found {len(blockers)} BLOCKER-level security issues that must be addressed. "
                   f"These represent serious vulnerabilities that could lead to data breaches or system compromise."
        ))
        
    if errors:
        guidance_items.append(GuidanceItem(
            title="Security Errors Found",
            detail=f"Found {len(errors)} ERROR-level security issues. "
                   f"These should be fixed to meet security best practices."
        ))
    
    if warnings:
        guidance_items.append(GuidanceItem(
            title="Security Warnings",
            detail=f"Found {len(warnings)} WARNING-level issues. "
                   f"Consider addressing these to improve security posture."
        ))
    
    # Only build constraints for Medium and High risk
    if risk_level in ["Medium", "High"]:
        # Build constraints based on specific finding codes
        for finding in findings:
            # Map finding codes to specific constraints
            if "UNAUTH" in finding.code or "NO_AUTH" in finding.code:
                constraints.add("Require proper authentication and authorization for all endpoints")
                
            if "TLS" in finding.code or "HTTPS" in finding.code or "HTTP" in finding.code:
                constraints.add("Use HTTPS/TLS for all network communication, especially authentication flows")
                
            if "SECRET" in finding.code or "HARDCODED" in finding.code:
                constraints.add("Never hardcode secrets, tokens, or credentials in code or config files")
                constraints.add("Use environment variables or secure secret management systems")
                
            if "PASSWORD" in finding.code and "PLAINTEXT" in finding.code:
                constraints.add("Never store passwords in plain text; use bcrypt, Argon2, or PBKDF2 for password hashing")
                
            if "ADMIN" in finding.code or "BACKDOOR" in finding.code:
                constraints.add("Never auto-create admin accounts or backdoors")
                constraints.add("Implement secure admin account creation with strong authentication")
                
            if "DB_WIPE" in finding.code or "DROP" in finding.code:
                constraints.add("Never automatically wipe or recreate production data")
                constraints.add("Require explicit admin action for destructive operations")
                
            if "TMP" in finding.code:
                constraints.add("Store uploads in secure, persistent locations, not temporary directories")
                
            if "STACKTRACE" in finding.code or "DEBUG" in finding.code:
                constraints.add("Never expose stack traces, debug info, or environment variables to clients")
                constraints.add("Log sensitive errors securely on the server side only")
                
            if "DOCKER" in finding.code and "ROOT" in finding.code:
                constraints.add("Run Docker containers as non-root users for security")
                
            if "VALIDATION" in finding.code or "SKIP" in finding.code:
                constraints.add("Implement strict input validation on all external inputs")
                
            if "MD5" in finding.code or "WEAK_HASH" in finding.code:
                constraints.add("Use strong hashing algorithms (SHA-256 or better) instead of MD5 or SHA-1")
                
            if "GET" in finding.code and "AUTH" in finding.code:
                constraints.add("Use POST requests for authentication, not GET (to avoid credentials in URLs/logs)")
                
            if "FINANCIAL" in finding.code or "BALANCE" in finding.code or "PAYMENT" in finding.code:
                constraints.add("Implement strict authentication and authorization for all financial operations")
                constraints.add("Validate and audit all balance adjustments and transactions")
                
            if "PHI" in finding.code or "PATIENT" in finding.code:
                constraints.add("Encrypt all Protected Health Information (PHI) at rest and in transit")
                constraints.add("Implement HIPAA-compliant access controls")
                
            if "ARCH_" in finding.code:
                # Architecture warnings - add to guidance but not constraints
                if "CONFLICTING" in finding.code or "VAGUE" in finding.code:
                    guidance_items.append(GuidanceItem(
                        title="Clarify Technology Stack",
                        detail="Choose a single, consistent technology stack. Avoid mixing incompatible frameworks."
                    ))
    
    # Convert constraints set to sorted list for consistent output
    constraints_list = sorted(list(constraints))
    
    # Build the final curated prompt
    final_curated_prompt = build_curated_prompt(prompt, constraints_list, risk_level)
    
    # Add summary guidance
    if findings:
        guidance_items.insert(0, GuidanceItem(
            title="Security Analysis Summary",
            detail=f"Analyzed prompt and found {len(findings)} total issues: "
                   f"{len(blockers)} blockers, {len(errors)} errors, {len(warnings)} warnings. "
                   f"Risk Level: {risk_level}."
        ))
    else:
        guidance_items.append(GuidanceItem(
            title="No Security Issues Detected",
            detail="The prompt passed all security checks. Proceed with implementation following best practices."
        ))
    
    return guidance_items, final_curated_prompt


def build_curated_prompt(original_prompt: str, constraints: list[str], risk_level: str) -> str:
    """
    Build a curated prompt by adding security constraints to the original.
    
    Args:
        original_prompt: The original developer prompt
        constraints: List of constraint strings to add
        risk_level: The computed risk level (Low, Medium, High)
        
    Returns:
        Curated prompt with security constraints
    """
    if risk_level == "Low":
        # No security issues found, return original with minimal note
        return f"""{original_prompt}

---
SECURITY ANALYSIS: Low Risk
No security issues detected. Follow standard secure development practices.
"""
    
    if not constraints:
        # Medium/High risk but no specific constraints generated
        return f"""{original_prompt}

---
SECURITY ANALYSIS: {risk_level} Risk
Security issues detected. Review the findings and address them during implementation.
"""
    
    # Medium or High risk with specific constraints
    # Format constraints with bullet points
    formatted_constraints = "\n".join([f"- {c}" for c in constraints])
    
    curated = f"""{original_prompt}

---
IMPORTANT SECURITY CONSTRAINTS:
The following security requirements MUST be followed during implementation:

{formatted_constraints}

---
These constraints have been added based on automated security analysis (Risk Level: {risk_level}).
Do not implement features that violate these requirements.
"""
    
    return curated
