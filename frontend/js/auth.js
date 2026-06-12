function renderAuth() {
  return `
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-brand">
          <div class="brand-icon">FV</div>
          <h1>FraudVault</h1>
          <p>Document & image forgery detection</p>
        </div>

        <div class="auth-tabs">
          <button class="auth-tab active" data-tab="login">Sign In</button>
          <button class="auth-tab" data-tab="register">Sign Up</button>
        </div>

        <div id="auth-form-login">
          <form id="login-form">
            <div class="form-group">
              <label>Email</label>
              <input type="email" class="form-input" name="email" placeholder="you@example.com" required>
            </div>
            <div class="form-group">
              <label>Password</label>
              <input type="password" class="form-input" name="password" placeholder="Min 8 characters" required>
            </div>
            <button type="submit" class="btn btn-primary btn-block" id="login-btn">Sign In</button>
          </form>
        </div>

        <div id="auth-form-register" style="display:none">
          <form id="register-form">
            <div class="form-group">
              <label>Full Name</label>
              <input type="text" class="form-input" name="full_name" placeholder="Jane Doe">
            </div>
            <div class="form-group">
              <label>Email</label>
              <input type="email" class="form-input" name="email" placeholder="you@example.com" required>
            </div>
            <div class="form-group">
              <label>Password</label>
              <input type="password" class="form-input" name="password" placeholder="Min 8 characters" minlength="8" required>
            </div>
            <button type="submit" class="btn btn-primary btn-block" id="register-btn">Create Account</button>
          </form>
        </div>
      </div>
    </div>
  `;
}

function initAuth() {
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const which = tab.dataset.tab;
      document.getElementById('auth-form-login').style.display = which === 'login' ? '' : 'none';
      document.getElementById('auth-form-register').style.display = which === 'register' ? '' : 'none';
    });
  });

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    try {
      const fd = new FormData(e.target);
      const data = await API.login(fd.get('email'), fd.get('password'));
      localStorage.setItem('fv_token', data.access_token);
      localStorage.setItem('fv_user', JSON.stringify(data.user));
      window.location.hash = '#/dashboard';
      App.route();
    } catch (err) {
      App.toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sign In';
    }
  });

  document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('register-btn');
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    try {
      const fd = new FormData(e.target);
      const data = await API.register(fd.get('email'), fd.get('password'), fd.get('full_name'));
      localStorage.setItem('fv_token', data.access_token);
      localStorage.setItem('fv_user', JSON.stringify(data.user));
      window.location.hash = '#/dashboard';
      App.route();
    } catch (err) {
      App.toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Create Account';
    }
  });
}
