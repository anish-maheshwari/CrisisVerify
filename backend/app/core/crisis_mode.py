"""
Crisis Mode module for CrisisVerify.
Isolated from scoring_engine.py — provides adjustments for high-stakes scenarios.

Crisis mode logic:
- Raises the minimum confidence threshold before issuing "Verified" verdict
- Applies a penalty multiplier to claims containing emotionally loaded language
- Flags such claims so the UI can highlight them
"""
import re
from app.core.config import settings

# Words and patterns commonly associated with emotionally loaded crisis claims
_EMOTIONAL_KEYWORDS = re.compile(
    r"\b("
    r"catastrophic|devastating|apocalyptic|mass.{0,10}death|genocide|"
    r"wiped.{0,5}out|total.{0,5}destruction|annihilated|obliterated|"
    r"hundreds.{0,10}dead|thousands.{0,10}dead|millions.{0,10}affected|"
    r"immediate.{0,5}threat|imminent|terror|bioweapon|nuclear|chemical.{0,5}attack"
    r")\b",
    re.IGNORECASE,
)


def apply_crisis_adjustments(
    raw_score: float,
    claim: str,
    crisis_mode: bool,
) -> tuple[float, float, bool]:
    """
    Apply crisis mode adjustments to a raw credibility score.

    Args:
        raw_score: The base score computed by scoring_engine (0-100).
        claim: The claim text, used for emotional language detection.
        crisis_mode: Whether crisis mode is active.

    Returns:
        Tuple of (adjusted_score, penalty_applied, is_emotionally_loaded).
    """
    if not crisis_mode:
        return raw_score, 0.0, False

    is_emotionally_loaded = bool(_EMOTIONAL_KEYWORDS.search(claim))
    penalty = 0.0

    if is_emotionally_loaded:
        # Apply penalty as percentage reduction
        penalty = settings.crisis_mode_emotional_penalty
        adjusted_score = raw_score * (1.0 - penalty)
    else:
        adjusted_score = raw_score

    # In crisis mode, the effective score must clear a higher bar.
    # We represent this by reducing the score by the threshold boost,
    # keeping verdicts conservative.
    adjusted_score = max(0.0, adjusted_score - settings.crisis_mode_threshold_boost)

    return round(adjusted_score, 2), round(penalty * 100, 2), is_emotionally_loaded
