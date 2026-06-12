function renderPlans() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Plans & Billing</h1>
        <p>Choose the right plan for your needs</p>
      </div>
      <div id="plans-content">
        <div class="loading-state"><div class="spinner"></div><span>Loading plans...</span></div>
      </div>
    </div>`;
}

async function initPlans() {
  try {
    const plans = await API.get('/plans');
    const user = JSON.parse(localStorage.getItem('fv_user') || '{}');
    const currentPlan = user.plan || 'free';

    if (!plans || plans.length === 0) {
      document.getElementById('plans-content').innerHTML = '<div class="empty-state"><h3>No plans available</h3></div>';
      return;
    }

    document.getElementById('plans-content').innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px">
        ${plans.map(p => {
          const isCurrent = p.name === currentPlan;
          const price = p.monthly_price_cents === 0
            ? (p.name === 'enterprise' ? 'Custom' : 'Free')
            : `$${(p.monthly_price_cents / 100).toFixed(0)}/mo`;
          const limit = p.monthly_detection_limit ? p.monthly_detection_limit.toLocaleString() : 'Unlimited';
          const features = (p.features || '').split(',').filter(Boolean);
          return `
            <div class="card" style="${isCurrent ? 'border-color:var(--primary)' : ''}">
              <div style="margin-bottom:16px">
                ${isCurrent ? '<span class="badge badge-completed" style="margin-bottom:8px;display:inline-block">Current Plan</span>' : ''}
                <h2>${escHtml(p.display_name)}</h2>
                <p style="color:var(--text-muted);font-size:0.85rem">${escHtml(p.description || '')}</p>
              </div>
              <div style="font-size:2rem;font-weight:800;margin-bottom:16px">${price}</div>
              <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:16px">
                <div>${limit} detections/mo</div>
                <div>${p.max_members} team members</div>
                <div>${p.max_api_keys} API keys</div>
                <div>${p.max_file_size_mb}MB max file</div>
              </div>
              <ul style="list-style:none;font-size:0.85rem;margin-bottom:16px">
                ${features.map(f => `<li style="padding:3px 0;color:var(--text)">&#10003; ${escHtml(f.trim())}</li>`).join('')}
              </ul>
              ${isCurrent
                ? '<button class="btn btn-ghost btn-block btn-sm" disabled>Current Plan</button>'
                : p.name === 'enterprise'
                  ? '<button class="btn btn-ghost btn-block btn-sm" disabled>Contact Sales</button>'
                  : `<button class="btn btn-primary btn-block btn-sm" disabled>Upgrade</button>`}
            </div>`;
        }).join('')}
      </div>
      <p style="color:var(--text-dim);font-size:0.8rem;margin-top:16px;text-align:center">
        Stripe checkout integration ready &mdash; connect your Stripe keys to enable self-service upgrades.
      </p>`;
  } catch (err) {
    document.getElementById('plans-content').innerHTML =
      `<div class="empty-state"><h3>Error</h3><p>${escHtml(err.message)}</p></div>`;
  }
}
