"""Scraper utilities for aggregating competitor and SERP content."""

from typing import Iterable, List, Optional

from ..models.schemas import ReferenceArticle


async def gather_reference_content(
    keyword: str,
    geo: str,
    competitors: Optional[Iterable[str]] = None,
) -> List[ReferenceArticle]:
    """
    Collect reference articles from search engines or provided competitor URLs.

    In production this module would orchestrate browser automation, HTTP requests,
    and extraction routines. For now we return deterministic placeholder data to
    unblock API consumers and integration tests.
    """

    references: List[ReferenceArticle] = [
        ReferenceArticle(
            title=f"{keyword.title()} insights ({geo})",
            url=f"https://example.com/{keyword}-insights",
            snippet="SERP summary placeholder used during development.",
        ),
        ReferenceArticle(
            title=f"{keyword.title()} playbook",
            url=f"https://example.com/{keyword}-playbook",
            snippet="Compiled competitor highlights and structural notes.",
        ),
    ]

    if competitors:
        for rank, url in enumerate(competitors, start=1):
            references.append(
                ReferenceArticle(
                    title=f"Competitor #{rank}",
                    url=url,
                    snippet="Pending scrape result.",
                )
            )

    return references
