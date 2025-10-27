/*
 * Entry point for the Social Hub microservice.
 *
 * Provides caption generation, social publishing, scheduling, and history
 * endpoints for the AIO Suite.
 */

const express = require('express');
const { loadConfig } = require('./config');
const { createPublisher } = require('./services/social');
const buildRouter = require('./routes/publish');

async function bootstrap() {
  const app = express();
  const config = loadConfig();
  const publisher = await createPublisher(config);

  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', service: 'social-hub', version: config.version });
  });

  app.use('/api', buildRouter({ publisher, config }));

  app.listen(config.port, () => {
    console.log(`Social hub listening on port ${config.port}`);
  });
}

bootstrap().catch((error) => {
  console.error('Failed to start social hub', error);
  process.exit(1);
});
