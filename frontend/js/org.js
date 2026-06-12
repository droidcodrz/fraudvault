function renderOrg() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Organization</h1>
        <p>Manage your team and members</p>
      </div>

      <div id="org-setup" style="display:none">
        <div class="card" style="max-width:500px">
          <h2 style="margin-bottom:16px">Create Organization</h2>
          <p style="color:var(--text-muted);margin-bottom:20px">Set up a team to collaborate on fraud detection.</p>
          <form id="create-org-form">
            <div class="form-group">
              <label>Organization Name</label>
              <input type="text" class="form-input" name="name" placeholder="Acme Inc." required>
            </div>
            <button type="submit" class="btn btn-primary">Create Organization</button>
          </form>
        </div>
      </div>

      <div id="org-content" style="display:none">
        <div class="stats-grid" style="margin-bottom:24px">
          <div class="stat-card">
            <div class="stat-label">Organization</div>
            <div class="stat-value" id="org-name">--</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Your Role</div>
            <div class="stat-value" id="org-role">--</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Members</div>
            <div class="stat-value" id="org-member-count">--</div>
          </div>
        </div>

        <div class="card" style="margin-bottom:24px" id="invite-section">
          <div class="card-header"><h2>Invite Member</h2></div>
          <form id="invite-form" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
            <div class="form-group" style="flex:1;min-width:200px;margin-bottom:0">
              <label>Email</label>
              <input type="email" class="form-input" name="email" placeholder="colleague@company.com" required>
            </div>
            <div class="form-group" style="width:140px;margin-bottom:0">
              <label>Role</label>
              <select class="form-input" name="role">
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <button type="submit" class="btn btn-primary">Send Invite</button>
          </form>
          <div id="invite-result" style="margin-top:12px"></div>
        </div>

        <div class="card">
          <div class="card-header"><h2>Members</h2></div>
          <div id="members-list">
            <div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>
          </div>
        </div>
      </div>
    </div>`;
}

async function initOrg() {
  try {
    const orgs = await API.get('/orgs');
    if (!orgs || orgs.length === 0) {
      document.getElementById('org-setup').style.display = '';
      document.getElementById('org-content').style.display = 'none';
      document.getElementById('create-org-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = new FormData(e.target).get('name');
        await API.post('/orgs', { name });
        App.toast('Organization created!', 'success');
        initOrg();
      });
      return;
    }

    document.getElementById('org-setup').style.display = 'none';
    document.getElementById('org-content').style.display = '';

    const org = orgs[0];
    document.getElementById('org-name').textContent = org.name;
    document.getElementById('org-role').textContent = org.role;

    const members = await API.get(`/orgs/${org.id}/members`);
    document.getElementById('org-member-count').textContent = members.length;

    const isAdmin = org.role === 'owner' || org.role === 'admin';
    document.getElementById('invite-section').style.display = isAdmin ? '' : 'none';

    const container = document.getElementById('members-list');
    container.innerHTML = `
      <div class="table-wrap"><table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Joined</th>${isAdmin ? '<th></th>' : ''}</tr></thead>
        <tbody>
          ${members.map(m => `
            <tr>
              <td>${escHtml(m.full_name || '--')}</td>
              <td>${escHtml(m.email)}</td>
              <td><span class="badge badge-${m.role === 'owner' ? 'live' : 'test'}">${m.role}</span></td>
              <td>${m.joined_at ? new Date(m.joined_at).toLocaleDateString() : '--'}</td>
              ${isAdmin && m.role !== 'owner' ? `<td><button class="btn btn-ghost btn-sm remove-member-btn" data-uid="${m.user_id}" data-oid="${org.id}">Remove</button></td>` : (isAdmin ? '<td></td>' : '')}
            </tr>
          `).join('')}
        </tbody>
      </table></div>`;

    container.querySelectorAll('.remove-member-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Remove this member?')) return;
        await API.del(`/orgs/${btn.dataset.oid}/members/${btn.dataset.uid}`);
        App.toast('Member removed', 'success');
        initOrg();
      });
    });

    document.getElementById('invite-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        const res = await API.post(`/orgs/${org.id}/invites`, { email: fd.get('email'), role: fd.get('role') });
        document.getElementById('invite-result').innerHTML = `
          <div class="key-display">
            <span id="invite-token-text">${res.token}</span>
            <button onclick="navigator.clipboard.writeText(document.getElementById('invite-token-text').textContent);App.toast('Copied!','success')">Copy</button>
          </div>
          <p style="font-size:0.8rem;color:var(--text-muted);margin-top:8px">Share this invite token with ${escHtml(fd.get('email'))}</p>`;
        e.target.reset();
      } catch (err) { App.toast(err.message, 'error'); }
    });
  } catch (err) {
    App.toast(err.message, 'error');
  }
}
