"""
FastAPI application for the AIO content intelligence service.

This service provides endpoints for generating articles based on keywords.
It uses a simple dummy implementation to demonstrate the API shape.  In
production, this would interface with scraping and AI providers.
"""

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="AIO Content Intelligence Service")


class GenerateRequest(BaseModel):
    """Request model for generating an article."""

    keyword: str
    geo: str = "ID"
    tone: str = "casual"
    min_words: int = 700
    max_words: int = 1200


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/generate_article")
async def generate_article(req: GenerateRequest):
    """
    Generate a dummy article based on the provided request.  This endpoint
    returns HTML content along with metadata and simple metrics.  In a real
    implementation you would call LLM providers, scrape reference content,
    and compute readability.
    """
    article_html = (
        f"<h1>{req.keyword.title()}</h1>\n"
        f"<p>Generated dummy content for the keyword '{req.keyword}'.</p>"
    )
    word_count = len(article_html.split())
    return {
        "article_html": article_html,
        "meta": {
            "title": f"{req.keyword} - AIO",
            "description": "Generated article description",
            "tags": [req.keyword],
        },
        "metrics": {
            "word_count": word_count,
            "headings": {"h2": 0, "h3": 0},
            "readability": {"flesch": 60.0, "fk_grade": 8.0},
        },
        "sources": [],
        "warnings": [],
    }