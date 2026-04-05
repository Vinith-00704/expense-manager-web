/* expenses.js */
const ExpensesModule = (() => {
  let meta = { categories: [], payment_modes: [] };
  let filter = { entry_type: 'all' };

  async function init() {
    if (!meta.categories.length) {
      const res = await API.get('/api/expenses/meta');
      if (res && res.success) meta = res.data;
    }
    render();
    load();
  }

  function render() {
    const el = document.getElementById('page-expenses');
    el.innerHTML = `
      <div class="page-top">
        <h2>Transactions</h2>
      </div>
      <div class="filter-bar" id="exp-filters">
        <span class="filter-chip active" data-type="all" onclick="ExpensesModule.setFilter('all',this)">All</span>
        <span class="filter-chip" data-type="expense" onclick="ExpensesModule.setFilter('expense',this)">Expenses</span>
        <span class="filter-chip" data-type="income" onclick="ExpensesModule.setFilter('income',this)">Income</span>
        <select class="filter-select" id="exp-cat-filter" onchange="ExpensesModule.load()">
          <option value="">All Categories</option>
          ${meta.categories.map(c=>`<option value="${c}">${c}</option>`).join('')}
        </select>
      </div>
      <div id="exp-list" class="tx-list"><div class="empty-state"><div class="empty-icon" style="animation:shimmer 1.4s infinite">…</div></div></div>
      <button class="fab" onclick="ExpensesModule.openAdd()">＋</button>`;
  }

  async function load() {
    const cat = document.getElementById('exp-cat-filter')?.value || '';
    const params = new URLSearchParams({ limit: 150 });
    if (filter.entry_type !== 'all') params.set('entry_type', filter.entry_type);
    if (cat) params.set('category', cat);
    const res = await API.get('/api/expenses?' + params);
    if (!res || !res.success) return;
    renderList(res.data);
  }

  function renderList(items) {
    const el = document.getElementById('exp-list');
    if (!items || !items.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-title">NO TRANSACTIONS</div><div class="empty-sub">press [+] to add your first entry</div></div>';
      return;
    }
    el.innerHTML = items.map(e => `
      <div class="tx-item">
        <div class="tx-icon tx-type-${e.entry_type}">${e.entry_type === 'income' ? 'IN' : 'EX'}</div>
        <div class="tx-info">
          <div class="tx-desc">${e.description || e.category}</div>
          <div class="tx-meta">${e.category} · ${App.fmtDate(e.expense_date)} · ${e.payment_mode || 'Cash'}</div>
        </div>
        <div class="tx-amount ${e.entry_type === 'income' ? 'income-val' : 'expense-val'}">${e.entry_type === 'income' ? '+' : '-'}${App.fmt(e.amount)}</div>
        <div class="tx-actions">
          <button class="btn btn-ghost btn-sm" onclick="ExpensesModule.openEdit(${e.id})">EDIT</button>
          <button class="btn btn-danger btn-sm" onclick="ExpensesModule.del(${e.id})">DEL</button>
        </div>
      </div>`).join('');
  }

  function setFilter(type, el) {
    filter.entry_type = type;
    document.querySelectorAll('#exp-filters .filter-chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    load();
  }

  function formHtml(e = {}) {
    return `
      <div class="form-group">
        <label>Type</label>
        <div style="display:flex;gap:.5rem">
          <label style="flex:1;cursor:pointer"><input type="radio" name="entry_type" value="expense" ${e.entry_type!=='income'?'checked':''}> Expense</label>
          <label style="flex:1;cursor:pointer"><input type="radio" name="entry_type" value="income" ${e.entry_type==='income'?'checked':''}> Income</label>
        </div>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Amount *</label>
          <input type="number" id="ef-amount" value="${e.amount||''}" step="0.01" min="0.01" placeholder="0.00" required />
        </div>
        <div class="form-group">
          <label>Date *</label>
          <input type="date" id="ef-date" value="${e.expense_date||new Date().toISOString().slice(0,10)}" required />
        </div>
      </div>
      <div class="form-group">
        <label>Category</label>
        <select id="ef-cat">
          ${meta.categories.map(c=>`<option ${e.category===c?'selected':''}>${c}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Description</label>
        <input type="text" id="ef-desc" value="${e.description||''}" placeholder="What was it for?" />
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Payment Mode</label>
          <select id="ef-mode">
            ${meta.payment_modes.map(m=>`<option ${e.payment_mode===m?'selected':''}>${m}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label>Notes</label>
          <input type="text" id="ef-notes" value="${e.notes||''}" placeholder="Optional note" />
        </div>
      </div>
      <div id="ef-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" id="ef-submit" onclick="ExpensesModule.save(${e.id||0})">${e.id ? 'Update' : 'Save'}</button>`;
  }

  function openAdd() { App.openModal('Add Transaction', formHtml()); }

  async function openEdit(id) {
    const res = await API.get('/api/expenses/' + id);
    if (!res || !res.success) return;
    App.openModal('Edit Transaction', formHtml(res.data));
  }

  async function save(id) {
    const btn = document.getElementById('ef-submit');
    const errEl = document.getElementById('ef-error');
    errEl.textContent = '';
    btn.disabled = true;
    const body = {
      entry_type: document.querySelector('input[name=entry_type]:checked')?.value || 'expense',
      amount: document.getElementById('ef-amount').value,
      expense_date: document.getElementById('ef-date').value,
      category: document.getElementById('ef-cat').value,
      description: document.getElementById('ef-desc').value,
      payment_mode: document.getElementById('ef-mode').value,
      notes: document.getElementById('ef-notes').value,
    };
    const res = id ? await API.put('/api/expenses/'+id, body) : await API.post('/api/expenses', body);
    btn.disabled = false;
    if (res && res.success) {
      App.closeModal(); App.toast(id ? 'Updated!' : 'Added!'); load();
    } else {
      errEl.textContent = (res && res.error) || 'Save failed';
    }
  }

  async function del(id) {
    if (!confirm('Delete this transaction?')) return;
    const res = await API.del('/api/expenses/' + id);
    if (res && res.success) { App.toast('Deleted'); load(); }
    else App.toast('Delete failed', 'error');
  }

  return { init, load, setFilter, openAdd, openEdit, save, del };
})();
