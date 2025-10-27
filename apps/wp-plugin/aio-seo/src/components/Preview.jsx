
function sanitize(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html || '', 'text/html');
  doc.querySelectorAll('script, style').forEach((node) => node.remove());
  return doc.body.innerHTML;
}

function renderWarnings(list, warnings) {
  list.innerHTML = '';
  if (!warnings || !warnings.length) {
    const item = document.createElement('span');
    item.className = 'aio-badge aio-badge--success';
    item.textContent = 'No warnings';
    list.appendChild(item);
    return;
  }
  warnings.forEach((code) => {
    const badge = document.createElement('span');
    badge.className = 'aio-badge aio-badge--warning';
    badge.textContent = code;
    list.appendChild(badge);
  });
}

export function createPreviewPanel() {
  const container = document.createElement('div');
  container.className = 'aio-preview-panel';

  const metaBox = document.createElement('div');
  metaBox.className = 'aio-preview-meta';

  const warningBox = document.createElement('div');
  warningBox.className = 'aio-preview-warnings';

  const articleBox = document.createElement('article');
  articleBox.className = 'aio-preview-article';
  articleBox.innerHTML = '<p>Preview akan tampil di sini.</p>';

  container.append(metaBox, warningBox, articleBox);

  function update(article, warnings = []) {
    const meta = article.meta || {};
    metaBox.innerHTML = `
      <div><strong>Judul:</strong> ${meta.title || '-'}</div>
      <div><strong>Deskripsi:</strong> ${meta.description || '-'}</div>
      <div><strong>Kata kunci:</strong> ${(meta.keywords || []).join(', ') || '-'}</div>
      <div><strong>Kategori:</strong> ${(meta.categories || []).join(', ') || '-'}</div>
      <div><strong>Waktu baca:</strong> ${meta.reading_time_minutes ? `${meta.reading_time_minutes} menit` : '—'}</div>
    `;

    renderWarnings(warningBox, warnings);

    articleBox.innerHTML = sanitize(article.article_html || '');
  }

  return {
    node: container,
    update,
  };
}

