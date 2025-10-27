"""Google Trends integration helpers for related query discovery."""

from __future__ import annotations

import asyncio
from typing import List

from pytrends.request import TrendReq

from ..config import settings


def _build_trend_client() -> TrendReq:
    """Create an authenticated (or anonymous) TrendReq client."""

    return TrendReq(
        hl=settings.default_locale.replace("_", "-"),
        tz=420,
        username=settings.google_trends_username,
        password=settings.google_trends_password,
        retries=2,
        backoff_factor=0.1,
    )


async def fetch_keyword_trends(keyword: str, geo: str) -> List[str]:
    """
    Retrieve trending related queries for the provided keyword and geographic code.

    Falls back to deterministic variants when rate-limited or unavailable.
    """

    def _fetch() -> List[str]:
        client = _build_trend_client()
        client.build_payload([keyword], timeframe="today 12-m", geo=geo.upper())
        related = client.related_queries()
        if not related or keyword not in related:
            return []

        top = related[keyword].get("top") or []
        rising = related[keyword].get("rising") or []

        def _extract(rows):
            return [
                row["query"]
                for row in rows
                if "query" in row and row.get("value", 0) >= 20
            ]

        suggestions = list(dict.fromkeys(_extract(top) + _extract(rising)))
        return suggestions[:10]

    try:
        loop = asyncio.get_running_loop()
        suggestions = await loop.run_in_executor(None, _fetch)
        if suggestions:
            return suggestions
    except Exception:
        pass

    keyword_lower = keyword.lower()
    geo_lower = geo.lower()
    return [
        f"{keyword_lower} trend {geo_lower}",
        f"{keyword_lower} case study",
        f"{keyword_lower} pricing {geo_lower}",
        f"{keyword_lower} tools",
        f"{keyword_lower} strategy update",
    ]
