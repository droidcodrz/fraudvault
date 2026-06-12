function renderKeys() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>API Keys</h1>
        <p>Manage keys for programmatic access</p>
      </div>

      <div class="card" style="margin-bottom:24px">
        <div class="card-header">
          <h2>Create New Key</h2>
        </div>
        <form id="create-key-form" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
          <div class="form-group" style="flex:1;min-width:180px;margin-bottom:0">
            <label>Key Name</label>
            <input type="text" class="form-input" name="name" placeholder="e.g. Production API">
          </div>
          <div class="form-group" style="width:140px;margin-bottom:0">
            <label>Environment</label>
            <select class="form-input" name="environment">
              <option value="live">Live</option>
              <option value="test">Test</option>
            </select>
          </div>
          <button type="submit" class="btn btn-primary">Create Key</button>
        </form>
      </div>

      <div id="new-key-banner" style="display:none"></div>

      <div class="card">
        <div class="card-header"><h2>Active Keys</h2></div>
        <div id="keys-list">
          <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
        </div>
      </div>
    </div>`;
}

async function initKeys() {
  document.getElementById('create-key-form').addEventListener('submit', createKey);
  await loadKeys();
}

async function loadKeys() {
  const container = document.getElementById('keys-list');
  try {
    const keys = await API.listKeys();
    if (keys.length === 0) {
      container.innerHTML = `<div class="empty-state"><h3>No API keys</h3><p>Create your first key above</p></div>`;
      return;
    }
    container.innerHTML = `
      <div class="table-wrap"><table>
        <thead><tr><th>Name</th><th>Prefix</th><th>Environment</th><th>Hits</th><th>Last Used</th><th></th></tr></thead>
        <tbody>
          ${keys.map(k => `
            <tr>
              <td>${escHtml(k.name || 'Unnamed')}</td>
              <td><code>${escHtml(k.prefix)}...</code></td>
              <td><span class="badge badge-${k.environment}">${k.environment}</span></td>
              <td>${(k.hit_count || 0).toLocaleString()}</td>
              <td>${k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}</td>
              <td><button class="btn btn-ghost btn-sm delete-key-btn" data-id="${k.id}">Revoke</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>`;

    container.querySelectorAll('.delete-key-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Revoke this API key? This cannot be undone.')) return;
        try {
          await API.deleteKey(btn.dataset.id);
          App.toast('Key revoked', 'success');
          await loadKeys();
        } catch (err) {
          App.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escHtml(err.message)}</p></div>`;
  }
}

async function createKey(e) {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const data = await API.createKey(fd.get('name'), fd.get('environment'));
    const banner = document.getElementById('new-key-banner');
    banner.style.display = '';
    banner.innerHTML = `
      <div class="card" style="margin-bottom:24px;border-color:var(--success)">
        <div class="card-header"><h2 style="color:var(--success)">Key Created — Copy It Now!</h2></div>
        <p style="color:var(--text-muted);margin-bottom:12px;font-size:0.85rem">
          This is the only time you'll see the full key. Save it somewhere safe.
        </p>
        <div class="key-display">
          <span id="raw-key-text">${escHtml(data.key)}</span>
          <button onclick="navigator.clipboard.writeText(document.getElementById('raw-key-text').textContent);App.toast('Copied!','success')">Copy</button>
        </div>
      </div>`;
    e.target.reset();
    await loadKeys();
  } catch (err) {
    App.toast(err.message, 'error');
  }
}
