"""
Claim Extractor Service for CrisisVerify.

Primary path: Uses Gemini LLM to extract structured factual claims from text.
Fallback path: Heuristic sentence-based extraction when API key is not configured.
"""
import json
import logging
import re
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Heuristic patterns for fallback extraction ──────────────────────────────
_PAST_TENSE_RE = re.compile(
    r"\b(was|were|has|have|had|is|are|collapsed|killed|injured|struck|"
    r"destroyed|confirmed|reported|announced|declared|erupted|attacked|hit)\b",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"\b\d[\d,\.]*\s*(people|killed|injured|dead|cases|deaths|km|miles|%)?\\b")
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")


def _heuristic_extract(text: str) -> list[str]:
    """
    Fallback extraction using simple NLP heuristics.
    Splits text into sentences and filters those likely to contain factual claims.
    """
    # Naive sentence split on . ! ?
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        has_past_tense = bool(_PAST_TENSE_RE.search(s))
        has_numeric = bool(_NUMERIC_RE.search(s))
        has_proper_noun = bool(_PROPER_NOUN_RE.search(s))
        if has_past_tense or has_numeric or has_proper_noun:
            claims.append(s)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in claims:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique[:settings.max_claims_to_process] or [text.strip()]


async def _llm_extract(text: str) -> Optional[list[str]]:
    """
    Use Gemini to extract and normalize structured factual claims.
    Returns None if the API is unavailable or the key is not set.
    """
    if not settings.gemini_api_key:
        return None

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "You are a fact-checking assistant for crisis and news verification.\n\n"
            "Your job is to extract and NORMALIZE factual claims from the input text.\n"
            "Rules:\n"
            "1. Rephrase questions into declarative statements "
            "(e.g. 'is X dead?' becomes 'X has died')\n"
            "2. Fix spelling of proper nouns to standard English "
            "(e.g. 'khameni' becomes 'Khamenei', 'modi' becomes 'Narendra Modi')\n"
            "3. Return only concrete, verifiable factual claims - not opinions or speculation\n"
            "4. Return ONLY a valid JSON object with a 'claims' key containing a list of concise claim strings\n"
            f"5. Limit to at most {settings.max_claims_to_process} claims\n\n"
            f"Text:\n\"\"\"\n{text[:1800]}\n\"\"\"\n\n"
            'Respond ONLY with JSON, example: {"claims": ["Claim 1", "Claim 2"]}'
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

        parsed = json.loads(raw)
        claims: list[str] = parsed.get("claims", [])
        if not isinstance(claims, list):
            raise ValueError("'claims' is not a list")

        return [str(c).strip() for c in claims if str(c).strip()][: settings.max_claims_to_process]

    except Exception as exc:
        logger.warning("LLM claim extraction failed, falling back to heuristics: %s", exc)
        return None


async def extract_claims(text: str) -> list[str]:
    """
    Public entry point. Attempts LLM extraction first; falls back to heuristics.

    Args:
        text: Raw input text (already validated for length).

    Returns:
        List of concise factual claim strings (1-5 items).
    """
    if not text or not text.strip():
        raise ValueError("Input text must not be empty.")

    claims = await _llm_extract(text)
    if claims is None:
        logger.info("Using heuristic claim extractor (no LLM API key configured).")
        claims = _heuristic_extract(text)

    if not claims:
        # Last resort: treat entire text as a single claim
        claims = [text.strip()[:300]]

    return claims
