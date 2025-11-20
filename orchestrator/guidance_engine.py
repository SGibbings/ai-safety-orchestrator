"""
Guidance engine that adds additional constraints and refines prompts
based on dev-spec-kit findings.
"""
from typing import Tuple
from .models import DevSpecFinding, GuidanceItem


def build_guidance(
    prompt: str, 
    findings: list[DevSpecFinding]
) -> Tuple[list[GuidanceItem], str]:
    """
    Generate guidance items and a curated prompt based on security findings.
    
    Args:
        prompt: The original developer prompt
        findings: List of findings from dev-spec-kit
        
    Returns:
        Tuple of (guidance_items, final_curated_prompt)
    """
    guidance_items = []
    constraints = []
    
    # Categorize findings by severity
    blockers = [f for f in findings if f.severity == "BLOCKER"]
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    
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
    
    # Build constraints based on specific finding codes
    seen_codes = set()
    for finding in findings:
        if finding.code in seen_codes:
            continue
        seen_codes.add(finding.code)
        
        # Map finding codes to specific constraints
        if "UNAUTH" in finding.code or "NO_AUTH" in finding.code:
            constraints.append("- Require proper authentication and authorization for all endpoints")
            guidance_items.append(GuidanceItem(
                title="Authentication Required",
                detail="All endpoints must implement proper authentication. Use established auth frameworks."
            ))
            
        if "TLS" in finding.code or "HTTPS" in finding.code:
            constraints.append("- Use HTTPS/TLS for all network communication, especially authentication flows")
            guidance_items.append(GuidanceItem(
                title="Use HTTPS/TLS",
                detail="Always use HTTPS/TLS for secure communication, even in internal networks."
            ))
            
        if "SECRET" in finding.code or "JWT" in finding.code or "TOKEN" in finding.code:
            constraints.append("- Never hardcode secrets, tokens, or credentials in code or config files")
            constraints.append("- Use environment variables or secure secret management systems")
            guidance_items.append(GuidanceItem(
                title="Secure Secret Management",
                detail="Use environment variables or dedicated secret managers (e.g., AWS Secrets Manager, HashiCorp Vault)."
            ))
            
        if "ADMIN" in finding.code or "BACKDOOR" in finding.code:
            constraints.append("- Never auto-create admin accounts or backdoors")
            constraints.append("- Implement secure admin account creation with strong authentication")
            
        if "DB_WIPE" in finding.code or "DROP" in finding.code:
            constraints.append("- Never automatically wipe or recreate production data")
            constraints.append("- Require explicit admin action for destructive operations")
            
        if "TMP" in finding.code:
            constraints.append("- Store uploads in secure, persistent locations, not temporary directories")
            
        if "STACKTRACE" in finding.code or "DEBUG" in finding.code:
            constraints.append("- Never expose stack traces, debug info, or environment variables to clients")
            constraints.append("- Log sensitive errors securely on the server side only")
            
        if "DOCKER" in finding.code and "ROOT" in finding.code:
            constraints.append("- Run Docker containers as non-root users for security")
            
        if "FINANCIAL" in finding.code or "BALANCE" in finding.code or "PAYMENT" in finding.code:
            constraints.append("- Implement strict authentication and authorization for all financial operations")
            constraints.append("- Validate and audit all balance adjustments and transactions")
            
        if "PHI" in finding.code or "PATIENT" in finding.code:
            constraints.append("- Encrypt all Protected Health Information (PHI) at rest and in transit")
            constraints.append("- Implement HIPAA-compliant access controls")
            
        if "ARCH_" in finding.code:
            # Architecture warnings
            if "CONFLICTING" in finding.code or "VAGUE" in finding.code:
                guidance_items.append(GuidanceItem(
                    title="Clarify Technology Stack",
                    detail="Choose a single, consistent technology stack. Avoid mixing incompatible frameworks."
                ))
    
    # Build the final curated prompt
    final_curated_prompt = build_curated_prompt(prompt, constraints)
    
    # Add summary guidance if we have findings
    if findings:
        guidance_items.insert(0, GuidanceItem(
            title="Security Analysis Summary",
            detail=f"Analyzed prompt and found {len(findings)} total issues: "
                   f"{len(blockers)} blockers, {len(errors)} errors, {len(warnings)} warnings."
        ))
    else:
        guidance_items.append(GuidanceItem(
            title="No Security Issues Detected",
            detail="The prompt passed all security checks. Proceed with implementation following best practices."
        ))
    
    return guidance_items, final_curated_prompt


def build_curated_prompt(original_prompt: str, constraints: list[str]) -> str:
    """
    Build a curated prompt by adding security constraints to the original.
    
    Args:
        original_prompt: The original developer prompt
        constraints: List of constraint strings to add
        
    Returns:
        Curated prompt with security constraints
    """
    if not constraints:
        # No issues found, return original with a note
        return f"""{original_prompt}

---
SECURITY NOTE: This prompt has been analyzed and no security issues were detected.
Please follow general security best practices during implementation.
"""
    
    # Add constraints to the prompt
    curated = f"""{original_prompt}

---
IMPORTANT SECURITY CONSTRAINTS:
The following security requirements MUST be followed during implementation:

{chr(10).join(constraints)}

---
These constraints have been added based on automated security analysis.
Do not implement features that violate these requirements.
"""
    
    return curated
