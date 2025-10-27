
"""LLM orchestration helpers used for article generation and rewriting."""

from __future__ import annotations

import asyncio
import json
import textwrap
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import httpx

from ..config import settings
from ..models.schemas import ReferenceArticle


class AIProviderError(RuntimeError):
    """Raised when a provider request cannot be fulfilled."""


@dataclass
class ProviderAdapter:
    name: str
    enabled: bool
    base_url: Optional[str] = None


class AIClient:
    """High level interface that routes prompts across multiple providers."""

    def __init__(self, order: Iterable[str]) -> None:
        unique_order = []
        for provider in order:
            if provider not in unique_order:
                unique_order.append(provider)
        if not unique_order:
            unique_order = ["openai", "deepseek", "openrouter", "gemini", "llama"]
        self.provider_order = unique_order

    async def generate_article(
        self,
        references: List[ReferenceArticle],
        keyword: str,
        tone: str,
        geo: str,
        min_words: int,
        max_words: int,
        trends: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """Generate an article body and rough outline.

        The client attempts providers in order. When no providers succeed, a deterministic
        rule-based generator is used to unblock the workflow.
        """

        prompt = self._build_article_prompt(references, keyword, tone, geo, min_words, max_words, trends)
        for provider in self.provider_order:
            try:
                response = await self._invoke_completion(provider, prompt)
                if response:
                    return self._parse_article_response(response, references, keyword, tone, geo, trends)
            except AIProviderError:
                continue

        return self._fallback_article(references, keyword, tone, geo, min_words, max_words, trends)

    async def rewrite(self, text: str, tone: str) -> str:
        """Rewrite arbitrary text into a fresh paraphrased version."""

        prompt = textwrap.dedent(
            f"""
            Rewrite the following article into fresh prose. Keep factual accuracy, use a {tone} tone,
            avoid plagiarism, and preserve HTML structure when present. Respond with HTML only.
            ---
            {text}
            """
        ).strip()

        for provider in self.provider_order:
            try:
                response = await self._invoke_completion(provider, prompt)
                if response:
                    return response.strip()
            except AIProviderError:
                continue

        return self._fallback_rewrite(text, tone)

    async def _invoke_completion(self, provider: str, prompt: str) -> str:
        """Execute a chat completion request against the selected provider."""

        adapter = self._resolve_adapter(provider)
        if not adapter.enabled:
            raise AIProviderError(f"Provider {provider} disabled or missing credentials")

        try:
            if adapter.name == "openai":
                payload = {
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful editorial assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": settings.llm_temperature,
                }
                headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(adapter.base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data['choices'][0]['message']['content']

            if adapter.name == "deepseek":
                payload = {
                    "model": settings.deepseek_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful editorial assistant."},
                        {"role": "user", "content": prompt},
                    ],
                }
                headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(adapter.base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data['choices'][0]['message']['content']

            if adapter.name == "openrouter":
                payload = {
                    "model": settings.openrouter_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful editorial assistant."},
                        {"role": "user", "content": prompt},
                    ],
                }
                headers = {
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://pixelwebid.ai/",
                    "X-Title": "AIO Suite",
                }
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(adapter.base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data['choices'][0]['message']['content']

            if adapter.name == "gemini":
                endpoint = f"{adapter.base_url}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": settings.llm_temperature},
                }
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data['candidates'][0]['content']['parts'][0]['text']

            if adapter.name == "llama":
                headers = {}
                if settings.openrouter_api_key:
                    headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
                payload = {"model": settings.llama_model, "prompt": prompt, "temperature": settings.llm_temperature}
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(settings.llama_endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data.get('content') or data.get('text', '')

        except Exception as exc:  # pragma: no cover - upstream failures are expected
            raise AIProviderError(str(exc)) from exc

        raise AIProviderError(f"Provider {provider} is not configured")

    def _resolve_adapter(self, provider: str) -> ProviderAdapter:
        provider = provider.lower()
        if provider == "openai":
            return ProviderAdapter("openai", bool(settings.openai_api_key), "https://api.openai.com/v1/chat/completions")
        if provider == "deepseek":
            return ProviderAdapter("deepseek", bool(settings.deepseek_api_key), "https://api.deepseek.com/chat/completions")
        if provider == "openrouter":
            return ProviderAdapter("openrouter", bool(settings.openrouter_api_key), "https://openrouter.ai/api/v1/chat/completions")
        if provider == "gemini":
            return ProviderAdapter("gemini", bool(settings.gemini_api_key), "https://generativelanguage.googleapis.com/v1beta/models")
        if provider == "llama":
            return ProviderAdapter("llama", bool(settings.llama_endpoint), settings.llama_endpoint)
        return ProviderAdapter(provider, False)

    def _build_article_prompt(
        self,
        references: List[ReferenceArticle],
        keyword: str,
        tone: str,
        geo: str,
        min_words: int,
        max_words: int,
        trends: Optional[List[str]],
    ) -> str:
        ref_lines = []
        for ref in references:
            outline = "; ".join(ref.outline[:5]) if ref.outline else "No outline captured"
            ref_lines.append(f"- {ref.title} ({ref.domain}): {ref.snippet}\n  Outline: {outline}")
        trend_text = "\n".join(trends or []) or "None"
        return textwrap.dedent(
            f"""
            Compose a long-form article in HTML. Requirements:
            - Primary keyword: {keyword}
            - Tone: {tone}
            - Geo focus: {geo}
            - Length between {min_words} and {max_words} words
            - Include experience, expertise, authority, trust elements
            - Use clear H2/H3 hierarchy (>=3 each) and actionable summaries
            - Integrate the provided references with citations and add call-to-action
            - Return JSON with keys: title, description, sections (list with heading and body HTML),
              conclusion, faq (list of question/answer), keywords (list), tags (list), social_summary.
            References:
            {chr(10).join(ref_lines)}
            Trend topics:
            {trend_text}
            """
        ).strip()

    def _parse_article_response(
        self,
        response: str,
        references: List[ReferenceArticle],
        keyword: str,
        tone: str,
        geo: str,
        trends: Optional[List[str]],
    ) -> Dict[str, object]:
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            return self._fallback_article(references, keyword, tone, geo, 700, 1600, trends)

        sections_html = []
        for section in payload.get('sections', []):
            heading = section.get('heading', 'Section')
            body = section.get('body', '')
            sections_html.append(f"<h2>{heading}</h2>{body}")

        faq_html = []
        for faq in payload.get('faq', []):
            faq_html.append(f"<h3>{faq.get('question')}</h3><p>{faq.get('answer')}</p>")

        body_html = "".join(sections_html) + "".join(faq_html)
        if payload.get('conclusion'):
            body_html += f"<h2>Kesimpulan</h2><p>{payload['conclusion']}</p>"

        html = f"<h1>{payload.get('title', keyword.title())}</h1><p>{payload.get('description', '')}</p>{body_html}"

        return {
            "html": html,
            "title": payload.get('title', keyword.title()),
            "description": payload.get('description', ''),
            "keywords": payload.get('keywords', [keyword]),
            "tags": payload.get('tags', payload.get('keywords', [keyword])),
            "social_summary": payload.get('social_summary', ''),
        }

    def _fallback_article(
        self,
        references: List[ReferenceArticle],
        keyword: str,
        tone: str,
        geo: str,
        min_words: int,
        max_words: int,
        trends: Optional[List[str]],
    ) -> Dict[str, object]:
        paragraphs: List[str] = []
        for ref in references[:4]:
            outline = ref.outline[:3] or [f"Insight dari {ref.domain}"]
            body = " ".join(ref.snippet.split()[:80])
            paragraphs.append(
                f"<h2>{outline[0]}</h2><p>{body}. Artikel ini mengadaptasi temuan tersebut untuk audiens {geo.upper()} dengan tone {tone}.</p>"
            )
            if len(outline) > 1:
                paragraphs.append(
                    "".join(
                        f"<h3>{heading}</h3><p>Penjelasan lanjutan mengenai {heading.lower()} berdasarkan referensi {ref.domain}.</p>"
                        for heading in outline[1:]
                    )
                )

        trends_html = "".join(
            f"<li>{topic}</li>" for topic in (trends or [])
        ) or "<li>Tidak ada tren tambahan.</li>"

        html = (
            f"<h1>{keyword.title()} Strategi Terbaru</h1>"
            f"<p>Artikel ini merangkum wawasan praktis tentang {keyword.lower()} untuk pasar {geo.upper()} dalam tone {tone}.</p>"
            + "".join(paragraphs)
            + f"<h2>Topik Tren</h2><ul>{trends_html}</ul>"
            + "<h2>Rencana Aksi</h2><p>Langkah prioritas: audit konten, optimasi on-page, dan aktivasi kampanye multiplatform.</p>"
        )

        return {
            "html": html,
            "title": f"{keyword.title()} Strategy Guide",
            "description": f"Panduan praktis {keyword.lower()} dengan fokus pasar {geo.upper()}.",
            "keywords": [keyword] + (trends or []),
            "tags": [keyword, geo.lower()],
            "social_summary": f"{keyword.title()} lagi trending! Kami susun insight dan checklist terbaru untuk pasar {geo.upper()}.",
        }

    def _fallback_rewrite(self, text: str, tone: str) -> str:
        snippets = [segment.strip() for segment in text.split('\n') if segment.strip()]
        rewritten = []
        for idx, snippet in enumerate(snippets, start=1):
            rewritten.append(
                f"<p>{snippet} (disajikan ulang dengan tone {tone}, paragraf #{idx}).</p>"
            )
        return "".join(rewritten)
