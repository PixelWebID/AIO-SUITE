const express = require('express');
const pino = require('pino');
const { loadConfig } = require('./config');
const createPublishRouter = require('./routes/publish');

function bootstrap() {
  const config = loadConfig();
  const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
  const app = express();

  app.use(express.json({ limit: '1mb' }));

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', service: 'social-hub', version: config.version });
  });

  app.use('/', createPublishRouter({ config, logger }));

  app.use((err, _req, res, _next) => {
    logger.error({ err }, 'Unhandled error');
    res.status(500).json({ error: 'Internal server error' });
  });

  app.listen(config.port, () => {
    logger.info({ port: config.port }, 'Social hub listening');
  });
}

bootstrap();
