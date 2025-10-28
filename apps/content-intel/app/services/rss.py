
"""RSS feed ingestion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import feedparser
import httpx
from trafilatura import extract as trafilatura_extract

from .ai_providers import AIClient


@dataclass
class RSSItem:
    title: str
    summary: str
    body_html: str
    link: str
    published_at: str


async def parse_rss_feed(feed_url: str, max_items: int = 3) -> List[RSSItem]:
    parsed = feedparser.parse(feed_url)
    items: List[RSSItem] = []
    for entry in parsed.entries[:max_items]:
        link = entry.get('link') or entry.get('id') or ''
        summary = entry.get('summary') or entry.get('description') or ''
        title = entry.get('title') or 'Feed Item'
        published = entry.get('published') or entry.get('updated') or ''
        body_html = entry.get('content')[0].get('value') if entry.get('content') else ''

        if not body_html and link:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.get(link, follow_redirects=True)
                    response.raise_for_status()
                    extracted = trafilatura_extract(response.text, include_comments=False, include_tables=True)
                    body_html = extracted or ''
            except Exception:
                body_html = ''

        if not body_html:
            body_html = f"<p>{summary}</p>"

        items.append(
            RSSItem(
                title=title,
                summary=summary,
                body_html=body_html,
                link=link,
                published_at=published,
            )
        )

    return items


async def rewrite_content(
    text: str,
    tone: str,
    *,
    provider_priority: Optional[Iterable[str]] = None,
) -> str:
    client = AIClient(provider_priority or ["openai", "deepseek", "openrouter", "gemini", "llama"])
    rewritten = await client.rewrite(text, tone)
    if not rewritten.strip():
        return f"<p>{text}</p>"
    return rewritten
