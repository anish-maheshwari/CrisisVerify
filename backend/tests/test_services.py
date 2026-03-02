"""
Pytest tests for CrisisVerify backend services.
Validates deterministic logic without requiring network or API keys.
"""
import pytest
from datetime import datetime, timezone
from app.models.claim_models import Evidence, Verdict
from app.services.scoring_engine import (
    _compute_recency_factor,
    _compute_relevance_score,
    _determine_verdict,
    score_claim,
)
from app.services.stance_classifier import classify_stance, compute_stance_ratios
from app.services.report_generator import generate_report, _majority_verdict
from app.models.claim_models import ClaimResult


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_evidence(
    source_name="Reuters",
    url="https://www.reuters.com/article",
    snippet="Government officials confirmed the collapse of the dam after the earthquake.",
    published_date="2024-01-01",
    credibility_weight=0.80,
) -> Evidence:
    return Evidence(
        source_name=source_name, url=url, snippet=snippet,
        published_date=published_date, credibility_weight=credibility_weight,
    )


def make_recent_evidence(credibility_weight=0.80, snippet=None) -> Evidence:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return make_evidence(
        snippet=snippet or "Officials confirmed the collapse. Hundreds were killed.",
        published_date=today,
        credibility_weight=credibility_weight,
    )


# ── Stance Classifier ─────────────────────────────────────────────────────────
def test_stance_supports_confirmed_death():
    """'confirmed dead' in snippet → SUPPORTS."""
    result = classify_stance("official died", "Official has been confirmed dead by state media.", 0.80)
    assert result["stance"] == "supports"


def test_stance_refutes_alive():
    """'is alive' in snippet → REFUTES."""
    result = classify_stance("Modi died", "Modi is alive and well, addressed the nation today.", 0.80)
    assert result["stance"] == "refutes"


def test_stance_refutes_hoax():
    """'hoax' in snippet → REFUTES."""
    result = classify_stance("celebrity died", "This is a hoax. The celebrity is alive.", 0.80)
    assert result["stance"] == "refutes"


def test_stance_neutral_unrelated():
    """Unrelated snippet → NEUTRAL."""
    result = classify_stance("dam collapsed", "Local weather forecast predicts sunny skies.", 0.30)
    assert result["stance"] == "neutral"


def test_stance_refute_priority_over_support():
    """When both patterns match, refute wins (e.g. 'confirmed: false claim')."""
    result = classify_stance("died", "Confirmed: this death claim is false and misleading.", 0.80)
    assert result["stance"] == "refutes"


# ── New Stance-Aware Scoring Tests ────────────────────────────────────────────
def test_strong_refutation_collapses_score():
    """
    When credible sources predominantly REFUTE the claim,
    the final score must be < 25 (Likely False), regardless of additive score.
    """
    claim = "Narendra Modi has died"
    refuting_snippets = [
        "Modi is alive and well. This is a false claim circulating online.",
        "Fact-check: Modi death rumours are a hoax. He is alive.",
        "Modi chaired a government meeting today. Death reports are misleading.",
    ]
    evidence = [
        make_recent_evidence(credibility_weight=0.90, snippet=refuting_snippets[0]),
        make_recent_evidence(credibility_weight=0.80, snippet=refuting_snippets[1]),
        make_recent_evidence(credibility_weight=0.80, snippet=refuting_snippets[2]),
    ]
    result = score_claim(claim, evidence, crisis_mode=False)
    assert result.claim_score < 25.0, f"Expected < 25, got {result.claim_score}"
    assert result.verdict == Verdict.LIKELY_FALSE
    assert result.breakdown.refute_ratio >= 0.60


def test_strong_support_pushes_verified():
    """
    When credible sources predominantly SUPPORT/CONFIRM the claim,
    the final score must be ≥ 75 (Verified).
    """
    claim = "Khamenei has died"
    supporting_snippets = [
        "Khamenei was killed in a confirmed airstrike. Government confirmed the death.",
        "Iranian state media confirmed Khamenei's death. Officially declared.",
        "Khamenei has died aged 86. Death confirmed by official sources.",
    ]
    evidence = [
        make_recent_evidence(credibility_weight=0.90, snippet=supporting_snippets[0]),
        make_recent_evidence(credibility_weight=0.80, snippet=supporting_snippets[1]),
        make_recent_evidence(credibility_weight=0.80, snippet=supporting_snippets[2]),
    ]
    result = score_claim(claim, evidence, crisis_mode=False)
    assert result.claim_score >= 75.0, f"Expected >= 75, got {result.claim_score}"
    assert result.verdict == Verdict.VERIFIED
    assert result.breakdown.support_ratio >= 0.60


def test_mixed_stance_is_developing():
    """
    When support and refute are roughly balanced,
    the score must be between 40–74 (Developing).
    """
    claim = "explosion at central station"
    evidence = [
        make_recent_evidence(credibility_weight=0.80,
            snippet="Officials confirmed an explosion at the station. Dozens killed."),
        make_recent_evidence(credibility_weight=0.80,
            snippet="Reports of explosion are misleading. No credible confirmation."),
        make_recent_evidence(credibility_weight=0.30,
            snippet="Unverified: explosion rumours circulating on social media."),
    ]
    result = score_claim(claim, evidence, crisis_mode=False)
    assert 40.0 <= result.claim_score <= 74.0, f"Expected 40-74, got {result.claim_score}"
    assert result.verdict == Verdict.DEVELOPING


# ── Additive Model Tests ───────────────────────────────────────────────────────
def test_strong_consensus_scores_above_80():
    """3+ high-credibility supporting sources → score > 80 (Verified)."""
    claim = "dam collapsed after earthquake killing hundreds"
    snippet = "The dam collapsed after a major earthquake. Hundreds were killed. Officials confirmed."
    evidence = [
        make_recent_evidence(credibility_weight=0.90, snippet=snippet),
        make_recent_evidence(credibility_weight=0.90, snippet=snippet),
        make_recent_evidence(credibility_weight=0.80, snippet=snippet),
    ]
    result = score_claim(claim, evidence, crisis_mode=False)
    assert result.claim_score > 80.0, f"Expected > 80, got {result.claim_score}"
    assert result.verdict == Verdict.VERIFIED


def test_no_credible_evidence_scores_below_40():
    """Only low-credibility, neutral stance sources → score < 40 (Likely False)."""
    claim = "celebrity died in hospital"
    evidence = [
        make_evidence(credibility_weight=0.30, snippet="Rumour circulating online about a celebrity.", published_date="2020-01-01"),
        make_evidence(credibility_weight=0.30, snippet="Unverified social media post mentions celebrity hospitalized.", published_date="2020-01-01"),
    ]
    result = score_claim(claim, evidence, crisis_mode=False)
    assert result.claim_score < 40.0, f"Expected < 40, got {result.claim_score}"


def test_crisis_mode_reduces_max_10_percent():
    """Crisis mode reduces score by ≤ 10%."""
    claim = "dam collapsed after earthquake killing hundreds"
    snippet = "The dam collapsed. Hundreds were killed. Officials confirmed."
    evidence = [make_recent_evidence(credibility_weight=0.90, snippet=snippet)]
    normal = score_claim(claim, evidence, crisis_mode=False)
    crisis = score_claim(claim, evidence, crisis_mode=True)
    assert crisis.claim_score <= normal.claim_score
    if normal.claim_score > 0:
        reduction_pct = (normal.claim_score - crisis.claim_score) / normal.claim_score * 100
        assert reduction_pct <= 10.01, f"Exceeded 10%: {reduction_pct:.1f}%"


def test_score_breakdown_has_stance_fields():
    """ScoreBreakdown must include support_ratio, refute_ratio, and stance_summary."""
    result = score_claim("dam collapsed", [make_evidence()], crisis_mode=False)
    bd = result.breakdown
    assert hasattr(bd, "support_ratio")
    assert hasattr(bd, "refute_ratio")
    assert hasattr(bd, "stance_summary")
    assert 0.0 <= bd.support_ratio <= 1.0
    assert 0.0 <= bd.refute_ratio <= 1.0
    assert isinstance(bd.stance_summary, str) and len(bd.stance_summary) > 0


# ── Existing Tests ────────────────────────────────────────────────────────────
def test_heuristic_extraction_returns_sentences():
    from app.services.claim_extractor import _heuristic_extract
    text = "The dam collapsed after a 7.4 magnitude earthquake struck Region X. Thousands evacuated."
    claims = _heuristic_extract(text)
    assert len(claims) >= 1
    assert all(isinstance(c, str) for c in claims)


def test_heuristic_extraction_deduplicates():
    from app.services.claim_extractor import _heuristic_extract
    text = "The dam collapsed. The dam collapsed. Officials confirmed 200 deaths."
    claims = _heuristic_extract(text)
    assert len(claims) == len(set(claims))


def test_recency_factor_recent_date_is_1():
    from datetime import timedelta
    recent = (datetime.now(tz=timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%d")
    assert _compute_recency_factor(recent) == 1.0


def test_recency_factor_old_date_is_low():
    assert _compute_recency_factor("2020-01-01") == 0.40


def test_recency_factor_relative_string():
    assert _compute_recency_factor("3 days ago") == 0.90


def test_recency_factor_unknown_returns_default():
    assert _compute_recency_factor(None) == 0.60


def test_relevance_score_high_overlap():
    score = _compute_relevance_score(
        "dam collapsed earthquake region",
        "The dam collapsed after a major earthquake struck the region, officials confirmed.",
    )
    assert score > 0.5


def test_relevance_score_no_overlap():
    score = _compute_relevance_score("satellite launched agency", "Sunny skies this weekend.")
    assert score <= 0.20


def test_scoring_formula_deterministic():
    evidence = [make_evidence(snippet="dam collapsed earthquake", published_date="2024-01-01", credibility_weight=0.80)]
    s1 = score_claim("dam collapsed", evidence, crisis_mode=False)
    s2 = score_claim("dam collapsed", evidence, crisis_mode=False)
    assert s1.claim_score == s2.claim_score


def test_scoring_no_evidence_returns_low_score():
    result = score_claim("dam collapsed", evidence=[], crisis_mode=False)
    assert result.claim_score < 20.0
    assert result.verdict == Verdict.LIKELY_FALSE


def test_crisis_mode_lowers_score():
    evidence = [make_evidence(credibility_weight=0.80)]
    normal = score_claim("dam collapsed", evidence, crisis_mode=False)
    crisis = score_claim("dam collapsed", evidence, crisis_mode=True)
    assert crisis.claim_score <= normal.claim_score


def test_verdict_thresholds():
    assert _determine_verdict(80.0) == Verdict.VERIFIED
    assert _determine_verdict(55.0) == Verdict.DEVELOPING
    assert _determine_verdict(30.0) == Verdict.LIKELY_FALSE
    assert _determine_verdict(75.0) == Verdict.VERIFIED
    assert _determine_verdict(74.9) == Verdict.DEVELOPING


def test_report_aggregation_averages_scores():
    evidences = [make_evidence()]
    r1 = ClaimResult(claim="A", evidence=evidences, score=score_claim("Claim A", evidences, False))
    r2 = ClaimResult(claim="B", evidence=evidences, score=score_claim("dam collapse earthquake region official", evidences, False))
    report = generate_report("Test text", [r1, r2], crisis_mode=False)
    expected = round((r1.score.claim_score + r2.score.claim_score) / 2, 2)
    assert report.overall_confidence == expected


def test_report_majority_verdict_conservative():
    dev = ClaimResult(
        claim="Unverified",
        evidence=[make_evidence(credibility_weight=0.30, snippet="foo bar")],
        score=score_claim("unrelated satellite topic", [make_evidence(credibility_weight=0.30, snippet="foo bar")], False),
    )
    ver = ClaimResult(
        claim="Confirmed",
        evidence=[make_evidence()],
        score=score_claim("dam collapsed earthquake region official confirmed", [make_evidence()], False),
    )
    report = generate_report("Test", [dev, ver], crisis_mode=False)
    assert report.overall_verdict in [Verdict.VERIFIED, Verdict.DEVELOPING, Verdict.LIKELY_FALSE]


def test_report_empty_claims():
    report = generate_report("text", [], crisis_mode=False)
    assert report.overall_confidence == 0.0
    assert report.overall_verdict == Verdict.LIKELY_FALSE
