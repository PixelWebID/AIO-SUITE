const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'llama', label: 'Meta Llama' },
];

function buildProviderOptions(selected = 'openai') {
  return PROVIDERS.map((provider) => {
    const option = document.createElement('option');
    option.value = provider.value;
    option.textContent = provider.label;
    option.selected = provider.value === selected;
    return option;
  });
}

function renderSettings(root) {
  root.innerHTML = '';

  const wrapper = document.createElement('div');
  wrapper.className = 'aio-settings';

  const apiField = document.createElement('label');
  apiField.className = 'aio-field';
  apiField.innerHTML = `
    <span>Primary API Key</span>
    <input type="password" id="aio-api-key" placeholder="sk-********" autocomplete="off" />
  `;

  const providerField = document.createElement('label');
  providerField.className = 'aio-field';
  providerField.innerHTML = `
    <span>Default Provider</span>
    <select id="aio-provider"></select>
  `;
  const providerSelect = providerField.querySelector('select');
  buildProviderOptions().forEach((node) => providerSelect.appendChild(node));

  const networkWrapper = document.createElement('fieldset');
  networkWrapper.className = 'aio-fieldset';
  networkWrapper.innerHTML = `
    <legend>Network Settings</legend>
    <label class="aio-field aio-field--inline">
      <input type="checkbox" id="aio-network-sync" />
      <span>Share settings across multisite network</span>
    </label>
    <label class="aio-field aio-field--inline">
      <input type="checkbox" id="aio-network-enforce" />
      <span>Enforce provider & limits for child sites</span>
    </label>
  `;

  const buttonRow = document.createElement('div');
  buttonRow.className = 'aio-actions';

  const saveButton = document.createElement('button');
  saveButton.className = 'button button-primary';
  saveButton.type = 'button';
  saveButton.textContent = 'Save Settings';
  saveButton.addEventListener('click', () => {
    const payload = {
      apiKey: document.getElementById('aio-api-key').value.trim(),
      provider: document.getElementById('aio-provider').value,
      networkSync: document.getElementById('aio-network-sync').checked,
      networkEnforce: document.getElementById('aio-network-enforce').checked,
    };
    // TODO: Replace with real REST call.
    console.table(payload);
    const notice = document.createElement('div');
    notice.className = 'notice notice-success';
    notice.innerHTML = '<p>Settings saved locally (mock).</p>';
    root.prepend(notice);
    setTimeout(() => notice.remove(), 4000);
  });

  buttonRow.appendChild(saveButton);

  [apiField, providerField, networkWrapper, buttonRow].forEach((node) =>
    wrapper.appendChild(node),
  );

  root.appendChild(wrapper);
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('aio-settings-root');
  if (!root) {
    return;
  }
  renderSettings(root);
});
