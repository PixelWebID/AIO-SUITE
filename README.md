# AIO Suite

AIO Suite is a multi-app platform that blends WordPress editorial tooling, AI-assisted
content creation, and social media distribution. The monorepo is organised as follows:

```
aio-suite/
  apps/
    wp-plugin/
      aio-seo/
        aio-seo.php          # WordPress plugin bootstrap & REST handlers
        src/                 # Admin dashboards (modular ES scripts)
        languages/           # Localisation assets
    content-intel/
      app/                   # FastAPI microservice for content intelligence
    social-hub/
      routes/ + services/    # Express routing + social distribution layer
  infra/
    docker/                  # Local docker-compose + nginx
    gcp/                     # Cloud Run deployment scripts
  docs/
    overview.md              # Architecture guide
  .github/workflows/
    ci.yml                   # Unified lint/build/test pipeline
```

Each service now ships with production-ready functionality: multi-provider LLM routing,
Google Trends enrichment, RSS rewriting, duplicate detection (SimHash + checksums),
internal link discovery (sitemap parsing), WordPress settings encryption, and omnichannel
social scheduling.

## Services

### Content Intelligence API (FastAPI)

Environment-driven configuration lives in `apps/content-intel/app/config.py`. Key features
include reference aggregation (Google/Bing/Serper/custom URLs), LLM brief orchestration with
deterministic fallbacks, SEO/E-E-A-T validation, image sourcing (Pexels/Pixabay/AI), Google
Trends pulls, and activity/history persistence via SQLite.

Example usage:

```bash
curl -X POST "http://localhost:8000/api/content/generate_article" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "wisata kuliner bandung",
    "geo": "ID",
    "tone": "friendly",
    "min_words": 850,
    "include_images": true,
    "sitemap_url": "https://your-site.com/sitemap.xml",
    "secondary_keywords": ["cafe instagramable", "jajanan malam"]
  }'
```

```bash
curl "http://localhost:8000/api/content/history?limit=5"
```

```bash
curl -X POST "http://localhost:8000/api/content/generate_from_rss" \
  -H "Content-Type: application/json" \
  -d '{
    "feed_url": "https://news.google.com/rss/search?q=bandung",
    "geo": "ID",
    "tone": "formal"
  }'
```

### Social Hub (Express)

`apps/social-hub` exposes caption generation, multi-network delivery (X, Facebook, Instagram,
Threads fallback), scheduling, multi-site propagation, and history storage. Configuration is
provided via `.env` or environment variables (see `config.js`).

Sample publish call:

```bash
curl -X POST "http://localhost:8080/api/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Panduan Liburan Bandung",
    "url": "https://your-site.com/panduan-liburan-bandung",
    "summary": "Agenda 3 hari penuh kuliner dan hidden gem.",
    "networks": ["x", "facebook"],
    "tone": "casual",
    "scheduleAt": "2025-10-30T09:00:00+07:00"
  }'
```

```bash
curl "http://localhost:8080/api/publish/scheduled"
```

### WordPress Plugin (AIO Content Suite)

Located at `apps/wp-plugin/aio-seo`. The plugin registers encrypted settings, bridges to the
content-intel service, exposes activity/history lookups, ingests social webhooks using a shared
token, and ships a modern admin UI (auto/manual editor, live preview, keyword highlights,
history explorer).

REST entry points inside WordPress (`wp-json/aio/v1/...`):

```bash
# Fetch settings (requires authenticated WP nonce)
curl -H "X-WP-Nonce: <nonce>" "https://your-site.com/wp-json/aio/v1/settings"

# Trigger article generation via WordPress bridge
curl -X POST "https://your-site.com/wp-json/aio/v1/generate" \
  -H "Content-Type: application/json" \
  -H "X-WP-Nonce: <nonce>" \
  -d '{
    "keyword": "strategi marketing umkm",
    "geo": "ID",
    "tone": "authoritative",
    "include_images": true
  }'

# Retrieve activity log
curl -H "X-WP-Nonce: <nonce>" "https://your-site.com/wp-json/aio/v1/activity?limit=10"
```

To ingest scheduled social posts (used by the Social Hub), send:

```bash
curl -X POST "https://your-site.com/wp-json/aio/v1/social" \
  -H "Content-Type: application/json" \
  -H "X-AIO-Token: $AIO_SUITE_SOCIAL_TOKEN" \
  -d '{
    "title": "Thread Instagram",
    "caption": "Highlight destinasi kuliner terbaru.",
    "url": "https://your-site.com/panduan-kuliner"
  }'
```

## Local Development

* **Content Intelligence** – `cd apps/content-intel && uvicorn app.main:app --reload`
* **Social Hub** – `cd apps/social-hub && npm install && npm run dev`
* **WordPress Plugin** – symlink `apps/wp-plugin/aio-seo` into `wp-content/plugins` and activate
  from the WP admin.

The `/infra/docker` directory provides compose files for running all services behind nginx if you
prefer a containerised workflow.
