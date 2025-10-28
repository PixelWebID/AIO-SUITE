const dotenv = require('dotenv');

dotenv.config();

const DEFAULT_TIMEOUT_MS = Number(process.env.SOCIAL_HTTP_TIMEOUT || 15000);

function loadConfig() {
  return {
    port: Number(process.env.PORT || 8080),
    version: process.env.SOCIAL_HUB_VERSION || '1.0.0',
    defaultTone: process.env.SOCIAL_DEFAULT_TONE || 'casual',
    timeoutMs: DEFAULT_TIMEOUT_MS,
    openai: {
      apiKey: process.env.OPENAI_API_KEY || '',
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
    },
    summarization: {
      maxChars: Number(process.env.CAPTION_MAX_CHARS || 260),
      sentences: Number(process.env.CAPTION_SENTENCES || 3),
    },
    tokens: {
      x: process.env.X_BEARER_TOKEN || process.env.TWITTER_BEARER_TOKEN || '',
      facebook: {
        token:
          process.env.FACEBOOK_ACCESS_TOKEN ||
          process.env.FACEBOOK_GRAPH_TOKEN ||
          process.env.FACEBOOK_APP_TOKEN ||
          '',
        pageId: process.env.FACEBOOK_PAGE_ID || '',
      },
      instagram: {
        token:
          process.env.INSTAGRAM_ACCESS_TOKEN ||
          process.env.INSTAGRAM_GRAPH_TOKEN ||
          process.env.INSTAGRAM_APP_TOKEN ||
          '',
        businessAccountId: process.env.INSTAGRAM_BUSINESS_ID || '',
      },
      threads: process.env.THREADS_ACCESS_TOKEN || process.env.THREADS_APP_TOKEN || '',
    },
  };
}

module.exports = { loadConfig };
