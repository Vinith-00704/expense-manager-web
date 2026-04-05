/* rooms.js */
const RoomsModule = (() => {
  let currentRoom = null;

  async function init(params) {
    if (params && params[0]) {
      await loadDetail(parseInt(params[0]));
    } else {
      await loadList();
    }
  }

  async function loadList() {
    const el = document.getElementById('page-rooms');
    el.innerHTML = `
      <div class="page-top"><h2>Rooms</h2><button class="btn btn-primary btn-sm" onclick="RoomsModule.openCreate()">＋ Room</button></div>
      <div id="rooms-grid" style="display:flex;flex-direction:column;gap:.75rem"></div>`;

    const res = await API.get('/api/rooms');
    if (!res || !res.success) return;
    const rooms = res.data;
    const el2 = document.getElementById('rooms-grid');
    if (!rooms.length) {
      el2.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div><div class="empty-title">No rooms yet</div><div class="empty-sub">Create a room to split expenses</div></div>';
      return;
    }
    el2.innerHTML = rooms.map(r => `
      <div class="room-card" onclick="App.navigate('rooms/${r.id}')">
        <div class="room-name">${r.name}</div>
        <div class="room-meta">
          <span>👤 ${r.member_count} members</span>
          <span>💸 ${App.fmt(r.total_spent)} total</span>
          ${r.is_owner ? '<span class="badge badge-accent">Owner</span>' : ''}
        </div>
      </div>`).join('');
  }

  async function loadDetail(roomId) {
    document.getElementById('page-rooms').classList.remove('active');
    document.getElementById('page-room-detail').classList.add('active');
    document.getElementById('header-title').textContent = 'Room Detail';

    const el = document.getElementById('page-room-detail');
    el.innerHTML = `<div class="page-top">
      <a class="back-btn" onclick="App.navigate('rooms')">← Back</a>
      <div style="display:flex;gap:.5rem">
        <button class="btn btn-ghost btn-sm" onclick="RoomsModule.openAddMember(${roomId})">＋ Member</button>
        <button class="btn btn-primary btn-sm" onclick="RoomsModule.openAddExpense(${roomId})">＋ Expense</button>
      </div>
    </div><div id="room-detail-body">Loading…</div>`;

    const res = await API.get('/api/rooms/' + roomId);
    if (!res || !res.success) { document.getElementById('room-detail-body').textContent = 'Failed to load room'; return; }
    const room = res.data;
    currentRoom = room;

    const settRes = await API.get(`/api/rooms/${roomId}/settlements`);
    const settlements = (settRes && settRes.success) ? settRes.data : [];

    document.getElementById('room-detail-body').innerHTML = `
      <h2 style="font-size:1.3rem;font-weight:800;margin-bottom:.25rem">${room.name}</h2>
      <p class="text-muted text-sm mb-2">${room.description || ''}</p>

      <div class="section-title">Members</div>
      <div class="member-chips mb-2">
        ${room.members.map(m=>`<span class="member-chip selected">${m.full_name}</span>`).join('')}
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

      <div class="section-title">Expense Ledger</div>
      <div id="room-ledger" class="tx-list"></div>`;

    loadLedger(roomId);
  }

  async function loadLedger(roomId) {
    const res = await API.get(`/api/rooms/${roomId}/expenses`);
    if (!res || !res.success) return;
    const el = document.getElementById('room-ledger');
    if (!res.data.length) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-sub">No expenses yet</div></div>'; return; }
    el.innerHTML = res.data.map(e => `
      <div class="tx-item">
        <div class="tx-icon">💸</div>
        <div class="tx-info">
          <div class="tx-desc">${e.description}</div>
          <div class="tx-meta">Paid by ${e.payer_name} · ${App.fmtDate(e.expense_date)}</div>
        </div>
        <div class="tx-amount expense">${App.fmt(e.amount)}</div>
      </div>`).join('');
  }

  function openCreate() {
    App.openModal('Create Room', `
      <div class="form-group"><label>Room Name *</label><input type="text" id="rc-name" placeholder="Flat 4B, Road Trip…"/></div>
      <div class="form-group"><label>Description</label><input type="text" id="rc-desc" placeholder="Optional description"/></div>
      <div id="rc-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="RoomsModule.createRoom()">Create Room</button>`);
  }

  async function createRoom() {
    const name = document.getElementById('rc-name').value;
    if (!name.trim()) { document.getElementById('rc-error').textContent = 'Name required'; return; }
    const res = await API.post('/api/rooms', { name, description: document.getElementById('rc-desc').value });
    if (res && res.success) { App.closeModal(); App.toast('Room created!'); loadList(); }
    else document.getElementById('rc-error').textContent = (res && res.error) || 'Failed';
  }

  function openAddMember(roomId) {
    App.openModal('Add Member', `
      <div class="form-group"><label>Username</label><input type="text" id="rm-user" placeholder="their_username"/></div>
      <div id="rm-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="RoomsModule.addMember(${roomId})">Add Member</button>`);
  }

  async function addMember(roomId) {
    const username = document.getElementById('rm-user').value;
    const res = await API.post(`/api/rooms/${roomId}/members`, { username });
    if (res && res.success) { App.closeModal(); App.toast('Member added!'); loadDetail(roomId); }
    else document.getElementById('rm-error').textContent = (res && res.error) || 'Failed';
  }

  function openAddExpense(roomId) {
    const members = currentRoom ? currentRoom.members : [];
    App.openModal('Add Shared Expense', `
      <div class="form-group"><label>Description *</label><input type="text" id="re-desc" placeholder="Groceries, Rent…"/></div>
      <div class="grid-2">
        <div class="form-group"><label>Amount *</label><input type="number" id="re-amount" step="0.01" min="0.01" placeholder="0.00"/></div>
        <div class="form-group"><label>Date *</label><input type="date" id="re-date" value="${new Date().toISOString().slice(0,10)}"/></div>
      </div>
      <div class="form-group"><label>Split Between</label>
        <div class="member-chips" id="re-members">
          ${members.map(m=>`<span class="member-chip selected" data-id="${m.id}" onclick="this.classList.toggle('selected')">${m.full_name}</span>`).join('')}
        </div>
      </div>
      <div id="re-error" class="form-error"></div>
      <button class="btn btn-primary btn-full" onclick="RoomsModule.addExpense(${roomId})">Add Expense</button>`);
  }

  async function addExpense(roomId) {
    const memberIds = [...document.querySelectorAll('#re-members .member-chip.selected')].map(c => parseInt(c.dataset.id));
    const body = {
      description: document.getElementById('re-desc').value,
      amount: document.getElementById('re-amount').value,
      expense_date: document.getElementById('re-date').value,
      member_ids: memberIds,
    };
    const res = await API.post(`/api/rooms/${roomId}/expenses`, body);
    if (res && res.success) { App.closeModal(); App.toast('Expense added!'); loadDetail(roomId); }
    else document.getElementById('re-error').textContent = (res && res.error) || 'Failed';
  }

  return { init, openCreate, createRoom, openAddMember, addMember, openAddExpense, addExpense };
})();
