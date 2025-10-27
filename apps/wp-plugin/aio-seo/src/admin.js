
import { createEditorPanel } from './components/Editor.jsx';
import { createPreviewPanel } from './components/Preview.jsx';
import { createHistoryPanel } from './components/History.jsx';

const env = window.AIO_SUITE_ENV || {};
const state = {
  article: null,
  record: null,
  settings: env.settings || {},
};

async function request(path, options = {}) {
  const response = await fetch(`${env.restUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-WP-Nonce': env.nonce,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function computeWarnings(article) {
  const warnings = new Set(article.warnings || []);
  const metrics = article.metrics || {};

  if (metrics.word_count && metrics.word_count < 700) {
    warnings.add('WORD_COUNT_LOW');
  }
  if (metrics.flesch_reading_ease && metrics.flesch_reading_ease < 55) {
    warnings.add('READABILITY_LOW');
  }
  const headingCounts = metrics.heading_counts || { h2: 0, h3: 0 };
  if ((headingCounts.h2 || 0) < 3) {
    warnings.add('H2_LOW');
  }
  const duplicates = metrics.duplicate_matches || metrics.similarity_warnings || [];
  if (Array.isArray(duplicates) && duplicates.length > 0) {
    warnings.add('DUPLICATE_HIGH');
  }
  return Array.from(warnings);
}
function createForm() {
  const form = document.createElement('form');
  form.className = 'aio-form-layout';
  form.addEventListener('submit', (event) => event.preventDefault());

  const keyword = document.createElement('input');
  keyword.type = 'text';
  keyword.placeholder = 'contoh: wisata kuliner bandung';
  keyword.required = true;

  const geo = document.createElement('select');
  ['ID', 'US', 'SG', 'MY', 'AU'].forEach((code) => {
    const option = document.createElement('option');
    option.value = code;
    option.textContent = code;
    geo.appendChild(option);
  });
  geo.value = state.settings.default_geo || 'ID';

  const tone = document.createElement('select');
  ['neutral', 'formal', 'casual', 'authoritative', 'friendly'].forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    tone.appendChild(option);
  });
  tone.value = state.settings.default_tone || 'neutral';

  const minWords = document.createElement('input');
  minWords.type = 'number';
  minWords.min = '300';
  minWords.value = '800';

  const maxRefs = document.createElement('input');
  maxRefs.type = 'number';
  maxRefs.min = '3';
  maxRefs.value = '7';

  const feedUrl = document.createElement('input');
  feedUrl.type = 'url';
  feedUrl.placeholder = 'https://example.com/feed.xml';

  const competitorField = document.createElement('textarea');
  competitorField.rows = 2;
  competitorField.placeholder = 'Competitor URLs (pisahkan baris)';

  const includeImages = document.createElement('input');
  includeImages.type = 'checkbox';
  includeImages.checked = true;

  const scheduleInput = document.createElement('input');
  scheduleInput.type = 'datetime-local';

  const networks = ['x', 'facebook', 'instagram', 'threads'].map((network) => {
    const label = document.createElement('label');
    label.className = 'aio-field aio-field--inline';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = network;
    label.appendChild(input);
    label.appendChild(document.createTextNode(network.toUpperCase()));
    return { label, input };
  });

  const fields = [
    { label: 'Keyword', node: keyword },
    { label: 'Geo', node: geo },
    { label: 'Tone', node: tone },
    { label: 'Min words', node: minWords },
    { label: 'Max references', node: maxRefs },
    { label: 'Feed URL (RSS)', node: feedUrl },
    { label: 'Competitors', node: competitorField },
  ];

  fields.forEach(({ label, node }) => {
    const wrapper = document.createElement('label');
    wrapper.className = 'aio-field';
    wrapper.innerHTML = `<span>${label}</span>`;
    wrapper.appendChild(node);
    form.appendChild(wrapper);
  });

  const toggleRow = document.createElement('label');
  toggleRow.className = 'aio-field aio-field--inline';
  toggleRow.appendChild(includeImages);
  toggleRow.appendChild(document.createTextNode('Sertakan rekomendasi gambar'));
  form.appendChild(toggleRow);

  const scheduleRow = document.createElement('label');
  scheduleRow.className = 'aio-field';
  scheduleRow.innerHTML = '<span>Jadwal publish (opsional)</span>';
  scheduleRow.appendChild(scheduleInput);
  form.appendChild(scheduleRow);

  const networkGroup = document.createElement('div');
  networkGroup.className = 'aio-field';
  networkGroup.innerHTML = '<span>Social networks</span>';
  networks.forEach(({ label }) => networkGroup.appendChild(label));
  form.appendChild(networkGroup);

  return {
    form,
    fields: {
      keyword,
      geo,
      tone,
      minWords,
      maxRefs,
      feedUrl,
      includeImages,
      scheduleInput,
      competitorField,
      networks,
    },
  };
}
function renderGapResult(container, data) {
  container.innerHTML = '';
  if (!data) {
    container.textContent = 'Belum ada analisis.';
    return;
  }

  const summary = document.createElement('p');
  summary.textContent = data.summary || 'Tidak ada ringkasan.';
  container.appendChild(summary);

  const list = document.createElement('ul');
  list.className = 'aio-gap-list';
  (data.insights || []).forEach((insight) => {
    const item = document.createElement('li');
    item.innerHTML = `
      <header><strong>${insight.title}</strong> <span class="aio-pill">${insight.difficulty}</span></header>
      <p>${insight.summary}</p>
      <footer>Opportunity: ${(insight.opportunity_score * 100).toFixed(0)}%</footer>
    `;
    list.appendChild(item);
  });
  container.appendChild(list);
}

function collectNetworks(fields) {
  return fields.networks
    .filter(({ input }) => input.checked)
    .map(({ input }) => input.value);
}
function initialise() {
  const root = document.getElementById('aio-root');
  if (!root) {
    return;
  }

  const { form, fields } = createForm();
  const actions = document.createElement('div');
  actions.className = 'aio-actions-row';

  const analyzeBtn = document.createElement('button');
  analyzeBtn.type = 'button';
  analyzeBtn.className = 'button';
  analyzeBtn.textContent = 'Analyze Gap';

  const generateBtn = document.createElement('button');
  generateBtn.type = 'button';
  generateBtn.className = 'button button-primary';
  generateBtn.textContent = 'Generate Article';

  const rssBtn = document.createElement('button');
  rssBtn.type = 'button';
  rssBtn.className = 'button';
  rssBtn.textContent = 'Generate from RSS';

  const publishBtn = document.createElement('button');
  publishBtn.type = 'button';
  publishBtn.className = 'button button-secondary';
  publishBtn.textContent = 'Publish';

  const scheduleBtn = document.createElement('button');
  scheduleBtn.type = 'button';
  scheduleBtn.className = 'button';
  scheduleBtn.textContent = 'Schedule';

  actions.append(analyzeBtn, generateBtn, rssBtn, publishBtn, scheduleBtn);

  const editorPanel = createEditorPanel({
    onContentChange(value) {
      if (state.article) {
        state.article.article_html = value;
      }
    },
  });
  const previewPanel = createPreviewPanel();
  const historyPanel = createHistoryPanel({
    onSelect: async (id) => {
      try {
        const data = await request(`/history/${id}`);
        state.article = data.record;
        state.record = data.record;
        editorPanel.setContent(data.record.article_html, data.record.meta);
        editorPanel.setKeywords(data.record.meta?.keywords || []);
        previewPanel.update(data.record, computeWarnings(data.record));
      } catch (error) {
        notify(error.message, 'error');
      }
    },
    fetchHistory: (query) => request(`/history${query}`),
  });

  const gapPanel = document.createElement('div');
  gapPanel.className = 'aio-gap-panel';
  gapPanel.textContent = 'Belum ada analisis.';

  const statusBar = document.createElement('div');
  statusBar.className = 'aio-status';

  function notify(message, type = 'info') {
    statusBar.className = `aio-status aio-status--${type}`;
    statusBar.textContent = message;
  }
  async function handleGenerate() {
    const payload = {
      keyword: fields.keyword.value.trim(),
      geo: fields.geo.value,
      tone: fields.tone.value,
      min_words: parseInt(fields.minWords.value, 10) || 800,
      max_references: parseInt(fields.maxRefs.value, 10) || 7,
      include_images: fields.includeImages.checked,
      additional_context: fields.competitorField.value,
      custom_reference_urls: fields.competitorField.value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.startsWith('http')),
    };

    if (!payload.keyword) {
      notify('Masukkan keyword terlebih dahulu.', 'error');
      return;
    }

    notify('Menghasilkan artikel…');
    generateBtn.disabled = true;
    try {
      const data = await request('/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      state.article = data.article;
      state.record = data.record;
      editorPanel.setContent(data.article.article_html, data.article.meta);
      editorPanel.setKeywords(data.article.meta?.keywords || []);
      previewPanel.update(data.article, computeWarnings(data.article));
      historyPanel.reload();
      notify('Draft berhasil dibuat.', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      generateBtn.disabled = false;
    }
  }

  async function handleGenerateRss() {
    if (!fields.feedUrl.value) {
      notify('Isi Feed URL terlebih dahulu.', 'error');
      return;
    }
    notify('Mengolah RSS…');
    rssBtn.disabled = true;
    try {
      const data = await request('/generate_rss', {
        method: 'POST',
        body: JSON.stringify({
          feed_url: fields.feedUrl.value.trim(),
          tone: fields.tone.value,
          geo: fields.geo.value,
        }),
      });
      state.article = data.article;
      state.record = data.record;
      editorPanel.setContent(data.article.article_html, data.article.meta);
      editorPanel.setKeywords(data.article.meta?.keywords || []);
      previewPanel.update(data.article, computeWarnings(data.article));
      historyPanel.reload();
      notify('Draft RSS siap ditinjau.', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      rssBtn.disabled = false;
    }
  }

  async function handleGap() {
    const keyword = fields.keyword.value.trim();
    if (!keyword) {
      notify('Masukkan keyword untuk analisis gap.', 'error');
      return;
    }
    notify('Menganalisis gap…');
    analyzeBtn.disabled = true;
    try {
      const params = new URLSearchParams({ keyword, geo: fields.geo.value });
      const competitors = fields.competitorField.value
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
      competitors.forEach((url) => params.append('competitors[]', url));
      const data = await request(`/gap?${params.toString()}`);
      renderGapResult(gapPanel, data);
      notify('Analisis gap selesai.', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      analyzeBtn.disabled = false;
    }
  }

  async function handlePublish(schedule = null) {
    if (!state.article) {
      notify('Belum ada artikel untuk dipublish.', 'error');
      return;
    }

    const networks = collectNetworks(fields);
    try {
      const payload = {
        article: state.article,
        record_id: state.record?.id,
        schedule_at: schedule,
        social: networks.length
          ? {
              networks,
              tone: fields.tone.value,
            }
          : null,
      };
      notify(schedule ? 'Menjadwalkan publikasi…' : 'Mempublish artikel…');
      publishBtn.disabled = true;
      scheduleBtn.disabled = true;
      const data = await request('/publish', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      historyPanel.reload();
      notify(schedule ? 'Artikel dijadwalkan.' : 'Artikel dipublish.', 'success');
      return data;
    } catch (error) {
      notify(error.message, 'error');
      throw error;
    } finally {
      publishBtn.disabled = false;
      scheduleBtn.disabled = false;
    }
  }
  analyzeBtn.addEventListener('click', handleGap);
  generateBtn.addEventListener('click', handleGenerate);
  rssBtn.addEventListener('click', handleGenerateRss);
  publishBtn.addEventListener('click', () => handlePublish().catch(() => {}));
  scheduleBtn.addEventListener('click', () => {
    if (!fields.scheduleInput.value) {
      notify('Pilih tanggal untuk penjadwalan.', 'error');
      return;
    }
    handlePublish(fields.scheduleInput.value).catch(() => {});
  });

  const layout = document.createElement('div');
  layout.className = 'aio-dashboard-grid';

  const formCard = document.createElement('section');
  formCard.className = 'aio-card';
  formCard.innerHTML = '<h2>Generate Konten</h2>';
  formCard.append(form, actions);

  const gapCard = document.createElement('section');
  gapCard.className = 'aio-card';
  gapCard.innerHTML = '<h2>Gap Analysis</h2>';
  gapCard.appendChild(gapPanel);

  const editorCard = document.createElement('section');
  editorCard.className = 'aio-card aio-card--large';
  editorCard.innerHTML = '<h2>Editor</h2>';
  editorCard.appendChild(editorPanel.node);

  const previewCard = document.createElement('section');
  previewCard.className = 'aio-card aio-card--large';
  previewCard.innerHTML = '<h2>Preview & Metrics</h2>';
  previewCard.appendChild(previewPanel.node);

  const historyCard = document.createElement('section');
  historyCard.className = 'aio-card aio-card--stack';
  historyCard.innerHTML = '<h2>History</h2>';
  historyCard.appendChild(historyPanel.node);

  layout.append(formCard, gapCard, editorCard, previewCard, historyCard);

  root.innerHTML = '';
  root.append(layout, statusBar);

  historyPanel.reload();
  notify('Siap digunakan.');
}

document.addEventListener('DOMContentLoaded', initialise);

