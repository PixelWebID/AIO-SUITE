# AIO Suite Overview

This document provides a high‑level overview of the AIO Suite project.  The
suite is composed of three main components:

1. **WordPress Plugin** (`apps/wp-plugin`): Adds admin pages and REST routes
   to WordPress, allowing site administrators to request content generation
   and schedule publication.  The plugin communicates with backend services
   over HTTP.

2. **Content Intelligence Service** (`apps/content-intel`): A FastAPI
   application that handles scraping, AI interaction, content generation,
   and validation.  It exposes API endpoints such as `/generate_article` to
   accept keyword requests and return generated HTML and metadata.

3. **Social Hub Service** (`apps/social-hub`): A Node.js service for
   publishing content to social media platforms.  It abstracts away
   platform specifics and supports multiple providers through a unified
   interface.

This directory can be expanded with more detailed design docs, API
contracts, and implementation notes as the project evolves.