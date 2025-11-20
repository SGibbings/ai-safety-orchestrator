"""
Legacy entry point for orchestrator - now superseded by api/main.py

The orchestrator functionality has been refactored into:
- orchestrator/pipeline.py - Main orchestration logic
- orchestrator/devspec_runner.py - Dev-spec-kit wrapper
- orchestrator/guidance_engine.py - Guidance generation
- orchestrator/claude_client.py - Claude API stub
- api/main.py - FastAPI application

To run the API server:
    python api/main.py
    
Or use uvicorn directly:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""
from .pipeline import analyze_prompt
import sys


def main():
    """
    Command-line interface for the orchestrator.
    Reads prompt from stdin or file and outputs analysis.
    """
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r') as f:
            prompt = f.read()
    else:
        # Read from stdin
        print("Enter your prompt (Ctrl+D or Ctrl+Z to finish):")
        prompt = sys.stdin.read()
    
    # Run analysis
    result = analyze_prompt(prompt)
    
    # Print results
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    print(f"\nExit Code: {result.exit_code}")
    print(f"Blockers: {result.has_blockers}")
    print(f"Errors: {result.has_errors}")
    print(f"\nFindings: {len(result.devspec_findings)}")
    for finding in result.devspec_findings:
        print(f"  [{finding.severity}] {finding.code}: {finding.message}")
    
    print(f"\nGuidance Items: {len(result.guidance)}")
    for item in result.guidance:
        print(f"  - {item.title}: {item.detail}")
    
    print("\n" + "="*80)
    print("CURATED PROMPT")
    print("="*80)
    print(result.final_curated_prompt)
    print("="*80)


if __name__ == "__main__":
    main()
