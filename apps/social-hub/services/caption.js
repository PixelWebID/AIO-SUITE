
const axios = require('axios');
const { loadConfig } = require('../config');

const config = loadConfig();

function formatSentence(sentence, tone) {
  if (tone === 'formal') {
    return sentence.replace(/!+/g, '.');
  }
  return sentence;
}

function buildLocalCaption({ title, url, summary, tone, trends = [], includeImage }) {
  const sentences = [];
  const trimmedSummary = (summary || '').replace(/\s+/g, ' ').trim();
  const lead = trimmedSummary ? trimmedSummary : ${title} diringkas untuk kamu.;
  sentences.push(formatSentence(lead, tone));

  if (trends.length) {
    sentences.push(formatSentence(Highlight terbaru: ., tone));
  }

  const callToAction = tone === 'formal'
    ? 'Pelajari detail lengkapnya melalui tautan berikut.'
    : 'Selengkapnya di artikel utama, langsung cek link-nya.';

  sentences.push(${callToAction} );

  if (includeImage) {
    sentences.push('#visualstory');
  }

  return sentences.join('\n');
}

async function generateCaption({ title, url, summary, tone = config.defaultTone, trends = [], includeImage = false }) {
  if (process.env.CAPTION_API_URL) {
    try {
      const response = await axios.post(process.env.CAPTION_API_URL, {
        title,
        url,
        summary,
        tone,
        trends,
        includeImage,
      });
      if (response.data && response.data.caption) {
        return response.data.caption;
      }
    } catch (error) {
      console.warn('caption service unavailable, falling back to local generator', error.message);
    }
  }

  return buildLocalCaption({ title, url, summary, tone, trends, includeImage });
}

module.exports = { generateCaption };

