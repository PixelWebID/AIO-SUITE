"""Internal linking utilities (sitemap parsing and anchor extraction)."""

from __future__ import annotations

import asyncio
import difflib
import html
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Dict, List, Tuple

import httpx

from ..config import settings
from ..models.schemas import LinkSuggestion

REQUEST_TIMEOUT = 15.0


@lru_cache(maxsize=64)
def _extract_slug(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[-_]+", " ", slug)
    return slug


_SITEMAP_CACHE: Dict[str, Tuple[float, List[str]]] = {}


async def _load_sitemap(url: str) -> List[str]:
    now = asyncio.get_running_loop().time()
    cached = _SITEMAP_CACHE.get(url)
    if cached and now - cached[0] <= settings.sitemap_cache_ttl:
        return cached[1]

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.text

    root = ET.fromstring(content)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//sm:loc", namespace) if loc.text]

    _SITEMAP_CACHE[url] = (now, urls)
    return urls


async def suggest_internal_links(keyword: str, sitemap_url: str, limit: int = 5) -> List[LinkSuggestion]:
    """Parse the sitemap and return internal link suggestions ranked by relevance."""

    try:
        urls = await _load_sitemap(sitemap_url)
    except Exception:
        return []

    suggestions: List[LinkSuggestion] = []
    keyword_lower = keyword.lower()

    for url in urls:
        slug = _extract_slug(url)
        ratio = difflib.SequenceMatcher(None, slug.lower(), keyword_lower).ratio()
        if ratio < 0.35:
            continue
        anchor = html.escape(slug.title())
        suggestions.append(
            LinkSuggestion(
                type="internal",
                anchor=anchor,
                url=url,
                rationale=f"Konteks mirip berdasarkan slug {slug}",
                relevance=round(ratio, 2),
            )
        )

    suggestions.sort(key=lambda item: item.relevance, reverse=True)
    return suggestions[:limit]
