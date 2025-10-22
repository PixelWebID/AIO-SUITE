"""AI provider orchestration layer."""

from typing import Dict, List, Optional

from ..config import settings
from ..models.schemas import ArticleRequest, ReferenceArticle


async def generate_article_draft(
    payload: ArticleRequest,
    references: List[ReferenceArticle],
    *,
    trends: Optional[List[str]] = None,
) -> Dict:
    """
    Generate a structured article draft combining AI output with contextual hints.

    A real implementation would route to OpenAI, DeepSeek, OpenRouter, Gemini, or
    Llama depending on availability, cost, and latency constraints. We expose the
    contract here so that downstream services remain stable while integrations are
    developed.
    """

    tone = payload.tone.capitalize()
    keyword = payload.keyword.title()
    insight = trends[0] if trends else f"{keyword} marketing"
    intro = (
        f"<h1>{keyword}</h1>"
        f"<p>This article explores {keyword.lower()} with a {tone.lower()} tone.</p>"
    )

    body = [
        "<h2>Overview</h2>",
        "<p>Generated content placeholder. Replace with LLM output.</p>",
        "<h2>Key Insights</h2>",
        f"<p>Trending focus: {insight}.</p>",
    ]

    return {
        "article_html": intro + "\n".join(body),
        "meta": {
            "title": f"{keyword} — AIO Draft",
            "description": f"Stub description for {keyword}.",
            "tags": [payload.keyword, tone.lower()],
            "provider": settings.environment,
        },
        "metrics": {
            "word_count": 240,
            "outline": ["Overview", "Key Insights"],
        },
        "warnings": ["LLM provider not connected. This is mock data."],
    }
