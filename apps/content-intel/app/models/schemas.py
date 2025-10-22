"""Pydantic request/response schemas shared across routes."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ReferenceArticle(BaseModel):
    """Metadata for external reference content."""

    title: str
    url: HttpUrl
    snippet: str = Field(default="")


class ImageAsset(BaseModel):
    """Represents an image suggestion for generated content."""

    provider: str
    url: HttpUrl
    caption: Optional[str] = None
    attribution: Optional[str] = None


class ArticleRequest(BaseModel):
    """Request payload for keyword-driven article generation."""

    keyword: str
    geo: str = "ID"
    tone: str = "neutral"
    min_words: int = Field(default=800, ge=300)
    max_words: int = Field(default=1600, ge=301)
    include_images: bool = True
    additional_context: Optional[str] = None


class ArticleResponse(BaseModel):
    """Structured response for article generation output."""

    article_html: str
    meta: dict
    metrics: dict
    sources: List[ReferenceArticle]
    warnings: List[str] = Field(default_factory=list)
    images: List[ImageAsset] = Field(default_factory=list)


class RssRequest(BaseModel):
    """Request payload for generating content from RSS feeds."""

    feed_url: HttpUrl
    site: Optional[str] = None
    rewrite: bool = True
    keyword: Optional[str] = None


class RssResponse(BaseModel):
    """Response payload generated from RSS sources."""

    article_html: str
    source_item: dict
    warnings: List[str] = Field(default_factory=list)


class ContentGapRequest(BaseModel):
    """Request for performing competitor gap analysis."""

    keyword: str
    competitors: List[HttpUrl]
    geo: str = "ID"
    language: str = "id"


class GapInsight(BaseModel):
    """Data structure describing a single content gap insight."""

    title: str
    summary: str
    difficulty: str
    opportunity_score: float


class ContentGapResponse(BaseModel):
    """Response containing actionable insights for content gaps."""

    keyword: str
    insights: List[GapInsight]
    references: List[ReferenceArticle] = Field(default_factory=list)
