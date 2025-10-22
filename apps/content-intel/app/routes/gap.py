"""Content gap analysis endpoints."""

from fastapi import APIRouter

from ..models.schemas import ContentGapRequest, ContentGapResponse
from ..services.scraper import gather_reference_content
from ..services.trends import fetch_keyword_trends
from ..utils.db import log_gap_job

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/content_gap", response_model=ContentGapResponse)
async def content_gap(payload: ContentGapRequest) -> ContentGapResponse:
    """Perform a lightweight content-gap analysis for provided competitors."""

    references = await gather_reference_content(payload.keyword, payload.geo, payload.competitors)
    trends = await fetch_keyword_trends(payload.keyword, payload.geo)

    insights = [
        {
            "title": "Topical authority opportunity",
            "summary": "Competitors lack evergreen guides covering user intent at the awareness stage.",
            "difficulty": "medium",
            "opportunity_score": 0.72,
        },
        {
            "title": "Schema markup gap",
            "summary": "Implement FAQ schema for transactional pages to improve SERP coverage.",
            "difficulty": "low",
            "opportunity_score": 0.65,
        },
    ]

    response = ContentGapResponse(
        keyword=payload.keyword,
        insights=insights,
        references=references,
    )

    await log_gap_job(payload, response, trends=trends)
    return response
