"""
Pydantic request schemas for the CrisisVerify API.
"""
from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Request body for the /analyze endpoint."""
    text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The text input to analyze (tweet, article paragraph, etc.)",
    )
    crisis_mode: bool = Field(
        default=False,
        description="Enable crisis mode for heightened verification thresholds",
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Input text must not be empty or whitespace only.")
        return v.strip()
