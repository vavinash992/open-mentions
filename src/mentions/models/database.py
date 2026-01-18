"""Database models using SQLModel."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Mention(SQLModel, table=True):
    """
    Database model for storing scraped mentions.

    Mirrors ScrapedItem but with database-specific fields.
    Uses url as primary key to prevent duplicates.
    """

    __tablename__ = "mentions"

    url: str = Field(primary_key=True, description="The URL of the scraped item (unique identifier)")
    keyword: str = Field(..., description="The keyword that was searched for.")
    platform: str = Field(..., description="The platform from which the item was scraped.")
    content: str = Field(..., description="The main content of the scraped item.")
    upvotes: Optional[int] = Field(None, description="Number of upvotes or likes the item received.")
    mention_type: Optional[str] = Field(None, description="Type of mention (e.g., post, comment).")
    user_id: Optional[str] = Field(None, description="Unique identifier for the user who created the item.")
    user_profile_url: Optional[str] = Field(None, description="URL to the user's profile on the platform.")
    timestamp: Optional[str] = Field(None, description="Timestamp when the item was created or posted.")
    comments: Optional[int] = Field(None, description="Number of comments associated with the item.")
    # LLM Classification fields
    relevance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score indicating how relevant the mention is to the target company (0.0 to 1.0).",
    )
    is_relevant: Optional[bool] = Field(
        None,
        description="Whether this mention is actually about the target company (LLM classified).",
    )
    sentiment: Optional[str] = Field(
        None,
        description="Sentiment classification of the content (positive, negative, neutral).",
    )
    emotion: Optional[str] = Field(
        None,
        description="Primary emotion detected in the text (e.g., 'frustration', 'joy', 'curiosity', 'disappointment', 'anger', 'neutral', 'excitement', 'concern', 'satisfaction', 'confusion').",
    )
    summary: Optional[str] = Field(
        None,
        max_length=150,
        description="Concise one-sentence summary of what the mention is about (max 150 characters).",
    )
    # Database metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the mention was stored in the database",
    )

    @classmethod
    def from_scraped_item(cls, item: "ScrapedItem") -> "Mention":  # noqa: F821
        """
        Create a Mention database model from a ScrapedItem.

        Args:
            item: ScrapedItem object to convert.

        Returns:
            Mention database model instance.
        """
        return cls(
            url=item.url,
            keyword=item.keyword,
            platform=item.platform,
            content=item.content,
            upvotes=item.upvotes,
            mention_type=item.mention_type,
            user_id=item.user_id,
            user_profile_url=item.user_profile_url,
            timestamp=item.timestamp,
            comments=item.comments,
            relevance_score=item.relevance_score,
            is_relevant=item.is_relevant,
            sentiment=item.sentiment,
            emotion=item.emotion,
            summary=item.summary,
        )

    def to_scraped_item(self) -> "ScrapedItem":  # noqa: F821
        """
        Convert Mention database model back to ScrapedItem.

        Returns:
            ScrapedItem object.
        """
        from mentions.scrapers.base import ScrapedItem

        return ScrapedItem(
            keyword=self.keyword,
            platform=self.platform,
            content=self.content,
            url=self.url,
            upvotes=self.upvotes,
            mention_type=self.mention_type,
            user_id=self.user_id,
            user_profile_url=self.user_profile_url,
            timestamp=self.timestamp,
            comments=self.comments,
            relevance_score=self.relevance_score,
            is_relevant=self.is_relevant,
            sentiment=self.sentiment,
            emotion=self.emotion,
            summary=self.summary,
        )


class TrackedKeyword(SQLModel, table=True):
    """
    Database model for tracking keywords that should be monitored automatically.

    Used by the periodic monitoring script to know which keywords to search for.
    """

    __tablename__ = "tracked_keywords"

    id: Optional[int] = Field(default=None, primary_key=True, description="Unique identifier for the tracked keyword")
    keyword: str = Field(..., unique=True, description="The keyword/company name to track")
    is_active: bool = Field(
        default=True,
        description="Whether this keyword is currently being actively monitored",
    )
    last_searched_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last time this keyword was searched",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the keyword was first added for tracking",
    )
