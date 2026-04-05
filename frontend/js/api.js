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

  return {
    token,
    TOKEN_KEY,
    setToken(t) { localStorage.setItem(TOKEN_KEY, t); },
    clearToken() { localStorage.removeItem(TOKEN_KEY); },
    get:  (path)       => request('GET',    path),
    post: (path, body) => request('POST',   path, body),
    put:  (path, body) => request('PUT',    path, body),
    del:  (path)       => request('DELETE', path),
    downloadUrl(path) {
      return `${BASE}${path}${path.includes('?') ? '&' : '?'}token=${token()}`;
    },
  };
})();
