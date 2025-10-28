# AIO Suite

AIO Suite delivers AI-assisted content production for WordPress with automated social publishing. The monorepo bundles three services plus infrastructure tooling:

```
aio-suite/
  apps/
    wp-plugin/            # WordPress admin plugin (editor UI + REST bridge)
    content-intel/        # FastAPI microservice (SERP, LLM orchestration)
    social-hub/           # Node/Express caption & social delivery service
  infra/
    docker/               # Docker Compose stack + nginx config
    gcp/                  # Cloud Run deployment scripts
  docs/
    overview.md           # Detailed architecture notes
  .github/workflows/      # CI pipeline (pytest/jest/phpunit + Docker build)
```

## Services

### Content Intelligence (FastAPI)
- Multi-provider SERP aggregation (Google/Bing/Serper/custom URLs)
- Trend analysis via Google Trends
- LLM orchestration with automatic failover (OpenAI, DeepSeek, OpenRouter, Gemini, Llama)
- Readability + duplication guards (Flesch, FK grade, SimHash)
- Image suggestions (Pexels, Pixabay, optional AI endpoint)
- SQLite-backed history/logging out of the box (replace `DATABASE_URL` for production)

Example request:
```bash
curl -X POST "$CONTENT_INTEL_URL/api/content/generate_article" \
  -H 'Content-Type: application/json' \
  -d '{
        "keyword": "wisata kuliner bandung",
        "geo": "ID",
        "tone": "friendly",
        "include_images": true,
        "sitemap_url": "https://your-site.com/sitemap.xml"
      }'
```

### Social Hub (Node/Express)
- Tone-aware caption generation using OpenAI with character/ sentence controls
- Platform adapters for X, Facebook, Instagram (Graph API), Threads placeholder
- Structured per-platform result payloads for monitoring/retries

Example publish:
```bash
curl -X POST "$SOCIAL_HUB_URL/publish" \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Panduan Liburan Bandung",
        "url": "https://your-site.com/panduan",
        "article_html": "<p>Agenda seru di Bandung.</p>",
        "platforms": ["x", "facebook"],
        "tone": "casual"
      }'
```

### WordPress Plugin (apps/wp-plugin/aio-seo)
- React-free admin panels (vanilla JS) for Editor, Preview, History, Settings
- REST endpoints: `/wp-json/aio/v1/generate`, `/wp-json/aio/v1/history`, `/wp-json/aio/v1/social`, etc.
- Encrypted API-key storage with multisite propagation
- Configurable provider order, auto-publish toggles, and sitemap-driven internal linking

## Local Development

1. **WordPress stack**
   ```bash
   docker compose -f infra/docker/wp-compose.yml up -d
   ```
   - WordPress: `http://localhost:8081`
   - MariaDB + Redis volumes stay under Docker-managed storage
   - Plugin mounted read-only to `/wp-content/plugins/aio-seo`

2. **Backend services**
   ```bash
   # Content Intelligence
   cd apps/content-intel
   uvicorn app.main:app --reload

   # Social Hub
   cd apps/social-hub
   npm install
   npm start
   ```

3. **Reverse proxy (optional)**
   Use the supplied `infra/docker/nginx.conf` inside an nginx container to proxy `/api/content/*` and `/publish` with gzip + security headers.

## Deployment

A Cloud Run deployment helper is available:
```bash
export PROJECT_ID=your-gcp-project
export REGION=us-central1
./infra/gcp/deploy.sh
```
The script builds and pushes the Content Intelligence and Social Hub images to GCR, deploys them to Cloud Run, and prints the resulting URLs. Configure secrets (e.g., `openai_key`) in Secret Manager before running.

## Continuous Integration

`.github/workflows/ci.yml` runs on every push/PR:
- **Python** – install requirements + `pytest`
- **Node** – install dependencies + `jest`
- **PHP** – `composer install`, `phpcs`, `phpunit`
- **Docker** – build images for content-intel and social-hub
- Optional Cloud Run deploy on tags `v*` (requires `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY` secrets)

## Environment Variables

| Service | Key variables |
|---------|---------------|
| Content Intelligence | `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `DATABASE_URL`, `GOOGLE_SEARCH_API_KEY`, `BING_SEARCH_API_KEY`, `AI_IMAGE_ENDPOINT`, `AI_IMAGE_API_KEY` |
| Social Hub | `OPENAI_API_KEY`, `SOCIAL_DEFAULT_TONE`, `SOCIAL_HTTP_TIMEOUT`, `X_BEARER_TOKEN`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`, `THREADS_ACCESS_TOKEN` |
| WordPress Plugin | `CONTENT_INTEL_URL`, `SOCIAL_HUB_URL`, `AIO_SUITE_ENC_KEY`, `AIO_SUITE_PROVIDER_KEY`, `AIO_SUITE_SOCIAL_TOKEN` |

## Useful curl Commands

```bash
# Content health
curl "$CONTENT_INTEL_URL/health"

# Social hub health
curl "$SOCIAL_HUB_URL/health"

# Gap analysis
curl "$CONTENT_INTEL_URL/api/analysis/content_gap?keyword=bali%20travel&geo=ID"
```
