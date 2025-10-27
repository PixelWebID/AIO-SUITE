"""Image sourcing helpers for Pexels/Pixabay/AI."""

from __future__ import annotations

from typing import List, Optional

import httpx

from ..config import settings
from ..models.schemas import ImageAsset

REQUEST_TIMEOUT = 20.0


async def search_image(keyword: str, *, limit: int = 4) -> List[ImageAsset]:
    """Aggregate results from Pexels and Pixabay."""

    results: List[ImageAsset] = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        if settings.pexels_api_key:
            try:
                response = await client.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": keyword, "orientation": "landscape", "per_page": limit},
                    headers={"Authorization": settings.pexels_api_key},
                )
                response.raise_for_status()
                for photo in response.json().get("photos", []):
                    results.append(
                        ImageAsset(
                            provider="pexels",
                            url=photo["src"]["large2x"],
                            caption=photo.get("alt") or keyword.title(),
                            attribution=f"Pexels / {photo.get('photographer', 'Contributor')}",
                            width=photo.get("width"),
                            height=photo.get("height"),
                            thumbnail_url=photo["src"].get("medium"),
                        )
                    )
            except Exception:
                pass

        if settings.pixabay_api_key and len(results) < limit:
            try:
                response = await client.get(
                    "https://pixabay.com/api/",
                    params={
                        "key": settings.pixabay_api_key,
                        "q": keyword,
                        "image_type": "photo",
                        "per_page": limit,
                    },
                )
                response.raise_for_status()
                for hit in response.json().get("hits", []):
                    results.append(
                        ImageAsset(
                            provider="pixabay",
                            url=hit["largeImageURL"],
                            caption=hit.get("tags", keyword),
                            attribution=f"Pixabay / {hit.get('user', 'Contributor')}",
                            width=hit.get("imageWidth"),
                            height=hit.get("imageHeight"),
                            thumbnail_url=hit.get("previewURL"),
                        )
                    )
            except Exception:
                pass

    return results[:limit]


async def generate_ai_image(keyword: str) -> Optional[ImageAsset]:
    if not settings.ai_image_endpoint or not settings.ai_image_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                settings.ai_image_endpoint,
                json={"prompt": f"Editorial illustration about {keyword}"},
                headers={"Authorization": f"Bearer {settings.ai_image_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            if "url" not in data:
                return None
            return ImageAsset(
                provider="ai",
                url=data["url"],
                caption=data.get("caption") or f"AI generated visual for {keyword}",
                attribution=data.get("attribution"),
            )
    except Exception:
        return None


def select_image(results: List[ImageAsset]) -> Optional[ImageAsset]:
    return results[0] if results else None


async def suggest_images(keyword: str, *, provider_preference: str = "auto", limit: int = 3) -> List[ImageAsset]:
    candidates: List[ImageAsset] = []

    if provider_preference in ("auto", "pexels", "pixabay"):
        candidates.extend(await search_image(keyword, limit=limit))

    if provider_preference in ("auto", "ai") and len(candidates) < limit:
        ai_image = await generate_ai_image(keyword)
        if ai_image:
            candidates.append(ai_image)

    if not candidates:
        candidates.append(
            ImageAsset(
                provider="fallback",
                url=f"https://source.unsplash.com/featured/?{keyword.replace(' ', ',')}",
                caption=f"Generic imagery for {keyword}",
            )
        )

    return candidates[:limit]
