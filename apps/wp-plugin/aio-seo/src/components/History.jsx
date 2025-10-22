function createHistoryItem(record) {
  const item = document.createElement('li');
  item.className = 'aio-history-item';
  item.innerHTML = `
    <header>
      <strong>${record.title}</strong>
      <time>${record.date}</time>
    </header>
    <p>${record.summary}</p>
    <footer>
      <span>Related: ${record.related.join(', ') || '—'}</span>
      <button type="button" class="button-link" data-id="${record.id}">Load draft</button>
    </footer>
  `;
  return item;
}

const MOCK_HISTORY = [
  {
    id: 'draft-001',
    title: 'AI Content Guidelines',
    summary: 'Initial draft exploring AI guidelines and publishing workflow.',
    date: '2024-10-01',
    related: ['workflow', 'guidelines'],
  },
  {
    id: 'draft-002',
    title: 'Bali Travel Trends',
    summary: 'Outline generated from RSS feeds covering hospitality news.',
    date: '2024-10-04',
    related: ['travel', 'rss'],
  },
];

export function createHistoryPanel() {
  const container = document.createElement('div');
  container.className = 'aio-history';

  const title = document.createElement('h2');
  title.textContent = 'History & Relations';

  const list = document.createElement('ul');
  list.className = 'aio-history-list';
  MOCK_HISTORY.forEach((record) => list.appendChild(createHistoryItem(record)));

  list.addEventListener('click', (event) => {
    if (!(event.target instanceof HTMLElement)) {
      return;
    }
    const id = event.target.dataset.id;
    if (!id) {
      return;
    }
    // TODO: fetch draft details from the backend.
    console.log(`Load history item ${id}`);
    event.preventDefault();
  });

  container.appendChild(title);
  container.appendChild(list);
  return container;
}
