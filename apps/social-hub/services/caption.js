const axios = require('axios');

async function generateCaption({ title, url, summary }) {
  if (!process.env.CAPTION_API_URL) {
    return `${title} - ${summary || 'Read more'} ${url}`;
  }

  try {
    const response = await axios.post(process.env.CAPTION_API_URL, {
      title,
      url,
      summary,
    });
    return response.data.caption;
  } catch (error) {
    console.warn('caption service unavailable, falling back to default', error.message);
    return `${title} - ${summary || 'Read more'} ${url}`;
  }
}

module.exports = { generateCaption };
