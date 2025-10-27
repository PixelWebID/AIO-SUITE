
function sanitizeHtml(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html || '', 'text/html');
  doc.querySelectorAll('script, style').forEach((node) => node.remove());
  return doc.body.innerHTML;
}

function highlightKeywords(html, keywords) {
  if (!keywords || !keywords.length) {
    return html;
  }
  let output = html;
  keywords.forEach((keyword) => {
    if (!keyword) {
      return;
    }
    const pattern = new RegExp(`(>[^<]*)(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})([^<]*<)`, 'gi');
    output = output.replace(pattern, (match, before, word, after) => `${before}<mark class="aio-keyword">${word}</mark>${after}`);
  });
  return output;
}

function applyHeadingDecorations(root) {
  root.querySelectorAll('h2, h3').forEach((heading) => {
    heading.classList.add('aio-heading');
  });
}
export function createEditorPanel({ onContentChange } = {}) {
  const container = document.createElement('div');
  container.className = 'aio-editor-panel';

  const toolbar = document.createElement('div');
  toolbar.className = 'aio-editor-toolbar';
  toolbar.innerHTML = `
    <button type="button" data-command="bold">B</button>
    <button type="button" data-command="italic"><em>I</em></button>
    <button type="button" data-command="insertHeading" data-level="2">H2</button>
    <button type="button" data-command="insertHeading" data-level="3">H3</button>
  `;

  const toggleRow = document.createElement('label');
  toggleRow.className = 'aio-field aio-field--inline aio-editor-toggle';
  const manualToggle = document.createElement('input');
  manualToggle.type = 'checkbox';
  toggleRow.append(manualToggle, document.createTextNode('Manual edit mode'));

  const editor = document.createElement('div');
  editor.className = 'aio-editor-area';
  editor.contentEditable = false;

  let keywords = [];
  let changeTimer = null;

  function emitChange() {
    if (onContentChange) {
      onContentChange(editor.innerHTML);
    }
  }

  function scheduleChange() {
    clearTimeout(changeTimer);
    changeTimer = setTimeout(() => emitChange(), 300);
  }

  toolbar.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button || !manualToggle.checked) {
      return;
    }
    const command = button.dataset.command;
    if (command === 'insertHeading') {
      document.execCommand('formatBlock', false, `H${button.dataset.level}`);
    } else {
      document.execCommand(command, false, null);
    }
    applyHeadingDecorations(editor);
    scheduleChange();
  });

  let lastSnapshot = '';

  manualToggle.addEventListener('change', () => {
    const enabled = manualToggle.checked;
    editor.contentEditable = enabled;
    editor.classList.toggle('is-editable', enabled);
    if (enabled) {
      editor.innerHTML = sanitizeHtml(lastSnapshot);
      applyHeadingDecorations(editor);
    } else {
      setContent(editor.innerHTML);
    }
  });

  editor.addEventListener('input', () => {
    applyHeadingDecorations(editor);
    scheduleChange();
  });

  function setContent(html, meta = {}) {
    const normalized = sanitizeHtml(html || '');
    lastSnapshot = normalized;
    editor.innerHTML = highlightKeywords(normalized, keywords);
    applyHeadingDecorations(editor);
    if (meta && meta.keywords) {
      setKeywords(meta.keywords);
    }
  }

  function setKeywords(list) {
    keywords = Array.isArray(list) ? list.filter(Boolean) : [];
    if (lastSnapshot) {
      editor.innerHTML = highlightKeywords(lastSnapshot, keywords);
      applyHeadingDecorations(editor);
    }
  }

  container.append(toolbar, toggleRow, editor);

  return {
    node: container,
    setContent,
    setKeywords,
    getContent: () => editor.innerHTML,
  };
}

