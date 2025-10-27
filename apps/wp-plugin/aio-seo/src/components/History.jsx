
function formatDate(value) {
  if (!value) {
    return '-';
  }
  return new Date(value).toLocaleString();
}

export function createHistoryPanel({ onSelect, fetchHistory }) {
  const container = document.createElement('div');
  container.className = 'aio-history-panel';

  const controls = document.createElement('div');
  controls.className = 'aio-history-controls';

  const statusSelect = document.createElement('select');
  ['', 'draft', 'published', 'scheduled'].forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value ? value : 'Semua status';
    statusSelect.appendChild(option);
  });

  const fromInput = document.createElement('input');
  fromInput.type = 'date';
  const toInput = document.createElement('input');
  toInput.type = 'date';

  const filterButton = document.createElement('button');
  filterButton.type = 'button';
  filterButton.className = 'button';
  filterButton.textContent = 'Filter';

  controls.append(statusSelect, fromInput, toInput, filterButton);

  const list = document.createElement('ul');
  list.className = 'aio-history-list';

  const emptyState = document.createElement('p');
  emptyState.className = 'aio-history-empty';
  emptyState.textContent = 'Belum ada riwayat.';

  container.append(controls, emptyState, list);

  async function load(query = '') {
    const qs = new URLSearchParams();
    if (statusSelect.value) {
      qs.set('status', statusSelect.value);
    }
    if (fromInput.value) {
      qs.set('date_from', fromInput.value);
    }
    if (toInput.value) {
      qs.set('date_to', toInput.value);
    }
    if (query) {
      qs.append('extra', query);
    }

    list.innerHTML = '';
    emptyState.textContent = 'Memuat…';
    try {
      const data = await fetchHistory(`?${qs.toString()}`);
      const history = data.history || [];
      if (!history.length) {
        emptyState.textContent = 'Belum ada riwayat.';
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
            <time>${formatDate(record.created_at)}</time>
          </header>
          <p>${record.meta?.description || 'Tanpa deskripsi.'}</p>
          <footer>
            <span>Status: ${record.status}</span>
            <button type="button" class="button-link">Lihat</button>
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
      emptyState.textContent = error.message;
      emptyState.style.display = 'block';
    }
  }

  filterButton.addEventListener('click', () => load());

  return {
    node: container,
    reload: () => load(),
  };
}

