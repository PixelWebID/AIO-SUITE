import { createPreviewPanel } from './Preview.jsx';

function createSection(title, content) {
  const section = document.createElement('section');
  section.className = 'aio-section';

  const heading = document.createElement('h2');
  heading.textContent = title;

  section.appendChild(heading);
  section.appendChild(content);
  return section;
}

function createToolbar() {
  const toolbar = document.createElement('div');
  toolbar.className = 'aio-toolbar';
  toolbar.innerHTML = `
    <button type="button" data-action="outline" class="button">Outline</button>
    <button type="button" data-action="rewrite" class="button">Rewrite</button>
    <button type="button" data-action="optimize" class="button">Optimize SEO</button>
  `;
  toolbar.addEventListener('click', (event) => {
    if (!(event.target instanceof HTMLElement)) {
      return;
    }
    const action = event.target.dataset.action;
    if (!action) {
      return;
    }
    // TODO: integrate with TipTap/Monaco actions.
    console.log(`Trigger editor action: ${action}`);
  });
  return toolbar;
}

function createEditorCanvas() {
  const editor = document.createElement('textarea');
  editor.id = 'aio-editor';
  editor.rows = 20;
  editor.placeholder = 'Start drafting your article...';
  editor.className = 'aio-editor';
  return editor;
}

function createInsightPane() {
  const insights = document.createElement('aside');
  insights.className = 'aio-insights';
  insights.innerHTML = `
    <h3>Live Insights</h3>
    <ul>
      <li data-insight="readability">Readability: —</li>
      <li data-insight="keywords">Keywords: —</li>
      <li data-insight="warnings">Warnings: —</li>
    </ul>
  `;
  return insights;
}

export function createEditorPanel() {
  const container = document.createElement('div');
  container.className = 'aio-editor-screen';

  const layout = document.createElement('div');
  layout.className = 'aio-editor-layout';

  const editorColumn = document.createElement('div');
  editorColumn.className = 'aio-editor-column';
  editorColumn.appendChild(createToolbar());
  editorColumn.appendChild(createEditorCanvas());

  const previewColumn = document.createElement('div');
  previewColumn.className = 'aio-preview-column';
  previewColumn.appendChild(createPreviewPanel(true));
  previewColumn.appendChild(createInsightPane());

  layout.appendChild(editorColumn);
  layout.appendChild(previewColumn);

  container.appendChild(createSection('Article Workspace', layout));

  const footer = document.createElement('div');
  footer.className = 'aio-panel-footer';

  const generateBtn = document.createElement('button');
  generateBtn.className = 'button button-primary';
  generateBtn.type = 'button';
  generateBtn.textContent = 'Generate Draft';

  generateBtn.addEventListener('click', async () => {
    const keyword = prompt('Keyword for generation', 'travel tips bali');
    if (!keyword) {
      return;
    }
    const output = container.querySelector('[data-insight="keywords"]');
    if (output) {
      output.textContent = `Keywords: ${keyword}`;
    }

    const editor = container.querySelector('#aio-editor');
    if (editor) {
      editor.value = `# ${keyword}\n\nThis is a mock article draft generated for ${keyword}.`;
    }

    try {
      const response = await fetch('/wp-json/aio/v1/ping');
      const data = await response.json();
      const readability = container.querySelector('[data-insight="readability"]');
      if (readability) {
        readability.textContent = `Readability: ${(data.time % 10) + 60}/100`;
      }
    } catch (error) {
      console.error('Failed to ping backend', error);
    }
  });

  footer.appendChild(generateBtn);
  container.appendChild(footer);

  return container;
}
