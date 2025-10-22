/*
 * Entry point for the Social Hub microservice.
 *
 * This service coordinates social network posting, caption generation, and
 * scheduling using external APIs. The current implementation wires together
 * routers and service skeletons so CI and deployment pipelines can be verified.
 */

const express = require('express');
const { loadConfig } = require('./config');
const publishRouter = require('./routes/publish');

const app = express();
const config = loadConfig();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'social-hub', version: config.version });
});

app.use('/api', publishRouter);

app.listen(config.port, () => {
  console.log(`Social hub listening on port ${config.port}`);
});
