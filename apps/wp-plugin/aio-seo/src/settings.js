
const env = window.AIO_SUITE_ENV || {};

async function request(path, options = {}) {
  const response = await fetch(`${env.restUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-WP-Nonce': env.nonce,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function notify(container, message, type = 'info') {
  container.className = `aio-status aio-status--${type}`;
  container.textContent = message;
}
function buildFallbackList(order) {
  const list = document.createElement('ul');
  list.className = 'aio-fallback-list';
  order.forEach((provider) => {
    const item = document.createElement('li');
    item.draggable = true;
    item.dataset.value = provider;
    item.textContent = provider;
    list.appendChild(item);
  });

  let dragEl = null;
  list.addEventListener('dragstart', (event) => {
    dragEl = event.target;
    event.dataTransfer.effectAllowed = 'move';
  });
  list.addEventListener('dragover', (event) => {
    event.preventDefault();
    const target = event.target.closest('li');
    if (!target || target === dragEl) {
      return;
    }
    const rect = target.getBoundingClientRect();
    const next = (event.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
    list.insertBefore(dragEl, next ? target.nextSibling : target);
  });
  list.addEventListener('dragend', () => {
    dragEl = null;
  });

  return list;
}

function getFallbackOrder(list) {
  return Array.from(list.querySelectorAll('li')).map((item) => item.dataset.value);
}
async function testSiteConnection(domain, token, output) {
  if (!domain || !token) {
    notify(output, 'Isi domain dan token terlebih dahulu.', 'error');
    return;
  }
  notify(output, 'Menguji koneksi…');
  try {
    const response = await fetch(`${domain.replace(/\/$/, '')}/wp-json/aio/v1/ping`, {
      headers: {
        'X-AIO-Token': token,
      },
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    notify(output, 'Koneksi berhasil.', 'success');
  } catch (error) {
    notify(output, `Gagal: ${error.message}`, 'error');
  }
}

function buildSitesSection(data = []) {
  const container = document.createElement('div');
  container.className = 'aio-sites';

  const list = document.createElement('div');
  list.className = 'aio-sites-list';

  function addRow(site = { domain: '', token: '' }) {
    const row = document.createElement('div');
    row.className = 'aio-sites-row';

    const domain = document.createElement('input');
    domain.type = 'url';
    domain.placeholder = 'https://subsite.com';
    domain.value = site.domain || '';

    const token = document.createElement('input');
    token.type = 'text';
    token.placeholder = 'Token';
    token.value = site.token || '';

    const testButton = document.createElement('button');
    testButton.type = 'button';
    testButton.className = 'button';
    testButton.textContent = 'Test';

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'button-link';
    removeButton.textContent = 'Hapus';

    const status = document.createElement('div');
    status.className = 'aio-status';

    testButton.addEventListener('click', () => testSiteConnection(domain.value.trim(), token.value.trim(), status));
    removeButton.addEventListener('click', () => {
      row.remove();
    });

    row.append(domain, token, testButton, removeButton, status);
    list.appendChild(row);
  }

  data.forEach(addRow);

  const addButton = document.createElement('button');
  addButton.type = 'button';
  addButton.className = 'button';
  addButton.textContent = 'Tambah Site';
  addButton.addEventListener('click', () => addRow());

  container.append(list, addButton);

  return {
    container,
    getValues() {
      return Array.from(list.querySelectorAll('.aio-sites-row')).map((row) => {
        const [domain, token] = row.querySelectorAll('input');
        return {
          domain: domain.value.trim(),
          token: token.value.trim(),
        };
      }).filter((site) => site.domain && site.token);
    },
  };
}
function buildKeyFields(keys = {}) {
  const wrapper = document.createElement('div');
  wrapper.className = 'aio-settings-grid';

  const items = [
    { id: 'openai', label: 'OpenAI API Key' },
    { id: 'deepseek', label: 'DeepSeek API Key' },
    { id: 'openrouter', label: 'OpenRouter API Key' },
    { id: 'gemini', label: 'Google Gemini API Key' },
    { id: 'llama', label: 'Llama Endpoint Token' },
    { id: 'pexels', label: 'Pexels API Key' },
    { id: 'pixabay', label: 'Pixabay API Key' },
    { id: 'trends_username', label: 'Google Trends Username' },
    { id: 'trends_password', label: 'Google Trends Password' },
  ];

  const fields = {};
  items.forEach((item) => {
    const field = document.createElement('label');
    field.className = 'aio-field';
    field.innerHTML = `<span>${item.label}</span>`;
    const input = document.createElement('input');
    input.type = item.id.includes('password') ? 'password' : 'text';
    input.value = keys[item.id] || '';
    field.appendChild(input);
    wrapper.appendChild(field);
    fields[item.id] = input;
  });

  return {
    wrapper,
    getValues() {
      const output = {};
      Object.keys(fields).forEach((key) => {
        if (fields[key].value.trim()) {
          output[key] = fields[key].value.trim();
        }
      });
      return output;
    },
  };
}
async function renderSettings() {
  const root = document.getElementById('aio-settings-root');
  if (!root) {
    return;
  }

  root.innerHTML = '<p>Memuat pengaturan…</p>';

  try {
    const settings = await request('/settings');

    const form = document.createElement('div');
    form.className = 'aio-settings-layout';

    const statusBar = document.createElement('div');
    statusBar.className = 'aio-status';

    const intelField = document.createElement('input');
    intelField.type = 'url';
    intelField.value = settings.content_intel_url;
    intelField.placeholder = 'https://content-intel.local';

    const socialField = document.createElement('input');
    socialField.type = 'url';
    socialField.value = settings.social_hub_url;
    socialField.placeholder = 'https://social-hub.local';

    const apiModeBackend = document.createElement('input');
    apiModeBackend.type = 'radio';
    apiModeBackend.name = 'api-mode';
    apiModeBackend.value = 'backend';

    const apiModeWp = document.createElement('input');
    apiModeWp.type = 'radio';
    apiModeWp.name = 'api-mode';
    apiModeWp.value = 'wp';

    if (settings.api_mode === 'wp') {
      apiModeWp.checked = true;
    } else {
      apiModeBackend.checked = true;
    }

    const fallbackList = buildFallbackList(settings.fallback_order || []);
    const keysSection = buildKeyFields();

    const sitesSection = buildSitesSection(settings.sites || []);

    const autoPublish = document.createElement('input');
    autoPublish.type = 'checkbox';
    autoPublish.checked = !!settings.auto_publish;

    const autoRegenerate = document.createElement('input');
    autoRegenerate.type = 'checkbox';
    autoRegenerate.checked = !!settings.auto_regenerate;

    const defaultGeo = document.createElement('select');
    ['ID', 'US', 'SG', 'MY', 'AU'].forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      defaultGeo.appendChild(option);
    });
    defaultGeo.value = settings.default_geo || 'ID';

    const defaultTone = document.createElement('select');
    ['neutral', 'formal', 'casual', 'authoritative', 'friendly'].forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      defaultTone.appendChild(option);
    });
    defaultTone.value = settings.default_tone || 'neutral';

    const defaultLang = document.createElement('select');
    ['id', 'en', 'ms', 'zh', 'fr'].forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      defaultLang.appendChild(option);
    });
    defaultLang.value = settings.default_language || 'id';

    const validateBtn = document.createElement('button');
    validateBtn.type = 'button';
    validateBtn.className = 'button';
    validateBtn.textContent = 'Validate Backends';

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'button button-primary';
    saveBtn.textContent = 'Simpan Pengaturan';

    const sectionGeneral = document.createElement('section');
    sectionGeneral.className = 'aio-settings-card';
    sectionGeneral.innerHTML = '<h2>Backend</h2>';
    sectionGeneral.appendChild(labeledField('Content Intel URL', intelField));
    sectionGeneral.appendChild(labeledField('Social Hub URL', socialField));

    const modeWrapper = document.createElement('div');
    modeWrapper.className = 'aio-radio-group';
    modeWrapper.innerHTML = '<span>API Key Mode</span>';

    const backendLabel = document.createElement('label');
    backendLabel.className = 'aio-field aio-field--inline';
    backendLabel.appendChild(apiModeBackend);
    backendLabel.appendChild(document.createTextNode('Backend (ENV managed)'));

    const wpLabel = document.createElement('label');
    wpLabel.className = 'aio-field aio-field--inline';
    wpLabel.appendChild(apiModeWp);
    wpLabel.appendChild(document.createTextNode('Simpan terenkripsi di WordPress'));

    modeWrapper.append(backendLabel, wpLabel);
    sectionGeneral.appendChild(modeWrapper);
    sectionGeneral.appendChild(validateBtn);
    sectionGeneral.appendChild(fallbackList);

    const sectionKeys = document.createElement('section');
    sectionKeys.className = 'aio-settings-card';
    sectionKeys.innerHTML = '<h2>API Keys</h2>';
    sectionKeys.appendChild(keysSection.wrapper);
    sectionKeys.style.display = settings.api_mode === 'wp' ? 'block' : 'none';

    const sectionOptions = document.createElement('section');
    sectionOptions.className = 'aio-settings-card';
    sectionOptions.innerHTML = '<h2>Defaults & Toggles</h2>';
    sectionOptions.appendChild(labeledToggle('Auto publish', autoPublish));
    sectionOptions.appendChild(labeledToggle('Auto regenerate', autoRegenerate));
    sectionOptions.appendChild(labeledField('Default geo', defaultGeo));
    sectionOptions.appendChild(labeledField('Default tone', defaultTone));
    sectionOptions.appendChild(labeledField('Default language', defaultLang));

    const sectionSites = document.createElement('section');
    sectionSites.className = 'aio-settings-card';
    sectionSites.innerHTML = '<h2>Multi-site Credentials</h2>';
    sectionSites.appendChild(sitesSection.container);

    form.append(sectionGeneral, sectionKeys, sectionOptions, sectionSites, saveBtn, statusBar);
    root.innerHTML = '';
    root.appendChild(form);

    function refreshKeyVisibility() {
      sectionKeys.style.display = apiModeWp.checked ? 'block' : 'none';
    }

    apiModeBackend.addEventListener('change', refreshKeyVisibility);
    apiModeWp.addEventListener('change', refreshKeyVisibility);

    validateBtn.addEventListener('click', async () => {
      notify(statusBar, 'Memvalidasi backends…');
      try {
        const result = await request('/settings/validate', {
          method: 'POST',
          body: JSON.stringify({
            content_intel_url: intelField.value.trim(),
            social_hub_url: socialField.value.trim(),
          }),
        });
        const parts = [];
        if (result.content_intel) {
          parts.push(`Content Intel: ${result.content_intel.ok ? 'OK' : 'Error'} (${result.content_intel.detail})`);
        }
        if (result.social_hub) {
          parts.push(`Social Hub: ${result.social_hub.ok ? 'OK' : 'Error'} (${result.social_hub.detail})`);
        }
        notify(statusBar, parts.join(' | ') || 'Tidak ada respon.');
      } catch (error) {
        notify(statusBar, error.message, 'error');
      }
    });

    saveBtn.addEventListener('click', async () => {
      notify(statusBar, 'Menyimpan…');
      saveBtn.disabled = true;
      try {
        const payload = {
          content_intel_url: intelField.value.trim(),
          social_hub_url: socialField.value.trim(),
          api_mode: apiModeWp.checked ? 'wp' : 'backend',
          fallback_order: getFallbackOrder(fallbackList),
          auto_publish: autoPublish.checked,
          auto_regenerate: autoRegenerate.checked,
          default_tone: defaultTone.value,
          default_language: defaultLang.value,
          default_geo: defaultGeo.value,
          sites: sitesSection.getValues(),
        };
        if (apiModeWp.checked) {
          payload.keys = keysSection.getValues();
        }
        await request('/settings', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        notify(statusBar, 'Pengaturan disimpan.', 'success');
      } catch (error) {
        notify(statusBar, error.message, 'error');
      } finally {
        saveBtn.disabled = false;
      }
    });
  } catch (error) {
    root.innerHTML = `<div class="notice notice-error"><p>${error.message}</p></div>`;
  }
}
function labeledField(label, node) {
  const wrapper = document.createElement('label');
  wrapper.className = 'aio-field';
  wrapper.innerHTML = `<span>${label}</span>`;
  wrapper.appendChild(node);
  return wrapper;
}

function labeledToggle(label, input) {
  const wrapper = document.createElement('label');
  wrapper.className = 'aio-field aio-field--inline';
  wrapper.appendChild(input);
  wrapper.appendChild(document.createTextNode(label));
  return wrapper;
}

document.addEventListener('DOMContentLoaded', renderSettings);



