"""
Pydantic response schemas for the CrisisVerify API.
"""
from typing import Optional
from pydantic import BaseModel, Field
from app.models.claim_models import ClaimResult, Verdict


class ScoringBreakdown(BaseModel):
    """Detailed breakdown of how the overall score was calculated."""
    formula: str = "Score = SourceWeight × RelevanceScore × RecencyFactor × 100"
    crisis_mode_active: bool
    claim_count: int
    average_source_weight: float
    average_relevance_score: float
    average_recency_factor: float


class PerformanceMetadata(BaseModel):
    """Timing metadata for engineering transparency."""
    processing_time_ms: int = Field(..., description="Total end-to-end processing time in milliseconds")
    claims_extracted: int
    evidence_items_retrieved: int


class AnalysisResponse(BaseModel):
    """Full structured response returned by the /analyze endpoint."""
    original_text: str = Field(..., description="The original input text")
    extracted_claims: list[str] = Field(..., description="List of extracted factual claims")
    claim_results: list[ClaimResult] = Field(..., description="Per-claim analysis results")
    overall_confidence: float = Field(..., ge=0.0, le=100.0, description="Overall confidence score 0-100")
    overall_verdict: Verdict = Field(..., description="Aggregate verdict across all claims")
    scoring_breakdown: ScoringBreakdown
    performance: Optional[PerformanceMetadata] = Field(None, description="Processing performance data")
    disclaimer: str = Field(
        default=(
            "CrisisVerify is an AI-assisted tool and NOT a fact-checking authority. "
            "Results are not 100% accurate. Human review is strongly recommended before "
            "acting on any information."
        )
    )


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str
    detail: Optional[str] = None
