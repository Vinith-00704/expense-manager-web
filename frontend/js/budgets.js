/**
 * budgets.js — Monthly Budget Management UI
 */
const Budgets = (() => {
  const CATS = [
    'Food & Dining','Transportation','Shopping','Bills & Utilities',
    'Healthcare','Entertainment','Education','Travel',
    'Investments','Home & Rent','Personal Care','Other'
  ];

  async function render() {
    const el = document.getElementById('page-budgets');
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    el.innerHTML = `
      <div class="page-header">
        <h2 class="page-title">&gt; BUDGET_CONTROL</h2>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap">
          <button class="btn btn-ghost" onclick="Budgets.aiSuggest()">AI SUGGEST</button>
          <button class="btn btn-primary" onclick="Budgets.openCreate()">+ SET BUDGET</button>
        </div>
      </div>
      <div class="budget-month-bar">
        <label>Month: </label>
        <input type="month" id="budget-month" value="${month}" onchange="Budgets.loadStatus()" class="month-picker" />
      </div>
      <div id="ai-budget-suggestions" class="hidden" style="margin-bottom:.75rem"></div>
      <div id="budgets-status" class="budgets-grid"><p class="loading-text">LOADING...</p></div>
    `;
    loadStatus();
  }

  async function loadStatus() {
    const month = document.getElementById('budget-month')?.value;
    const el = document.getElementById('budgets-status');
    if (!el) return;
    el.innerHTML = `<p class="loading-text">CALCULATING...</p>`;
    try {
      const res = await API.get(`/api/budgets/status?month=${month || ''}`);
      if (!res.success) { el.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      if (!res.data.length) {
        el.innerHTML = `<div class="empty-state">
          <p class="empty-title">NO_BUDGETS_SET</p>
          <p class="empty-sub">Set spending limits per category to track overspending.</p>
          <button class="btn btn-primary" onclick="Budgets.openCreate()">SET FIRST BUDGET</button>
        </div>`; return;
      }
      el.innerHTML = res.data.map(_budgetCard).join('');
    } catch(e) { el.innerHTML = `<p class="form-error">${e.message}</p>`; }
  }

  function _budgetCard(b) {
    const pct = b.pct_used;
    const barCls = pct >= 100 ? 'bar-over' : pct >= 80 ? 'bar-warn' : 'bar-ok';
    return `
      <div class="budget-card ${b.overspent ? 'budget-over' : ''}">
        <div class="budget-header">
          <span class="budget-cat">${b.category}</span>
          ${b.overspent ? '<span class="dup-badge">OVER</span>' : ''}
        </div>
        <div class="budget-bar-track">
          <div class="budget-bar-fill ${barCls}" style="width:${Math.min(pct,100)}%"></div>
        </div>
        <div class="budget-numbers">
          <span class="${b.overspent ? 'amount-debit' : 'amount-credit'}">${App.fmt(b.spent)} spent</span>
          <span class="goal-sep">/</span>
          <span>${App.fmt(b.monthly_limit)} limit</span>
          <span class="goal-pct">${pct}%</span>
        </div>
        ${b.overspent
          ? `<p class="budget-warning">OVER by ${App.fmt(Math.abs(b.remaining))}</p>`
          : `<p class="budget-remaining">${App.fmt(b.remaining)} remaining</p>`}
        <div class="goal-actions">
          <button class="btn-xs" onclick="Budgets.openEdit(${b.id}, '${b.category}', ${b.monthly_limit})">EDIT</button>
          <button class="btn-xs btn-reject" onclick="Budgets.deleteBudget(${b.id})">DELETE</button>
        </div>
      </div>
    `;
  }

  function openCreate() {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    App.openModal('SET MONTHLY BUDGET', `
      <form onsubmit="Budgets.create(event)" class="modal-form">
        <div class="form-group">
          <label>Category</label>
          <select id="b-cat">${CATS.map(c => `<option>${c}</option>`).join('')}</select>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Monthly Limit</label><input id="b-limit" type="number" min="1" step="0.01" placeholder="5000" required /></div>
          <div class="form-group"><label>Month</label><input id="b-month" type="month" value="${month}" /></div>
        </div>
        <button type="submit" class="btn btn-primary btn-full">SAVE BUDGET</button>
      </form>
    `);
  }

  async function create(e) {
    e.preventDefault();
    try {
      const res = await API.post('/api/budgets/', {
        category: document.getElementById('b-cat').value,
        monthly_limit: parseFloat(document.getElementById('b-limit').value),
        month: document.getElementById('b-month').value,
      });
      if (res.success) { App.closeModal(); App.toast('Budget saved!', 'success'); loadStatus(); }
      else App.toast(res.error, 'error');
    } catch(e) { App.toast(e.message, 'error'); }
  }

  function openEdit(id, cat, limit) {
    App.openModal(`EDIT BUDGET — ${cat}`, `
      <form onsubmit="Budgets.update(event, ${id}, '${cat}')" class="modal-form">
        <div class="form-group"><label>Category</label>
          <input value="${cat}" disabled style="opacity:.6" />
        </div>
        <div class="form-group"><label>New Monthly Limit for ${cat}</label>
          <input id="be-limit" type="number" min="1" step="0.01" value="${limit}" required />
        </div>
        <button type="submit" class="btn btn-primary btn-full">UPDATE</button>
      </form>
    `);
  }

  async function update(e, id, category) {
    e.preventDefault();
    const limit = parseFloat(document.getElementById('be-limit').value);
    if (!limit || limit <= 0) { App.toast('Enter a valid amount.', 'error'); return; }
    try {
      const now   = new Date();
      const month = document.getElementById('budget-month')?.value
                    || `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
      const res = await API.post('/api/budgets/', { category, monthly_limit: limit, month });
      if (res.success) { App.closeModal(); App.toast('Budget updated!', 'success'); loadStatus(); }
      else App.toast(res.error, 'error');
    } catch(e) { App.toast(e.message, 'error'); }
  }

  async function deleteBudget(id) {
    const res = await API.delete(`/api/budgets/${id}`);
    if (res.success) { App.toast('Budget deleted.', 'success'); loadStatus(); }
    else App.toast(res.error, 'error');
  }

  function aiSuggest() {
    if (typeof AI !== 'undefined') AI.suggestBudgets('ai-budget-suggestions');
    else App.toast('AI module not loaded.', 'error');
  }

  async function createFromAI(category, limit) {
    const now   = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    try {
      const res = await API.post('/api/budgets/', { category, monthly_limit: limit, month });
      if (res.success) loadStatus();
    } catch(e) { /* silent */ }
  }

  return { render, loadStatus, openCreate, create, openEdit, update, deleteBudget, aiSuggest, createFromAI };
})();
