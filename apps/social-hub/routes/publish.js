const express = require('express');
const { generateCaption } = require('../services/caption');

function buildRouter({ publisher, config }) {
  const router = express.Router();

  router.post('/publish', async (req, res) => {
    const {
      title,
      url,
      summary,
      networks = ['x'],
      tone = config.defaultTone,
      trends = [],
      includeImage = false,
      image,
      scheduleAt,
      manualPublish = !config.autoPublishDefault,
      sites = [],
    } = req.body || {};

    if (!title || !url) {
      return res.status(400).json({ error: 'title and url are required' });
    }

    if (!Array.isArray(networks) || networks.length === 0) {
      return res.status(400).json({ error: 'networks must contain at least one network' });
    }

    const caption = await generateCaption({ title, url, summary, tone, trends, includeImage });

    if (manualPublish) {
      return res.json({
        status: 'manual-ready',
        caption,
        networks,
        sites,
      });
    }

    const payload = {
      title,
      url,
      summary,
      caption,
      tone,
      trends,
      includeImage,
      image,
      networks,
      scheduleAt,
      sites,
    };

    try {
      const result = await publisher.publish(payload);
      return res.json({
        status: result.status,
        caption,
        result,
      });
    } catch (error) {
      return res.status(502).json({
        error: 'Failed to publish to networks',
        detail: error.message,
      });
    }
  });

  router.get('/publish/scheduled', (_req, res) => {
    res.json({ jobs: publisher.listScheduled() });
  });

  router.get('/publish/history', (req, res) => {
    const limit = Math.min(Number(req.query.limit) || 20, 100);
    res.json({ history: publisher.listHistory(limit) });
  });

  return router;
}

module.exports = buildRouter;
