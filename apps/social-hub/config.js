const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '.env') });

function loadConfig() {
  return {
    port: Number(process.env.PORT || 8080),
    version: process.env.SOCIAL_HUB_VERSION || '0.1.0',
    providers: {
      twitter: {
        token: process.env.TWITTER_BEARER_TOKEN || null,
      },
      facebook: {
        token: process.env.FACEBOOK_APP_TOKEN || null,
      },
      instagram: {
        token: process.env.INSTAGRAM_APP_TOKEN || null,
      },
      threads: {
        token: process.env.THREADS_APP_TOKEN || null,
      },
    },
  };
}

module.exports = { loadConfig };
