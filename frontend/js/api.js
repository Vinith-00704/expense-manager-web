/* api.js — JWT fetch wrapper */
const API = (() => {
  const BASE = '';
  const TOKEN_KEY = 'fm_token';

  function token() { return localStorage.getItem(TOKEN_KEY); }
  function headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    if (token()) h['Authorization'] = 'Bearer ' + token();
    return h;
  }

  async function request(method, path, body) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    const json = await res.json().catch(() => ({ success: false, error: 'Parse error' }));
    if (res.status === 401) { App.logout(); return null; }
    return json;
  }

  async function postForm(path, formData) {
    const h = {};
    if (token()) h['Authorization'] = 'Bearer ' + token();
    const res = await fetch(BASE + path, { method: 'POST', headers: h, body: formData });
    return res.json().catch(() => ({ success: false, error: 'Parse error' }));
  }

  return {
    token,
    TOKEN_KEY,
    setToken(t) { localStorage.setItem(TOKEN_KEY, t); },
    clearToken() { localStorage.removeItem(TOKEN_KEY); },
    get:      (path)       => request('GET',    path),
    post:     (path, body) => request('POST',   path, body),
    put:      (path, body) => request('PUT',    path, body),
    patch:    (path, body) => request('PATCH',  path, body),
    del:      (path)       => request('DELETE', path),
    delete:   (path)       => request('DELETE', path),  // alias
    postForm,
    downloadUrl(path) {
      return `${BASE}${path}${path.includes('?') ? '&' : '?'}token=${token()}`;
    },
  };
})();
