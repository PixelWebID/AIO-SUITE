const express = require('express');
const { generateCaption } = require('../services/caption');
const { publishToNetworks } = require('../services/social');
const { loadConfig } = require('../config');

const router = express.Router();
const config = loadConfig();

router.post('/publish', async (req, res) => {
  const { title, url, networks = ['twitter'], summary } = req.body || {};

  if (!title || !url) {
    return res.status(400).json({ error: 'title and url are required' });
  }

  const caption = await generateCaption({ title, url, summary });
  const result = await publishToNetworks({ title, url, networks, caption }, config.providers);

  res.json({
    status: 'ok',
    caption,
    deliveries: result,
  });
});

module.exports = router;
