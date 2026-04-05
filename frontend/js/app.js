/* app.js — SPA router, auth guard, global utilities */
const App = (() => {
  let currentUser = null;
  let currentPage = '';

  const PAGES = {
    dashboard:     { title: 'Dashboard',     mod: () => DashboardModule },
    expenses:      { title: 'Expenses',      mod: () => ExpensesModule },
    rooms:         { title: 'Rooms',         mod: () => RoomsModule },
    'room-detail': { title: 'Room Detail',   mod: () => RoomsModule },
    trips:         { title: 'Trips',         mod: () => TripsModule },
    'trip-detail': { title: 'Trip Detail',   mod: () => TripsModule },
    subscriptions: { title: 'Subscriptions', mod: () => SubscriptionsModule },
    analytics:     { title: 'Analytics',     mod: () => AnalyticsModule },
    reports:       { title: 'Reports',       mod: () => ReportsModule },
    settings:      { title: 'Settings',      mod: () => SettingsModule },
  };

  async function boot() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(console.warn);
    }
    window.addEventListener('hashchange', route);
    const t = API.token();
    if (!t) { showAuth(); return; }

    const res = await API.get('/api/auth/me');
    if (res && res.success) {
      onLogin(res.data);
    } else {
      API.clearToken(); showAuth();
    }
  }

  function onLogin(user) {
    currentUser = user;
    document.getElementById('auth-overlay').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    updateUserUI(user);
    route();
  }

  function updateUserUI(u) {
    const init = (u.full_name || u.username || 'U')[0].toUpperCase();
    ['sidebar-avatar','header-user'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = init;
    });
    const nameEl = document.getElementById('sidebar-name');
    if (nameEl) nameEl.textContent = u.full_name || u.username;
    const curEl = document.getElementById('sidebar-currency');
    if (curEl) curEl.textContent = (u.currency || '₹') + ' ' + (u.username || '');
  }

  function route() {
    const hash = window.location.hash.slice(2) || 'dashboard';
    const parts = hash.split('/');
    const page = parts[0] || 'dashboard';
    const params = parts.slice(1);

    if (!currentUser) return;

    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    // Update nav
    document.querySelectorAll('.nav-link, .bnav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.page === page);
    });

    const cfg = PAGES[page];
    if (!cfg) { navigate('dashboard'); return; }

    document.getElementById('header-title').textContent = cfg.title;
    const pageEl = document.getElementById('page-' + page);
    if (pageEl) pageEl.classList.add('active');

    currentPage = page;
    if (cfg.mod) {
      const mod = cfg.mod();
      if (mod && mod.init) mod.init(params);
    }
  }

  function navigate(path) { window.location.hash = '#/' + path; }

  /* ── AUTH ── */
  function showAuth() {
    document.getElementById('auth-overlay').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
  }

  async function login(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-login');
    const errEl = document.getElementById('login-error');
    errEl.textContent = '';
    btn.disabled = true; btn.textContent = 'Signing in…';
    const res = await API.post('/api/auth/login', {
      identifier: document.getElementById('login-identifier').value,
      password: document.getElementById('login-password').value,
    });
    btn.disabled = false; btn.textContent = 'Sign In';
    if (res && res.success) {
      API.setToken(res.data.token);
      onLogin(res.data.user);
    } else {
      errEl.textContent = (res && res.error) || 'Login failed';
    }
  }

  async function register(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-register');
    const errEl = document.getElementById('reg-error');
    errEl.textContent = '';
    btn.disabled = true; btn.textContent = 'Creating…';
    const res = await API.post('/api/auth/register', {
      username: document.getElementById('reg-username').value,
      full_name: document.getElementById('reg-fullname').value,
      password: document.getElementById('reg-password').value,
      email: document.getElementById('reg-email').value,
      monthly_salary: document.getElementById('reg-salary').value || 0,
    });
    btn.disabled = false; btn.textContent = 'Create Account';
    if (res && res.success) {
      API.setToken(res.data.token);
      onLogin(res.data.user);
    } else {
      errEl.textContent = (res && res.error) || 'Registration failed';
    }
  }

  function logout() {
    API.clearToken();
    currentUser = null;
    window.location.hash = '';
    showAuth();
  }

  function authTab(tab) {
    document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
    document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
    document.getElementById('tab-login').classList.toggle('active', tab === 'login');
    document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  }

  function togglePwd(id, btn) {
    const inp = document.getElementById(id);
    if (inp.type === 'password') { inp.type = 'text'; btn.textContent = '🙈'; }
    else { inp.type = 'password'; btn.textContent = '👁'; }
  }

  /* ── MODAL ── */
  function openModal(title, bodyHtml, wide = false) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    const box = document.getElementById('modal-box');
    box.style.maxWidth = wide ? '640px' : '480px';
    document.getElementById('modal-overlay').classList.remove('hidden');
  }

  function closeModal(e) {
    if (e && e.target !== document.getElementById('modal-overlay')) return;
    document.getElementById('modal-overlay').classList.add('hidden');
  }

  /* ── DRAWER ── */
  function openDrawer() { document.getElementById('more-drawer').classList.remove('hidden'); }
  function closeDrawer(e) {
    if (e && e.target !== document.getElementById('more-drawer') && e.target !== document.getElementById('more-drawer').querySelector('.drawer-content') === false) {}
    document.getElementById('more-drawer').classList.add('hidden');
  }

  /* ── TOAST ── */
  function toast(msg, type = 'success') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = (type === 'success' ? '✓ ' : type === 'error' ? '✕ ' : '⚠ ') + msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  /* ── HELPERS ── */
  function fmt(amount) {
    const cur = currentUser ? (currentUser.currency || '₹') : '₹';
    return cur + Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function getUser() { return currentUser; }

  function setUser(u) { currentUser = u; updateUserUI(u); }

  function categoryIcon(cat) {
    const MAP = {
      'Food & Dining':'🍔','Transportation':'🚗','Shopping':'🛍️','Entertainment':'🎬',
      'Healthcare':'💊','Bills & Utilities':'⚡','Education':'📚','Travel':'✈️',
      'Personal Care':'💄','Home & Rent':'🏠','Investments':'📈','Salary':'💼',
      'Freelance':'💻','Business':'🏢','Gift':'🎁','Other':'💰',
    };
    return MAP[cat] || '💰';
  }

  return {
    boot, login, register, logout, authTab, togglePwd,
    navigate, route,
    openModal, closeModal,
    openDrawer, closeDrawer,
    toast, fmt, fmtDate, getUser, setUser, categoryIcon,
  };
})();

document.addEventListener('DOMContentLoaded', App.boot);
