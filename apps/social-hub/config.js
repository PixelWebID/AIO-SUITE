const path = require('path');
const fs = require('fs');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '.env') });

const DEFAULT_STORAGE = path.resolve(__dirname, '..', '..', 'data', 'social-jobs.json');

function ensureStorageFile(filePath) {
  if (!fs.existsSync(path.dirname(filePath))) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
  }
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, '[]', 'utf8');
  }
}

function loadConfig() {
  const port = Number(process.env.PORT || 8080);
  const storagePath = process.env.SOCIAL_STORAGE_PATH || DEFAULT_STORAGE;
  ensureStorageFile(storagePath);

  return {
    port,
    version: process.env.SOCIAL_HUB_VERSION || '0.2.0',
    contentIntelUrl: process.env.CONTENT_INTEL_URL || 'http://localhost:8000',
    defaultTone: process.env.SOCIAL_DEFAULT_TONE || 'casual',
    autoPublishDefault: process.env.SOCIAL_AUTO_PUBLISH === 'true',
    storagePath,
    providers: {
      x: {
        token: process.env.X_BEARER_TOKEN || process.env.TWITTER_BEARER_TOKEN || null,
      },
      facebook: {
        token: process.env.FACEBOOK_GRAPH_TOKEN || process.env.FACEBOOK_APP_TOKEN || null,
        pageId: process.env.FACEBOOK_PAGE_ID || null,
      },
      instagram: {
        token: process.env.INSTAGRAM_GRAPH_TOKEN || process.env.INSTAGRAM_APP_TOKEN || null,
        businessAccountId: process.env.INSTAGRAM_BUSINESS_ID || null,
      },
      threads: {
        token: process.env.THREADS_APP_TOKEN || null,
      },
    },
    sites: (process.env.MULTISITE_ENDPOINTS || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean),
  };
}

module.exports = { loadConfig };
