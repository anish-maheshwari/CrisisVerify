"""
Configuration module for CrisisVerify.
All environment variables and configurable weights are loaded here.
Never hardcode API keys or credibility weights elsewhere.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Explicitly inject .env values into os.environ using python-dotenv.
# We use dotenv_values (not load_dotenv) and manually inject to avoid
# the override=False semantics that skip already-set (even empty) vars.
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import dotenv_values as _dotenv_values
    for _k, _v in _dotenv_values(_env_path).items():
        if _k not in os.environ or not os.environ[_k]:
            os.environ[_k] = _v or ""


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Copy .env.example to .env and fill in your values.
    python-dotenv loads .env into os.environ before this class is instantiated.
    """
    model_config = SettingsConfigDict(extra="ignore")

    # --- LLM ---
    gemini_api_key: str = Field(default="")

    # --- Search / Evidence ---
    serper_api_key: str = Field(default="")

    # --- Rate Limiting ---
    rate_limit_per_minute: int = Field(default=10)

    # --- Input Guards ---
    max_input_length: int = Field(default=2000)
    max_claims_to_process: int = Field(default=5)

    # -------------------------------------------------------
    # Source Credibility Weights (0.0 – 1.0)
    # These are loaded from config so judges/operators can
    # adjust them without touching business logic.
    # -------------------------------------------------------
    source_weight_government: float = Field(default=0.90)
    source_weight_established_media: float = Field(default=0.80)
    source_weight_academic: float = Field(default=0.85)
    source_weight_ngo: float = Field(default=0.75)
    source_weight_unknown: float = Field(default=0.30)

    # Whitelist of high-credibility domain fragments
    government_domains: list[str] = Field(
        default=["gov", "mil", "un.org", "who.int", "cdc.gov", "fema.gov",
                 "wikipedia.org", "reliefweb.int", "icrc.org"]
    )
    academic_domains: list[str] = Field(
        default=["edu", "ac.uk", "researchgate.net", "scholar.google", "pubmed"]
    )
    established_media_domains: list[str] = Field(
        default=[
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "nytimes.com", "theguardian.com", "aljazeera.com",
            "washingtonpost.com", "npr.org", "cnbc.com", "bloomberg.com",
            "nbcnews.com", "cbsnews.com", "abcnews.go.com", "cnn.com",
            "foxnews.com", "skynews.com", "sky.com", "time.com",
            "newsweek.com", "theatlantic.com", "politico.com",
            "usatoday.com", "latimes.com", "wsj.com", "ft.com",
            "ndtv.com", "hindustantimes.com", "thehindu.com",
            "bbc.in", "pbs.org", "msnbc.com", "independant.co.uk",
            "independent.co.uk", "thetimes.co.uk", "telegraph.co.uk",
            "dw.com", "france24.com", "euronews.com", "rt.com",
            "abc.net.au", "smh.com.au", "cbc.ca", "globalnews.ca",
        ]
    )
    ngo_domains: list[str] = Field(
        default=["msf.org", "amnesty.org", "hrw.org", "oxfam.org",
                 "savethechildren.org", "unicef.org", "unhcr.org"]
    )

    # --- Crisis Mode ---
    crisis_mode_threshold_boost: float = Field(default=15.0)
    crisis_mode_emotional_penalty: float = Field(default=0.15)


# Module-level singleton — import this in other modules
settings = Settings()
