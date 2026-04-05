/* subscriptions.js */
const SubscriptionsModule = (() => {
  async function init() {
    const el = document.getElementById('page-subscriptions');
    el.innerHTML = `
      <div class="page-top"><h2>Subscriptions</h2><button class="btn btn-primary btn-sm" onclick="SubscriptionsModule.openAdd()">＋ Add</button></div>
      <div id="sub-total" class="card mb-1" style="display:flex;justify-content:space-between;align-items:center;padding:.85rem 1rem">
        <span class="text-muted text-sm">Monthly cost</span>
        <span class="font-bold text-accent" id="sub-total-val">…</span>
      </div>
      <div id="sub-grid" class="sub-grid"></div>`;
    load();
  }

  async function load() {
    const res = await API.get('/api/subscriptions');
    if (!res || !res.success) return;
    const items = res.data;

    const totalRes = await API.get('/api/subscriptions/monthly-total');
    if (totalRes && totalRes.success) {
      document.getElementById('sub-total-val').textContent = App.fmt(totalRes.data.monthly_total) + '/mo';
    }

    const el = document.getElementById('sub-grid');
    if (!items.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">🔔</div><div class="empty-title">No subscriptions</div><div class="empty-sub">Track your recurring bills</div></div>';
      return;
    }
    el.innerHTML = items.map(s => {
      const badge = s.days_left <= 3 ? 'badge-danger' : s.days_left <= 7 ? 'badge-warning' : 'badge-success';
      return `<div class="sub-card">
        <div class="sub-card-top">
          <div class="sub-name">${s.name}</div>
          <span class="badge ${badge}">${s.days_left}d</span>
        </div>
        <div class="sub-amount">${App.fmt(s.amount)}<span class="text-muted text-sm"> /${s.billing_cycle.replace('ly','')}</span></div>
        <div class="sub-renewal">Next: ${App.fmtDate(s.next_renewal)}</div>
        <div class="sub-footer">
          <span class="badge badge-accent">${s.category}</span>
          <div style="display:flex;gap:.3rem">
            <button class="btn btn-ghost btn-sm" onclick="SubscriptionsModule.openEdit(${s.id})">✏️</button>
            <button class="btn btn-danger btn-sm" onclick="SubscriptionsModule.del(${s.id})">🗑</button>
          </div>
        </div>
      </div>`;
    }).join('');
  }

  function formHtml(s = {}) {
    const cycles = ['monthly','quarterly','yearly'];
    return `
      <div class="form-group"><label>Service Name *</label><input type="text" id="sf-name" value="${s.name||''}" placeholder="Netflix, Spotify…" required/></div>
      <div class="grid-2">
        <div class="form-group"><label>Amount *</label><input type="number" id="sf-amount" value="${s.amount||''}" step="0.01" min="0.01" placeholder="0.00"/></div>
        <div class="form-group"><label>Billing Cycle</label><select id="sf-cycle">${cycles.map(c=>`<option value="${c}" ${s.billing_cycle===c?'selected':''}>${c.charAt(0).toUpperCase()+c.slice(1)}</option>`).join('')}</select></div>
      </div>
      <div class="form-group"><label>Last Paid Date *</label><input type="date" id="sf-date" value="${s.last_paid_date||new Date().toISOString().slice(0,10)}"/></div>
      <div class="form-group"><label>Category</label><input type="text" id="sf-cat" value="${s.category||'Other'}" placeholder="Streaming, Software…"/></div>
      <div class="form-group"><label>Notes</label><input type="text" id="sf-notes" value="${s.notes||''}" placeholder="Optional"/></div>
      <div id="sf-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="SubscriptionsModule.save(${s.id||0})">${s.id?'Update':'Add Subscription'}</button>`;
  }

  function openAdd() { App.openModal('Add Subscription', formHtml()); }
  async function openEdit(id) {
    const res = await API.get('/api/subscriptions');
    if (!res || !res.success) return;
    const s = res.data.find(x => x.id === id);
    if (s) App.openModal('Edit Subscription', formHtml(s));
  }

  async function save(id) {
    const errEl = document.getElementById('sf-error');
    errEl.textContent = '';
    const body = {
      name: document.getElementById('sf-name').value,
      amount: document.getElementById('sf-amount').value,
      billing_cycle: document.getElementById('sf-cycle').value,
      last_paid_date: document.getElementById('sf-date').value,
      category: document.getElementById('sf-cat').value,
      notes: document.getElementById('sf-notes').value,
    };
    const res = id ? await API.put('/api/subscriptions/'+id, body) : await API.post('/api/subscriptions', body);
    if (res && res.success) { App.closeModal(); App.toast(id?'Updated!':'Added!'); load(); }
    else { errEl.textContent = (res && res.error) || 'Save failed'; }
  }

  async function del(id) {
    if (!confirm('Delete subscription?')) return;
    const res = await API.del('/api/subscriptions/'+id);
    if (res && res.success) { App.toast('Deleted'); load(); }
  }

  return { init, load, openAdd, openEdit, save, del };
})();
