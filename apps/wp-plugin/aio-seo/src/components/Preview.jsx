export function createPreviewPanel() {
  const wrapper = document.createElement('div');
  wrapper.className = 'aio-preview';

  const title = document.createElement('h2');
  title.textContent = 'Preview';

  const status = document.createElement('div');
  status.className = 'aio-preview-status';
  status.innerHTML = '<strong>Status:</strong> Belum ada draft.';

  const metaBox = document.createElement('div');
  metaBox.className = 'aio-preview-meta';

  const article = document.createElement('article');
  article.className = 'aio-preview-content';
  article.innerHTML = '<p>Draft akan ditampilkan setelah proses generate selesai.</p>';

  const warnings = document.createElement('div');
  warnings.className = 'aio-preview-warnings';
  warnings.innerHTML = '<h3>Peringatan</h3><ul><li>Tidak ada.</li></ul>';

  wrapper.append(title, status, metaBox, article, warnings);

  wrapper.updatePreview = (data) => {
    status.innerHTML = '<strong>Status:</strong> Draft terbaru siap ditinjau.';

    const meta = data.meta || {};
    metaBox.innerHTML = `
      <div><strong>Judul:</strong> ${meta.title || 'Tanpa judul'}</div>
      <div><strong>Deskripsi:</strong> ${meta.description || '-'}</div>
      <div><strong>Kata kunci:</strong> ${(meta.keywords || []).join(', ') || '-'}</div>
      <div><strong>Kategori:</strong> ${(meta.categories || []).join(', ') || '-'}</div>
      <div><strong>Waktu baca:</strong> ~${meta.reading_time_minutes || 0} menit</div>
    `;

    article.innerHTML = data.article_html;

    const warningList = data.warnings && data.warnings.length
      ? data.warnings.map((item) => `<li>${item}</li>`).join('')
      : '<li>Tidak ada.</li>';
    warnings.innerHTML = `<h3>Peringatan</h3><ul>${warningList}</ul>`;
  };

  return wrapper;
}
