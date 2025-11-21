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


class SpecKitStructure(BaseModel):
    """Structured representation of spec elements extracted from spec-kit."""
    features: list[str] = Field(default_factory=list, description="Features or capabilities mentioned")
    entities: list[str] = Field(default_factory=list, description="Entities, models, or data structures")
    flows: list[str] = Field(default_factory=list, description="User flows, workflows, or processes")
    configuration: list[str] = Field(default_factory=list, description="Configuration or environment settings")
    error_handling: list[str] = Field(default_factory=list, description="Error handling or fallback strategies")
    testing: list[str] = Field(default_factory=list, description="Testing strategies or test cases")
    logging: list[str] = Field(default_factory=list, description="Logging or observability plans")
    authentication: list[str] = Field(default_factory=list, description="Authentication or authorization mechanisms")
    data_storage: list[str] = Field(default_factory=list, description="Data storage or persistence layer")


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
    
    # Spec-kit integration fields (optional, backwards compatible)
    spec_kit_enabled: bool = Field(default=False, description="Whether spec-kit was used in this analysis")
    spec_kit_success: Optional[bool] = Field(default=None, description="Whether spec-kit call succeeded (None if not used)")
    spec_kit_raw_output: Optional[str] = Field(default=None, description="Raw output from spec-kit (None if not used or failed)")
    spec_kit_summary: Optional[str] = Field(default=None, description="Summary of spec-kit results (None if not used)")
    spec_kit_structure: Optional[dict] = Field(default=None, description="Structured spec breakdown from spec-kit (None if not used)")
    spec_quality_warnings: list[str] = Field(default_factory=list, description="Warnings about missing or weak spec areas")
    spec_quality_score: Optional[int] = Field(default=None, ge=0, le=100, description="Spec quality score 0-100 (None if spec-kit not used)")

