"""FastAPI entrypoint for the AIO Content Intelligence microservice."""

from fastapi import FastAPI

from .config import settings
from .routes.articles import router as articles_router
from .routes.gap import router as gap_router

app = FastAPI(
    title="AIO Content Intelligence Service",
    version=settings.version,
    description="Content generation, enrichment, and analysis APIs for the AIO Suite.",
)

app.include_router(articles_router, prefix="/api")
app.include_router(gap_router, prefix="/api")


@app.get("/health", tags=["system"])
async def health_check():
    """Simple health endpoint used by orchestrators and load balancers."""
    return {"status": "ok", "service": "content-intel", "version": settings.version}
