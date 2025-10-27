"""Article generation, history, and RSS enrichment endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import (
    ArticleMeta,
    ArticleMetrics,
    ArticleRequest,
    ArticleResponse,
    RssRequest,
    RssResponse,
)
from ..services.ai_providers import generate_article_draft
from ..services.images import suggest_images
from ..services.rss import rewrite_rss_item
from ..services.scraper import gather_reference_content
from ..services.trends import fetch_keyword_trends
from ..utils.db import (
    fetch_activity,
    fetch_history_item,
    fetch_recent_history,
    log_generation_job,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate_article", response_model=ArticleResponse)
async def generate_article(payload: ArticleRequest) -> ArticleResponse:
    """Generate an article draft using AI providers, trends, and curated references."""

    references = await gather_reference_content(
        payload.keyword,
        payload.geo,
        custom_urls=[str(url) for url in payload.custom_reference_urls],
    )
    if not references:
        raise HTTPException(status_code=424, detail="Unable to collect reference content.")

    trends = await fetch_keyword_trends(payload.keyword, payload.geo)
    draft = await generate_article_draft(payload, references, trends=trends)

    images = (
        await suggest_images(
            payload.keyword,
            provider_preference=payload.image_provider_preference,
        )
        if payload.include_images
        else []
    )

    meta = draft["meta"]
    if isinstance(meta, dict):
        meta = ArticleMeta(**meta)

    metrics = draft["metrics"]
    if isinstance(metrics, dict):
        metrics = ArticleMetrics(**metrics)

    response = ArticleResponse(
        article_html=draft["article_html"],
        meta=meta,
        metrics=metrics,
        sources=references,
        warnings=draft.get("warnings", []),
        images=images,
        history_id=draft.get("history_id"),
    )

    history_id = await log_generation_job(payload, response)
    response.history_id = history_id

    return response


@router.post("/generate_from_rss", response_model=RssResponse)
async def generate_from_rss(payload: RssRequest) -> RssResponse:
    """Rewrite an RSS item into a fresh article draft."""

    item = await rewrite_rss_item(payload)
    if not item:
        raise HTTPException(status_code=404, detail="No content available for the provided feed.")
    return item


@router.get("/history")
async def list_history(limit: int = Query(default=10, ge=1, le=50)):
    """Return the most recent article generation jobs."""

    return await fetch_recent_history(limit=limit)


@router.get("/history/{history_id}")
async def get_history(history_id: str):
    """Fetch a single article generation record."""

    record = await fetch_history_item(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History item not found.")
    return record


@router.get("/activity")
async def get_activity(limit: int = Query(default=25, ge=1, le=100)):
    """Return recent activity log entries."""

    return await fetch_activity(limit=limit)
