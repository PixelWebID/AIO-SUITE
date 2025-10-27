"""Image sourcing helpers for Pexels, Pixabay, and custom AI generation."""

from __future__ import annotations

from typing import List, Optional

import asyncio

import httpx

from ..config import settings
from ..models.schemas import ImageAsset
from ..utils.notifications import notify_failure

REQUEST_TIMEOUT = 15.0


async def _fetch_pexels(keyword: str, limit: int) -> List[ImageAsset]:
    if not settings.pexels_api_key:
        return []

    headers = {"Authorization": settings.pexels_api_key}
    params = {"query": keyword, "orientation": "landscape", "per_page": limit}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get("https://api.pexels.com/v1/search", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    assets = []
    for photo in data.get("photos", []):
        assets.append(
            ImageAsset(
                provider="pexels",
                url=photo["src"]["large2x"],
                caption=photo.get("alt") or keyword.title(),
                attribution=f"Pexels / {photo.get('photographer', 'Unknown')}",
                width=photo.get("width"),
                height=photo.get("height"),
                thumbnail_url=photo["src"].get("medium"),
            )
        )
    return assets


async def _fetch_pixabay(keyword: str, limit: int) -> List[ImageAsset]:
    if not settings.pixabay_api_key:
        return []

    params = {
        "key": settings.pixabay_api_key,
        "q": keyword,
        "image_type": "photo",
        "per_page": limit,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get("https://pixabay.com/api/", params=params)
        response.raise_for_status()
        data = response.json()

    assets = []
    for hit in data.get("hits", []):
        assets.append(
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
    return assets


async def _generate_ai_image(keyword: str) -> Optional[ImageAsset]:
    if not settings.ai_image_endpoint or not settings.ai_image_api_key:
        return None

    payload = {"prompt": f"Photo-realistic editorial image about {keyword}"}
    headers = {"Authorization": f"Bearer {settings.ai_image_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(settings.ai_image_endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # pragma: no cover - network variations
        await notify_failure({"keyword": keyword, "error": str(exc), "stage": "ai_image"})
        return None

    if "url" not in data:
        return None

    return ImageAsset(
        provider="ai",
        url=data["url"],
        caption=data.get("caption") or f"AI generated hero for {keyword}",
        attribution=data.get("attribution"),
    )


async def suggest_images(
    keyword: str,
    *,
    provider_preference: str = "auto",
    limit: int = 3,
) -> List[ImageAsset]:
    """
    Suggest stock or AI-generated images related to the keyword.

    provider_preference accepts `auto`, `pexels`, `pixabay`, or `ai`.
    """

    providers = []
    if provider_preference in ("auto", "pexels"):
        providers.append(_fetch_pexels(keyword, limit))
    if provider_preference in ("auto", "pixabay"):
        providers.append(_fetch_pixabay(keyword, limit))

    images: List[ImageAsset] = []
    provider_results = await asyncio.gather(*providers, return_exceptions=True)
    for result in provider_results:
        if isinstance(result, Exception):
            await notify_failure({"keyword": keyword, "error": str(result), "stage": "image"})
            continue
        images.extend(result)

    if provider_preference in ("auto", "ai") and len(images) < limit:
        ai_asset = await _generate_ai_image(keyword)
        if ai_asset:
            images.append(ai_asset)

    if not images:
        fallback_url = f"https://source.unsplash.com/featured/?{keyword.replace(' ', ',')}"
        images.append(
            ImageAsset(
                provider="upload",
                url=fallback_url,
                caption=f"Representative imagery for {keyword}",
            )
        )

    return images[:limit]
