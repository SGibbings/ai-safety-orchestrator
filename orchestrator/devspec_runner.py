"""
Wrapper module for calling dev-spec-kit shell scripts and parsing their output.
"""
import subprocess
import os
import re
from typing import Tuple
from .models import DevSpecFinding


def run_dev_spec_kit(prompt: str) -> Tuple[str, list[DevSpecFinding], int]:
    """
    Run the dev-spec-kit security checker on the given prompt.
    
    Args:
        prompt: The developer prompt to analyze
        
    Returns:
        Tuple of (raw_output, parsed_findings, exit_code)
    """
    # Determine the path to the security-check script
    # Assuming we're running from repo root
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dev-spec-kit",
        "scripts",
        "security-check.new.sh"
    )
    
    if not os.path.exists(script_path):
        # Fall back to security-check.sh if .new.sh doesn't exist
        script_path = script_path.replace("security-check.new.sh", "security-check.sh")
    
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Dev-spec-kit script not found at {script_path}")
    
    # Make sure script is executable
    os.chmod(script_path, 0o755)
    
    try:
        # Run the script with prompt as stdin
        result = subprocess.run(
            [script_path],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        raw_output = result.stdout
        exit_code = result.returncode
        
        # Parse the output into findings
        findings = parse_devspec_output(raw_output)
        
        return raw_output, findings, exit_code
        
    except subprocess.TimeoutExpired:
        return "ERROR: Script execution timed out", [], -1
    except Exception as e:
        return f"ERROR: {str(e)}", [], -1


def parse_devspec_output(output: str) -> list[DevSpecFinding]:
    """
    Parse the output from dev-spec-kit into structured findings.
    
    Expected format:
    [CATEGORY][SEVERITY][CODE]
    Message text
    Suggestion: Suggestion text
    
    Args:
        output: Raw text output from the script
        
    Returns:
        List of DevSpecFinding objects
    """
    findings = []
    lines = output.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for pattern like [SECURITY][BLOCKER][SEC_UNAUTH_DELETE]
        match = re.match(r'\[([A-Z]+)\]\[([A-Z]+)\]\[([A-Z_0-9]+)\]', line)
        
        if match:
            category = match.group(1)
            severity = match.group(2)
            code = match.group(3)
            
            # Next line should be the message
            message = ""
            suggestion = ""
            
            i += 1
            if i < len(lines):
                message = lines[i].strip()
            
            # Next line should be the suggestion
            i += 1
            if i < len(lines) and lines[i].strip().startswith("Suggestion:"):
                suggestion = lines[i].strip().replace("Suggestion:", "").strip()
            
            finding = DevSpecFinding(
                category=category,
                severity=severity,
                code=code,
                message=message,
                suggestion=suggestion
            )
            findings.append(finding)
        
        i += 1
    
    return findings
