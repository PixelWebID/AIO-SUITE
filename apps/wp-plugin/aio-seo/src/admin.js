import { createEditorPanel } from './components/Editor.jsx';
import { createPreviewPanel } from './components/Preview.jsx';
import { createHistoryPanel } from './components/History.jsx';

const TABS = [
  { id: 'editor', label: 'Editor', factory: createEditorPanel },
  { id: 'preview', label: 'Preview', factory: createPreviewPanel },
  { id: 'history', label: 'History', factory: createHistoryPanel },
];

function renderTabs(root) {
  const header = document.createElement('div');
  header.className = 'aio-tabs';

  const content = document.createElement('div');
  content.className = 'aio-panel';

  TABS.forEach((tab, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'aio-tab';
    button.dataset.tab = tab.id;
    button.textContent = tab.label;
    button.addEventListener('click', () => setActiveTab(tab.id, header, content));
    if (index === 0) {
      button.classList.add('is-active');
      content.appendChild(tab.factory());
    }
    header.appendChild(button);
  });

  root.innerHTML = '';
  root.appendChild(header);
  root.appendChild(content);
}

function setActiveTab(tabId, header, content) {
  header.querySelectorAll('.aio-tab').forEach((node) => {
    node.classList.toggle('is-active', node.dataset.tab === tabId);
  });

  const tab = TABS.find((item) => item.id === tabId);
  if (!tab) {
    return;
  }

  content.innerHTML = '';
  content.appendChild(tab.factory());
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('aio-root');
  if (!root) {
    return;
  }
  renderTabs(root);
});
