// Strict TypeScript types for all CrisisVerify analysis domain objects.
// These must mirror the backend Pydantic response schemas exactly.

export type Verdict = "Verified" | "Developing" | "Likely False";

export interface Evidence {
    source_name: string;
    url: string;
    snippet: string;
    published_date: string | null;
    credibility_weight: number;
}

export interface ScoreBreakdown {
    // Component contributions (points added to BaseScore)
    weighted_source_component: number;   // 0–40  (WSS × 0.40)
    stance_component: number;            // 0–35  (Stance × 0.35)
    relevance_component: number;         // 0–15  (Rel × 0.15)
    recency_component: number;           // 0–10  (Rec × 0.10)
    crisis_modifier: number;             // 0.9 or 1.0
    final_score: number;

    // Raw sub-scores (0–100 each)
    weighted_source_score: number;
    stance_score: number;
    relevance_score: number;
    recency_score: number;

    // Stance-specific
    support_ratio: number;     // 0–1: fraction of credible weight that SUPPORTS
    refute_ratio: number;      // 0–1: fraction of credible weight that REFUTES
    stance_summary: string;    // e.g. "3 credible sources refute this claim."
}

export interface ClaimScore {
    claim_score: number;
    verdict: Verdict;
    reasoning: string;
    // Legacy fields
    source_weight_avg: number;
    relevance_score: number;
    recency_factor: number;
    crisis_penalty: number;
    // Detailed breakdown
    breakdown: ScoreBreakdown;
}

export interface ClaimResult {
    claim: string;
    evidence: Evidence[];
    score: ClaimScore;
}

export interface ScoringBreakdown {
    formula: string;
    crisis_mode_active: boolean;
    claim_count: number;
    average_source_weight: number;
    average_relevance_score: number;
    average_recency_factor: number;
}

export interface PerformanceMetrics {
    processing_time_ms: number;
    claims_extracted: number;
    evidence_items_retrieved: number;
}

export interface AnalysisResult {
    original_text: string;
    extracted_claims: string[];
    claim_results: ClaimResult[];
    overall_confidence: number;
    overall_verdict: Verdict;
    scoring_breakdown: ScoringBreakdown;
    disclaimer: string;
    performance?: PerformanceMetrics;
}

export interface AnalyzeRequest {
    text: string;
    crisis_mode: boolean;
}

export interface ApiError {
    error: string;
    detail?: string;
}
