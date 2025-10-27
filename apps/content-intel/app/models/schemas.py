"""Pydantic request/response schemas for the content intelligence service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class ReferenceArticle(BaseModel):
    """Metadata describing a single reference document retrieved from search."""

    title: str
    url: HttpUrl
    snippet: str = Field(default="")
    domain: Optional[str] = None
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    published_at: Optional[datetime] = None


class ImageAsset(BaseModel):
    """Image suggestion sourced from stock providers or AI generators."""

    provider: Literal["pexels", "pixabay", "ai", "upload"]
    url: HttpUrl
    caption: Optional[str] = None
    attribution: Optional[str] = None
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    thumbnail_url: Optional[HttpUrl] = None


class LinkSuggestion(BaseModel):
    """Internal or external link recommendation accompanied by a confidence score."""

    type: Literal["internal", "external"]
    anchor: str
    url: HttpUrl
    rationale: str
    relevance: float = Field(ge=0.0, le=1.0)


class ArticleMeta(BaseModel):
    """SEO metadata and publishing directives generated alongside the article."""

    title: str
    description: str
    slug: str
    keywords: List[str]
    tags: List[str]
    categories: List[str]
    canonical_url: Optional[HttpUrl] = None
    hero_image: Optional[ImageAsset] = None
    internal_links: List[LinkSuggestion] = Field(default_factory=list)
    external_links: List[LinkSuggestion] = Field(default_factory=list)
    reading_time_minutes: float = Field(default=0.0, ge=0.0)
    geo_profile: Optional[str] = None
    language: str = "id"
    publish_mode: Literal["manual", "auto"] = "manual"
    scheduled_at: Optional[datetime] = None
    social_summary: Optional[str] = None


class ArticleMetrics(BaseModel):
    """Analytic data points used for quality gates and downstream automation."""

    word_count: int = Field(ge=0)
    heading_counts: Dict[str, int]
    keyword_density: Dict[str, float]
    flesch_reading_ease: float
    fk_grade_level: float
    checksum_sha1: str
    checksum_sha256: str
    simhash: str
    duplicate_matches: List[str] = Field(default_factory=list)
    auto_regenerations: int = Field(default=0, ge=0)


class ArticleRequest(BaseModel):
    """Request payload for keyword-driven article generation."""

    keyword: str
    geo: str = "ID"
    tone: Literal["neutral", "formal", "casual", "authoritative", "friendly"] = "neutral"
    target_language: str = "id"
    min_words: int = Field(default=800, ge=500)
    max_words: int = Field(default=1600, ge=600)
    include_images: bool = True
    image_provider_preference: Literal["auto", "pexels", "pixabay", "ai"] = "auto"
    include_social_summary: bool = True
    additional_context: Optional[str] = None
    sitemap_url: Optional[HttpUrl] = None
    site_url: Optional[HttpUrl] = None
    custom_reference_urls: List[HttpUrl] = Field(default_factory=list)
    secondary_keywords: List[str] = Field(default_factory=list)
    llm_provider_priority: List[str] = Field(
        default_factory=lambda: ["openai", "deepseek", "openrouter", "gemini", "llama"]
    )
    auto_internal_linking: bool = True
    auto_external_linking: bool = True
    auto_publish: bool = False
    schedule_at: Optional[datetime] = None

    @validator("max_words")
    def validate_word_bounds(cls, value: int, values: Dict) -> int:
        """Ensure the maximum requested words exceed the minimum."""

        min_words = values.get("min_words", 500)
        if value < min_words:
            raise ValueError("max_words must be greater than or equal to min_words")
        return value


class ArticleResponse(BaseModel):
    """Structured response returned after article generation."""

    article_html: str
    meta: ArticleMeta
    metrics: ArticleMetrics
    sources: List[ReferenceArticle]
    warnings: List[str] = Field(default_factory=list)
    images: List[ImageAsset] = Field(default_factory=list)
    history_id: Optional[str] = None


class RssRequest(BaseModel):
    """Request payload for rewriting and enriching RSS entries."""

    feed_url: HttpUrl
    site: Optional[str] = None
    rewrite: bool = True
    keyword: Optional[str] = None
    tone: Literal["neutral", "formal", "casual", "authoritative", "friendly"] = "neutral"
    target_language: str = "id"
    geo: str = "ID"
    max_items: int = Field(default=1, ge=1, le=5)
    sitemap_url: Optional[HttpUrl] = None
    site_url: Optional[HttpUrl] = None
    llm_provider_priority: List[str] = Field(
        default_factory=lambda: ["openai", "deepseek", "openrouter", "gemini", "llama"]
    )


class RssResponse(BaseModel):
    """Response payload generated from RSS sources."""

    article_html: str
    meta: ArticleMeta
    metrics: ArticleMetrics
    source_item: Dict
    warnings: List[str] = Field(default_factory=list)


class ContentGapRequest(BaseModel):
    """Request for performing competitor gap analysis."""

    keyword: str
    competitors: List[HttpUrl]
    geo: str = "ID"
    language: str = "id"
    site_url: Optional[HttpUrl] = None
    sitemap_url: Optional[HttpUrl] = None


class GapInsight(BaseModel):
    """Data structure describing a single content gap insight."""

    title: str
    summary: str
    difficulty: Literal["low", "medium", "high"]
    opportunity_score: float = Field(ge=0.0, le=1.0)
    action_items: List[str]
    evidence_links: List[HttpUrl] = Field(default_factory=list)


class ContentGapResponse(BaseModel):
    """Response containing actionable insights for content gaps."""

    keyword: str
    insights: List[GapInsight]
    references: List[ReferenceArticle] = Field(default_factory=list)
    trend_topics: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    suggested_headlines: List[str] = Field(default_factory=list)
