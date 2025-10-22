"""Image sourcing helpers for external providers."""

from typing import List

from ..models.schemas import ImageAsset


async def suggest_images(keyword: str) -> List[ImageAsset]:
    """
    Suggest stock or AI-generated images related to the keyword.

    Integrations with Pexels, Pixabay, and internal generators are wired in the
    full implementation. Here we emit placeholder data to satisfy the contract.
    """

    base = keyword.replace(" ", "-")
    return [
        ImageAsset(
            provider="pexels",
            url=f"https://images.example.com/{base}-hero.jpg",
            caption=f"Hero image for {keyword}",
            attribution="Courtesy of Pexels (placeholder)",
        ),
        ImageAsset(
            provider="pixabay",
            url=f"https://images.example.com/{base}-detail.jpg",
            caption=f"Detail shot for {keyword}",
        ),
    ]
