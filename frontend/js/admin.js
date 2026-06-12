function renderAdmin() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Admin Dashboard</h1>
        <p>System overview and user management</p>
      </div>
      <div id="admin-stats" class="stats-grid" style="margin-bottom:24px">
        <div class="stat-card"><div class="stat-label">Loading...</div><div class="stat-value">--</div></div>
      </div>
      <div class="card" style="margin-bottom:24px">
        <div class="card-header">
          <h2>Users</h2>
          <div style="display:flex;gap:8px">
            <input type="text" class="form-input" id="admin-search" placeholder="Search users..." style="width:200px">
          </div>
        </div>
        <div id="admin-users">
          <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
        </div>
        <div id="admin-pagination"></div>
      </div>
    </div>`;
}

let _adminPage = 1;

async function initAdmin() {
  _adminPage = 1;
  try {
    const stats = await API.get('/admin/stats');
    document.getElementById('admin-stats').innerHTML = `
      <div class="stat-card"><div class="stat-label">Total Users</div><div class="stat-value">${stats.total_users}</div></div>
      <div class="stat-card"><div class="stat-label">Active Users</div><div class="stat-value">${stats.active_users}</div></div>
      <div class="stat-card"><div class="stat-label">Organizations</div><div class="stat-value">${stats.total_organizations}</div></div>
      <div class="stat-card"><div class="stat-label">Total Detections</div><div class="stat-value">${stats.total_jobs}</div></div>
      <div class="stat-card"><div class="stat-label">Monthly Events</div><div class="stat-value">${stats.monthly_billing_events}</div></div>
      <div class="stat-card"><div class="stat-label">Completed</div><div class="stat-value">${stats.completed_jobs}</div></div>
    `;
    await loadAdminUsers();

    document.getElementById('admin-search').addEventListener('input', debounce(async (e) => {
      _adminPage = 1;
      await loadAdminUsers(e.target.value);
    }, 300));
  } catch (err) {
    if (err.message.includes('Admin')) {
      document.getElementById('admin-stats').innerHTML = '<div class="empty-state"><h3>Access Denied</h3><p>Admin privileges required.</p></div>';
      document.querySelector('.card').style.display = 'none';
    } else {
      App.toast(err.message, 'error');
    }
  }
}

async function loadAdminUsers(search) {
  const container = document.getElementById('admin-users');
  try {
    let url = `/admin/users?page=${_adminPage}&per_page=15`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const data = await API.get(url);

    container.innerHTML = `
      <div class="table-wrap"><table>
        <thead><tr><th>Email</th><th>Name</th><th>Plan</th><th>Role</th><th>Active</th><th>Verified</th><th>Joined</th><th></th></tr></thead>
        <tbody>
          ${data.items.map(u => `
            <tr>
              <td>${escHtml(u.email)}</td>
              <td>${escHtml(u.full_name || '--')}</td>
              <td>
                <select class="form-input" style="width:auto;padding:4px 8px;font-size:0.8rem" data-uid="${u.id}" data-action="plan">
                  ${['free','starter','growth','pro','enterprise'].map(p => `<option value="${p}" ${u.plan===p?'selected':''}>${p}</option>`).join('')}
                </select>
              </td>
              <td><span class="badge badge-${u.role === 'admin' ? 'live' : 'test'}">${u.role}</span></td>
              <td><button class="btn btn-ghost btn-sm toggle-active-btn" data-uid="${u.id}">${u.is_active ? 'Active' : 'Disabled'}</button></td>
              <td>${u.email_verified ? '&#10003;' : '&#10007;'}</td>
              <td>${u.created_at ? new Date(u.created_at).toLocaleDateString() : '--'}</td>
              <td></td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>`;

    container.querySelectorAll('select[data-action="plan"]').forEach(sel => {
      sel.addEventListener('change', async () => {
        try {
          await API._request('PUT', `/admin/users/${sel.dataset.uid}/plan`, { plan: sel.value });
          App.toast('Plan updated', 'success');
        } catch (err) { App.toast(err.message, 'error'); }
      });
    });

    container.querySelectorAll('.toggle-active-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          const res = await API._request('PUT', `/admin/users/${btn.dataset.uid}/toggle-active`);
          btn.textContent = res.is_active ? 'Active' : 'Disabled';
          App.toast('User status updated', 'success');
        } catch (err) { App.toast(err.message, 'error'); }
      });
    });

    const totalPages = Math.ceil(data.total / data.per_page);
    const pag = document.getElementById('admin-pagination');
    if (totalPages > 1) {
      pag.innerHTML = `<div class="pagination">
        <button class="btn btn-ghost btn-sm" ${_adminPage<=1?'disabled':''} id="adm-prev">Prev</button>
        <span style="color:var(--text-muted);font-size:0.85rem">Page ${data.page} of ${totalPages}</span>
        <button class="btn btn-ghost btn-sm" ${_adminPage>=totalPages?'disabled':''} id="adm-next">Next</button>
      </div>`;
      document.getElementById('adm-prev')?.addEventListener('click', () => { _adminPage--; loadAdminUsers(search); });
      document.getElementById('adm-next')?.addEventListener('click', () => { _adminPage++; loadAdminUsers(search); });
    } else { pag.innerHTML = ''; }
  } catch (err) { container.innerHTML = `<div class="empty-state"><p>${escHtml(err.message)}</p></div>`; }
}

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}
