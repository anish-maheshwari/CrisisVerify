"""
Evidence Fetcher Service for CrisisVerify.

Primary path: Queries the Serper.dev Google Search API.
Fallback path: Returns structured mock evidence when no API key is configured.
This allows the app to run a credible demo without live search connectivity.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.models.claim_models import Evidence

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/search"


def _classify_source_weight(url: str) -> float:
    """
    Determine credibility weight for a source URL based on domain whitelists
    loaded from config. Unknown domains receive the lowest weight.
    """
    url_lower = url.lower()

    for domain in settings.government_domains:
        if domain in url_lower:
            return settings.source_weight_government

    for domain in settings.academic_domains:
        if domain in url_lower:
            return settings.source_weight_academic

    for domain in settings.established_media_domains:
        if domain in url_lower:
            return settings.source_weight_established_media

    for domain in settings.ngo_domains:
        if domain in url_lower:
            return settings.source_weight_ngo

    return settings.source_weight_unknown


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Normalize date strings from Serper results into ISO format."""
    if not date_str:
        return None
    # Serper returns strings like "3 days ago" or "Jan 5, 2024"
    return date_str


def _build_mock_evidence(claim: str) -> list[Evidence]:
    """
    Returns realistic mock evidence for demo purposes when no search API is configured.
    The mock reflects a "developing situation" scenario to match the demo use-case.
    """
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return [
        Evidence(
            source_name="Reuters",
            url="https://www.reuters.com/world/demo-claim-unverified",
            snippet=f"Reports are emerging of {claim[:80]}... Authorities have not yet confirmed. Situation is developing.",
            published_date=today,
            credibility_weight=settings.source_weight_established_media,
        ),
        Evidence(
            source_name="Associated Press",
            url="https://apnews.com/article/demo-claim-developing",
            snippet=f"Unconfirmed reports regarding {claim[:80]}. Local officials are assessing the situation. No official statement yet.",
            published_date=today,
            credibility_weight=settings.source_weight_established_media,
        ),
        Evidence(
            source_name="ReliefWeb (UN OCHA)",
            url="https://reliefweb.int/report/demo",
            snippet="Humanitarian agencies are monitoring the area. No verified casualty figures have been released by credible sources.",
            published_date=today,
            credibility_weight=settings.source_weight_government,
        ),
    ]


async def _search_serper(claim: str) -> Optional[list[dict]]:
    """Call the Serper.dev search API and return raw organic results."""
    if not settings.serper_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                _SERPER_URL,
                headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
                json={"q": claim, "num": 5, "gl": "us", "hl": "en"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("organic", [])[:5]
    except Exception as exc:
        logger.warning("Serper search failed for claim '%s': %s", claim[:60], exc)
        return None


async def fetch_evidence(claim: str) -> list[Evidence]:
    """
    Public entry point. Fetches evidence for a single claim.

    Args:
        claim: A single factual claim string.

    Returns:
        List of Evidence objects (3–5 items).
    """
    results = await _search_serper(claim)

    if results is None:
        logger.info("Using mock evidence (no Serper API key configured).")
        return _build_mock_evidence(claim)

    evidence_list: list[Evidence] = []
    for item in results:
        url: str = item.get("link", "")
        weight = _classify_source_weight(url)
        evidence_list.append(
            Evidence(
                source_name=item.get("source") or _extract_domain(url),
                url=url,
                snippet=item.get("snippet", "No excerpt available."),
                published_date=_parse_date(item.get("date")),
                credibility_weight=weight,
            )
        )

    if not evidence_list:
        return _build_mock_evidence(claim)

    return evidence_list


def _extract_domain(url: str) -> str:
    """Extract a readable domain name from a URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url
