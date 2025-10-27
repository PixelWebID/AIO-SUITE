"""AI provider orchestration and deterministic fallback authoring."""

from __future__ import annotations

import asyncio
import html
import json
import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

from ..config import settings
from ..models.schemas import (
    ArticleMeta,
    ArticleMetrics,
    ArticleRequest,
    LinkSuggestion,
    ReferenceArticle,
)
from ..utils.db import fetch_recent_simhashes
from ..utils.duplicate import compute_signatures, detect_similar_overlaps
from ..utils.notifications import notify_failure
from ..utils.readability import score_readability
from .linking import suggest_internal_links


LLM_TIMEOUT = settings.llm_timeout_seconds
WORD_TARGET_BUFFER = 80
MIN_FLESCH = 55.0
MIN_HEADING_THRESHOLD = 3


@dataclass
class ArticleBrief:
    title: str
    introduction: str
    sections: List[Dict[str, object]]
    faq: List[Dict[str, str]]
    call_to_action: str
    social_summary: str


PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
}


def _provider_available(provider: str) -> bool:
    """Check whether the provider credentials are present."""

    mapping = {
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
        "openrouter": settings.openrouter_api_key,
        "gemini": settings.gemini_api_key,
        "llama": settings.llama_endpoint,
    }
    return bool(mapping.get(provider))


def _summarise_references(references: Sequence[ReferenceArticle]) -> str:
    """Return a compact textual summary of references."""

    lines = []
    for ref in references[:7]:
        snippet = ref.snippet[:180]
        lines.append(f"- {ref.title} ({ref.domain}): {snippet}")
    return "\n".join(lines)


def _build_brief_prompt(payload: ArticleRequest, references: Sequence[ReferenceArticle], trends: Sequence[str]) -> str:
    """Construct a system prompt instructing the LLM to output JSON."""

    secondary = ", ".join(payload.secondary_keywords) if payload.secondary_keywords else "None"
    trend_lines = "\n".join(f"- {trend}" for trend in trends) or "None"
    return (
        "You are an editor creating an article outline that enforces SEO best practices.\n"
        "Return a compact JSON object with the keys title, introduction, sections, faq,"
        " cta, and social_summary.\n"
        "sections should be an array of objects with heading, subheading, key_points (array).\n"
        "Each FAQ entry must contain question and answer.\n"
        "The introduction should be 2 sentences highlighting experience/expertise.\n"
        "Social summary must be 2 short sentences for social media.\n"
        "Context:\n"
        f"Primary keyword: {payload.keyword}\n"
        f"Secondary keywords: {secondary}\n"
        f"Geo focus: {payload.geo}\n"
        f"Tone: {payload.tone}\n"
        f"Additional context: {payload.additional_context or 'None'}\n"
        f"Trends:\n{trend_lines}\n"
        f"References:\n{_summarise_references(references)}\n"
    )


def _parse_llm_json(raw: str) -> Optional[ArticleBrief]:
    """Parse a JSON payload from an LLM response."""

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    sections = payload.get("sections") or []
    faq = payload.get("faq") or []
    introduction = payload.get("introduction") or ""

    if not isinstance(sections, list) or len(sections) < 3:
        return None
    if not isinstance(faq, list):
        faq = []

    return ArticleBrief(
        title=payload.get("title") or "",
        introduction=introduction,
        sections=sections,
        faq=faq,
        call_to_action=payload.get("cta") or payload.get("call_to_action") or "",
        social_summary=payload.get("social_summary") or "",
    )


class LLMOrchestrator:
    """Attempt to collect an article brief from multiple LLM providers."""

    def __init__(self, providers: Sequence[str]):
        self.providers = providers
        self.provider_used: Optional[str] = None

    async def _call_chat_completion(
        self,
        endpoint: str,
        headers: Dict[str, str],
        payload: Dict[str, object],
    ) -> Optional[str]:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            return message.get("content")

    async def _invoke_provider(self, provider: str, prompt: str) -> Optional[str]:
        """Dispatch prompt to the active provider."""

        if provider == "openai":
            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            model = settings.openai_model
            endpoint = settings.openai_base_url or PROVIDER_ENDPOINTS["openai"]
            payload = {
                "model": model,
                "temperature": settings.llm_temperature,
                "messages": [{"role": "system", "content": prompt}],
            }
            return await self._call_chat_completion(endpoint, headers, payload)

        if provider == "deepseek":
            headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
            payload = {
                "model": settings.deepseek_model,
                "temperature": settings.llm_temperature,
                "messages": [{"role": "system", "content": prompt}],
            }
            return await self._call_chat_completion(PROVIDER_ENDPOINTS["deepseek"], headers, payload)

        if provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://pixelwebid.ai/",
                "X-Title": "AIO Suite",
            }
            payload = {
                "model": settings.openrouter_model,
                "messages": [{"role": "system", "content": prompt}],
                "temperature": settings.llm_temperature,
            }
            return await self._call_chat_completion(PROVIDER_ENDPOINTS["openrouter"], headers, payload)

        if provider == "gemini":
            endpoint = (
                f"{PROVIDER_ENDPOINTS['gemini']}/{settings.gemini_model}:generateContent"
                f"?key={settings.gemini_api_key}"
            )
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": settings.llm_temperature},
            }
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                candidates = response.json().get("candidates") or []
                if not candidates:
                    return None
                return candidates[0]["content"]["parts"][0]["text"]

        if provider == "llama":
            headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"} if settings.openrouter_api_key else {}
            body = {
                "model": settings.llama_model,
                "prompt": prompt,
                "temperature": settings.llm_temperature,
            }
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                response = await client.post(settings.llama_endpoint, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("content") or data.get("text")

        return None

    async def generate_brief(
        self,
        payload: ArticleRequest,
        references: Sequence[ReferenceArticle],
        trends: Sequence[str],
    ) -> Optional[ArticleBrief]:
        """Try to produce an outline using configured providers."""

        prompt = _build_brief_prompt(payload, references, trends)
        for provider in self.providers:
            if not _provider_available(provider):
                continue
            try:
                raw = await self._invoke_provider(provider, prompt)
                if not raw:
                    continue
                brief = _parse_llm_json(raw)
                if brief:
                    self.provider_used = provider
                    return brief
            except Exception as exc:  # pragma: no cover - depends on network
                await notify_failure(
                    {
                        "keyword": payload.keyword,
                        "provider": provider,
                        "error": str(exc),
                        "stage": "llm_brief",
                    }
                )
                continue
        return None


def _create_default_brief(
    payload: ArticleRequest,
    references: Sequence[ReferenceArticle],
    trends: Sequence[str],
) -> ArticleBrief:
    """Construct a deterministic outline ensuring coverage for key sections."""

    primary = payload.keyword.title()
    intro = (
        f"{primary} terus berkembang di pasar {payload.geo.upper()}, dan pelaku industri membutuhkan panduan yang "
        f"menggabungkan pengalaman lapangan serta verifikasi data. Artikel ini memadukan analisis kompetitor "
        f"dan temuan terbaru untuk menghadirkan strategi yang bisa segera dijalankan."
    )

    sections = [
        {
            "heading": f"Panorama {primary} Saat Ini",
            "subheading": "Mengukur perilaku audiens dan pendorong permintaan",
            "key_points": [
                "Apa yang diungkapkan referensi utama mengenai tren volume pencarian.",
                "Bagaimana konsumen di wilayah target merespon penawaran terbaru.",
                "Perubahan regulasi atau budaya yang wajib diantisipasi dalam konten.",
            ],
        },
        {
            "heading": "Kerangka E-E-A-T untuk {0}".format(primary),
            "subheading": "Menggabungkan pengalaman praktis dan bukti otoritatif",
            "key_points": [
                "Sisipkan cerita pengalaman nyata (experience) dari praktisi lokal.",
                "Cantumkan referensi otoritatif yang menjamin akurasi klaim.",
                "Tunjukkan transparansi proses dan ajakan untuk memverifikasi data.",
            ],
        },
        {
            "heading": "Strategi Konten & SEO Mendalam",
            "subheading": "Memaksimalkan kata kunci turunan dan struktur on-page",
            "key_points": [
                "Gunakan kata kunci turunan dari Google Trends sebagai sub-topik.",
                "Bangun internal link untuk mendukung topical authority.",
                "Optimalkan heading dan meta agar CTR meningkat.",
            ],
        },
        {
            "heading": f"Adaptasi Lokal di {payload.geo.upper()}",
            "subheading": "Rekomendasi pemasaran berbasis geo dan budaya",
            "key_points": [
                "Sesuaikan contoh kasus dengan perilaku audiens daerah.",
                "Masukkan data harga, kebiasaan, atau musim lokal yang relevan.",
                "Kolaborasikan dengan figur lokal untuk memperkuat kepercayaan.",
            ],
        },
        {
            "heading": "Rencana Eksekusi 30-60-90 Hari",
            "subheading": "Langkah bertahap dari audit hingga distribusi konten",
            "key_points": [
                "Audit konten lama dan ukur kesenjangan terhadap kompetitor.",
                "Produksi konten baru dengan jadwal kampanye lintas kanal.",
                "Bangun sistem evaluasi berkala menggunakan KPI prioritas.",
            ],
        },
    ]

    faq = [
        {
            "question": f"Apa indikator utama keberhasilan strategi {primary.lower()}?",
            "answer": "Gabungkan pertumbuhan trafik organik, metrik engagement, dan kontribusi terhadap pipeline penjualan.",
        },
        {
            "question": f"Bagaimana cara menjaga konten {primary.lower()} tetap relevan?",
            "answer": "Jadwalkan review berkala untuk memperbarui data, memperluas studi kasus lokal, dan menguji format baru.",
        },
    ]

    if trends:
        faq.append(
            {
                "question": "Bagaimana memanfaatkan tren terbaru?",
                "answer": f"Sisipkan {trends[0]} sebagai kampanye tematik dan gunakan konten interaktif untuk menjelaskan manfaatnya.",
            }
        )

    social_summary = (
        f"{primary} lagi panas dibicarakan! Kami merangkum temuan terbaru, checklist praktis, dan insight lokal "
        f"untuk menaikkan performa kampanye Anda."
    )

    return ArticleBrief(
        title=f"{primary}: Strategi Terbaru {datetime.utcnow().year} untuk Pasar {payload.geo.upper()}",
        introduction=intro,
        sections=sections,
        faq=faq,
        call_to_action="Siapkan audit konten mendalam dan integrasikan rekomendasi ini ke kalender editorial minggu ini.",
        social_summary=social_summary,
    )


def _render_section(
    index: int,
    section: Dict[str, object],
    references: Sequence[ReferenceArticle],
    payload: ArticleRequest,
) -> str:
    heading = html.escape(str(section.get("heading") or "Section"))
    subheading = html.escape(str(section.get("subheading") or "Subheading"))
    key_points = section.get("key_points") or []
    body_parts = []

    for point in key_points:
        sentences = str(point).rstrip(".") + "."
        body_parts.append(sentences)

    reference_snippet = ""
    if references:
        ref = references[index % len(references)]
        reference_snippet = (
            f"Mengacu pada {ref.title} dari {ref.domain}, "
            f"pendekatan ini relevan untuk audiens {payload.geo.upper()}."
        )

    paragraph = " ".join(body_parts + [reference_snippet])
    supporting_list = "".join(f"<li>{html.escape(str(point))}</li>" for point in key_points)

    return (
        f"<h2>{heading}</h2>"
        f"<p>{paragraph}</p>"
        f"<h3>{subheading}</h3>"
        f"<ul>{supporting_list}</ul>"
    )


def _render_faq(entries: Sequence[Dict[str, str]]) -> str:
    html_blocks = ["<h2>Pertanyaan Populer</h2>"]
    for entry in entries:
        question = html.escape(entry.get("question", ""))
        answer = html.escape(entry.get("answer", ""))
        html_blocks.append(f"<h3>{question}</h3><p>{answer}</p>")
    return "".join(html_blocks)


def _inject_links(
    article_html: str,
    keywords: Sequence[str],
    internal_links: Sequence[LinkSuggestion],
    external_links: Sequence[LinkSuggestion],
) -> str:
    soup = BeautifulSoup(article_html, "html.parser")
    keyword_patterns = [re.compile(rf"\b({re.escape(word)})\b", re.IGNORECASE) for word in keywords if word]

    for text_node in soup.find_all(string=True):
        parent = text_node.parent
        if parent.name in {"a", "script", "style"}:
            continue
        new_text = str(text_node)
        for pattern in keyword_patterns:
            new_text = pattern.sub(r'<mark class="aio-keyword">\1</mark>', new_text)
        if new_text != text_node:
            text_node.replace_with(BeautifulSoup(new_text, "html.parser"))

    def _apply_links(suggestions: Sequence[LinkSuggestion]) -> None:
        for suggestion in suggestions:
            anchor_pattern = re.compile(rf"\b({re.escape(suggestion.anchor)})\b", re.IGNORECASE)
            applied = False
            for text_node in soup.find_all(string=anchor_pattern):
                parent = text_node.parent
                if parent.name == "a":
                    continue
                new_html = anchor_pattern.sub(
                    rf'<a href="{suggestion.url}" rel="{"noopener" if suggestion.type == "external" else "noopener noreferrer"}">{suggestion.anchor}</a>',
                    str(text_node),
                    count=1,
                )
                text_node.replace_with(BeautifulSoup(new_html, "html.parser"))
                applied = True
                break
            if not applied:
                paragraph = soup.find("p")
                if paragraph:
                    paragraph.append(
                        BeautifulSoup(
                            f' <a href="{suggestion.url}" rel="noopener">{suggestion.anchor}</a>',
                            "html.parser",
                        )
                    )

    _apply_links(internal_links)
    _apply_links(external_links)

    return str(soup)


def _calculate_keyword_density(text: str, keywords: Sequence[str]) -> Dict[str, float]:
    word_list = re.findall(r"\b[\w-]+\b", text.lower())
    total = max(len(word_list), 1)
    density = {}
    for keyword in keywords:
        if not keyword:
            continue
        occurrences = len(re.findall(rf"\b{re.escape(keyword.lower())}\b", text.lower()))
        density[keyword] = round(occurrences / total * 100, 2)
    return density


def _compute_headings(html_text: str) -> Dict[str, int]:
    counts = {"h2": 0, "h3": 0}
    soup = BeautifulSoup(html_text, "html.parser")
    counts["h2"] = len(soup.find_all("h2"))
    counts["h3"] = len(soup.find_all("h3"))
    return counts


async def _derive_internal_links(payload: ArticleRequest) -> List[LinkSuggestion]:
    if not payload.auto_internal_linking or not payload.sitemap_url:
        return []
    return await suggest_internal_links(payload.keyword, str(payload.sitemap_url))


def _derive_external_links(references: Sequence[ReferenceArticle]) -> List[LinkSuggestion]:
    suggestions = []
    for reference in references[:5]:
        suggestions.append(
            LinkSuggestion(
                type="external",
                anchor=reference.title.split(" | ")[0][:60],
                url=reference.url,
                rationale=f"Referensi sumber {reference.domain}",
                relevance=min(0.95, max(0.4, reference.relevance or 0.7)),
            )
        )
    return suggestions


def _build_meta(
    payload: ArticleRequest,
    brief: ArticleBrief,
    internal_links: Sequence[LinkSuggestion],
    external_links: Sequence[LinkSuggestion],
    word_count: int,
    social_summary: str,
) -> ArticleMeta:
    keywords = [payload.keyword] + payload.secondary_keywords
    trends_slug = slugify("-".join(keywords[:3]))[:40]
    slug = slugify(brief.title) or trends_slug or slugify(payload.keyword)

    description = brief.introduction[:155]
    categories = ["Content Strategy", payload.keyword.title()]
    tags = list(dict.fromkeys(keywords))

    return ArticleMeta(
        title=brief.title,
        description=description,
        slug=slug,
        keywords=keywords,
        tags=tags,
        categories=categories,
        canonical_url=str(payload.site_url) if payload.site_url else None,
        internal_links=list(internal_links),
        external_links=list(external_links),
        reading_time_minutes=round(word_count / 200, 2),
        geo_profile=payload.geo,
        language=payload.target_language,
        publish_mode="auto" if payload.auto_publish else "manual",
        scheduled_at=payload.schedule_at,
        social_summary=social_summary if payload.include_social_summary else None,
    )


async def generate_article_draft(
    payload: ArticleRequest,
    references: List[ReferenceArticle],
    *,
    trends: Optional[List[str]] = None,
) -> Dict[str, object]:
    """Generate a structured article draft combining AI output with contextual hints."""

    orchestrator = LLMOrchestrator(payload.llm_provider_priority)
    brief = await orchestrator.generate_brief(payload, references, trends or [])
    if not brief:
        brief = _create_default_brief(payload, references, trends or [])
        provider_used = "rule_based"
    else:
        provider_used = orchestrator.provider_used or "unknown"

    internal_links = await _derive_internal_links(payload)
    external_links = _derive_external_links(references)

    keywords = [payload.keyword] + payload.secondary_keywords + (trends or [])
    keywords = [kw for kw in keywords if kw]

    auto_regenerations = 0
    article_html = ""
    metrics = None

    for attempt in range(3):
        sections_html = "".join(
            _render_section(idx, section, references, payload)
            for idx, section in enumerate(brief.sections)
        )
        faq_html = _render_faq(brief.faq)

        geo_note = (
            f"<h2>Catatan Khusus {payload.geo.upper()}</h2>"
            f"<p>Konten ini menekankan kebutuhan audiens di {payload.geo.upper()} dengan mempertimbangkan bahasa, "
            f"kebiasaan konsumsi, dan regulasi terbaru yang mempengaruhi {payload.keyword.lower()}.</p>"
        )

        sources_list = "".join(
            f'<li><a href="{ref.url}" rel="noopener">{html.escape(ref.title)}</a> — {html.escape(ref.snippet[:140])}</li>'
            for ref in references
        )

        article_html = (
            f"<h1>{html.escape(brief.title)}</h1>"
            f"<p>{html.escape(brief.introduction)}</p>"
            f"{sections_html}"
            f"{geo_note}"
            f"{faq_html}"
            f"<h2>Panduan Tindakan</h2><p>{html.escape(brief.call_to_action)}</p>"
            f"<h2>Referensi Terkurasi</h2><ul>{sources_list}</ul>"
        )

        article_html = _inject_links(article_html, keywords[:6], internal_links, external_links)

        readability = score_readability(article_html)
        word_count = int(readability["word_count"])
        headings = _compute_headings(article_html)
        density = _calculate_keyword_density(article_html, keywords[:8])

        signatures = compute_signatures(article_html)
        prior_simhashes = await fetch_recent_simhashes()
        overlaps = detect_similar_overlaps(
            signatures["simhash"],
            [(entry["history_id"], entry["simhash"]) for entry in prior_simhashes if entry.get("simhash")],
        )

        metrics = ArticleMetrics(
            word_count=word_count,
            heading_counts=headings,
            keyword_density=density,
            flesch_reading_ease=float(readability["flesch_reading_ease"]),
            fk_grade_level=float(readability["fk_grade_level"]),
            checksum_sha1=signatures["sha1"],
            checksum_sha256=signatures["sha256"],
            simhash=signatures["simhash"],
            duplicate_matches=overlaps,
            auto_regenerations=auto_regenerations,
        )

        meets_word = word_count >= payload.min_words
        meets_heading = headings["h2"] >= MIN_HEADING_THRESHOLD and headings["h3"] >= MIN_HEADING_THRESHOLD
        meets_flesch = metrics.flesch_reading_ease >= MIN_FLESCH

        if meets_word and meets_heading and meets_flesch:
            break

        auto_regenerations += 1
        if auto_regenerations > 2:
            break

        # Augment brief for regeneration attempts with additional prompt details.
        expansion = (
            "Tambahkan contoh praktis tambahan, bagi kalimat panjang menjadi dua kalimat yang lebih pendek, "
            "dan sisipkan wawasan baru dari referensi untuk meningkatkan nilai Flesch."
        )
        brief.sections.append(
            {
                "heading": "Insight Tambahan untuk Memenuhi Kelayakan Publikasi",
                "subheading": "Penyesuaian hasil regenerasi",
                "key_points": [expansion],
            }
        )

    if metrics is None:
        raise RuntimeError("Gagal menghasilkan artikel dengan metrik yang valid.")

    meta = _build_meta(payload, brief, internal_links, external_links, metrics.word_count, brief.social_summary)

    warnings: List[str] = []
    if metrics.flesch_reading_ease < MIN_FLESCH:
        warnings.append(f"Flesch reading ease {metrics.flesch_reading_ease} di bawah target {MIN_FLESCH}.")
    if metrics.heading_counts["h2"] < MIN_HEADING_THRESHOLD or metrics.heading_counts["h3"] < MIN_HEADING_THRESHOLD:
        warnings.append("Struktur heading perlu ditinjau ulang (minimal 3 H2 dan 3 H3).")
    if metrics.duplicate_matches:
        warnings.append(f"Potensi duplikasi terdeteksi: {', '.join(metrics.duplicate_matches)}.")

    if provider_used == "rule_based":
        warnings.append("Menggunakan penulis deterministik internal karena provider LLM tidak tersedia.")

    return {
        "article_html": article_html,
        "meta": meta,
        "metrics": metrics.dict(),
        "warnings": warnings,
        "provider": provider_used,
    }
