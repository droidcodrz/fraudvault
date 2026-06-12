function renderDashboard() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your detection activity</p>
      </div>
      <div class="stats-grid" id="dash-stats">
        <div class="stat-card"><div class="stat-label">Total Scans</div><div class="stat-value">--</div></div>
        <div class="stat-card"><div class="stat-label">Plan Limit</div><div class="stat-value">--</div></div>
        <div class="stat-card"><div class="stat-label">Remaining</div><div class="stat-value">--</div></div>
        <div class="stat-card"><div class="stat-label">API Keys</div><div class="stat-value">--</div></div>
      </div>
      <div class="card">
        <div class="card-header">
          <h2>Recent Detections</h2>
          <a href="#/history" class="btn btn-ghost btn-sm">View All</a>
        </div>
        <div id="dash-recent">
          <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
        </div>
      </div>
    </div>
  `;
}

async function initDashboard() {
  try {
    const [usage, history, keys] = await Promise.all([
      API.getUsage(),
      API.listResults(1),
      API.listKeys(),
    ]);

    const limit = usage.plan_limit === -1 ? 'Unlimited' : usage.plan_limit.toLocaleString();
    const remaining = usage.plan_limit === -1 ? 'Unlimited' : Math.max(0, usage.plan_limit - usage.total_hits).toLocaleString();

    document.getElementById('dash-stats').innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Scans</div>
        <div class="stat-value">${usage.total_hits.toLocaleString()}</div>
        <div class="stat-sub">This month</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Plan Limit</div>
        <div class="stat-value">${limit}</div>
        <div class="stat-sub">${usage.period_start || 'Current period'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Remaining</div>
        <div class="stat-value">${remaining}</div>
        <div class="stat-sub">Detections left</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">API Keys</div>
        <div class="stat-value">${keys.length}</div>
        <div class="stat-sub">Active keys</div>
      </div>
    `;

    const container = document.getElementById('dash-recent');
    if (!history.items || history.items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No detections yet</h3>
          <p>Upload your first file to get started</p>
          <a href="#/detect" class="btn btn-primary" style="margin-top:12px">Start Detection</a>
        </div>`;
      return;
    }

    container.innerHTML = `
      <div class="table-wrap"><table>
        <thead><tr>
          <th>File</th><th>Type</th><th>Verdict</th><th>Risk</th><th>Date</th><th></th>
        </tr></thead>
        <tbody>
          ${history.items.slice(0, 8).map(item => `
            <tr>
              <td>${escHtml(item.file_name)}</td>
              <td><span class="badge badge-${item.file_type}">${item.file_type}</span></td>
              <td>${item.verdict ? `<span class="badge badge-${item.verdict}">${item.verdict.replace('_',' ')}</span>` : `<span class="badge badge-${item.status}">${item.status}</span>`}</td>
              <td>${item.risk_score != null ? item.risk_score : '--'}</td>
              <td>${item.queued_at ? new Date(item.queued_at).toLocaleDateString() : '--'}</td>
              <td><a href="#/result/${item.job_id}" class="btn btn-ghost btn-sm">View</a></td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>`;
  } catch (err) {
    App.toast(err.message, 'error');
  }
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}
