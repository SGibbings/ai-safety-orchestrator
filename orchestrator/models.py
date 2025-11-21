"""
Pydantic models for request/response validation and data structures.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PromptRequest(BaseModel):
    """Request model for analyzing a developer prompt."""
    prompt: str = Field(..., description="The raw developer prompt to analyze")


class DevSpecFinding(BaseModel):
    """A single finding from the dev-spec-kit security checker."""
    category: str = Field(default="UNKNOWN", description="Category like SECURITY or ARCH")
    severity: str = Field(default="UNKNOWN", description="Severity level: INFO, WARNING, ERROR, or BLOCKER")
    code: str = Field(default="UNKNOWN", description="Rule code that triggered")
    message: str = Field(default="", description="Description of the issue")
    suggestion: str = Field(default="", description="Recommendation to fix the issue")


class GuidanceItem(BaseModel):
    """Additional guidance generated on top of dev-spec-kit findings."""
    title: str = Field(..., description="Short title for the guidance")
    detail: str = Field(..., description="Detailed explanation or constraint")


class AnalysisResponse(BaseModel):
    """Complete analysis response including all stages of processing."""
    original_prompt: str = Field(..., description="The original input prompt")
    normalized_prompt: Optional[str] = Field(None, description="Normalized version of the prompt")
    devspec_raw_output: str = Field(..., description="Raw output from dev-spec-kit")
    devspec_findings: list[DevSpecFinding] = Field(default_factory=list, description="Parsed findings from dev-spec-kit")
    guidance: list[GuidanceItem] = Field(default_factory=list, description="Additional guidance items")
    final_curated_prompt: str = Field(..., description="Refined prompt with security constraints")
    claude_output: Optional[str] = Field(None, description="Output from Claude (placeholder for now)")
    exit_code: int = Field(default=0, description="Exit code from dev-spec-kit script")
    has_blockers: bool = Field(default=False, description="Whether any BLOCKER issues were found")
    has_errors: bool = Field(default=False, description="Whether any ERROR issues were found")
    risk_level: str = Field(default="Low", description="Overall risk level: Low, Medium, or High")
