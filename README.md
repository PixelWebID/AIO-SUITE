# AIO Suite

This repository contains the **AIO Suite** project.  It is organised as a
monorepo containing multiple services and components:

- **WordPress plugin**: `apps/wp-plugin` — a plugin that adds the AIO Suite
  functionality into a WordPress site.  It registers admin pages and REST
  endpoints for interacting with the backend services.
- **Content intelligence service**: `apps/content-intel` — a FastAPI service
  responsible for scraping reference content, generating articles with AI,
  validating the output (length, readability, heading structure), and
  returning metadata.
- **Social hub service**: `apps/social-hub` — a Node.js service that handles
  posting content to social media platforms and integrating with external
  APIs for images.
- **Infrastructure**: `infra/docker` and `infra/gcp` — configuration files
  for running the project in containers and on Google Cloud Platform.

Start by reading this file and the READMEs in each module for
instructions on how to set up and run the components locally.