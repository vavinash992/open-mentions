"""Search Router for Open Mentions API."""

from collections import Counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from mentions.scrapers.base import ScrapedItem
from mentions.services.orchestrator import search_all_platforms

search_router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    company_name: str = Field(..., description="The company name to search for", min_length=1)
    filter_by: str = Field(
        default="week",
        description="Time filter: 'day', 'week', 'month', or 'year'",
    )
    max_results_per_platform: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum results to fetch per platform",
    )

    @field_validator("filter_by")
    @classmethod
    def validate_filter_by(cls, v: str) -> str:
        """Validate that filter_by is one of the allowed values."""
        allowed_values = {"day", "week", "month", "year"}
        if v not in allowed_values:
            msg = f"filter_by must be one of {allowed_values}, got {v}"
            raise ValueError(msg)
        return v


class SearchResponse(BaseModel):
    """Response model for search endpoint."""

    total_mentions: int = Field(..., description="Total number of relevant mentions found")
    sentiment_breakdown: dict[str, int] = Field(
        ...,
        description="Count of mentions by sentiment (positive, negative, neutral)",
    )
    platform_breakdown: dict[str, int] = Field(
        ...,
        description="Count of mentions by platform",
    )
    average_confidence: float = Field(
        ...,
        description="Average confidence score across all mentions",
    )
    mentions: list[ScrapedItem] = Field(..., description="List of classified relevant mentions")


@search_router.post("/search", response_model=SearchResponse)
async def search_mentions(request: SearchRequest) -> SearchResponse:
    """
    Search for company mentions across all platforms and classify them.

    This endpoint:
    1. Searches all available platforms (Reddit, Hacker News, Dev.to, Stack Exchange, etc.) concurrently
    2. Uses LLM to classify each mention for relevance and sentiment
    3. Returns only relevant mentions with analytics

    Args:
        request: Search request with company_name, filter_by, and max_results_per_platform

    Returns:
        SearchResponse with classified mentions and analytics

    Raises:
        HTTPException: If search fails or returns an error
    """
    try:
        # Run search across all platforms
        mentions = await search_all_platforms(
            company_name=request.company_name,
            filter_by=request.filter_by,
            max_results_per_platform=request.max_results_per_platform,
        )

        # Calculate analytics
        total_mentions = len(mentions)

        # Sentiment breakdown
        sentiment_counter = Counter(item.sentiment or "neutral" for item in mentions)
        sentiment_breakdown = {
            "positive": sentiment_counter.get("positive", 0),
            "negative": sentiment_counter.get("negative", 0),
            "neutral": sentiment_counter.get("neutral", 0),
        }

        # Platform breakdown
        platform_counter = Counter(item.platform for item in mentions)
        platform_breakdown = dict(platform_counter)

        # Average confidence
        confidence_scores = [item.confidence_score for item in mentions if item.confidence_score is not None]
        average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return SearchResponse(
            total_mentions=total_mentions,
            sentiment_breakdown=sentiment_breakdown,
            platform_breakdown=platform_breakdown,
            average_confidence=round(average_confidence, 3),
            mentions=mentions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e
