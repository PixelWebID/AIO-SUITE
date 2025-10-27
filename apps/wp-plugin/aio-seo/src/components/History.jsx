const env = window.AIO_SUITE_ENV || {};

async function fetchHistory(limit = 12) {
  const response = await fetch(`${env.restUrl}/history?limit=${limit}`, {
    headers: { 'X-WP-Nonce': env.nonce },
  });
  if (!response.ok) {
    throw new Error('Gagal memuat riwayat');
  }
  return response.json();
}

export function createHistoryPanel(onSelect) {
  const container = document.createElement('div');
  container.className = 'aio-history';

  const title = document.createElement('h2');
  title.textContent = 'Riwayat & Relasi';

  const list = document.createElement('ul');
  list.className = 'aio-history-list';

  const emptyState = document.createElement('p');
  emptyState.className = 'aio-history-empty';
  emptyState.textContent = 'Belum ada riwayat.';

  container.append(title, emptyState, list);

  async function load() {
    try {
      const payload = await fetchHistory();
      const history = payload.history || payload;
      list.innerHTML = '';
      if (!history.length) {
        emptyState.style.display = 'block';
        return;
      }
      emptyState.style.display = 'none';
      history.forEach((record) => {
        const item = document.createElement('li');
        item.className = 'aio-history-item';
        item.innerHTML = `
          <header>
            <strong>${record.meta?.title || record.keyword}</strong>
            <time>${new Date(record.created_at || Date.now()).toLocaleString()}</time>
          </header>
          <p>${record.meta?.description || 'Tidak ada ringkasan.'}</p>
          <footer>
            <span>${(record.meta?.keywords || []).join(', ')}</span>
            <button type="button" class="button-link">Muat draft</button>
          </footer>
        `;
        const button = item.querySelector('button');
        button.addEventListener('click', () => {
          if (typeof onSelect === 'function') {
            onSelect(record.id);
          }
        });
        list.appendChild(item);
      });
    } catch (error) {
      emptyState.style.display = 'block';
      emptyState.textContent = error.message;
    }
  }

  container.reload = load;
  load();

  return container;
}
