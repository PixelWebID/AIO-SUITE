const express = require('express');
const { generateCaption } = require('../services/caption');
const { postToX, postToFBIG, postToThreads } = require('../services/social');

function normalisePlatforms(platforms) {
  if (!Array.isArray(platforms)) {
    return [];
  }
  return Array.from(new Set(platforms.map((p) => String(p || '').trim().toLowerCase()).filter(Boolean)));
}

module.exports = function createPublishRouter({ config, logger }) {
  const router = express.Router();

  router.post('/publish', async (req, res) => {
    const {
      title,
      url,
      article_html: articleHtml,
      image_url: imageUrl,
      tone = config.defaultTone,
      platforms = [],
    } = req.body || {};

    if (!title || !url || !articleHtml) {
      return res.status(400).json({ error: 'title, url, and article_html are required' });
    }

    const targetPlatforms = normalisePlatforms(platforms);
    if (!targetPlatforms.length) {
      return res.status(400).json({ error: 'platforms must be a non-empty array' });
    }

    try {
      const caption = await generateCaption(articleHtml, tone);
      const payload = {
        title,
        url,
        caption,
        imageUrl,
        tone,
      };

      const promises = targetPlatforms.map(async (platform) => {
        switch (platform) {
          case 'x':
          case 'twitter':
            return postToX(payload, config.tokens.x, config.timeoutMs, logger);
          case 'facebook':
            return postToFBIG('facebook', payload, config.tokens.facebook, config.timeoutMs, logger);
          case 'instagram':
            return postToFBIG('instagram', payload, config.tokens.instagram, config.timeoutMs, logger);
          case 'threads':
            return postToThreads(payload, config.tokens.threads, config.timeoutMs, logger);
          default:
            return { platform, ok: false, error: 'Unsupported platform' };
        }
      });

      const results = await Promise.all(promises);

      res.json({
        title,
        url,
        caption,
        tone,
        results,
      });
    } catch (error) {
      logger.error({ error: error.message }, 'Publish request failed');
      res.status(500).json({ error: 'Failed to publish content', detail: error.message });
    }
  });

  return router;
};
