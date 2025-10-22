(function () {
  const root = document.getElementById('aio-root');
  if (!root) return;
  // Build a simple UI for demonstration.  In a real project this would be
  // replaced with a React or other framework application.
  root.innerHTML = `
    <div style="margin:10px 0;">
      <label for="aio-keyword">Keyword:</label>
      <input id="aio-keyword" placeholder="Enter a keyword" style="margin-right:8px; padding:4px;" />
      <button id="aio-generate" class="button button-primary">Generate</button>
    </div>
    <div id="aio-output" style="background:#fff; border:1px solid #ccd0d4; padding:10px;"></div>
  `;
  const btn = document.getElementById('aio-generate');
  btn.addEventListener('click', async () => {
    const keywordEl = document.getElementById('aio-keyword');
    const keyword = keywordEl.value.trim();
    if (!keyword) {
      alert('Please enter a keyword');
      return;
    }
    const out = document.getElementById('aio-output');
    out.innerHTML = 'Generating...';
    try {
      const response = await fetch('/wp-json/aio/v1/ping');
      const data = await response.json();
      out.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      out.innerHTML = `<strong>Error:</strong> ${err.message}`;
    }
  });
})();