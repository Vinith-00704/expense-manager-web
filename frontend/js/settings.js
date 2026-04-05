/* settings.js */
const SettingsModule = (() => {
  const CURRENCIES = ['₹ INR','$ USD','€ EUR','£ GBP','¥ JPY','₩ KRW','A$ AUD','S$ SGD'];

  async function init() {
    const user = App.getUser();
    const el = document.getElementById('page-settings');
    el.innerHTML = `
      <div class="page-top"><h2>Settings</h2></div>

      <div class="settings-section">
        <h3>Profile</h3>
        <div class="card" style="padding:1.25rem;display:flex;flex-direction:column;gap:.85rem">
          <div class="form-group"><label>Full Name</label><input type="text" id="set-name" value="${user.full_name||''}"/></div>
          <div class="form-group"><label>Email</label><input type="email" id="set-email" value="${user.email||''}"/></div>
          <div class="form-group"><label>Phone</label><input type="tel" id="set-phone" value="${user.phone||''}"/></div>
          <div class="grid-2">
            <div class="form-group"><label>Monthly Income</label><input type="number" id="set-salary" value="${user.monthly_salary||0}" min="0" step="0.01"/></div>
            <div class="form-group"><label>Age</label><input type="number" id="set-age" value="${user.age||0}" min="0" max="120"/></div>
          </div>
          <div class="form-group">
            <label>Currency</label>
            <select id="set-currency">
              ${CURRENCIES.map(c => {
                const sym = c.split(' ')[0];
                return `<option value="${sym}" ${user.currency===sym?'selected':''}>${c}</option>`;
              }).join('')}
            </select>
          </div>
          <div id="set-error" class="form-error"></div>
          <button class="btn btn-primary" onclick="SettingsModule.saveProfile()">Save Changes</button>
        </div>
      </div>

      <div class="settings-section">
        <h3>Security</h3>
        <div class="card" style="padding:1.25rem;display:flex;flex-direction:column;gap:.85rem">
          <div class="form-group">
            <label>Current Password</label>
            <input type="password" id="set-old-pwd" placeholder="Current password"/>
          </div>
          <div class="form-group">
            <label>New Password</label>
            <input type="password" id="set-new-pwd" placeholder="Min 6 characters"/>
          </div>
          <div id="pwd-error" class="form-error"></div>
          <div id="pwd-success" style="color:var(--green);font-size:.82rem"></div>
          <button class="btn btn-ghost" onclick="SettingsModule.changePassword()">Change Password</button>
        </div>
      </div>

      <div class="settings-section">
        <h3>Account</h3>
        <div class="settings-card">
          <div class="settings-row">
            <span class="settings-row-label">Username</span>
            <span class="settings-row-value">@${user.username}</span>
          </div>
          <div class="settings-row">
            <span class="settings-row-label">Member since</span>
            <span class="settings-row-value">${App.fmtDate(user.created_at)}</span>
          </div>
        </div>
      </div>

      <button class="btn btn-danger btn-full mt-2" onclick="App.logout()">🚪 Sign Out</button>`;
  }

  async function saveProfile() {
    const errEl = document.getElementById('set-error');
    errEl.textContent = '';
    const body = {
      full_name: document.getElementById('set-name').value,
      email: document.getElementById('set-email').value,
      phone: document.getElementById('set-phone').value,
      monthly_salary: document.getElementById('set-salary').value,
      age: document.getElementById('set-age').value,
      currency: document.getElementById('set-currency').value,
    };
    const res = await API.put('/api/auth/profile', body);
    if (res && res.success) { App.setUser(res.data); App.toast('Profile saved!'); }
    else errEl.textContent = (res && res.error) || 'Save failed';
  }

  async function changePassword() {
    const errEl = document.getElementById('pwd-error');
    const okEl = document.getElementById('pwd-success');
    errEl.textContent = ''; okEl.textContent = '';
    const body = {
      old_password: document.getElementById('set-old-pwd').value,
      new_password: document.getElementById('set-new-pwd').value,
    };
    const res = await API.put('/api/auth/password', body);
    if (res && res.success) { okEl.textContent = '✓ Password changed'; document.getElementById('set-old-pwd').value = ''; document.getElementById('set-new-pwd').value = ''; }
    else errEl.textContent = (res && res.error) || 'Failed';
  }

  return { init, saveProfile, changePassword };
})();
