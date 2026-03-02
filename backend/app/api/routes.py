"""
API routes for CrisisVerify. Exposes the POST /analyze endpoint.
"""
import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request

from app.models.claim_models import ClaimResult
from app.models.request_models import AnalyzeRequest
from app.models.response_models import AnalysisResponse, ErrorResponse, PerformanceMetadata
from app.services.claim_extractor import extract_claims
from app.services.evidence_fetcher import fetch_evidence
from app.services.report_generator import generate_report
from app.services.scoring_engine import score_claim

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Analyze text for factual claims and credibility",
    description=(
        "Accepts any text (tweet, news paragraph, official statement) and returns "
        "a structured credibility report with extracted claims, evidence, and scoring."
    ),
)
async def analyze_text(request: Request, body: AnalyzeRequest) -> AnalysisResponse:
    """
    Full verification pipeline:
    Input Text → Claim Extraction → Evidence Retrieval → Scoring → Report
    """
    t_start = time.monotonic()

    logger.info(
        "Received /analyze | crisis_mode=%s | text_len=%d",
        body.crisis_mode,
        len(body.text),
    )

    try:
        # ── Step 1: Extract Claims ─────────────────────────────────────────
        t_extract = time.monotonic()
        claims = await extract_claims(body.text)
        logger.info(
            "Claim extraction: %d claim(s) in %.0fms",
            len(claims),
            (time.monotonic() - t_extract) * 1000,
        )

        # ── Step 2 & 3: Fetch Evidence and Score — run claims concurrently ─
        t_evidence = time.monotonic()

        async def process_claim(claim: str) -> ClaimResult:
            evidence = await fetch_evidence(claim)
            score = score_claim(claim, evidence, body.crisis_mode)
            return ClaimResult(claim=claim, evidence=evidence, score=score)

        claim_results: list[ClaimResult] = await asyncio.gather(
            *[process_claim(c) for c in claims]
        )

        total_evidence = sum(len(r.evidence) for r in claim_results)
        logger.info(
            "Evidence + scoring: %d items across %d claims in %.0fms",
            total_evidence,
            len(claims),
            (time.monotonic() - t_evidence) * 1000,
        )

        # ── Step 4: Generate Report ────────────────────────────────────────
        report = generate_report(
            original_text=body.text,
            claim_results=list(claim_results),
            crisis_mode=body.crisis_mode,
        )

        processing_time_ms = int((time.monotonic() - t_start) * 1000)
        report.performance = PerformanceMetadata(
            processing_time_ms=processing_time_ms,
            claims_extracted=len(claims),
            evidence_items_retrieved=total_evidence,
        )

        logger.info(
            "Report complete | verdict=%s | confidence=%.1f | time=%dms",
            report.overall_verdict,
            report.overall_confidence,
            processing_time_ms,
        )
        return report

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in /analyze pipeline")
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        ) from exc
