"""Article generation and enrichment endpoints."""

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
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
from ..utils.db import log_generation_job
from ..utils.duplicate import compute_signatures
from ..utils.readability import score_readability

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate_article", response_model=ArticleResponse)
async def generate_article(payload: ArticleRequest) -> ArticleResponse:
    """Generate an article draft using AI providers and curated references."""

    references = await gather_reference_content(payload.keyword, payload.geo)
    if not references:
        raise HTTPException(status_code=424, detail="Unable to collect reference content.")

    trends = await fetch_keyword_trends(payload.keyword, payload.geo)
    draft = await generate_article_draft(payload, references, trends=trends)
    readability = score_readability(draft["article_html"])
    signatures = compute_signatures(draft["article_html"])
    images = await suggest_images(payload.keyword) if payload.include_images else []

    response = ArticleResponse(
        article_html=draft["article_html"],
        meta=draft["meta"],
        metrics={
            **draft["metrics"],
            "readability": readability,
            "signatures": signatures,
        },
        sources=references,
        warnings=draft.get("warnings", []),
        images=images,
    )

    await log_generation_job(payload, response)
    return response


@router.post("/generate_from_rss", response_model=RssResponse)
async def generate_from_rss(payload: RssRequest) -> RssResponse:
    """Rewrite an RSS item into a fresh article draft."""

    item = await rewrite_rss_item(payload)
    if not item:
        raise HTTPException(status_code=404, detail="No content available for the provided feed.")

    return item
