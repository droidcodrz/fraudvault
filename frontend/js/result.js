function renderResultPage(jobId) {
  return `
    <div class="page">
      <div class="page-header">
        <a href="#/history" style="color:var(--text-muted);font-size:0.85rem;">&larr; Back to History</a>
        <h1>Detection Result</h1>
      </div>
      <div id="result-content">
        <div class="loading-state"><div class="spinner"></div><span>Loading result...</span></div>
      </div>
    </div>`;
}

async function initResultPage(jobId) {
  try {
    const data = await API.getResult(jobId);
    document.getElementById('result-content').innerHTML = buildResultHTML(data);
  } catch (err) {
    document.getElementById('result-content').innerHTML =
      `<div class="empty-state"><h3>Error</h3><p>${escHtml(err.message)}</p></div>`;
  }
}

const VERDICT_INFO = {
  authentic: { icon: '✓', label: 'Authentic', desc: 'No signs of tampering detected' },
  tampered: { icon: '!', label: 'Tampered', desc: 'Evidence of modification found' },
  ai_generated: { icon: '✱', label: 'AI Generated', desc: 'Image appears to be AI-generated' },
  inconclusive: { icon: '?', label: 'Inconclusive', desc: 'Some suspicious signals detected' },
};

function scoreColor(val) {
  if (val >= 0.7) return 'var(--danger)';
  if (val >= 0.4) return 'var(--warning)';
  return 'var(--success)';
}

function buildResultHTML(data) {
  if (data.status === 'queued' || data.status === 'processing') {
    return `<div class="loading-state"><div class="spinner"></div><span>Detection in progress...</span></div>`;
  }
  if (data.status === 'failed') {
    return `<div class="empty-state"><h3>Detection Failed</h3><p>${escHtml(data.error || 'Unknown error')}</p></div>`;
  }

  const v = data.verdict || 'inconclusive';
  const info = VERDICT_INFO[v] || VERDICT_INFO.inconclusive;
  const scores = data.scores || {};

  const scoreEntries = [
    ['ELA', scores.ela],
    ['Clone Detection', scores.clone_detection],
    ['Metadata', scores.metadata],
    ['Synthetic', scores.synthetic],
    ['Provenance', scores.provenance],
    ['Font Consistency', scores.font_consistency],
    ['OCR Diff', scores.ocr_diff],
    ['Effective AI', scores.effective_ai],
  ].filter(([, val]) => val != null);

  const flags = data.flags || [];

  let html = `
    <div class="result-banner ${v}">
      <div class="verdict-icon">${info.icon}</div>
      <div class="verdict-text">
        <h2>${info.label}</h2>
        <p>${info.desc}</p>
      </div>
      <div class="verdict-meta">
        <div class="risk-score" style="color:${scoreColor((data.risk_score || 0) / 100)}">${data.risk_score ?? '--'}</div>
        <div class="risk-label">Risk Score</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <div class="card-header"><h2>Score Breakdown</h2></div>
      <div class="scores-grid">
        ${scoreEntries.map(([label, val]) => `
          <div class="score-item">
            <div class="score-label">${label}</div>
            <div class="score-bar"><div class="score-bar-fill" style="width:${Math.round(val * 100)}%;background:${scoreColor(val)}"></div></div>
            <div class="score-value" style="color:${scoreColor(val)}">${(val * 100).toFixed(1)}%</div>
          </div>
        `).join('')}
      </div>
    </div>`;

  if (flags.length) {
    html += `
    <div class="card" style="margin-bottom:24px">
      <div class="card-header"><h2>Flags (${flags.length})</h2></div>
      <div class="flags-list">
        ${flags.map(f => `
          <div class="flag-item">
            <div class="flag-severity ${f.severity || 'medium'}"></div>
            <div>
              <div class="flag-type">${escHtml(f.type)}</div>
              ${f.details ? `<div class="flag-details">${escHtml(f.details)}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    </div>`;
  }

  if (data.heatmap_url) {
    html += `
    <div class="card">
      <div class="card-header"><h2>ELA Heatmap</h2></div>
      <div class="heatmap-container">
        <img src="${data.heatmap_url}" alt="ELA Heatmap" loading="lazy">
      </div>
    </div>`;
  }

  html += `
    <div style="margin-top:16px;display:flex;gap:12px">
      <a href="#/detect" class="btn btn-primary">Analyze Another File</a>
      <a href="#/history" class="btn btn-ghost">View History</a>
    </div>`;

  return html;
}
