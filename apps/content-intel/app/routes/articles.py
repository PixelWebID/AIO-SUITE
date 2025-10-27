"""Article generation and RSS rewriting routes."""

from __future__ import annotations

import textwrap
import uuid
from typing import List

from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    ArticleMeta,
    ArticleMetrics,
    ArticleRequest,
    ArticleResponse,
    RSSRequest,
    ReferenceArticle,
)
from ..services.ai_providers import AIClient
from ..services.images import suggest_images
from ..services.rss import parse_rss_feed
from ..services.scraper import gather_reference_content
from ..services.trends import fetch_keyword_trends
from ..utils.db import (
    fetch_recent_simhashes,
    log_event,
    store_article,
    store_references,
)
from ..utils.duplicate import checksum, compute_simhash, detect_similarities
from ..utils.readability import score_readability

router = APIRouter(prefix="/content", tags=["content"])

MIN_HEADING_TARGET = 3
MIN_WORD_TARGET = 700
MIN_FLESCH = 55.0


def _count_headings(html: str) -> dict[str, int]:
    soup = BeautifulSoup(html, "html.parser")
    return {
        "h2": len(soup.find_all("h2")),
        "h3": len(soup.find_all("h3")),
    }


def _keyword_density(html: str, keywords: List[str]) -> dict[str, float]:
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    words = [w.lower() for w in text.split()] or [""]
    total = len(words)
    density = {}
    for keyword in keywords:
        if not keyword:
            continue
        count = sum(1 for w in words if keyword.lower() in w)
        density[keyword] = round((count / total) * 100, 2)
    return density


def _build_meta(payload: ArticleRequest, title: str, description: str, keywords: List[str], social_summary: str, word_count: int) -> ArticleMeta:
    from slugify import slugify

    return ArticleMeta(
        title=title,
        description=description,
        slug=slugify(title) or slugify(payload.keyword),
        keywords=list(dict.fromkeys(keywords or [payload.keyword])),
        tags=list(dict.fromkeys(keywords or [payload.keyword])),
        categories=[payload.keyword.title()],
        reading_time_minutes=round(word_count / 200, 2),
        geo=payload.geo,
        language=payload.target_language,
        social_summary=social_summary,
    )


def _to_reference_dict(ref: ReferenceArticle) -> dict:
    return {
        "title": ref.title,
        "url": str(ref.url),
        "snippet": ref.snippet,
        "domain": ref.domain,
    }


@router.post("/generate_article", response_model=ArticleResponse)
async def generate_article(payload: ArticleRequest) -> ArticleResponse:
    references = await gather_reference_content(
        payload.keyword,
        payload.geo,
        max_results=payload.max_references,
        custom_urls=[str(url) for url in payload.custom_reference_urls],
    )
    if not references:
        raise HTTPException(status_code=424, detail="Unable to gather reference material.")

    trends = await fetch_keyword_trends(payload.keyword, payload.geo)
    client = AIClient(payload.llm_provider_priority)

    best_article = None
    warnings: List[str] = []
    auto_regenerations = 0

    trend_feedback = list(trends)
    for attempt in range(3):
        ai_output = await client.generate_article(
            references,
            payload.keyword,
            payload.tone,
            payload.geo,
            payload.min_words,
            payload.max_words,
            trend_feedback,
        )

        article_html = ai_output["html"]
        readability = score_readability(article_html)
        heading_counts = _count_headings(article_html)
        word_count = int(readability["word_count"])
        density = _keyword_density(article_html, [payload.keyword] + payload.secondary_keywords + trend_feedback)
        sha1, sha256 = checksum(article_html)
        sim = compute_simhash(article_html)
        duplicates = detect_similarities(sim, [(row["history_id"], row["simhash"]) for row in fetch_recent_simhashes()])

        metrics = ArticleMetrics(
            word_count=word_count,
            heading_counts=heading_counts,
            keyword_density=density,
            flesch_reading_ease=readability["flesch_reading_ease"],
            fk_grade_level=readability["fk_grade_level"],
            checksum_sha1=sha1,
            checksum_sha256=sha256,
            simhash=sim,
            duplicate_matches=duplicates,
            auto_regenerations=auto_regenerations,
        )

        meta = _build_meta(
            payload,
            ai_output["title"],
            ai_output["description"],
            ai_output["keywords"],
            ai_output["social_summary"],
            word_count,
        )

        fails = []
        if word_count < max(payload.min_words, MIN_WORD_TARGET):
            fails.append("WORD_COUNT_LOW")
        if heading_counts.get("h2", 0) < MIN_HEADING_TARGET or heading_counts.get("h3", 0) < MIN_HEADING_TARGET:
            fails.append("HEADINGS_LOW")
        if metrics.flesch_reading_ease < MIN_FLESCH:
            fails.append("READABILITY_LOW")
        if duplicates:
            warnings.append("Potential duplicate detected: " + ", ".join(duplicates))

        best_article = (article_html, meta, metrics)

        if not fails:
            break

        warnings.extend(fails)
        auto_regenerations += 1
        trend_feedback.append("Perbaiki kelemahan: " + ", ".join(fails))

    if best_article is None:
        raise HTTPException(status_code=500, detail="Unable to generate article")

    article_html, meta, metrics = best_article

    history_id = str(uuid.uuid4())
    images = []
    if payload.include_images:
        images = await suggest_images(payload.keyword, provider_preference=payload.image_provider_preference)

    store_article(
        history_id,
        payload.keyword,
        payload.geo,
        payload.tone,
        article_html,
        meta.dict(),
        metrics.dict(),
        warnings,
    )
    store_references(history_id, [_to_reference_dict(ref) for ref in references])
    log_event(history_id, 'info', 'article_generated', {'keyword': payload.keyword})

    curl = textwrap.dedent(
        f"""
        curl -X POST "http://localhost:8000/api/content/generate_article" \\
          -H "Content-Type: application/json" \\
          -d '{{"keyword": "{payload.keyword}", "geo": "{payload.geo}", "tone": "{payload.tone}"}}'
        """
    ).strip()

    return ArticleResponse(
        article_html=article_html,
        meta=meta,
        metrics=metrics,
        sources=references,
        images=images,
        warnings=warnings,
        history_id=history_id,
        curl_example=curl,
    )


@router.post("/generate_from_rss", response_model=ArticleResponse)
async def generate_from_rss(payload: RSSRequest) -> ArticleResponse:
    entries = await parse_rss_feed(payload.feed_url, payload.max_items)
    if not entries:
        raise HTTPException(status_code=404, detail="Feed did not return any entries")

    primary = entries[0]
    client = AIClient(["openai", "deepseek", "openrouter", "gemini", "llama"])
    rewritten_html = await client.rewrite(primary.body_html, payload.tone)

    references = await gather_reference_content(primary.title or payload.keyword or "feed", payload.geo)
    trends = await fetch_keyword_trends(payload.keyword or primary.title, payload.geo)

    readability = score_readability(rewritten_html)
    heading_counts = _count_headings(rewritten_html)
    word_count = int(readability["word_count"])
    sha1, sha256 = checksum(rewritten_html)
    sim = compute_simhash(rewritten_html)
    duplicates = detect_similarities(sim, [(row["history_id"], row["simhash"]) for row in fetch_recent_simhashes()])

    warnings: List[str] = []
    if word_count < MIN_WORD_TARGET:
        warnings.append("WORD_COUNT_LOW")
    if heading_counts.get("h2", 0) < MIN_HEADING_TARGET or heading_counts.get("h3", 0) < MIN_HEADING_TARGET:
        warnings.append("HEADINGS_LOW")
    if readability["flesch_reading_ease"] < MIN_FLESCH:
        warnings.append("READABILITY_LOW")
    if duplicates:
        warnings.append("Potential duplicate detected")

    meta = _build_meta(
        ArticleRequest(keyword=primary.title or payload.keyword or "RSS", geo=payload.geo, tone=payload.tone),
        primary.title,
        primary.summary,
        trends[:5] or [primary.title],
        primary.summary[:160],
        word_count,
    )

    metrics = ArticleMetrics(
        word_count=word_count,
        heading_counts=heading_counts,
        keyword_density=_keyword_density(rewritten_html, trends[:5]),
        flesch_reading_ease=readability["flesch_reading_ease"],
        fk_grade_level=readability["fk_grade_level"],
        checksum_sha1=sha1,
        checksum_sha256=sha256,
        simhash=sim,
        duplicate_matches=duplicates,
        auto_regenerations=0,
    )

    history_id = str(uuid.uuid4())
    store_article(history_id, primary.title or payload.keyword or "RSS", payload.geo, payload.tone, rewritten_html, meta.dict(), metrics.dict(), warnings)
    store_references(history_id, [_to_reference_dict(ref) for ref in references])
    log_event(history_id, 'info', 'rss_rewrite', {'feed': str(payload.feed_url)})

    curl = textwrap.dedent(
        f"""
        curl -X POST "http://localhost:8000/api/content/generate_from_rss" \\
          -H "Content-Type: application/json" \\
          -d '{{"feed_url": "{payload.feed_url}", "tone": "{payload.tone}"}}'
        """
    ).strip()

    return ArticleResponse(
        article_html=rewritten_html,
        meta=meta,
        metrics=metrics,
        sources=references,
        images=[],
        warnings=warnings,
        history_id=history_id,
        curl_example=curl,
    )







