"""
Stance Classifier for CrisisVerify.

Deterministic, rule-based classification of whether an evidence snippet
SUPPORTS, REFUTES, or is NEUTRAL toward a factual claim.

No ML models, no external APIs. Fully explainable keyword logic.
"""
import re
from typing import Literal

StanceLabel = Literal["supports", "refutes", "neutral"]


# ── Keyword Patterns ─────────────────────────────────────────────────────────
# Patterns that indicate the snippet SUPPORTS the claim (confirms it is true).
_SUPPORT_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"\bconfirmed\b",
    r"\bhas died\b",
    r"\bhave died\b",
    r"\bwas killed\b",
    r"\bwere killed\b",
    r"\bkilled in\b",
    r"\bdied (in|from|after|during|following)\b",
    r"\bdeclared dead\b",
    r"\bofficial(ly)?\b.{0,30}\bdead\b",
    r"\bdeath\b.{0,30}\bconfirmed\b",
    r"\bconfirmed\b.{0,30}\bdeath\b",
    r"\bstate media confirmed\b",
    r"\bgovernment confirmed\b",
    r"\bofficially announced\b",
    r"\bpronounced dead\b",
    r"\bconfirmed( the)? (killing|death|strike)\b",
    r"\bdied aged\b",
    r"\bdied at (age|the age)\b",
]]

# Patterns that indicate the snippet REFUTES the claim (says it is false).
_REFUTE_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"\bhoax\b",
    r"\bdebunked\b",
    r"\bfact.?check\b",
    r"\bmisleading\b",
    r"\bfalse( claim| report| news| information| story)?\b",
    r"\bnot true\b",
    r"\buntrue\b",
    r"\bdenied\b",
    r"\bno evidence\b",
    r"\bno credible\b",
    r"\bsatire\b",
    r"\bfake news\b",
    r"\bright-wing\b.{0,30}\bmisinformation\b",
    r"\bmisinformation\b",
    r"\bstill alive\b",
    r"\bis alive\b",
    r"\bremains alive\b",
    r"\bwas seen alive\b",
    r"\bcurrently alive\b",
    r"\b(not|has not|have not|did not) (died?|been killed|passed away)\b",
    r"\balive and (well|healthy|active|present|meeting)\b",
    r"\bunverified (claim|report|rumou?r)\b",
    r"\brunning\b.{0,30}\bgovernment\b",          # "running the government" = alive
    r"\bchaired\b.{0,30}\bmeeting\b",             # "chaired a meeting today" = alive
    r"\baddressed\b.{0,30}\bnation\b",            # "addressed the nation" = alive
    r"\battended\b.{0,30}\b(summit|event|meeting)\b",  # "attended summit" = alive
    r"\bspoke\b.{0,30}\babout\b",
    r"\bcontinues\b.{0,30}\b(to serve|as prime|as president|as leader)\b",
]]


def classify_stance(claim: str, snippet: str, credibility_weight: float) -> dict:
    """
    Classify the stance of a snippet toward a claim.

    Args:
        claim: The factual claim being verified.
        snippet: The evidence snippet text.
        credibility_weight: Source credibility (0-1).

    Returns:
        dict with keys:
          stance: "supports" | "refutes" | "neutral"
          confidence: float (0.0-1.0)
          support_hits: int  — number of support patterns matched
          refute_hits: int   — number of refute patterns matched
    """
    text = (snippet or "").strip()
    if not text:
        return {"stance": "neutral", "confidence": 0.5, "support_hits": 0, "refute_hits": 0}

    support_hits = sum(1 for p in _SUPPORT_PATTERNS if p.search(text))
    refute_hits  = sum(1 for p in _REFUTE_PATTERNS  if p.search(text))

    # Refutation takes precedence when both patterns match
    # (e.g. "Confirmed: death claim is false" → refutes)
    if refute_hits > 0 and refute_hits >= support_hits:
        confidence = min(0.95, 0.5 + refute_hits * 0.15)
        return {
            "stance": "refutes",
            "confidence": round(confidence, 3),
            "support_hits": support_hits,
            "refute_hits": refute_hits,
        }

    if support_hits > 0:
        confidence = min(0.95, 0.5 + support_hits * 0.15)
        return {
            "stance": "supports",
            "confidence": round(confidence, 3),
            "support_hits": support_hits,
            "refute_hits": refute_hits,
        }

    return {"stance": "neutral", "confidence": 0.5, "support_hits": 0, "refute_hits": 0}


def compute_stance_ratios(
    claim: str,
    evidence: list,           # list[Evidence] — typed loosely to avoid circular import
) -> dict:
    """
    Compute support/refute ratios across all credible evidence sources.

    Only sources with credibility_weight >= 0.75 contribute to ratios
    (low-credibility sources are too unreliable to determine truth direction).

    Returns:
        {
          support_ratio: float,     # 0-1, fraction of credible weight that supports
          refute_ratio: float,      # 0-1, fraction of credible weight that refutes
          stances: list[dict],      # per-source stance results
          stance_summary: str,      # human-readable summary
        }
    """
    stances = []
    support_weight = 0.0
    refute_weight  = 0.0
    neutral_weight = 0.0
    credible_weight = 0.0

    support_count = 0
    refute_count  = 0

    for ev in evidence:
        result = classify_stance(claim, ev.snippet, ev.credibility_weight)
        result["source_name"] = ev.source_name
        result["weight"] = ev.credibility_weight
        stances.append(result)

        if ev.credibility_weight >= 0.75:
            credible_weight += ev.credibility_weight
            if result["stance"] == "supports":
                support_weight += ev.credibility_weight
                support_count  += 1
            elif result["stance"] == "refutes":
                refute_weight  += ev.credibility_weight
                refute_count   += 1
            else:
                neutral_weight += ev.credibility_weight

    if credible_weight == 0:
        # No credible sources — fall back to all sources
        for ev, st in zip(evidence, stances):
            if st["stance"] == "supports":
                support_weight += ev.credibility_weight
                support_count  += 1
            elif st["stance"] == "refutes":
                refute_weight  += ev.credibility_weight
                refute_count   += 1
        credible_weight = max(sum(ev.credibility_weight for ev in evidence), 1e-9)

    support_ratio = support_weight / credible_weight
    refute_ratio  = refute_weight  / credible_weight

    # Build human-readable summary
    if refute_count > 0 and support_count == 0:
        summary = f"{refute_count} credible source{'s' if refute_count > 1 else ''} refute this claim."
    elif support_count > 0 and refute_count == 0:
        summary = f"{support_count} credible source{'s' if support_count > 1 else ''} confirm this claim."
    elif refute_count > 0 and support_count > 0:
        summary = f"Mixed signals: {support_count} support, {refute_count} refute. Treat with caution."
    else:
        summary = "No clear confirmation or refutation found in retrieved sources."

    return {
        "support_ratio": round(support_ratio, 3),
        "refute_ratio":  round(refute_ratio, 3),
        "stances":       stances,
        "stance_summary": summary,
    }
