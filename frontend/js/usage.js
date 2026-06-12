function renderUsage() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Usage</h1>
        <p>Your current billing period statistics</p>
      </div>
      <div id="usage-content">
        <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
      </div>
    </div>`;
}

async function initUsage() {
  try {
    const u = await API.getUsage();
    const limit = u.plan_limit === -1 ? Infinity : u.plan_limit;
    const pct = limit === Infinity ? 0 : Math.min(100, Math.round((u.total_hits / limit) * 100));
    const limitStr = limit === Infinity ? 'Unlimited' : limit.toLocaleString();
    const remaining = limit === Infinity ? 'Unlimited' : Math.max(0, limit - u.total_hits).toLocaleString();

    const user = JSON.parse(localStorage.getItem('fv_user') || '{}');

    document.getElementById('usage-content').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Current Plan</div>
          <div class="stat-value" style="text-transform:capitalize">${escHtml(user.plan || 'free')}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Detections Used</div>
          <div class="stat-value">${u.total_hits.toLocaleString()}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Plan Limit</div>
          <div class="stat-value">${limitStr}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Remaining</div>
          <div class="stat-value">${remaining}</div>
        </div>
      </div>

      <div class="card" style="margin-bottom:24px">
        <div class="card-header"><h2>Usage This Period</h2></div>
        <div style="display:flex;justify-content:space-between;font-size:0.85rem;color:var(--text-muted);margin-bottom:4px">
          <span>${u.total_hits.toLocaleString()} used</span>
          <span>${limitStr} limit</span>
        </div>
        <div class="usage-bar">
          <div class="usage-bar-fill" style="width:${limit === Infinity ? 0 : pct}%"></div>
        </div>
        ${u.overage_hits > 0 ? `<p style="color:var(--warning);font-size:0.85rem;margin-top:8px">Overage: ${u.overage_hits.toLocaleString()} hits beyond plan limit</p>` : ''}
      </div>

      <div class="card" style="margin-bottom:24px">
        <div class="card-header"><h2>By Type</h2></div>
        <div class="table-wrap"><table>
          <thead><tr><th>Type</th><th>Hits</th></tr></thead>
          <tbody>
            ${Object.entries(u.by_type || {}).map(([type, hits]) => `
              <tr><td style="text-transform:capitalize">${type.replace('_', ' ')}</td><td>${hits.toLocaleString()}</td></tr>
            `).join('') || '<tr><td colspan="2" style="color:var(--text-muted)">No usage data</td></tr>'}
          </tbody>
        </table></div>
      </div>

      ${(u.by_key || []).length > 0 ? `
      <div class="card">
        <div class="card-header"><h2>By API Key</h2></div>
        <div class="table-wrap"><table>
          <thead><tr><th>Key Prefix</th><th>Hits</th></tr></thead>
          <tbody>
            ${u.by_key.map(k => `<tr><td><code>${escHtml(k.key_prefix)}</code></td><td>${k.hits.toLocaleString()}</td></tr>`).join('')}
          </tbody>
        </table></div>
      </div>
      ` : ''}
    `;
  } catch (err) {
    document.getElementById('usage-content').innerHTML =
      `<div class="empty-state"><h3>Error</h3><p>${escHtml(err.message)}</p></div>`;
  }
}
