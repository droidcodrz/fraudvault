let _historyPage = 1;

function renderHistory() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Detection History</h1>
        <p>All your past detection jobs</p>
      </div>
      <div class="card">
        <div id="history-content">
          <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
        </div>
        <div id="history-pagination"></div>
      </div>
    </div>`;
}

async function initHistory() {
  _historyPage = 1;
  await loadHistory();
}

async function loadHistory() {
  const container = document.getElementById('history-content');
  try {
    const data = await API.listResults(_historyPage);

    if (!data.items || data.items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No detections yet</h3>
          <p>Upload a file to start detecting forgery</p>
          <a href="#/detect" class="btn btn-primary" style="margin-top:12px">Start Detection</a>
        </div>`;
      document.getElementById('history-pagination').innerHTML = '';
      return;
    }

    container.innerHTML = `
      <div class="table-wrap"><table>
        <thead><tr>
          <th>File</th><th>Type</th><th>Size</th><th>Status</th><th>Verdict</th><th>Risk</th><th>Date</th><th></th>
        </tr></thead>
        <tbody>
          ${data.items.map(item => `
            <tr>
              <td title="${escHtml(item.file_name)}">${escHtml(truncate(item.file_name, 30))}</td>
              <td><span class="badge badge-${item.file_type}">${item.file_type}</span></td>
              <td>${formatSize(item.file_size)}</td>
              <td><span class="badge badge-${item.status}">${item.status}</span></td>
              <td>${item.verdict ? `<span class="badge badge-${item.verdict}">${item.verdict.replace('_',' ')}</span>` : '--'}</td>
              <td>${item.risk_score != null ? item.risk_score : '--'}</td>
              <td>${item.queued_at ? new Date(item.queued_at).toLocaleDateString() : '--'}</td>
              <td><a href="#/result/${item.job_id}" class="btn btn-ghost btn-sm">View</a></td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>`;

    const totalPages = Math.ceil(data.total / data.per_page);
    const pag = document.getElementById('history-pagination');
    if (totalPages > 1) {
      pag.innerHTML = `
        <div class="pagination">
          <button class="btn btn-ghost btn-sm" ${_historyPage <= 1 ? 'disabled' : ''} id="pg-prev">Prev</button>
          <span style="color:var(--text-muted);font-size:0.85rem">Page ${data.page} of ${totalPages}</span>
          <button class="btn btn-ghost btn-sm" ${_historyPage >= totalPages ? 'disabled' : ''} id="pg-next">Next</button>
        </div>`;
      document.getElementById('pg-prev')?.addEventListener('click', () => { _historyPage--; loadHistory(); });
      document.getElementById('pg-next')?.addEventListener('click', () => { _historyPage++; loadHistory(); });
    } else {
      pag.innerHTML = '';
    }
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escHtml(err.message)}</p></div>`;
  }
}

function truncate(str, n) { return (str || '').length > n ? str.slice(0, n) + '...' : str || ''; }
function formatSize(bytes) {
  if (!bytes) return '--';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(2) + ' MB';
}
