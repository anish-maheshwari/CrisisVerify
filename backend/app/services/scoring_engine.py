"""
Scoring Engine for CrisisVerify — Weighted Additive + Stance-Aware Model.

Formula:
    BaseScore =
        (WeightedSourceScore × 0.40) +
        (StanceScore         × 0.35) +
        (RelevanceScore      × 0.15) +
        (RecencyScore        × 0.10)

    FinalScore = BaseScore × CrisisModifier  (CrisisModifier = 0.9 if crisis, else 1.0)

Stance Dominance Hard Overrides (applied after formula):
    refute_ratio  ≥ 0.60  →  FinalScore clamped to 10–25  (Likely False)
    support_ratio ≥ 0.60  →  FinalScore boosted to 75–95  (Verified)

StanceScore:
    If support_ratio ≥ refute_ratio:  StanceScore = support_ratio × 100
    Else:                              StanceScore = (1 - refute_ratio) × 100
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from app.models.claim_models import ClaimScore, Evidence, ScoreBreakdown, Verdict
from app.services.stance_classifier import classify_stance, compute_stance_ratios

logger = logging.getLogger(__name__)

# ── Verdict thresholds ───────────────────────────────────────────────────────
_THRESHOLD_VERIFIED   = 75.0
_THRESHOLD_DEVELOPING = 40.0

# Stance dominance thresholds
_STANCE_DOMINANCE_THRESHOLD = 0.60

# Score ranges for stance dominance override
_REFUTE_SCORE_RANGE   = (10.0, 25.0)  # collapsed when strongly refuted
_SUPPORT_SCORE_RANGE  = (75.0, 95.0)  # boosted when strongly supported


# ── Recency ──────────────────────────────────────────────────────────────────

def _compute_recency_score(published_date: Optional[str]) -> float:
    """Map publication age to 0–100."""
    if not published_date:
        return 60.0

    now = datetime.now(tz=timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(published_date, fmt).replace(tzinfo=timezone.utc)
            hours = (now - parsed).total_seconds() / 3600
            if hours <= 24:
                return 100.0
            elif hours <= 72:
                return 90.0
            elif hours <= 168:
                return 80.0
            else:
                return 40.0
        except ValueError:
            continue

    m = re.search(r"(\d+)\s+day", published_date, re.IGNORECASE)
    if m:
        d = int(m.group(1))
        return 100.0 if d < 1 else (90.0 if d <= 3 else (80.0 if d <= 7 else 40.0))
    if re.search(r"(\d+)\s+(hour|minute)", published_date, re.IGNORECASE):
        return 100.0
    return 60.0


def _compute_recency_factor(published_date: Optional[str]) -> float:
    return _compute_recency_score(published_date) / 100.0


def _compute_avg_recency(evidence: list[Evidence]) -> tuple[float, float]:
    scores = [_compute_recency_score(e.published_date) for e in evidence]
    avg = sum(scores) / len(scores) if scores else 60.0
    return round(avg, 2), round(avg / 100.0, 3)


# ── Relevance ─────────────────────────────────────────────────────────────────

def _stem(word: str) -> str:
    w = word.lower()
    for suffix in ("ings", "ing", "tion", "ions", "ies", "ied", "ers", "ed", "es", "ly", "s"):
        stem = w[: -len(suffix)] if w.endswith(suffix) else None
        if stem and len(stem) >= 3:
            return stem
    return w


_SYNONYM_ROOTS = [
    {"die", "dead", "death", "kill", "perish", "fatal"},
    {"collaps", "destroy", "demolish", "fall"},
    {"injur", "wound", "hurt"},
    {"confirm", "announc", "declar", "stat"},
    {"displac", "evacuat", "fled", "refugee"},
    {"attack", "struck", "bomb", "airstrik", "shell"},
    {"arrest", "detain", "captur"},
]

_STOPWORDS = {
    "a", "an", "the", "is", "in", "of", "to", "and", "or", "was",
    "were", "has", "have", "had", "it", "be", "are", "for", "on",
    "at", "by", "with", "from", "that", "this", "as", "but", "not",
    "its", "his", "her", "their", "also", "been", "who", "how",
    "what", "when", "where", "why", "will", "would", "could", "should",
}


def _expand_synonyms(stems: set[str]) -> set[str]:
    expanded = set(stems)
    for group in _SYNONYM_ROOTS:
        if stems & group:
            expanded |= group
    return expanded


def _tokenize_and_stem(text: str) -> set[str]:
    raw = {w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text) if w.lower() not in _STOPWORDS}
    return {_stem(w) for w in raw}


def _compute_relevance_score(claim: str, snippet: str) -> float:
    """Relevance 0.0–1.0 using stemming + synonym expansion + prefix matching."""
    if not snippet:
        return 0.10
    claim_stems = _expand_synonyms(_tokenize_and_stem(claim))
    snippet_stems = _expand_synonyms(_tokenize_and_stem(snippet))
    if not claim_stems:
        return 0.30
    direct = claim_stems & snippet_stems
    partial: set[str] = set()
    for cs in claim_stems - direct:
        if len(cs) < 5:
            continue
        for ss in snippet_stems - direct:
            if len(ss) >= 5 and ss[:5] == cs[:5]:
                partial.add(cs)
                break
    total = len(direct) + len(partial)
    coverage = total / max(len(claim_stems), 1)
    jaccard = total / max(len(claim_stems | snippet_stems), 1)
    score = 0.35 * jaccard + 0.65 * coverage
    return round(min(1.0, max(0.10, score)), 3)


def _determine_verdict(score: float) -> Verdict:
    if score >= _THRESHOLD_VERIFIED:
        return Verdict.VERIFIED
    elif score >= _THRESHOLD_DEVELOPING:
        return Verdict.DEVELOPING
    else:
        return Verdict.LIKELY_FALSE


# ── Scoring Components ────────────────────────────────────────────────────────

def _compute_weighted_source_score(evidence: list[Evidence]) -> tuple[float, float]:
    """Average credibility weight × 100. Returns (score_0_100, avg_weight)."""
    if not evidence:
        return 0.0, 0.0
    avg_w = sum(e.credibility_weight for e in evidence) / len(evidence)
    return round(avg_w * 100.0, 2), round(avg_w, 3)


def _compute_stance_score(support_ratio: float, refute_ratio: float) -> float:
    """
    StanceScore (0–100).
    If support dominates → support_ratio × 100.
    If refute dominates  → (1 - refute_ratio) × 100.
    Collapsed toward 50 when neither dominates (uncertain).
    """
    if support_ratio >= refute_ratio:
        return round(support_ratio * 100.0, 2)
    else:
        return round((1.0 - refute_ratio) * 100.0, 2)


def _apply_stance_override(
    base_score: float,
    support_ratio: float,
    refute_ratio: float,
) -> tuple[float, bool]:
    """
    Apply stance dominance hard override.
    Returns (overridden_score, was_overridden_bool).
    """
    if refute_ratio >= _STANCE_DOMINANCE_THRESHOLD:
        # Strong refutation: collapse to 10–25 range
        # Scale within range based on refute_ratio severity
        low, high = _REFUTE_SCORE_RANGE
        score = high - (refute_ratio - _STANCE_DOMINANCE_THRESHOLD) / 0.4 * (high - low)
        return round(max(low, min(high, score)), 2), True

    if support_ratio >= _STANCE_DOMINANCE_THRESHOLD:
        # Strong support: boost to 75–95 range
        low, high = _SUPPORT_SCORE_RANGE
        score = low + (support_ratio - _STANCE_DOMINANCE_THRESHOLD) / 0.4 * (high - low)
        return round(max(low, min(high, score)), 2), True

    return base_score, False


def _compute_avg_relevance(evidence: list[Evidence], claim: str) -> tuple[float, float]:
    """Returns (avg_relevance_0_100, avg_relevance_0_1)."""
    if not evidence:
        return 0.0, 0.0
    scores = [_compute_relevance_score(claim, e.snippet) for e in evidence]
    avg01 = sum(scores) / len(scores)
    return round(avg01 * 100.0, 2), round(avg01, 3)


# ── Transparency ──────────────────────────────────────────────────────────────

def _build_reasoning(
    breakdown: ScoreBreakdown,
    verdict: Verdict,
    stance_override: bool,
) -> str:
    verdict_text = {
        Verdict.VERIFIED: "Multiple credible sources with strong supporting stance confirm this claim.",
        Verdict.DEVELOPING: "Partial or mixed evidence. Sources exist but consensus or stance is insufficient for full verification.",
        Verdict.LIKELY_FALSE: "Credible sources predominantly refute or contradict this claim.",
    }

    lines = [
        f"Source Credibility: {breakdown.weighted_source_score:.1f}/100 → {breakdown.weighted_source_component:.1f} pts (×0.40)",
        f"Stance Score: {breakdown.stance_score:.1f}/100 → {breakdown.stance_component:.1f} pts (×0.35) | support={breakdown.support_ratio:.0%} refute={breakdown.refute_ratio:.0%}",
        f"Relevance: {breakdown.relevance_score:.1f}/100 → {breakdown.relevance_component:.1f} pts (×0.15)",
        f"Recency: {breakdown.recency_score:.1f}/100 → {breakdown.recency_component:.1f} pts (×0.10)",
    ]

    if stance_override:
        if breakdown.refute_ratio >= _STANCE_DOMINANCE_THRESHOLD:
            lines.append(f"⚠ Stance override applied: {breakdown.refute_ratio:.0%} of credible sources REFUTE. Score clamped to {_REFUTE_SCORE_RANGE[0]}–{_REFUTE_SCORE_RANGE[1]}.")
        elif breakdown.support_ratio >= _STANCE_DOMINANCE_THRESHOLD:
            lines.append(f"✓ Stance override applied: {breakdown.support_ratio:.0%} of credible sources SUPPORT. Score boosted to {_SUPPORT_SCORE_RANGE[0]}–{_SUPPORT_SCORE_RANGE[1]}.")

    if breakdown.crisis_modifier < 1.0:
        base = breakdown.weighted_source_component + breakdown.stance_component + breakdown.relevance_component + breakdown.recency_component
        lines.append(f"Crisis modifier ×{breakdown.crisis_modifier} applied (base={base:.1f} → final={breakdown.final_score:.1f})")

    lines.append(f"Verdict: {verdict.value} — {verdict_text[verdict]}")
    return " | ".join(lines)


# ── Public Entry Point ────────────────────────────────────────────────────────

def score_claim(
    claim: str,
    evidence: list[Evidence],
    crisis_mode: bool,
) -> ClaimScore:
    """
    Compute claim credibility using the weighted additive + stance-aware model.
    Stance dominance can hard-override the formula score.
    """
    if not evidence:
        empty = ScoreBreakdown(
            weighted_source_component=0.0, stance_component=0.0,
            relevance_component=0.0, recency_component=0.0,
            crisis_modifier=1.0, final_score=5.0,
            weighted_source_score=0.0, stance_score=0.0,
            relevance_score=0.0, recency_score=0.0,
            support_ratio=0.0, refute_ratio=0.0,
            stance_summary="No evidence retrieved.",
        )
        return ClaimScore(
            claim_score=5.0, verdict=Verdict.LIKELY_FALSE,
            reasoning="No supporting evidence retrieved. Score defaulted to minimum.",
            source_weight_avg=0.0, relevance_score=0.0, recency_factor=0.0,
            crisis_penalty=0.0, breakdown=empty,
        )

    # ── 1. Source credibility ─────────────────────────────────────────────────
    wss, avg_weight = _compute_weighted_source_score(evidence)

    # ── 2. Stance analysis ────────────────────────────────────────────────────
    stance_result = compute_stance_ratios(claim, evidence)
    support_ratio  = stance_result["support_ratio"]
    refute_ratio   = stance_result["refute_ratio"]
    stance_summary = stance_result["stance_summary"]
    stance_score   = _compute_stance_score(support_ratio, refute_ratio)

    # ── 3. Relevance ──────────────────────────────────────────────────────────
    relevance_100, relevance_01 = _compute_avg_relevance(evidence, claim)

    # ── 4. Recency ────────────────────────────────────────────────────────────
    recency_score, recency_factor = _compute_avg_recency(evidence)

    # ── 5. Weighted additive formula ──────────────────────────────────────────
    w_source   = round(wss          * 0.40, 2)
    w_stance   = round(stance_score * 0.35, 2)
    w_relevance = round(relevance_100 * 0.15, 2)
    w_recency  = round(recency_score * 0.10, 2)

    base_score = round(min(100.0, max(0.0, w_source + w_stance + w_relevance + w_recency)), 2)

    # ── 6. Stance dominance hard override ─────────────────────────────────────
    overridden_score, stance_override = _apply_stance_override(base_score, support_ratio, refute_ratio)

    # ── 7. Crisis modifier (max –10%) ─────────────────────────────────────────
    crisis_modifier = 0.9 if crisis_mode else 1.0
    final_score = round(max(0.0, overridden_score * crisis_modifier), 2)
    crisis_penalty = round(overridden_score - final_score, 2) if crisis_mode else 0.0

    breakdown = ScoreBreakdown(
        weighted_source_component=w_source,
        stance_component=w_stance,
        relevance_component=w_relevance,
        recency_component=w_recency,
        crisis_modifier=crisis_modifier,
        final_score=final_score,
        weighted_source_score=wss,
        stance_score=stance_score,
        relevance_score=relevance_100,
        recency_score=recency_score,
        support_ratio=support_ratio,
        refute_ratio=refute_ratio,
        stance_summary=stance_summary,
    )

    verdict = _determine_verdict(final_score)
    reasoning = _build_reasoning(breakdown, verdict, stance_override)

    return ClaimScore(
        claim_score=final_score,
        verdict=verdict,
        reasoning=reasoning,
        source_weight_avg=avg_weight,
        relevance_score=relevance_01,
        recency_factor=recency_factor,
        crisis_penalty=crisis_penalty,
        breakdown=breakdown,
    )
