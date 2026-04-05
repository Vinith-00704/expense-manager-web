/* trips.js */
const TripsModule = (() => {
  let currentTrip = null;

  async function init(params) {
    if (params && params[0]) {
      await loadDetail(parseInt(params[0]));
    } else {
      await loadList();
    }
  }

  async function loadList() {
    const el = document.getElementById('page-trips');
    el.innerHTML = `
      <div class="page-top"><h2>Trip Planner</h2><button class="btn btn-primary btn-sm" onclick="TripsModule.openCreate()">＋ Trip</button></div>
      <div id="trips-grid" style="display:flex;flex-direction:column;gap:.75rem"></div>`;

    const res = await API.get('/api/trips');
    if (!res || !res.success) return;
    const trips = res.data;
    const el2 = document.getElementById('trips-grid');
    if (!trips.length) {
      el2.innerHTML = '<div class="empty-state"><div class="empty-icon">✈️</div><div class="empty-title">No trips yet</div><div class="empty-sub">Plan a trip and track expenses</div></div>';
      return;
    }
    el2.innerHTML = trips.map(t => {
      const pct = t.total_budget > 0 ? Math.min((t.total_spent / t.total_budget) * 100, 100) : 0;
      const fillClass = pct > 100 ? 'over' : pct > 80 ? 'warn' : '';
      const badge = t.status === 'active' ? 'badge-success' : t.status === 'completed' ? 'badge-info' : 'badge-accent';
      return `<div class="trip-card" onclick="App.navigate('trips/${t.id}')">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div class="trip-dest">✈️ ${t.destination}</div>
          <span class="badge ${badge}">${t.status}</span>
        </div>
        <div class="trip-dates">📅 ${App.fmtDate(t.start_date)} → ${App.fmtDate(t.end_date)}</div>
        <div class="budget-bar"><div class="budget-fill ${fillClass}" style="width:${pct}%"></div></div>
        <div class="trip-budget-info">
          <span>Spent: ${App.fmt(t.total_spent)}</span>
          <span>Budget: ${App.fmt(t.total_budget)}</span>
        </div>
        ${t.overspend > 0 ? `<div class="alert-banner danger mt-1" style="padding:.4rem .7rem;font-size:.78rem">⚠ Overspent by ${App.fmt(t.overspend)}</div>` : ''}
      </div>`;
    }).join('');
  }

  async function loadDetail(tripId) {
    document.getElementById('page-trips').classList.remove('active');
    document.getElementById('page-trip-detail').classList.add('active');
    document.getElementById('header-title').textContent = 'Trip Detail';

    const el = document.getElementById('page-trip-detail');
    el.innerHTML = `<div class="page-top">
      <a class="back-btn" onclick="App.navigate('trips')">← Back</a>
      <div style="display:flex;gap:.5rem">
        <button class="btn btn-ghost btn-sm" onclick="TripsModule.openAddMember(${tripId})">＋ Member</button>
        <button class="btn btn-primary btn-sm" onclick="TripsModule.openAddExpense(${tripId})">＋ Expense</button>
      </div>
    </div><div id="trip-detail-body">Loading…</div>`;

    const res = await API.get('/api/trips/' + tripId);
    if (!res || !res.success) { document.getElementById('trip-detail-body').textContent = 'Failed'; return; }
    const trip = res.data;
    currentTrip = trip;

    const settRes = await API.get(`/api/trips/${tripId}/settlements`);
    const settlements = (settRes && settRes.success) ? settRes.data : [];

    const pct = trip.total_budget > 0 ? Math.min((trip.total_spent / trip.total_budget) * 100, 100) : 0;
    const fillClass = pct > 100 ? 'over' : pct > 80 ? 'warn' : '';

    document.getElementById('trip-detail-body').innerHTML = `
      <h2 style="font-size:1.3rem;font-weight:800">✈️ ${trip.destination}</h2>
      <p class="text-muted text-sm mb-1">${App.fmtDate(trip.start_date)} → ${App.fmtDate(trip.end_date)}</p>

      <div class="card mb-2">
        <div style="display:flex;justify-content:space-between;font-size:.85rem;margin-bottom:.5rem">
          <span class="text-muted">Budget</span><span class="font-bold">${App.fmt(trip.total_budget)}</span>
        </div>
        <div class="budget-bar"><div class="budget-fill ${fillClass}" style="width:${pct}%"></div></div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-top:.5rem;text-align:center;font-size:.8rem">
          <div><div class="text-muted">Spent</div><div class="font-bold text-red">${App.fmt(trip.total_spent)}</div></div>
          <div><div class="text-muted">Remaining</div><div class="font-bold text-green">${App.fmt(trip.remaining)}</div></div>
          <div><div class="text-muted">Daily Budget</div><div class="font-bold text-accent">${App.fmt(trip.daily_budget)}</div></div>
        </div>
        ${trip.overspend > 0 ? `<div class="alert-banner danger mt-1" style="padding:.4rem .7rem;font-size:.78rem">⚠ Overspent by ${App.fmt(trip.overspend)}</div>` : ''}
      </div>

      <div class="section-title">Participants</div>
      <div class="member-chips mb-2">
        ${(trip.members||[]).map(m=>`<span class="member-chip selected">${m.member_name}</span>`).join('')}
      </div>

      <div class="section-title">Settlements</div>
      ${settlements.length ? `<div class="settlement-card mb-2">${settlements.map(s=>`
        <div class="settlement-row">
          <span class="sett-from">${s.from}</span>
          <span class="sett-arrow">→ owes →</span>
          <span class="sett-to">${s.to}</span>
          <span class="sett-amount">${App.fmt(s.amount)}</span>
        </div>`).join('')}</div>` :
        '<div class="card mb-2 text-muted text-sm" style="padding:.75rem 1rem">✅ All settled up!</div>'}

      <div class="section-title">Expenses</div>
      <div class="tx-list">
        ${(trip.expenses||[]).map(e=>`
          <div class="tx-item">
            <div class="tx-icon">💸</div>
            <div class="tx-info">
              <div class="tx-desc">${e.description}</div>
              <div class="tx-meta">Paid by ${e.payer_name||'—'} · ${App.fmtDate(e.expense_date)}</div>
            </div>
            <div class="tx-amount expense">${App.fmt(e.amount)}</div>
          </div>`).join('') || '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-sub">No expenses yet</div></div>'}
      </div>`;
  }

  function openCreate() {
    App.openModal('Plan a Trip', `
      <div class="form-group"><label>Destination *</label><input type="text" id="tc-dest" placeholder="Goa, Manali…"/></div>
      <div class="grid-2">
        <div class="form-group"><label>Start Date *</label><input type="date" id="tc-start"/></div>
        <div class="form-group"><label>End Date *</label><input type="date" id="tc-end"/></div>
      </div>
      <div class="form-group"><label>Total Budget *</label><input type="number" id="tc-budget" step="0.01" min="0.01" placeholder="0.00"/></div>
      <div class="form-group"><label>Notes</label><input type="text" id="tc-notes" placeholder="Optional"/></div>
      <div id="tc-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="TripsModule.createTrip()">Create Trip</button>`);
  }

  async function createTrip() {
    const body = {
      destination: document.getElementById('tc-dest').value,
      start_date: document.getElementById('tc-start').value,
      end_date: document.getElementById('tc-end').value,
      total_budget: document.getElementById('tc-budget').value,
      notes: document.getElementById('tc-notes').value,
    };
    const res = await API.post('/api/trips', body);
    if (res && res.success) { App.closeModal(); App.toast('Trip created!'); loadList(); }
    else document.getElementById('tc-error').textContent = (res && res.error) || 'Failed';
  }

  function openAddMember(tripId) {
    App.openModal('Add Member', `
      <div class="form-group"><label>Member Name *</label><input type="text" id="tm-name" placeholder="Name"/></div>
      <div class="form-group"><label>Contact (optional)</label><input type="text" id="tm-contact" placeholder="Phone or email"/></div>
      <div id="tm-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="TripsModule.addMember(${tripId})">Add</button>`);
  }

  async function addMember(tripId) {
    const name = document.getElementById('tm-name').value;
    const res = await API.post(`/api/trips/${tripId}/members`, { member_name: name, contact: document.getElementById('tm-contact').value });
    if (res && res.success) { App.closeModal(); App.toast('Member added!'); loadDetail(tripId); }
    else document.getElementById('tm-error').textContent = (res && res.error) || 'Failed';
  }

  function openAddExpense(tripId) {
    const members = currentTrip ? currentTrip.members : [];
    App.openModal('Add Travel Expense', `
      <div class="form-group"><label>Description *</label><input type="text" id="te-desc" placeholder="Hotel, Food…"/></div>
      <div class="grid-2">
        <div class="form-group"><label>Amount *</label><input type="number" id="te-amount" step="0.01" min="0.01" placeholder="0.00"/></div>
        <div class="form-group"><label>Date *</label><input type="date" id="te-date" value="${new Date().toISOString().slice(0,10)}"/></div>
      </div>
      <div class="form-group"><label>Paid By</label><select id="te-payer">
        <option value="">— Select —</option>
        ${members.map(m=>`<option value="${m.id}">${m.member_name}</option>`).join('')}
      </select></div>
      <div class="form-group"><label>Split Between</label><div class="member-chips" id="te-members">
        ${members.map(m=>`<span class="member-chip selected" data-id="${m.id}" onclick="this.classList.toggle('selected')">${m.member_name}</span>`).join('')}
      </div></div>
      <div id="te-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="TripsModule.addExpense(${tripId})">Add Expense</button>`);
  }

  async function addExpense(tripId) {
    const memberIds = [...document.querySelectorAll('#te-members .member-chip.selected')].map(c => parseInt(c.dataset.id));
    const body = {
      description: document.getElementById('te-desc').value,
      amount: document.getElementById('te-amount').value,
      expense_date: document.getElementById('te-date').value,
      paid_by_member_id: document.getElementById('te-payer').value || null,
      member_ids: memberIds,
    };
    const res = await API.post(`/api/trips/${tripId}/expenses`, body);
    if (res && res.success) { App.closeModal(); App.toast('Expense added!'); loadDetail(tripId); }
    else document.getElementById('te-error').textContent = (res && res.error) || 'Failed';
  }

  return { init, openCreate, createTrip, openAddMember, addMember, openAddExpense, addExpense };
})();
