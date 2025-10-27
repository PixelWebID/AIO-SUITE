const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'llama', label: 'Meta Llama' },
];

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
  return response.json();
}

function createInput(label, type = 'text') {
  const wrapper = document.createElement('label');
  wrapper.className = 'aio-field';
  const span = document.createElement('span');
  span.textContent = label;
  const input = document.createElement('input');
  input.type = type;
  wrapper.appendChild(span);
  wrapper.appendChild(input);
  return { wrapper, input };
}

async function renderSettings(root) {
  root.innerHTML = '<p>Loading settings…</p>';
  try {
    const settings = await request('/settings');

    const form = document.createElement('div');
    form.className = 'aio-settings';

    const intelField = createInput('Content Intel Service URL');
    intelField.input.value = settings.content_intel_url;
    intelField.input.placeholder = 'https://content-intel.internal';

    const socialField = createInput('Social Hub Service URL');
    socialField.input.value = settings.social_hub_url;
    socialField.input.placeholder = 'https://social-hub.internal';

    const providerField = document.createElement('label');
    providerField.className = 'aio-field';
    providerField.innerHTML = '<span>Default Provider</span>';
    const providerSelect = document.createElement('select');
    PROVIDERS.forEach((provider) => {
      const option = document.createElement('option');
      option.value = provider.value;
      option.textContent = provider.label;
      option.selected = provider.value === settings.default_provider;
      providerSelect.appendChild(option);
    });
    providerField.appendChild(providerSelect);

    const autoPublish = document.createElement('label');
    autoPublish.className = 'aio-field aio-field--inline';
    autoPublish.innerHTML = `
      <input type="checkbox" />
      <span>Aktifkan auto publish untuk post baru</span>
    `;
    const autoCheckbox = autoPublish.querySelector('input');
    autoCheckbox.checked = settings.auto_publish;

    const sitesField = document.createElement('label');
    sitesField.className = 'aio-field';
    sitesField.innerHTML = `
      <span>Multi-site REST endpoints (satu per baris)</span>
      <textarea rows="4" placeholder="https://site-a.com\nhttps://site-b.com"></textarea>
    `;
    const sitesTextarea = sitesField.querySelector('textarea');
    sitesTextarea.value = (settings.sites || []).join('\n');

    const apiWrapper = document.createElement('label');
    apiWrapper.className = 'aio-field';
    apiWrapper.innerHTML = `
      <span>Provider API Key (disimpan terenkripsi)</span>
      <input type="password" placeholder="••••••" autocomplete="off" />
    `;
    const apiInput = apiWrapper.querySelector('input');

    const keyNotice = document.createElement('p');
    keyNotice.className = 'description';
    keyNotice.textContent = settings.has_api_key
      ? 'Kunci sudah tersimpan. Isi kolom di atas untuk mengganti.'
      : 'Belum ada kunci tersimpan. Isi kolom di atas untuk menyimpan.';

    const clearKeyButton = document.createElement('button');
    clearKeyButton.type = 'button';
    clearKeyButton.className = 'button';
    clearKeyButton.textContent = 'Hapus kunci tersimpan';
    clearKeyButton.disabled = !settings.has_api_key;

    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.className = 'button button-primary';
    saveButton.textContent = 'Simpan Pengaturan';

    const notice = document.createElement('div');

    clearKeyButton.addEventListener('click', async () => {
      try {
        await request('/settings', {
          method: 'POST',
          body: JSON.stringify({ clear_api_key: true }),
        });
        clearKeyButton.disabled = true;
        keyNotice.textContent = 'Kunci terenkripsi telah dihapus.';
      } catch (error) {
        alert(error.message);
      }
    });

    saveButton.addEventListener('click', async () => {
      saveButton.disabled = true;
      notice.className = 'notice notice-info';
      notice.innerHTML = '<p>Menyimpan perubahan…</p>';
      root.prepend(notice);
      try {
        const payload = {
          content_intel_url: intelField.input.value.trim(),
          social_hub_url: socialField.input.value.trim(),
          default_provider: providerSelect.value,
          auto_publish: autoCheckbox.checked,
          sites: sitesTextarea.value
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean),
        };
        if (apiInput.value.trim()) {
          payload.api_key = apiInput.value.trim();
        }

        const response = await request('/settings', {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        apiInput.value = '';
        clearKeyButton.disabled = !response.has_api_key;
        keyNotice.textContent = response.has_api_key
          ? 'Kunci terenkripsi tersimpan.'
          : 'Belum ada kunci tersimpan.';

        notice.className = 'notice notice-success';
        notice.innerHTML = '<p>Pengaturan berhasil disimpan.</p>';
      } catch (error) {
        notice.className = 'notice notice-error';
        notice.innerHTML = `<p>${error.message}</p>`;
      } finally {
        saveButton.disabled = false;
        setTimeout(() => notice.remove(), 4000);
      }
    });

    form.append(
      intelField.wrapper,
      socialField.wrapper,
      providerField,
      autoPublish,
      sitesField,
      apiWrapper,
      keyNotice,
      clearKeyButton,
      saveButton,
    );

    root.innerHTML = '';
    root.appendChild(form);
  } catch (error) {
    root.innerHTML = `<div class="notice notice-error"><p>${error.message}</p></div>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('aio-settings-root');
  if (root) {
    renderSettings(root);
  }
});
