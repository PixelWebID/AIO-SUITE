"""Search aggregation utilities for gathering reference content."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Iterable, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from ..models.schemas import ReferenceArticle
from ..utils.notifications import notify_failure

MIN_REFERENCES = 3
MAX_REFERENCES = 7
REQUEST_TIMEOUT = 15.0


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url


def _normalize_results(items: Iterable[Tuple[str, str, str]]) -> List[ReferenceArticle]:
    seen: Set[str] = set()
    references: List[ReferenceArticle] = []

    for title, link, snippet in items:
        if not link or link in seen:
            continue
        seen.add(link)
        references.append(
            ReferenceArticle(
                title=title.strip() or "Untitled",
                url=link,
                snippet=snippet.strip(),
                domain=_extract_domain(link),
            )
        )
    return references


async def _fetch_google_search(keyword: str, geo: str) -> List[ReferenceArticle]:
    """Query Google Custom Search if credentials are available."""

    if not settings.serp_google_api_key or not settings.serp_google_cx:
        return []

    params = {
        "key": settings.serp_google_api_key,
        "cx": settings.serp_google_cx,
        "q": keyword,
        "gl": geo.lower(),
        "num": 5,
    }
    url = f"https://www.googleapis.com/customsearch/v1?{urlencode(params)}"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()

    items = []
    for item in payload.get("items", []):
        items.append((item.get("title", ""), item.get("link", ""), item.get("snippet", "")))
    return _normalize_results(items)


async def _fetch_bing_search(keyword: str, geo: str) -> List[ReferenceArticle]:
    """Query Bing Web Search API if configured."""

    if not settings.bing_api_key:
        return []

    headers = {"Ocp-Apim-Subscription-Key": settings.bing_api_key}
    params = {"q": keyword, "mkt": geo.lower(), "count": 5}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            "https://api.bing.microsoft.com/v7.0/search", params=params, headers=headers
        )
        response.raise_for_status()
        payload = response.json()

    web_pages = payload.get("webPages", {}).get("value", [])
    items = []
    for page in web_pages:
        items.append((page.get("name", ""), page.get("url", ""), page.get("snippet", "")))
    return _normalize_results(items)


async def _fetch_serper(keyword: str, geo: str) -> List[ReferenceArticle]:
    """Query Serper.dev as a Google Search proxy."""

    if not settings.serper_api_key:
        return []

    headers = {"X-API-KEY": settings.serper_api_key}
    payload = {"q": keyword, "gl": geo.lower(), "num": 5}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post("https://google.serper.dev/search", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    items = []
    for item in data.get("organic", []):
        items.append((item.get("title", ""), item.get("link", ""), item.get("snippet", "")))
    return _normalize_results(items)


async def _fetch_metadata(url: str) -> Optional[ReferenceArticle]:
    """Fetch metadata (title, description) from a direct URL."""

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:  # pragma: no cover - network failures handled gracefully
        await notify_failure({"keyword": url, "error": str(exc), "stage": "fetch_metadata"})
        return None

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    description = ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    if description_tag and description_tag.get("content"):
        description = description_tag["content"].strip()
    else:
        first_paragraph = soup.find("p")
        if first_paragraph:
            description = first_paragraph.text.strip()

    return ReferenceArticle(
        title=title,
        url=url,
        snippet=description,
        domain=_extract_domain(url),
    )


async def _fallback_references(keyword: str, geo: str) -> List[ReferenceArticle]:
    """Generate deterministic fallback references when APIs are unavailable."""

    base_url = f"https://{geo.lower()}.wikipedia.org/wiki/{keyword.replace(' ', '_')}"
    return [
        ReferenceArticle(
            title=f"{keyword.title()} Overview",
            url=base_url,
            snippet=f"Baseline knowledge article for {keyword} used when search providers are unavailable.",
            domain=_extract_domain(base_url),
        ),
        ReferenceArticle(
            title=f"{keyword.title()} Market Insights {datetime.utcnow().year}",
            url=f"https://www.statista.com/search/?q={keyword}",
            snippet="Industry trend data sourced from Statista public listings.",
            domain="www.statista.com",
        ),
        ReferenceArticle(
            title=f"{keyword.title()} Community Discussion",
            url=f"https://www.reddit.com/r/{keyword.replace(' ', '')}/",
            snippet="Community-driven experiences providing qualitative insights.",
            domain="www.reddit.com",
        ),
    ]


async def gather_reference_content(
    keyword: str,
    geo: str,
    competitors: Optional[Iterable[str]] = None,
    custom_urls: Optional[Iterable[str]] = None,
) -> List[ReferenceArticle]:
    """
    Collect reference articles from search engines or provided competitor URLs.

    Aggregates multi-provider SERP results, custom URLs, and deterministic fallbacks
    to ensure the minimum reference requirement is satisfied.
    """

    providers = [
        _fetch_google_search(keyword, geo),
        _fetch_serper(keyword, geo),
        _fetch_bing_search(keyword, geo),
    ]

    results: List[ReferenceArticle] = []
    provider_outputs = await asyncio.gather(*providers, return_exceptions=True)
    for output in provider_outputs:
        if isinstance(output, Exception):
            await notify_failure(
                {
                    "keyword": keyword,
                    "geo": geo,
                    "error": str(output),
                    "stage": "search_provider",
                }
            )
            continue
        results.extend(output)

    if competitors:
        competitor_tasks = [_fetch_metadata(url) for url in competitors]
        competitor_results = await asyncio.gather(*competitor_tasks)
        for item in competitor_results:
            if item:
                results.append(item)

    if custom_urls:
        custom_tasks = [_fetch_metadata(url) for url in custom_urls]
        custom_results = await asyncio.gather(*custom_tasks)
        for item in custom_results:
            if item:
                results.append(item)

    if len(results) < MIN_REFERENCES:
        results.extend(await _fallback_references(keyword, geo))

    # Deduplicate and clamp
    unique: List[ReferenceArticle] = []
    seen: Set[str] = set()
    for item in results:
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
        if len(unique) >= MAX_REFERENCES:
            break

    return unique[:MAX_REFERENCES]
