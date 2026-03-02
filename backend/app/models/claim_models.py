"""
Core domain models for CrisisVerify.
These represent the internal data structures that flow through the pipeline.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """The final credibility verdict for a claim."""
    VERIFIED = "Verified"
    DEVELOPING = "Developing"
    LIKELY_FALSE = "Likely False"


class Evidence(BaseModel):
    """A single piece of evidence retrieved for a claim."""
    source_name: str = Field(..., description="Name of the publication or source")
    url: str = Field(..., description="URL of the source article")
    snippet: str = Field(..., description="Relevant excerpt from the source")
    published_date: Optional[str] = Field(None, description="ISO date string if available")
    credibility_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Credibility weight for this source (0-1)"
    )


class ScoreBreakdown(BaseModel):
    """
    Full transparency breakdown of the weighted additive + stance scoring formula.

    FinalScore = (WeightedSourceScore × 0.40)
               + (StanceScore         × 0.35)
               + (RelevanceScore      × 0.15)
               + (RecencyScore        × 0.10)
               × CrisisModifier

    Stance dominance hard-overrides the additive score when ratios are decisive.
    """
    # Contribution points (what went into the base score sum)
    weighted_source_component: float = Field(..., description="WSS × 0.40 contribution (0–40)")
    stance_component: float = Field(..., description="StanceScore × 0.35 contribution (0–35)")
    relevance_component: float = Field(..., description="Relevance × 0.15 contribution (0–15)")
    recency_component: float = Field(..., description="Recency × 0.10 contribution (0–10)")
    crisis_modifier: float = Field(..., description="0.9 if crisis mode, 1.0 otherwise")
    final_score: float = Field(..., description="Computed final score (0–100)")

    # Raw sub-scores (0–100 scale, before weights)
    weighted_source_score: float = Field(..., description="Avg credibility × 100 (0–100)")
    stance_score: float = Field(..., description="StanceScore (0–100)")
    relevance_score: float = Field(..., description="Relevance (0–100)")
    recency_score: float = Field(..., description="Recency (0–100)")

    # Stance ratios (proportion of credible source weight)
    support_ratio: float = Field(..., description="Fraction of credible weight that supports (0–1)")
    refute_ratio: float = Field(..., description="Fraction of credible weight that refutes (0–1)")
    stance_summary: str = Field(..., description="Human-readable stance summary sentence")


class ClaimScore(BaseModel):
    """The scoring result for a single extracted claim."""
    claim_score: float = Field(..., ge=0.0, le=100.0, description="Credibility score 0-100")
    verdict: Verdict
    reasoning: str = Field(..., description="Human-readable explanation of the scoring")
    # Legacy fields (kept for backward compatibility)
    source_weight_avg: float
    relevance_score: float
    recency_factor: float
    crisis_penalty: float = Field(default=0.0)
    # Full breakdown
    breakdown: ScoreBreakdown


class ClaimResult(BaseModel):
    """The full analysis result for a single claim."""
    claim: str
    evidence: list[Evidence]
    score: ClaimScore
