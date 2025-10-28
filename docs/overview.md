# AIO Suite Overview

## High-Level Architecture

```
+---------------------+        +----------------------+        +----------------------+
|  WordPress (WP-CLI) | <----> |  Content Intelligence | <----> |  External Providers  |
|  Plugin (aio-seo)   |  HTTP  |  FastAPI (Python)     |  APIs  |  SERP / LLM / Images  |
+---------------------+        +----------------------+        +----------------------+
         |                                 |
         v                                 v
+---------------------+        +----------------------+
|   Social Hub (Node) | <----> |   Social Platforms   |
|   Caption & Publish |  HTTP  |   X / FB / IG etc.   |
+---------------------+        +----------------------+
```

* **WordPress Plugin (`apps/wp-plugin/aio-seo`)** – provides the editorial UI, settings storage, and REST bridges for requesting content and publishing timelines.
* **Content Intelligence (`apps/content-intel`)** – FastAPI microservice responsible for SERP aggregation, LLM orchestration, image sourcing, validation, and history logging.
* **Social Hub (`apps/social-hub`)** – Node/Express service that generates social captions and delivers posts to multiple networks with provider-specific API calls.
* **Infra** – Docker Compose for local WordPress stacks, nginx reverse proxy, and deployment tooling for Cloud Run.

## Persistence & Data Flow

The Content Intelligence service persists generation metadata using SQLite (or the configured SQLAlchemy backend). Key tables:

| Table                | Purpose                                                |
|----------------------|--------------------------------------------------------|
| `aio_articles`       | Generated article HTML, metadata, readability scores   |
| `aio_refs`           | SERP references linked to generation history           |
| `aio_logs`           | Activity/audit logs (generation, RSS rewrites)         |
| `aio_api_keys`       | Encrypted provider API keys (optional)                 |

WordPress settings are stored via the standard `wp_options` API (with optional encryption) and replicated to multisite child installations as needed. Social schedules are pushed to WordPress via the `/wp-json/aio/v1/social` ingestion endpoint when a post is published through the Social Hub.

## Service Responsibilities

### Content Intelligence
- Gather references from Google/Bing/Serper plus user-provided URLs
- Build trend-aware prompts and iterate across multiple LLM providers
- Validate minimum quality bars (word count, heading depth, readability, duplication)
- Persist history and expose APIs: `/api/content/generate_article`, `/api/content/generate_from_rss`, `/api/analysis/content_gap`

### Social Hub
- Generate tone-aware social captions (OpenAI or local fallback)
- Post to X, Facebook, Instagram, Threads (placeholder) with per-platform reporting
- Serve `/publish` for posting jobs and `/health` for monitoring

### WordPress Plugin
- Admin UI for generation, preview, history, and settings management
- Secure REST bridge with nonce and capability checks
- Optional multisite controls and encrypted secret storage

## Environment Variables

| Service            | Key Variables (examples)                                                                                  |
|--------------------|-------------------------------------------------------------------------------------------------------------|
| Content Intelligence | `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `DATABASE_URL`, `GOOGLE_SEARCH_API_KEY`, `BING_SEARCH_API_KEY`, `AI_IMAGE_ENDPOINT` |
| Social Hub         | `OPENAI_API_KEY`, `SOCIAL_DEFAULT_TONE`, `SOCIAL_HTTP_TIMEOUT`, `X_BEARER_TOKEN`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`, `THREADS_ACCESS_TOKEN` |
| WordPress Plugin   | `AIO_SUITE_ENC_KEY`, `AIO_SUITE_PROVIDER_KEY`, `CONTENT_INTEL_URL`, `SOCIAL_HUB_URL`, `AIO_SUITE_SOCIAL_TOKEN` |

## Local Development Workflow

1. **Launch WordPress stack**
   ```bash
   docker compose -f infra/docker/wp-compose.yml up -d
   ```
   WordPress will be available on `http://localhost:8081` with Redis and MariaDB persistent volumes. The plugin is mounted read-only.

2. **Run backend services locally**
   ```bash
   # Content Intelligence
   cd apps/content-intel
   uvicorn app.main:app --reload

   # Social Hub
   cd apps/social-hub
   npm install
   npm start
   ```

3. **Reverse proxy (optional)** – Use the provided `infra/docker/nginx.conf` within an nginx container to front the services with shared headers and gzip.

## Deployment (Cloud Run)

`infra/gcp/deploy.sh` builds and pushes the Content Intelligence and Social Hub images, then deploys them to Cloud Run. Required variables:

- `PROJECT_ID` (GCP project)
- Optional: `REGION`, `CONTENT_SERVICE`, `SOCIAL_SERVICE`, `TAG`
- Secrets referenced in the script must exist (e.g., `openai_key` secret for both services)

After execution the script prints the Cloud Run URLs for each service.

## API Examples

### Generate Article
```bash
curl -X POST "$CONTENT_INTEL_URL/api/content/generate_article" \
  -H 'Content-Type: application/json' \
  -d '{"keyword": "bali travel", "geo": "ID", "tone": "friendly", "include_images": true}'
```

### Publish to Social Networks
```bash
curl -X POST "$SOCIAL_HUB_URL/publish" \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Bali Travel Guide",
        "url": "https://example.com/bali",
        "article_html": "<p>Liburan seru di Bali.</p>",
        "platforms": ["x", "facebook"],
        "tone": "casual"
      }'
```
