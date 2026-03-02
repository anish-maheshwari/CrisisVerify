"""
Report Generator for CrisisVerify.
Aggregates per-claim results into a final structured AnalysisResponse.
"""
import logging
from collections import Counter

from app.models.claim_models import ClaimResult, Verdict
from app.models.response_models import AnalysisResponse, ScoringBreakdown

logger = logging.getLogger(__name__)


def _majority_verdict(results: list[ClaimResult]) -> Verdict:
    """
    Determine the overall verdict by majority rule over per-claim verdicts.
    In case of a tie, apply the more conservative verdict.
    """
    counts: Counter[Verdict] = Counter(r.score.verdict for r in results)
    # Priority order (most conservative wins ties)
    for verdict in [Verdict.LIKELY_FALSE, Verdict.DEVELOPING, Verdict.VERIFIED]:
        if counts[verdict] >= len(results) / 2:
            return verdict
    return Verdict.DEVELOPING  # Safe default


def generate_report(
    original_text: str,
    claim_results: list[ClaimResult],
    crisis_mode: bool,
) -> AnalysisResponse:
    """
    Aggregate per-claim scoring results into a final AnalysisResponse.

    Args:
        original_text: The original input text from the user.
        claim_results: List of fully scored ClaimResult objects.
        crisis_mode: Whether crisis mode was active for this run.

    Returns:
        A fully structured AnalysisResponse.
    """
    if not claim_results:
        return AnalysisResponse(
            original_text=original_text,
            extracted_claims=[],
            claim_results=[],
            overall_confidence=0.0,
            overall_verdict=Verdict.LIKELY_FALSE,
            scoring_breakdown=ScoringBreakdown(
                crisis_mode_active=crisis_mode,
                claim_count=0,
                average_source_weight=0.0,
                average_relevance_score=0.0,
                average_recency_factor=0.0,
            ),
        )

    # Aggregate scores
    scores = [r.score.claim_score for r in claim_results]
    overall_confidence = round(sum(scores) / len(scores), 2)
    overall_verdict = _majority_verdict(claim_results)

    # Aggregate scoring component averages for the breakdown
    avg_src = round(
        sum(r.score.source_weight_avg for r in claim_results) / len(claim_results), 3
    )
    avg_rel = round(
        sum(r.score.relevance_score for r in claim_results) / len(claim_results), 3
    )
    avg_rec = round(
        sum(r.score.recency_factor for r in claim_results) / len(claim_results), 3
    )

    scoring_breakdown = ScoringBreakdown(
        crisis_mode_active=crisis_mode,
        claim_count=len(claim_results),
        average_source_weight=avg_src,
        average_relevance_score=avg_rel,
        average_recency_factor=avg_rec,
    )

    return AnalysisResponse(
        original_text=original_text,
        extracted_claims=[r.claim for r in claim_results],
        claim_results=claim_results,
        overall_confidence=overall_confidence,
        overall_verdict=overall_verdict,
        scoring_breakdown=scoring_breakdown,
    )
