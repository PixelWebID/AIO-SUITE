"""Pydantic schemas shared across the Content Intelligence service."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class ReferenceArticle(BaseModel):
    """Metadata describing a single SERP or curated reference document."""

    title: str
    url: HttpUrl
    snippet: str = ""
    outline: List[str] = Field(default_factory=list)
    domain: Optional[str] = None
    published_at: Optional[datetime] = None
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ImageAsset(BaseModel):
    """Image recommendation sourced from stock providers or AI generators."""

    provider: Literal["pexels", "pixabay", "ai", "fallback"]
    url: HttpUrl
    caption: Optional[str] = None
    attribution: Optional[str] = None
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    thumbnail_url: Optional[HttpUrl] = None


class ArticleMeta(BaseModel):
    """SEO metadata produced alongside an article."""

    title: str
    description: str
    slug: str
    keywords: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    canonical_url: Optional[HttpUrl] = None
    reading_time_minutes: float = Field(default=0.0, ge=0.0)
    geo: Optional[str] = None
    language: Optional[str] = None
    social_summary: Optional[str] = None


class ArticleMetrics(BaseModel):
    """Quantitative metrics used for gatekeeping article quality."""

    word_count: int = Field(ge=0)
    heading_counts: Dict[str, int] = Field(default_factory=dict)
    keyword_density: Dict[str, float] = Field(default_factory=dict)
    flesch_reading_ease: float
    fk_grade_level: float
    checksum_sha1: str
    checksum_sha256: str
    simhash: str
    duplicate_matches: List[str] = Field(default_factory=list)
    auto_regenerations: int = Field(default=0, ge=0)


class ArticleRequest(BaseModel):
    """Request payload for AI-authored article generation."""

    keyword: str
    geo: str = "ID"
    tone: Literal["neutral", "formal", "casual", "authoritative", "friendly"] = "neutral"
    target_language: str = "id"
    min_words: int = Field(default=800, ge=500)
    max_words: int = Field(default=1600, ge=600)
    max_references: int = Field(default=7, ge=3, le=12)
    include_images: bool = True
    image_provider_preference: Literal["auto", "pexels", "pixabay", "ai"] = "auto"
    additional_context: Optional[str] = None
    sitemap_url: Optional[HttpUrl] = None
    site_url: Optional[HttpUrl] = None
    secondary_keywords: List[str] = Field(default_factory=list)
    custom_reference_urls: List[HttpUrl] = Field(default_factory=list)
    llm_provider_priority: List[str] = Field(
        default_factory=lambda: ["openai", "deepseek", "openrouter", "gemini", "llama"]
    )

    @validator("max_words")
    def _check_bounds(cls, value: int, values: Dict[str, int]) -> int:
        if value < values.get("min_words", 500):
            raise ValueError("max_words must be greater than or equal to min_words")
        return value


class RSSRequest(BaseModel):
    """Request payload for rewriting RSS content into unique drafts."""

    feed_url: HttpUrl
    tone: Literal["neutral", "formal", "casual", "authoritative", "friendly"] = "neutral"
    geo: str = "ID"
    keyword: Optional[str] = None
    max_items: int = Field(default=3, ge=1, le=5)


class ArticleResponse(BaseModel):
    """Structured response returned by generation endpoints."""

    article_html: str
    meta: ArticleMeta
    metrics: ArticleMetrics
    sources: List[ReferenceArticle]
    images: List[ImageAsset] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    history_id: Optional[str] = None
    curl_example: Optional[str] = None


class GapRecommendation(BaseModel):
    """Single gap insight describing missing coverage."""

    keyword: str
    status: Literal["missing", "existing"]
    headline: str
    outline: List[str]
    notes: Optional[str] = None


class GapResponse(BaseModel):
    """Response payload for the content gap endpoint."""

    keyword: str
    geo: str
    missing_keywords: List[str] = Field(default_factory=list)
    existing_keywords: List[str] = Field(default_factory=list)
    recommendations: List[GapRecommendation] = Field(default_factory=list)
    references: List[ReferenceArticle] = Field(default_factory=list)
    trend_topics: List[str] = Field(default_factory=list)
    curl_example: Optional[str] = None
