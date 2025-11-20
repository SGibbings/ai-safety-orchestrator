"""
FastAPI application for the AI Safety Orchestrator.

This API provides endpoints to:
- Analyze developer prompts for security issues
- Generate guidance and constraints
- Produce curated prompts for safe code generation
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.models import PromptRequest, AnalysisResponse
from orchestrator.pipeline import analyze_prompt

# Initialize FastAPI app
app = FastAPI(
    title="AI Safety Orchestrator",
    description="Orchestrates security analysis and prompt curation for AI-assisted development",
    version="1.0.0"
)

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AI Safety Orchestrator",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "analyze": "/api/analyze - Analyze a developer prompt for security issues",
            "health": "/health - Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-safety-orchestrator"
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(request: PromptRequest):
    """
    Analyze a developer prompt for security issues and generate guidance.
    
    This endpoint:
    1. Runs dev-spec-kit security checks
    2. Generates additional guidance
    3. Produces a curated prompt with security constraints
    
    Args:
        request: PromptRequest containing the prompt to analyze
        
    Returns:
        AnalysisResponse with complete analysis results
    """
    try:
        # Run the analysis pipeline
        result = analyze_prompt(
            prompt=request.prompt,
            call_claude_api=False  # For now, keep Claude stub disabled
        )
        
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dev-spec-kit not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/api/analyze-with-claude", response_model=AnalysisResponse)
async def analyze_with_claude_endpoint(request: PromptRequest):
    """
    Analyze a prompt and include Claude stub output.
    
    This is the same as /api/analyze but includes the Claude stub response.
    When Claude integration is implemented, this will make an actual API call.
    
    Args:
        request: PromptRequest containing the prompt to analyze
        
    Returns:
        AnalysisResponse including claude_output field
    """
    try:
        # Run the analysis pipeline with Claude enabled
        result = analyze_prompt(
            prompt=request.prompt,
            call_claude_api=True  # Enable Claude stub
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
