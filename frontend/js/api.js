const API = {
  BASE: '/v1',

  _token() { return localStorage.getItem('fv_token'); },

  async _request(method, path, body, isForm) {
    const headers = {};
    const token = this._token();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const opts = { method, headers };

    if (body && isForm) {
      opts.body = body;
    } else if (body) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    const res = await fetch(this.BASE + path, opts);

    if (res.status === 401) {
      localStorage.removeItem('fv_token');
      localStorage.removeItem('fv_user');
      window.location.hash = '#/login';
      throw new Error('Session expired');
    }

    if (res.status === 204) return null;

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || data.detail || `Error ${res.status}`);
    return data;
  },

  get(path) { return this._request('GET', path); },
  post(path, body) { return this._request('POST', path, body); },
  postForm(path, formData) { return this._request('POST', path, formData, true); },
  del(path) { return this._request('DELETE', path); },

  // Auth
  register(email, password, fullName) {
    return this.post('/auth/register', { email, password, full_name: fullName });
  },
  login(email, password) {
    return this.post('/auth/login', { email, password });
  },

  // Detection
  detect(file) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('async_mode', 'false');
    return this.postForm('/detect', fd);
  },

  // Results
  listResults(page = 1) { return this.get(`/results?page=${page}&per_page=15`); },
  getResult(jobId) { return this.get(`/results/${jobId}`); },

  // Keys
  listKeys() { return this.get('/keys'); },
  createKey(name, env) { return this.post('/keys', { name, environment: env }); },
  deleteKey(id) { return this.del(`/keys/${id}`); },

  // Usage
  getUsage() { return this.get('/usage'); },
};
