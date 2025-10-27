"""Gap analysis endpoint."""

from __future__ import annotations

import textwrap
from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import GapRecommendation, GapResponse
from ..services.scraper import gather_reference_content
from ..services.trends import fetch_keyword_trends
from ..utils.db import fetch_existing_keywords

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/content_gap", response_model=GapResponse)
async def content_gap(keyword: str = Query(...), geo: str = Query("ID")) -> GapResponse:
    references = await gather_reference_content(keyword, geo)
    if not references:
        raise HTTPException(status_code=424, detail="Unable to gather references for gap analysis")

    trends = await fetch_keyword_trends(keyword, geo)
    existing_keywords = [kw.lower() for kw in fetch_existing_keywords()] + [keyword.lower()]

    missing_keywords = []
    existing_related = []
    for trend in trends:
        (existing_related if trend.lower() in existing_keywords else missing_keywords).append(trend)

    recommendations: List[GapRecommendation] = []
    for idx, ref in enumerate(references[:5]):
        status = "missing" if idx < len(missing_keywords) else "existing"
        focus_keyword = missing_keywords[idx] if idx < len(missing_keywords) else ref.title
        outline = ref.outline[:4] or ["Pendahuluan", "Strategi", "Contoh Lokal", "CTA"]
        recommendations.append(
            GapRecommendation(
                keyword=focus_keyword,
                status=status,
                headline=f"{focus_keyword.title()} Playbook {geo.upper()}",
                outline=outline,
                notes=f"Berdasarkan referensi {ref.domain}"
            )
        )

    curl = textwrap.dedent(
        f"""
        curl "http://localhost:8000/api/analysis/content_gap?keyword={keyword}&geo={geo}"
        """
    ).strip()

    return GapResponse(
        keyword=keyword,
        geo=geo,
        missing_keywords=missing_keywords,
        existing_keywords=existing_related,
        recommendations=recommendations,
        references=references,
        trend_topics=trends,
        curl_example=curl,
    )
