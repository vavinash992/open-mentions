"""Database models using SQLModel (SQLite)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, Index, SQLModel


class Workspace(SQLModel, table=True):
    """
    Anonymous workspace for multi-tenant isolation.

    Users don't log in; they use a workspace_id to isolate all data.
    """

    __tablename__ = "workspaces"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = Field(..., unique=True, index=True, description="Public workspace identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Mention(SQLModel, table=True):
    """
    Global mention record (deduplicated by URL).

    The same URL can be tracked by multiple workspaces. We store the LLM classification
    once globally here, then link it to each workspace via WorkspaceMention.
    """

    __tablename__ = "mentions"

    url: str = Field(primary_key=True, description="The URL of the scraped item (global unique identifier)")
    platform: str = Field(..., description="The platform from which the item was scraped.")
    content: str = Field(..., description="The main content of the scraped item.")
    upvotes: int | None = Field(None, description="Number of upvotes or likes the item received.")
    mention_type: str | None = Field(None, description="Type of mention (e.g., post, comment).")
    user_id: str | None = Field(None, description="Unique identifier for the user who created the item.")
    user_profile_url: str | None = Field(None, description="URL to the user's profile on the platform.")
    timestamp: str | None = Field(None, description="Timestamp when the item was created or posted.")
    comments: int | None = Field(None, description="Number of comments associated with the item.")

    # LLM Classification fields (global)
    relevance_score: float | None = Field(None, ge=0.0, le=1.0)
    is_relevant: bool | None = Field(None)
    sentiment: str | None = Field(None, index=True)
    emotion: str | None = Field(None)
    summary: str | None = Field(None, max_length=150)
    themes: str | None = Field(None, description="Comma-separated list of themes")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    @classmethod
    def from_scraped_item(cls, item: ScrapedItem) -> Mention:  # noqa: F821
        themes = [theme.strip() for theme in (item.themes or []) if theme and theme.strip()]
        return cls(
            url=item.url,
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
            themes=", ".join(themes) if themes else None,
        )

    def to_scraped_item(self, *, keyword: str) -> ScrapedItem:  # noqa: F821
        """
        Convert a global Mention into a ScrapedItem for API responses.

        The ScrapedItem requires a keyword; in a multi-tenant model that keyword is stored
        on the WorkspaceMention association.
        """
        from mentions.scrapers.base import ScrapedItem

        return ScrapedItem(
            keyword=keyword,
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
            themes=[theme.strip() for theme in (self.themes or "").split(",") if theme.strip()],
        )


class WorkspaceMention(SQLModel, table=True):
    """
    Association table linking a global Mention to a Workspace.

    Stores the keyword used in that workspace when the mention was discovered.
    """

    __tablename__ = "workspace_mentions"
    __table_args__ = (
        Index("ix_workspace_mentions_workspace_id", "workspace_id"),
        Index("ix_workspace_mentions_workspace_keyword", "workspace_id", "keyword"),
        Index("ix_workspace_mentions_created_at", "created_at"),
    )

    workspace_id: str = Field(
        foreign_key="workspaces.workspace_id",
        primary_key=True,
        description="Workspace that is tracking this mention",
    )
    mention_url: str = Field(
        foreign_key="mentions.url",
        primary_key=True,
        description="Global mention URL",
    )
    keyword: str = Field(
        ...,
        primary_key=True,
        description="Keyword that discovered this mention in this workspace",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrackedKeyword(SQLModel, table=True):
    """
    Keywords that a workspace wants to track.
    """

    __tablename__ = "tracked_keywords"
    __table_args__ = (
        Index("ix_tracked_keywords_workspace_active", "workspace_id", "is_active"),
        Index("uq_tracked_keywords_workspace_keyword", "workspace_id", "keyword", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        description="Workspace that owns this keyword",
    )
    keyword: str = Field(..., description="The keyword/company name to track")
    category: str = Field(default="brand", description="Keyword category: brand or competitor")
    importance_score: int = Field(default=1, description="Priority weight for this keyword")
    is_active: bool = Field(default=True)
    last_searched_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceRateLimit(SQLModel, table=True):
    """
    Rate limit state per workspace for manual triggers.
    """

    __tablename__ = "workspace_rate_limits"

    workspace_id: str = Field(foreign_key="workspaces.workspace_id", primary_key=True)
    last_trigger_at: datetime | None = Field(default=None)


class WorkspaceTriggerJob(SQLModel, table=True):
    """
    Background monitoring job status per workspace.
    """

    __tablename__ = "workspace_trigger_jobs"
    __table_args__ = (
        Index("ix_workspace_trigger_jobs_workspace_id", "workspace_id"),
        Index("ix_workspace_trigger_jobs_created_at", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(..., unique=True, index=True, description="Public job identifier")
    workspace_id: str = Field(foreign_key="workspaces.workspace_id", index=True)
    status: str = Field(default="pending", description="pending, running, completed, failed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    keywords_processed: int | None = Field(default=None)
    total_new_mentions: int | None = Field(default=None)
    keyword_results: str | None = Field(default=None, description="JSON summary of keyword results")
    error: str | None = Field(default=None, description="Error message if failed")
