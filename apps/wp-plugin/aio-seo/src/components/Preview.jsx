export function createPreviewPanel(isInline = false) {
  const wrapper = document.createElement('div');
  wrapper.className = `aio-preview ${isInline ? 'aio-preview--inline' : ''}`.trim();

  const title = document.createElement('h2');
  title.textContent = 'Preview';
  wrapper.appendChild(title);

  const status = document.createElement('div');
  status.className = 'aio-preview-status';
  status.innerHTML = `
    <strong>Status:</strong> Waiting for draft
  `;
  wrapper.appendChild(status);

  const article = document.createElement('article');
  article.className = 'aio-preview-content';
  article.innerHTML = `
    <h1>Welcome to AIO Suite</h1>
    <p>
      Draft content will appear here after generation. Rich-text support and highlighting
      is provided by TipTap/Monaco in the full implementation.
    </p>
    <ul>
      <li>SEO score: —</li>
      <li>Reading time: —</li>
      <li>Primary keyword density: —</li>
    </ul>
  `;
  wrapper.appendChild(article);

  const warnings = document.createElement('div');
  warnings.className = 'aio-preview-warnings';
  warnings.innerHTML = `
    <h3>Warnings</h3>
    <ul>
      <li>No issues detected.</li>
    </ul>
  `;
  wrapper.appendChild(warnings);

  return wrapper;
}
