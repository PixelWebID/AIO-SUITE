process.env.CAPTION_MAX_CHARS = '140';
process.env.CAPTION_SENTENCES = '3';
process.env.OPENAI_API_KEY = '';

delete require.cache[require.resolve('../services/caption')];
const { generateCaption } = require('../services/caption');

describe('generateCaption', () => {
  it('returns a fallback caption within limits', async () => {
    const caption = await generateCaption('<p>Ini contoh artikel. Kalimat kedua menambahkan konteks.</p>', 'casual');
    expect(typeof caption).toBe('string');
    expect(caption.length).toBeLessThanOrEqual(140);
    expect(caption.split('.').length).toBeGreaterThan(1);
  });
});
