# AIO Suite

AIO Suite is a multi-app platform that blends WordPress integrations, AI-assisted
content creation, and social media distribution. The monorepo is organised as follows:

```
aio-suite/
  apps/
    wp-plugin/
      aio-seo/
        aio-seo.php          # WordPress plugin bootstrap
        src/                 # Admin dashboards (modular ES scripts)
        languages/           # Localisation assets
    content-intel/
      app/                   # FastAPI microservice
    social-hub/
      routes/ + services/    # Express routing + integrations
  infra/
    docker/                  # Local docker-compose + nginx
    gcp/                     # Cloud Run deployment scripts
  docs/
    overview.md              # Architecture guide
  .github/workflows/
    ci.yml                   # Unified lint/build/test pipeline
```

Each directory ships with lightweight scaffolding so CI can run while feature
development proceeds. See `docs/overview.md` for architecture notes and follow
service-level READMEs (where available) for local development instructions.
