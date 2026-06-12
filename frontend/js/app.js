const App = {
  init() {
    window.addEventListener('hashchange', () => this.route());
    document.getElementById('btn-logout').addEventListener('click', () => this.logout());
    this.route();
  },

  route() {
    const hash = window.location.hash || '#/login';
    const token = localStorage.getItem('fv_token');
    const sidebar = document.getElementById('sidebar');
    const main = document.getElementById('main-content');
    const content = document.getElementById('page-content');

    if (!token && !hash.startsWith('#/login')) {
      window.location.hash = '#/login';
      return;
    }

    if (token) {
      if (hash === '#/login') {
        window.location.hash = '#/dashboard';
        return;
      }
      sidebar.classList.remove('hidden');
      main.classList.add('with-sidebar');
      this.updateUser();
    } else {
      sidebar.classList.add('hidden');
      main.classList.remove('with-sidebar');
    }

    document.querySelectorAll('.nav-item').forEach(n => {
      const page = n.dataset.page;
      n.classList.toggle('active', hash.startsWith('#/' + page));
    });

    const [path, param] = this.parsePath(hash);

    switch (path) {
      case 'login':
        content.innerHTML = renderAuth();
        initAuth();
        break;
      case 'dashboard':
        content.innerHTML = renderDashboard();
        initDashboard();
        break;
      case 'detect':
        content.innerHTML = renderDetect();
        initDetect();
        break;
      case 'history':
        content.innerHTML = renderHistory();
        initHistory();
        break;
      case 'result':
        content.innerHTML = renderResultPage(param);
        initResultPage(param);
        break;
      case 'keys':
        content.innerHTML = renderKeys();
        initKeys();
        break;
      case 'usage':
        content.innerHTML = renderUsage();
        initUsage();
        break;
      case 'org':
        content.innerHTML = renderOrg();
        initOrg();
        break;
      case 'plans':
        content.innerHTML = renderPlans();
        initPlans();
        break;
      case 'admin':
        content.innerHTML = renderAdmin();
        initAdmin();
        break;
      default:
        window.location.hash = token ? '#/dashboard' : '#/login';
    }
  },

  parsePath(hash) {
    const parts = hash.replace('#/', '').split('/');
    return [parts[0], parts[1] || null];
  },

  updateUser() {
    try {
      const user = JSON.parse(localStorage.getItem('fv_user') || '{}');
      const name = user.full_name || user.email || 'User';
      document.getElementById('user-name').textContent = name;
      document.getElementById('user-avatar').textContent = name.charAt(0).toUpperCase();
      document.getElementById('user-plan').textContent = user.plan || 'free';

      const adminNav = document.getElementById('admin-nav-item');
      const adminSep = document.getElementById('admin-nav-sep');
      const isAdmin = user.role === 'admin';
      if (adminNav) adminNav.style.display = isAdmin ? '' : 'none';
      if (adminSep) adminSep.style.display = isAdmin ? '' : 'none';
    } catch {}
  },

  logout() {
    localStorage.removeItem('fv_token');
    localStorage.removeItem('fv_user');
    window.location.hash = '#/login';
    this.route();
  },

  toast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => { el.remove(); }, 4000);
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
