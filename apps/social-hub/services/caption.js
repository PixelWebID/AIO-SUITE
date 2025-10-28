const OpenAI = require('openai');
const { loadConfig } = require('../config');

const config = loadConfig();
const openAiClients = new Map();

function getOpenAIClient(apiKey) {
  if (!apiKey) {
    return null;
  }
  if (!openAiClients.has(apiKey)) {
    openAiClients.set(apiKey, new OpenAI({ apiKey }));
  }
  return openAiClients.get(apiKey);
}

function stripHtml(html) {
  return (html || '')
    .replace(/<style.*?>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script.*?>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function fallbackCaption(articleHtml, tone, maxChars, sentencesTarget) {
  const text = stripHtml(articleHtml);
  if (!text) {
    return tone === 'formal'
      ? 'Ringkasan tidak tersedia. Pelajari detail selengkapnya melalui tautan berikut.'
      : 'Belum ada ringkasan nih, cek langsung artikelnya ya!';
  }

  const sentences = text.match(/[^.!?]+[.!?]/g) || [text];
  const selected = sentences.slice(0, Math.max(2, Math.min(sentencesTarget, sentences.length)));
  let caption = selected.join(' ').trim();

  if (tone === 'formal') {
    caption = caption.replace(/!+/g, '.');
  }

  if (caption.length > maxChars) {
    caption = caption.slice(0, maxChars - 1).trimEnd();
    caption = caption.replace(/[\s,.!?;:-]+$/, '');
    caption += '…';
  }

  return caption;
}

async function generateCaption(articleHtml, tone = config.defaultTone) {
  const { openai, summarization } = config;
  const client = getOpenAIClient(openai.apiKey);
  const maxChars = summarization.maxChars;
  const sentencesTarget = summarization.sentences;

  if (!client) {
    return fallbackCaption(articleHtml, tone, maxChars, sentencesTarget);
  }

  const prompt = `Buat ringkasan 2-3 kalimat dengan tone ${tone}. Panjang maksimal ${maxChars} karakter. HTML sumber:\n\n${articleHtml}`;

  try {
    const response = await client.chat.completions.create({
      model: openai.model,
      temperature: 0.6,
      max_tokens: 180,
      messages: [
        {
          role: 'system',
          content:
            'Anda adalah copywriter media sosial. Tulis ringkasan singkat 2-3 kalimat, batasi jumlah karakter, dan jaga tone sesuai instruksi.',
        },
        { role: 'user', content: prompt },
      ],
    });

    const text = response.choices?.[0]?.message?.content?.trim();
    if (!text) {
      return fallbackCaption(articleHtml, tone, maxChars, sentencesTarget);
    }

    if (text.length > maxChars) {
      return text.slice(0, maxChars - 1).trimEnd() + '…';
    }
    return text;
  } catch (error) {
    return fallbackCaption(articleHtml, tone, maxChars, sentencesTarget);
  }
}

module.exports = { generateCaption };
