const fetch = require('node-fetch');

function withTimeout(timeoutMs) {
  return async (url, options = {}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      return response;
    } finally {
      clearTimeout(timer);
    }
  };
}

function joinCaptionAndUrl(caption, url, limit) {
  const combined = [caption.trim(), url ? url.trim() : ''].filter(Boolean).join(' ');
  if (limit && combined.length > limit) {
    return combined.slice(0, limit - 1).trimEnd() + '…';
  }
  return combined;
}

async function postToX(payload, tokens, timeoutMs, logger) {
  if (!tokens || !tokens.trim()) {
    return { platform: 'x', ok: false, error: 'Missing X bearer token' };
  }

  const request = withTimeout(timeoutMs);
  const body = { text: joinCaptionAndUrl(payload.caption, payload.url, 280) };

  try {
    const response = await request('https://api.twitter.com/2/tweets', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${tokens}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      logger.error({ platform: 'x', data }, 'Failed to post to X');
      return { platform: 'x', ok: false, error: data.error || response.statusText };
    }

    return { platform: 'x', ok: true, id: data.data?.id || null };
  } catch (error) {
    logger.error({ platform: 'x', error: error.message }, 'Error posting to X');
    return { platform: 'x', ok: false, error: error.message };
  }
}

async function postToFBIG(platform, payload, tokens, timeoutMs, logger) {
  if (!tokens?.token) {
    return { platform, ok: false, error: 'Missing Facebook/Instagram token' };
  }
  const request = withTimeout(timeoutMs);

  if (platform === 'facebook') {
    if (!tokens.pageId) {
      return { platform, ok: false, error: 'Missing Facebook page ID' };
    }
    const params = new URLSearchParams({
      message: joinCaptionAndUrl(payload.caption, payload.url),
      access_token: tokens.token,
    });
    if (payload.url) {
      params.append('link', payload.url);
    }
    try {
      const response = await request(`https://graph.facebook.com/v19.0/${tokens.pageId}/feed`, {
        method: 'POST',
        body: params,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        logger.error({ platform, data }, 'Facebook Graph API error');
        return { platform, ok: false, error: data.error?.message || response.statusText };
      }
      return { platform, ok: true, id: data.id || null };
    } catch (error) {
      logger.error({ platform, error: error.message }, 'Error posting to Facebook');
      return { platform, ok: false, error: error.message };
    }
  }

  if (platform === 'instagram') {
    if (!tokens.businessAccountId) {
      return { platform, ok: false, error: 'Missing Instagram business account ID' };
    }
    if (!payload.imageUrl) {
      return { platform, ok: false, error: 'Instagram requires image_url' };
    }
    try {
      const mediaParams = new URLSearchParams({
        caption: joinCaptionAndUrl(payload.caption, payload.url),
        image_url: payload.imageUrl,
        access_token: tokens.token,
      });
      const mediaResponse = await request(
        `https://graph.facebook.com/v19.0/${tokens.businessAccountId}/media`,
        { method: 'POST', body: mediaParams }
      );
      const mediaData = await mediaResponse.json().catch(() => ({}));
      if (!mediaResponse.ok) {
        logger.error({ platform, mediaData }, 'Instagram media creation failed');
        return { platform, ok: false, error: mediaData.error?.message || mediaResponse.statusText };
      }

      const publishParams = new URLSearchParams({
        creation_id: mediaData.id,
        access_token: tokens.token,
      });
      const publishResponse = await request(
        `https://graph.facebook.com/v19.0/${tokens.businessAccountId}/media_publish`,
        { method: 'POST', body: publishParams }
      );
      const publishData = await publishResponse.json().catch(() => ({}));
      if (!publishResponse.ok) {
        logger.error({ platform, publishData }, 'Instagram publish failed');
        return { platform, ok: false, error: publishData.error?.message || publishResponse.statusText };
      }

      return { platform, ok: true, id: publishData.id || mediaData.id || null };
    } catch (error) {
      logger.error({ platform, error: error.message }, 'Error posting to Instagram');
      return { platform, ok: false, error: error.message };
    }
  }

  return { platform, ok: false, error: 'Unsupported platform for postToFBIG' };
}

async function postToThreads(payload, token, timeoutMs, logger) {
  if (!token) {
    return { platform: 'threads', ok: false, error: 'Missing Threads token' };
  }

  logger.warn({ platform: 'threads' }, 'Threads API not publicly available, skipping');
  return { platform: 'threads', ok: false, error: 'Threads API not available' };
}

module.exports = { postToX, postToFBIG, postToThreads };
