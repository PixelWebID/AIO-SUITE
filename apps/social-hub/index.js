/*
 * Social hub service for the AIO Suite.
 *
 * This service exposes endpoints for posting content to social media
 * platforms.  In this skeleton implementation it simply returns a
 * success response without contacting any external APIs.
 */

const express = require('express');
const app = express();

app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.post('/publish', (req, res) => {
  const { title, url } = req.body;
  console.log(`Publishing article ${title} at ${url}`);
  res.json({ status: 'ok', result: { platform: 'x', posted: true } });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`Social hub listening on port ${PORT}`);
});