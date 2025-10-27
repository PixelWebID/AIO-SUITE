import { createPreviewPanel } from './Preview.jsx';

const env = window.AIO_SUITE_ENV || {};

const GEO_OPTIONS = [
  { value: 'ID', label: 'Indonesia' },
  { value: 'US', label: 'Amerika Serikat' },
  { value: 'SG', label: 'Singapura' },
  { value: 'MY', label: 'Malaysia' },
];

const TONES = [
  { value: 'neutral', label: 'Netral' },
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Santai' },
  { value: 'authoritative', label: 'Otoritatif' },
  { value: 'friendly', label: 'Ramah' },
];

async function api(path, options = {}) {
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
  return response.json();
}

function createSelect(options) {
  const select = document.createElement('select');
  options.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  });
  return select;
}

function renderMetrics(panel, metrics) {
  panel.innerHTML = `
    <h3>MetriK Utama</h3>
    <ul>
      <li>Kata: <strong>${metrics.word_count}</strong></li>
      <li>Flesch: <strong>${metrics.flesch_reading_ease}</strong></li>
      <li>FK Grade: <strong>${metrics.fk_grade_level}</strong></li>
      <li>H2/H3: <strong>${metrics.heading_counts.h2}</strong> / <strong>${metrics.heading_counts.h3}</strong></li>
    </ul>
    <h4>Kepadatan keyword</h4>
    <ul>${Object.entries(metrics.keyword_density || {})
      .map(([keyword, density]) => `<li>${keyword}: ${density}%</li>`)
      .join('')}</ul>
  `;
}

function renderImages(panel, images = []) {
  panel.innerHTML = '';
  if (!images.length) {
    panel.textContent = 'Tidak ada rekomendasi gambar.';
    return;
  }
  images.forEach((image) => {
    const figure = document.createElement('figure');
    const img = document.createElement('img');
    img.src = image.url;
    img.alt = image.caption || image.provider;
    img.loading = 'lazy';
    const figcaption = document.createElement('figcaption');
    figcaption.textContent = `${image.provider.toUpperCase()} • ${image.caption || 'Tanpa caption'}`;
    figure.append(img, figcaption);
    panel.appendChild(figure);
  });
}

export function createEditorPanel() {
  const container = document.createElement('div');
  container.className = 'aio-editor-screen';

  const layout = document.createElement('div');
  layout.className = 'aio-editor-layout';

  const form = document.createElement('form');
  form.className = 'aio-form';
  form.addEventListener('submit', (event) => event.preventDefault());

  const keywordField = document.createElement('label');
  keywordField.className = 'aio-field';
  keywordField.innerHTML = '
    <span>Kata kunci utama</span>
    <input type="text" placeholder="contoh: travel bali ramah keluarga" required />
  ';
  const keywordInput = keywordField.querySelector('input');

  const geoField = document.createElement('label');
  geoField.className = 'aio-field';
  geoField.innerHTML = '<span>Geo target</span>';
  const geoSelect = createSelect(GEO_OPTIONS);
  geoField.appendChild(geoSelect);

  const toneField = document.createElement('label');
  toneField.className = 'aio-field';
  toneField.innerHTML = '<span>Tone penulisan</span>';
  const toneSelect = createSelect(TONES);
  toneField.appendChild(toneSelect);

  const secondaryField = document.createElement('label');
  secondaryField.className = 'aio-field';
  secondaryField.innerHTML = '
    <span>Kata kunci turunan (pisahkan dengan koma)</span>
    <input type="text" placeholder="hotel ramah anak, itinerary 5 hari" />
  ';
  const secondaryInput = secondaryField.querySelector('input');

  const sitemapField = document.createElement('label');
  sitemapField.className = 'aio-field';
  sitemapField.innerHTML = '
    <span>Sitemap URL (opsional untuk internal link)</span>
    <input type="url" placeholder="https://example.com/sitemap.xml" />
  ';
  const sitemapInput = sitemapField.querySelector('input');

  const contextField = document.createElement('label');
  contextField.className = 'aio-field';
  contextField.innerHTML = '
    <span>Context tambahan</span>
    <textarea rows="4" placeholder="Masukkan poin penting, persona, CTA, dsb."></textarea>
  ';
  const contextInput = contextField.querySelector('textarea');

  const optionsRow = document.createElement('div');
  optionsRow.className = 'aio-options-row';
  optionsRow.innerHTML = `
    <label><input type="checkbox" data-option="images" checked /> Sertakan rekomendasi gambar</label>
    <label><input type="checkbox" data-option="social" checked /> Bangun ringkasan sosial</label>
    <label><input type="checkbox" data-option="auto" /> Auto publish</label>
    <label><input type="checkbox" data-option="manual" /> Mode manual</label>
  `;
  const includeImagesInput = optionsRow.querySelector('[data-option="images"]');
  const includeSocialInput = optionsRow.querySelector('[data-option="social"]');
  const autoPublishInput = optionsRow.querySelector('[data-option="auto"]');
  const manualModeInput = optionsRow.querySelector('[data-option="manual"]');

  const scheduleField = document.createElement('label');
  scheduleField.className = 'aio-field';
  scheduleField.innerHTML = '
    <span>Jadwal terbit (opsional)</span>
    <input type="datetime-local" />
  ';
  const scheduleInput = scheduleField.querySelector('input');

  const referencesField = document.createElement('label');
  referencesField.className = 'aio-field';
  referencesField.innerHTML = '
    <span>Referensi tambahan (URL pisahkan baris)</span>
    <textarea rows="3" placeholder="https://example.com/referensi"></textarea>
  ';
  const referencesInput = referencesField.querySelector('textarea');

  const generateButton = document.createElement('button');
  generateButton.type = 'button';
  generateButton.className = 'button button-primary';
  generateButton.textContent = 'Generate Draft';

  const syncButton = document.createElement('button');
  syncButton.type = 'button';
  syncButton.className = 'button';
  syncButton.textContent = 'Perbarui preview dari editor';

  const toolbar = document.createElement('div');
  toolbar.className = 'aio-toolbar';
  toolbar.append(generateButton, syncButton);

  const editorTextarea = document.createElement('textarea');
  editorTextarea.id = 'aio-editor';
  editorTextarea.rows = 24;
  editorTextarea.className = 'aio-editor';
  editorTextarea.readOnly = true;

  manualModeInput.addEventListener('change', () => {
    editorTextarea.readOnly = !manualModeInput.checked;
    editorTextarea.classList.toggle('aio-editor--editable', manualModeInput.checked);
  });

  const editorColumn = document.createElement('div');
  editorColumn.className = 'aio-editor-column';
  editorColumn.append(form, toolbar, editorTextarea);

  const previewColumn = document.createElement('div');
  previewColumn.className = 'aio-preview-column';
  const previewPanel = createPreviewPanel();
  const metricsPanel = document.createElement('section');
  metricsPanel.className = 'aio-insight-panel';
  metricsPanel.innerHTML = '<h3>MetriK Utama</h3><p>Belum ada data.</p>';
  const imagePanel = document.createElement('section');
  imagePanel.className = 'aio-image-panel';
  imagePanel.innerHTML = '<h3>Rekomendasi gambar</h3><p>-</p>';
  previewColumn.append(previewPanel, metricsPanel, imagePanel);

  layout.append(editorColumn, previewColumn);
  container.appendChild(layout);

  form.append(
    keywordField,
    geoField,
    toneField,
    secondaryField,
    sitemapField,
    contextField,
    optionsRow,
    scheduleField,
    referencesField,
  );

  const statusBar = document.createElement('div');
  statusBar.className = 'aio-status';
  container.appendChild(statusBar);

  function setStatus(message, type = 'info') {
    statusBar.className = `aio-status aio-status--${type}`;
    statusBar.textContent = message;
  }

  async function generateDraft() {
    const keyword = keywordInput.value.trim();
    if (!keyword) {
      setStatus('Masukkan kata kunci utama terlebih dahulu.', 'error');
      return;
    }

    const payload = {
      keyword,
      geo: geoSelect.value,
      tone: toneSelect.value,
      secondary_keywords: secondaryInput.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      sitemap_url: sitemapInput.value.trim(),
      additional_context: contextInput.value.trim(),
      include_images: includeImagesInput.checked,
      include_social_summary: includeSocialInput.checked,
      auto_publish: autoPublishInput.checked,
      schedule_at: scheduleInput.value ? new Date(scheduleInput.value).toISOString() : undefined,
      custom_reference_urls: referencesInput.value
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
    };

    setStatus('Menghubungi Content Intel…');
    generateButton.disabled = true;
    try {
      const data = await api('/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      editorTextarea.value = data.article_html;
      previewPanel.updatePreview(data);
      renderMetrics(metricsPanel, data.metrics);
      renderImages(imagePanel, data.images);
      setStatus('Draft berhasil dibuat.', 'success');
      document.dispatchEvent(new CustomEvent('aio:article-generated'));
    } catch (error) {
      console.error(error);
      setStatus(error.message, 'error');
    } finally {
      generateButton.disabled = false;
    }
  }

  async function loadHistoryItem(historyId) {
    if (!historyId) {
      return;
    }
    try {
      setStatus('Memuat riwayat…');
      const record = await api(`/history/${historyId}`);
      editorTextarea.value = record.article_html;
      previewPanel.updatePreview(record);
      renderMetrics(metricsPanel, record.metrics);
      renderImages(imagePanel, record.images || []);
      manualModeInput.checked = true;
      editorTextarea.readOnly = false;
      editorTextarea.classList.add('aio-editor--editable');
      setStatus(`Riwayat ${historyId} dimuat.`, 'success');
    } catch (error) {
      setStatus(error.message, 'error');
    }
  }

  generateButton.addEventListener('click', generateDraft);
  syncButton.addEventListener('click', () => {
    previewPanel.updatePreview({
      article_html: editorTextarea.value,
      meta: {
        title: 'Draft manual',
        description: 'Preview berdasarkan editor manual.',
        keywords: [],
        categories: [],
        reading_time_minutes: 0,
      },
      warnings: [],
    });
    setStatus('Preview diperbarui dari editor.', 'info');
  });

  container.loadHistoryItem = loadHistoryItem;

  return container;
}
