"""Content gap analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import ContentGapRequest, ContentGapResponse, GapInsight
from ..services.scraper import gather_reference_content
from ..services.trends import fetch_keyword_trends
from ..utils.db import log_gap_job

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/content_gap", response_model=ContentGapResponse)
async def content_gap(payload: ContentGapRequest) -> ContentGapResponse:
    """Perform an opinionated content-gap analysis against competitor URLs."""

    references = await gather_reference_content(
        payload.keyword,
        payload.geo,
        competitors=[str(url) for url in payload.competitors],
    )
    trends = await fetch_keyword_trends(payload.keyword, payload.geo)

    opportunity_score = 0.65 + min(len(trends), 5) * 0.03
    geo_upper = payload.geo.upper()
    action_items = [
        "Bangun pilar konten baru yang mengelompokkan kata kunci informasional dan transaksional.",
        "Perkuat bukti otoritas dengan data lokal dan kutipan ahli.",
        "Optimalkan internal link menuju halaman kategori prioritas di sitemap.",
    ]

    insights = [
        GapInsight(
            title="Peluang Topical Authority",
            summary="Hanya sebagian kecil kompetitor yang memiliki hub konten mendalam dengan FAQ dan studi kasus lokal.",
            difficulty="medium",
            opportunity_score=round(min(opportunity_score, 0.92), 2),
            action_items=action_items,
            evidence_links=[ref.url for ref in references[:2]],
        ),
        GapInsight(
            title="Schema & UX Improvisasi",
            summary="Skema FAQ dan HowTo jarang ditemui, padahal volume pertanyaan meningkat dari Google Trends.",
            difficulty="low",
            opportunity_score=0.74,
            action_items=[
                "Tambahkan schema FAQ di artikel edukatif yang menargetkan kata kunci turunan.",
                "Lengkapi elemen UX seperti tabel harga dan compare chart untuk meningkatkan dwell time.",
            ],
            evidence_links=[ref.url for ref in references[2:4]],
        ),
        GapInsight(
            title="Konten Lokal Kurang Personal",
            summary="Konten pesaing belum menyoroti kebiasaan dan budaya lokal sehingga kurang relevan bagi audiens target.",
            difficulty="medium",
            opportunity_score=0.68,
            action_items=[
                f"Masukkan studi kasus lokal yang menampilkan data perilaku pengguna {geo_upper}.",
                "Libatkan narasumber lokal untuk menambah kredibilitas.",
            ],
            evidence_links=[ref.url for ref in references[-2:]],
        ),
    ]

    response = ContentGapResponse(
        keyword=payload.keyword,
        insights=insights,
        references=references,
        trend_topics=trends,
        summary=(
            f"Kompetisi {payload.keyword} masih longgar untuk konten berformat pilar dengan bukti lokal. "
            "Prioritaskan integrasi schema dan pengalaman nyata untuk menutup kesenjangan."
        ),
        suggested_headlines=[
            f"{payload.keyword.title()} Roadmap {payload.geo.upper()}",
            f"Panduan Lokal {payload.keyword.lower()} dengan Studi Kasus Terkini",
        ],
    )

    await log_gap_job(payload, response, trends=trends)
    return response
