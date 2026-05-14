/**
 * goals.js — Financial Goals UI
 */
const Goals = (() => {
  async function render() {
    const el = document.getElementById('page-goals');
    el.innerHTML = `
      <div class="page-header">
        <h2 class="page-title">&gt; FINANCIAL_GOALS</h2>
        <button class="btn btn-primary" onclick="Goals.openCreate()">+ NEW GOAL</button>
      </div>
      <div id="goals-list" class="goals-grid"><p class="loading-text">LOADING...</p></div>
    `;
    _load();
  }

  async function _load() {
    try {
      const res = await API.get('/api/goals/');
      const el = document.getElementById('goals-list');
      if (!res.success) { el.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      if (!res.data.length) {
        el.innerHTML = `<div class="empty-state">
          <p class="empty-title">NO_GOALS_SET</p>
          <p class="empty-sub">Start saving toward a target. Create your first financial goal.</p>
          <button class="btn btn-primary" onclick="Goals.openCreate()">CREATE GOAL</button>
        </div>`; return;
      }
      el.innerHTML = res.data.map(_goalCard).join('');
    } catch(e) { document.getElementById('goals-list').innerHTML = `<p class="form-error">${e.message}</p>`; }
  }

  function _goalCard(g) {
    const pct = g.progress_pct;
    const barW = Math.min(pct, 100);
    const statusCls = g.status === 'achieved' ? 'status-active' : g.status === 'cancelled' ? 'status-revoked' : '';
    return `
      <div class="goal-card">
        <div class="goal-header">
          <span class="goal-name">${g.name}</span>
          <span class="device-status ${statusCls}">${g.status.toUpperCase()}</span>
        </div>
        <div class="goal-category">${g.category}</div>
        <div class="goal-progress-bar">
          <div class="goal-bar-fill ${pct >= 100 ? 'bar-complete' : ''}" style="width:${barW}%"></div>
        </div>
        <div class="goal-amounts">
          <span class="amount-credit">${App.fmt(g.current_amount)} saved</span>
          <span class="goal-sep">/</span>
          <span>${App.fmt(g.target_amount)} target</span>
          <span class="goal-pct">${pct}%</span>
        </div>
        ${g.deadline ? `<div class="goal-deadline">Deadline: ${g.deadline} ${g.days_remaining !== null ? `(${g.days_remaining}d left)` : ''}</div>` : ''}
        <div class="goal-actions">
          <button class="btn-xs btn-confirm" onclick="Goals.openDeposit(${g.id}, ${g.current_amount}, ${g.target_amount})">ADD FUNDS</button>
          <button class="btn-xs" onclick="Goals.openEdit(${JSON.stringify(g).replace(/"/g,'&quot;')})">EDIT</button>
          <button class="btn-xs" onclick="Goals.showAiAdvice(${g.id})">AI ADVICE</button>
          ${g.status === 'active' ? `<button class="btn-xs btn-reject" onclick="Goals.cancel(${g.id})">CANCEL</button>` : ''}
        </div>
        <div id="goal-ai-${g.id}" class="hidden" style="margin-top:.5rem"></div>
      </div>
    `;
  }

  function openCreate() {
    App.openModal('NEW FINANCIAL GOAL', `
      <form onsubmit="Goals.create(event)" class="modal-form">
        <div class="form-group"><label>Goal Name</label><input id="g-name" placeholder="e.g. Emergency Fund" required /></div>
        <div class="form-row">
          <div class="form-group"><label>Target Amount</label><input id="g-target" type="number" min="1" step="0.01" placeholder="50000" required /></div>
          <div class="form-group"><label>Current Savings</label><input id="g-current" type="number" min="0" step="0.01" placeholder="0" /></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Category</label>
            <select id="g-cat">
              <option>Emergency Fund</option><option>Vacation</option><option>Vehicle</option>
              <option>Gadget</option><option>Home</option><option>Education</option>
              <option>Investment</option><option>Other</option>
            </select>
          </div>
          <div class="form-group"><label>Deadline (optional)</label><input id="g-deadline" type="date" /></div>
        </div>
        <div class="form-group"><label>Description</label><input id="g-desc" placeholder="Brief description" /></div>
        <button type="submit" class="btn btn-primary btn-full">CREATE GOAL</button>
      </form>
    `);
  }

  async function create(e) {
    e.preventDefault();
    try {
      const res = await API.post('/api/goals/', {
        name: document.getElementById('g-name').value,
        target_amount: parseFloat(document.getElementById('g-target').value),
        current_amount: parseFloat(document.getElementById('g-current').value || 0),
        category: document.getElementById('g-cat').value,
        deadline: document.getElementById('g-deadline').value || null,
        description: document.getElementById('g-desc').value,
      });
      if (res.success) { App.closeModal(); App.toast('Goal created!', 'success'); _load(); }
      else App.toast(res.error, 'error');
    } catch(e) { App.toast(e.message, 'error'); }
  }

  function openDeposit(id, current, target) {
    App.openModal('ADD FUNDS TO GOAL', `
      <form onsubmit="Goals.deposit(event, ${id}, ${current})" class="modal-form">
        <div class="form-group">
          <label>Amount to Add</label>
          <input id="dep-amt" type="number" min="1" step="0.01" placeholder="Enter amount" required />
        </div>
        <p class="empty-sub">Current: ${App.fmt(current)} / Target: ${App.fmt(target)}</p>
        <button type="submit" class="btn btn-primary btn-full">ADD FUNDS</button>
      </form>
    `);
  }

  async function deposit(e, id, current) {
    e.preventDefault();
    const add = parseFloat(document.getElementById('dep-amt').value);
    const res = await API.put(`/api/goals/${id}`, { current_amount: current + add });
    if (res.success) { App.closeModal(); App.toast('Funds added!', 'success'); _load(); }
    else App.toast(res.error, 'error');
  }

  function openEdit(g) {
    App.openModal('EDIT GOAL', `
      <form onsubmit="Goals.update(event, ${g.id})" class="modal-form">
        <div class="form-group"><label>Name</label><input id="ge-name" value="${g.name}" required /></div>
        <div class="form-row">
          <div class="form-group"><label>Target</label><input id="ge-target" type="number" value="${g.target_amount}" required /></div>
          <div class="form-group"><label>Status</label>
            <select id="ge-status">
              <option ${g.status==='active'?'selected':''}>active</option>
              <option ${g.status==='achieved'?'selected':''}>achieved</option>
              <option ${g.status==='cancelled'?'selected':''}>cancelled</option>
            </select>
          </div>
        </div>
        <button type="submit" class="btn btn-primary btn-full">SAVE</button>
      </form>
    `);
  }

  async function update(e, id) {
    e.preventDefault();
    const res = await API.put(`/api/goals/${id}`, {
      name: document.getElementById('ge-name').value,
      target_amount: parseFloat(document.getElementById('ge-target').value),
      status: document.getElementById('ge-status').value,
    });
    if (res.success) { App.closeModal(); App.toast('Goal updated!', 'success'); _load(); }
    else App.toast(res.error, 'error');
  }

  async function cancel(id) {
    const res = await API.put(`/api/goals/${id}`, { status: 'cancelled' });
    if (res.success) { App.toast('Goal cancelled.', 'success'); _load(); }
  }

  function showAiAdvice(goalId) {
    if (typeof AI !== 'undefined') {
      AI.showGoalAdvice(goalId, `goal-ai-${goalId}`);
    } else {
      App.toast('AI module not loaded.', 'error');
    }
  }

  return { render, openCreate, create, openDeposit, deposit, openEdit, update, cancel, showAiAdvice };
})();
