const axios = require('axios');
const { Scheduler } = require('./scheduler');

function createMessage(payload) {
  const text = `${payload.caption}\n${payload.url}`.trim();
  return text.length > 280 ? `${text.slice(0, 277)}...` : text;
}

async function deliverX(payload, provider) {
  if (!provider.token) {
    return { status: 'skipped', detail: 'Missing X/Twitter token' };
  }
  try {
    const message = createMessage(payload);
    const response = await axios.post(
      'https://api.twitter.com/2/tweets',
      { text: message },
      {
        headers: { Authorization: `Bearer ${provider.token}` },
      },
    );
    return { status: 'posted', reference: response.data.data?.id };
  } catch (error) {
    return { status: 'failed', detail: error.response?.data || error.message };
  }
}

async function deliverFacebook(payload, provider) {
  if (!provider.token || !provider.pageId) {
    return { status: 'skipped', detail: 'Missing Facebook token or page ID' };
  }
  try {
    const message = `${payload.caption}\n${payload.url}`;
    const response = await axios.post(
      `https://graph.facebook.com/v19.0/${provider.pageId}/feed`,
      null,
      {
        params: {
          message,
          link: payload.url,
          access_token: provider.token,
        },
      },
    );
    return { status: 'posted', reference: response.data.id };
  } catch (error) {
    return { status: 'failed', detail: error.response?.data || error.message };
  }
}

async function deliverInstagram(payload, provider) {
  if (!provider.token || !provider.businessAccountId) {
    return { status: 'skipped', detail: 'Missing Instagram business credentials' };
  }
  try {
    const caption = `${payload.caption}\n${payload.url}`;
    const mediaResponse = await axios.post(
      `https://graph.facebook.com/v19.0/${provider.businessAccountId}/media`,
      null,
      {
        params: {
          caption,
          access_token: provider.token,
          image_url: payload.image || undefined,
        },
      },
    );

    const creationId = mediaResponse.data.id;
    await axios.post(
      `https://graph.facebook.com/v19.0/${provider.businessAccountId}/media_publish`,
      null,
      {
        params: {
          creation_id: creationId,
          access_token: provider.token,
        },
      },
    );

    return { status: 'posted', reference: creationId };
  } catch (error) {
    return { status: 'failed', detail: error.response?.data || error.message };
  }
}

async function deliverThreads() {
  return {
    status: 'skipped',
    detail: 'Threads API belum tersedia secara publik; gunakan export manual.',
  };
}

async function distributeToSites(sites, payload) {
  const targets = Array.from(new Set(sites)).filter(Boolean);
  if (!targets.length) {
    return [];
  }

  const results = [];
  await Promise.all(
    targets.map(async (site) => {
      const endpoint = site.replace(/\/$/, '') + '/wp-json/aio/v1/social';
      try {
        await axios.post(
          endpoint,
          {
            title: payload.title,
            url: payload.url,
            caption: payload.caption,
            tone: payload.tone,
            networks: payload.networks,
          },
          { timeout: 15000 },
        );
        results.push({ site, status: 'delivered' });
      } catch (error) {
        results.push({
          site,
          status: 'failed',
          detail: error.response?.data || error.message,
        });
      }
    }),
  );

  return results;
}

async function createPublisher(config) {
  let scheduler;

  async function deliverNow(payload, options = {}) {
    const deliveries = {};
    for (const network of payload.networks) {
      if (network === 'x' || network === 'twitter') {
        deliveries[network] = await deliverX(payload, config.providers.x);
      } else if (network === 'facebook') {
        deliveries[network] = await deliverFacebook(payload, config.providers.facebook);
      } else if (network === 'instagram') {
        deliveries[network] = await deliverInstagram(payload, config.providers.instagram);
      } else if (network === 'threads') {
        deliveries[network] = await deliverThreads(payload, config.providers.threads);
      } else {
        deliveries[network] = { status: 'skipped', detail: 'Unsupported network' };
      }
    }
    return {
      mode: options.immediate ? 'immediate' : 'scheduled',
      deliveries,
    };
  }

  scheduler = new Scheduler(config.storagePath, deliverNow);
  await scheduler.init();

  async function deliverAndMirror(payload) {
    const deliveries = await deliverNow(payload, { immediate: true });
    const siteResults = await distributeToSites([...config.sites, ...(payload.sites || [])], payload);
    return { ...deliveries, siteResults };
  }

  scheduler = new Scheduler(config.storagePath, deliverAndMirror);
  await scheduler.init();

  async function publish(payload) {
    if (payload.scheduleAt) {
      const runAt = new Date(payload.scheduleAt);
      if (runAt.getTime() > Date.now()) {
        const scheduledRecord = await scheduler.schedule({
          runAt: runAt.toISOString(),
          payload,
        });
        return { status: 'scheduled', record: scheduledRecord };
      }
    }

    const result = await deliverAndMirror(payload);
    await scheduler.recordImmediate(payload, result);
    return { status: 'sent', result };
  }

  return {
    publish,
    listScheduled: () => scheduler.listScheduled(),
    listHistory: (limit) => scheduler.listHistory(limit),
  };
}

module.exports = { createPublisher };
