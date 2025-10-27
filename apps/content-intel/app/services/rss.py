"""RSS feed ingestion and rewriting utilities."""

from __future__ import annotations

from typing import List, Optional

import feedparser

from ..models.schemas import ArticleRequest, ReferenceArticle, RssRequest, RssResponse
from ..utils.notifications import notify_failure
from .ai_providers import generate_article_draft
from .scraper import gather_reference_content


async def _entry_to_reference(entry: dict) -> ReferenceArticle:
    """Convert a feed entry into a ReferenceArticle stub."""

    link = entry.get("link") or entry.get("id") or "https://example.com"
    title = entry.get("title") or "RSS Item"
    summary = entry.get("summary") or entry.get("description") or ""

    return ReferenceArticle(
        title=title,
        url=link,
        snippet=summary[:280],
    )


async def rewrite_rss_item(payload: RssRequest) -> Optional[RssResponse]:
    """
    Fetch an RSS item and rewrite it into a unique article structure.

    Leverages the article generation pipeline to guarantee consistent quality gates.
    """

    parsed = feedparser.parse(str(payload.feed_url))
    if not parsed.entries:
        await notify_failure({"keyword": payload.keyword or "rss", "stage": "rss_fetch", "detail": "No entries"})
        return None

    entry = parsed.entries[0]
    base_reference = await _entry_to_reference(entry)

    keyword = payload.keyword or base_reference.title
    references: List[ReferenceArticle] = [base_reference]
    extra_refs = await gather_reference_content(keyword, payload.geo, custom_urls=[base_reference.url])
    references.extend(extra_refs)

    request = ArticleRequest(
        keyword=keyword,
        geo=payload.geo,
        tone=payload.tone,
        target_language=payload.target_language,
        include_images=False,
        additional_context=base_reference.snippet,
        sitemap_url=payload.sitemap_url,
        site_url=payload.site_url,
    )

    result = await generate_article_draft(request, references, trends=[])

    meta = result["meta"]
    metrics = result["metrics"]

    return RssResponse(
        article_html=result["article_html"],
        meta=meta,
        metrics=metrics,
        source_item={
            "title": base_reference.title,
            "link": base_reference.url,
            "published": entry.get("published") or entry.get("updated") or "",
        },
        warnings=result.get("warnings", []),
    )
