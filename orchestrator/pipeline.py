"""
Main orchestration pipeline that coordinates all components.
"""
from .models import AnalysisResponse
from .devspec_runner import run_dev_spec_kit
from .guidance_engine import build_guidance
from .claude_client import call_claude


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
    
    # Determine if we have blockers or errors
    has_blockers = any(f.severity == "BLOCKER" for f in devspec_findings)
    has_errors = any(f.severity == "ERROR" for f in devspec_findings)
    
    # Step 2: Generate guidance and curated prompt
    guidance_items, final_curated_prompt = build_guidance(normalized_prompt, devspec_findings)
    
    # Step 3: Optionally call Claude
    claude_output = None
    if call_claude_api:
        claude_output = call_claude(final_curated_prompt)
    
    # Build the complete response
    response = AnalysisResponse(
        original_prompt=prompt,
        normalized_prompt=normalized_prompt,
        devspec_raw_output=devspec_raw_output,
        devspec_findings=devspec_findings,
        guidance=guidance_items,
        final_curated_prompt=final_curated_prompt,
        claude_output=claude_output,
        exit_code=exit_code,
        has_blockers=has_blockers,
        has_errors=has_errors
    )
    
    return response
