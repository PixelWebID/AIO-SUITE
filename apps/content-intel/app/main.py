"""FastAPI application entrypoint for the Content Intelligence service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.articles import router as articles_router
from .routes.gap import router as gap_router
from .utils.db import init_engine


def create_app() -> FastAPI:
    """Application factory used by ASGI servers."""

    init_engine()

    app = FastAPI(
        title="AIO Content Intelligence",
        description=(
            "Content generation, enrichment, and gap analysis APIs powering the AIO Suite. "
            "The service aggregates SERP data, orchestrates multi-provider LLMs, and enforces "
            "strict editorial guardrails before returning publish-ready content."
        ),
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(articles_router, prefix="/api")
    app.include_router(gap_router, prefix="/api")

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        """Basic health probe used by orchestrators."""

        return {"status": "ok", "service": "content-intel", "version": settings.version}

    return app


app = create_app()
