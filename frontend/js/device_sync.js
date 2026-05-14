/**
 * device_sync.js — Device Sync & Notification Setup Page
 *
 * Features:
 *  1. Generate/revoke permanent device API keys
 *  2. Live setup wizard with copy-paste MacroDroid / Tasker configs
 *  3. Real-time notification badge (polls /api/device-keys/status every 30s)
 */

const DeviceSync = (() => {
  let _pollTimer = null;
  let _lastSeenCount = 0;

  // ── Notification Bell Polling ──────────────────────────────────────────────

  function startPolling() {
    if (_pollTimer) return;   // already running
    _checkNotifications();
    _pollTimer = setInterval(_checkNotifications, 30000);  // every 30s
  }

  function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  }

  async function _checkNotifications() {
    try {
      const res = await API.get('/api/device-keys/status');
      if (!res || !res.success) return;

      const { total_pending, recent_sms, has_new } = res.data;

      // Update nav badge
      _updateBadge(total_pending);

      // Toast if new SMS arrived since last check
      if (has_new && recent_sms > _lastSeenCount) {
        const diff = recent_sms - _lastSeenCount;
        App.toast(`📲 ${diff} new bank SMS transaction${diff > 1 ? 's' : ''} received! Check Import Center.`, 'success');
        _lastSeenCount = recent_sms;
        // Flash the import center nav item
        _flashNavItem();
      }
    } catch { /* silent — offline */ }
  }

  function _updateBadge(count) {
    let badge = document.getElementById('sms-notify-badge');
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  function _flashNavItem() {
    const navItem = document.querySelector('[data-page="imports"]');
    if (!navItem) return;
    navItem.classList.add('nav-flash');
    setTimeout(() => navItem.classList.remove('nav-flash'), 3000);
  }

  // ── Page Render ───────────────────────────────────────────────────────────

  async function render() {
    const el = document.getElementById('page-device-sync');
    if (!el) return;

    const serverUrl = window.location.origin;

    el.innerHTML = `
      <div class="page-header">
        <h2 class="page-title">&gt; DEVICE_SYNC</h2>
        <span class="badge badge-accent">ANDROID READY</span>
      </div>

      <!-- How It Works -->
      <div class="card ds-how-card">
        <div class="ds-section-label">HOW IT WORKS</div>
        <div class="ds-steps">
          <div class="ds-step"><span class="ds-step-num">01</span><span>Generate an API key below</span></div>
          <div class="ds-step"><span class="ds-step-num">02</span><span>Install MacroDroid on your Android phone (free)</span></div>
          <div class="ds-step"><span class="ds-step-num">03</span><span>Import the ready-made config (shown after key generation)</span></div>
          <div class="ds-step"><span class="ds-step-num">04</span><span>Every bank SMS auto-syncs to your Import Center</span></div>
        </div>
      </div>

      <!-- API Keys Section -->
      <div class="card" style="margin-bottom:.75rem">
        <div class="ds-section-label">YOUR DEVICE KEYS</div>
        <div id="ds-keys-list"><p class="loading-text">LOADING...</p></div>
        <button class="btn btn-primary" style="margin-top:.75rem" onclick="DeviceSync.openGenerateKey()">
          + GENERATE NEW KEY
        </button>
      </div>

      <!-- Sync Stats -->
      <div class="card" style="margin-bottom:.75rem">
        <div class="ds-section-label">SYNC STATUS</div>
        <div id="ds-sync-status"><p class="loading-text">LOADING...</p></div>
      </div>

      <!-- Test SMS -->
      <div class="card">
        <div class="ds-section-label">TEST YOUR CONNECTION</div>
        <p class="empty-sub" style="margin-bottom:.5rem">Paste a bank SMS to verify your server can parse it.</p>
        <textarea id="ds-test-sms" class="ds-textarea" placeholder="Dear Customer, Rs.450 debited from A/c XX1234 on 09-May-26 to SWIGGY via UPI. Avl Bal Rs.12,345.67" rows="3"></textarea>
        <button class="btn btn-ghost" style="margin-top:.5rem" onclick="DeviceSync.testSms()">TEST PARSE</button>
        <div id="ds-test-result" class="hidden" style="margin-top:.65rem"></div>
      </div>`;

    await _loadKeys();
    await _loadSyncStatus();
  }

  async function _loadKeys() {
    const el = document.getElementById('ds-keys-list');
    if (!el) return;
    const res = await API.get('/api/device-keys/');
    if (!res || !res.success) { el.innerHTML = '<p class="form-error">Failed to load keys.</p>'; return; }

    const keys = res.data;
    if (!keys.length) {
      el.innerHTML = '<p class="empty-sub">No device keys yet. Generate one to get started.</p>';
      return;
    }

    el.innerHTML = keys.map(k => `
      <div class="ds-key-row ${k.status === 'revoked' ? 'ds-key-revoked' : ''}">
        <div class="ds-key-info">
          <span class="ds-key-label">${k.label}</span>
          <span class="ds-key-prefix mono">${k.key_prefix}</span>
          <span class="badge ${k.status === 'active' ? 'badge-accent' : 'badge-danger'}">${k.status.toUpperCase()}</span>
        </div>
        <div class="ds-key-meta">
          <span>Created: ${k.created_at ? new Date(k.created_at).toLocaleDateString('en-IN') : '-'}</span>
          <span>Last used: ${k.last_used_at ? new Date(k.last_used_at).toLocaleString('en-IN') : 'Never'}</span>
          <span>Requests: ${k.total_requests}</span>
        </div>
        ${k.status === 'active' ? `
          <div class="ds-key-actions">
            <button class="btn-xs btn-reject" onclick="DeviceSync.revokeKey(${k.id}, '${k.label}')">REVOKE</button>
            <button class="btn-xs" onclick="DeviceSync.showSetupGuide('${k.key_prefix}...')">SETUP GUIDE</button>
          </div>` : ''}
      </div>`).join('');
  }

  async function _loadSyncStatus() {
    const el = document.getElementById('ds-sync-status');
    if (!el) return;
    const res = await API.get('/api/device-keys/status');
    if (!res || !res.success) return;
    const d = res.data;
    el.innerHTML = `
      <div class="ds-stats-grid">
        <div class="ds-stat"><div class="ds-stat-val">${d.pending_sms}</div><div class="ds-stat-lbl">PENDING SMS</div></div>
        <div class="ds-stat"><div class="ds-stat-val">${d.recent_sms}</div><div class="ds-stat-lbl">LAST 5 MIN</div></div>
        <div class="ds-stat"><div class="ds-stat-val">${d.total_pending}</div><div class="ds-stat-lbl">TOTAL PENDING</div></div>
      </div>
      ${d.has_new ? '<div class="ai-tip-bar">📲 New SMS transactions arrived recently! Go to Import Center → Pending to review them.</div>' : ''}`;
  }

  // ── Generate Key Modal ────────────────────────────────────────────────────

  function openGenerateKey() {
    App.openModal('GENERATE DEVICE KEY', `
      <div class="form-group">
        <label>Device Label</label>
        <input id="dk-label" placeholder="e.g. My Pixel 8, MacroDroid, Tasker" value="My Android Phone" />
      </div>
      <p class="empty-sub" style="margin-bottom:.75rem">
        This key never expires and lets your phone send SMS data to FinanceOS 24/7.
        Copy it immediately after generation — it won't be shown again.
      </p>
      <button class="btn btn-primary btn-full" onclick="DeviceSync.generateKey()">GENERATE KEY</button>`);
  }

  async function generateKey() {
    const label = document.getElementById('dk-label')?.value?.trim() || 'My Device';
    const res   = await API.post('/api/device-keys/generate', { label });
    if (!res || !res.success) { App.toast(res?.error || 'Failed.', 'error'); return; }

    const token = res.data.token;
    const serverUrl = window.location.origin;

    App.closeModal();

    // Show the token + full setup guide in a new modal
    App.openModal('YOUR API KEY — COPY NOW', `
      <div class="ds-token-warning">
        ⚠️ This key is shown ONCE. Copy it now and store it safely.
      </div>

      <div class="form-group" style="margin-top:.75rem">
        <label>Your Device API Key</label>
        <div class="ds-token-box">
          <code id="dk-token-text">${token}</code>
          <button class="btn-xs" onclick="DeviceSync.copyText('dk-token-text', this)">COPY</button>
        </div>
      </div>

      <div class="ds-section-label" style="margin-top:1rem">MACRODROID SETUP (Recommended)</div>
      <p class="empty-sub">In MacroDroid, create a new Macro:</p>
      <ul class="insight-list" style="margin:.5rem 0 .75rem">
        <li class="insight-item">> Trigger: SMS Received → filter by bank sender keywords</li>
        <li class="insight-item">> Action: HTTP Request (POST)</li>
      </ul>

      <div class="form-group">
        <label>HTTP Request URL</label>
        <div class="ds-token-box">
          <code id="dk-url">${serverUrl}/api/sms/raw</code>
          <button class="btn-xs" onclick="DeviceSync.copyText('dk-url', this)">COPY</button>
        </div>
      </div>

      <div class="form-group">
        <label>HTTP Headers (one per line)</label>
        <div class="ds-token-box">
          <code id="dk-headers">Content-Type: application/json
X-Device-Key: ${token}</code>
          <button class="btn-xs" onclick="DeviceSync.copyText('dk-headers', this)">COPY</button>
        </div>
      </div>

      <div class="form-group">
        <label>HTTP Body (JSON)</label>
        <div class="ds-token-box">
          <code id="dk-body">{"sms_text": "{sms_message_content}"}</code>
          <button class="btn-xs" onclick="DeviceSync.copyText('dk-body', this)">COPY</button>
        </div>
      </div>

      <div class="ds-section-label" style="margin-top:1rem">TASKER SETUP</div>
      <div class="ds-token-box" style="margin-bottom:.5rem">
        <code id="dk-tasker">Profile: SMS Received (sender ~HDFCBK|SBI|ICICIBK|AXISBK|KOTAKBK)
Task > HTTP Post:
  URL: ${serverUrl}/api/sms/raw
  Data: {"sms_text": "%SMSRB"}
  Headers:
    Content-Type:application/json
    X-Device-Key:${token}</code>
        <button class="btn-xs" onclick="DeviceSync.copyText('dk-tasker', this)">COPY</button>
      </div>

      <div class="ds-section-label" style="margin-top:1rem">BANK SMS FILTER KEYWORDS</div>
      <div class="ds-token-box">
        <code id="dk-banks">HDFCBK, SBI, ICICIBK, AXISBK, KOTAKBK, YESBANK, INDUSIND, FEDERAL, IDFC, RBLBANK, PAYTM, PHONEPE</code>
        <button class="btn-xs" onclick="DeviceSync.copyText('dk-banks', this)">COPY</button>
      </div>

      <button class="btn btn-primary btn-full" style="margin-top:1rem" onclick="App.closeModal(); DeviceSync.render()">DONE — I'VE SAVED MY KEY</button>`);

    _loadKeys();
  }

  function showSetupGuide(keyPrefix) {
    const serverUrl = window.location.origin;
    App.openModal('SETUP GUIDE', `
      <p class="empty-sub">Using key: <strong class="mono">${keyPrefix}</strong></p>
      <p class="empty-sub" style="margin-top:.5rem">
        You can't retrieve the full key again. If you lost it, revoke and generate a new one.
      </p>
      <div class="ds-section-label" style="margin-top:1rem">MACRODROID HTTP ACTION CONFIG</div>
      <div class="ds-token-box">
        <code>URL: ${serverUrl}/api/sms/raw
Method: POST
Header: Content-Type: application/json
Header: X-Device-Key: [YOUR_FULL_KEY]
Body: {"sms_text": "{sms_message_content}"}</code>
      </div>
      <p class="empty-sub" style="margin-top:.5rem">Replace [YOUR_FULL_KEY] with the key you copied when you generated it.</p>`);
  }

  async function revokeKey(id, label) {
    if (!confirm(`Revoke key "${label}"? Any automation using it will immediately stop working.`)) return;
    const res = await API.del(`/api/device-keys/${id}`);
    if (res && res.success) {
      App.toast('Key revoked.', 'success');
      _loadKeys();
    } else {
      App.toast(res?.error || 'Failed.', 'error');
    }
  }

  // ── SMS Test ──────────────────────────────────────────────────────────────

  async function testSms() {
    const sms = document.getElementById('ds-test-sms')?.value?.trim();
    const el  = document.getElementById('ds-test-result');
    if (!sms || !el) return;

    el.innerHTML = '<div class="ai-thinking"><div class="ai-spinner"></div><p>Parsing SMS...</p></div>';
    el.classList.remove('hidden');

    try {
      const res = await API.post('/api/sms/raw', { sms_text: sms });
      if (res && res.success) {
        const d = res.data;
        el.innerHTML = `
          <div class="ds-test-success">
            <div class="ds-section-label" style="margin-bottom:.5rem">✅ PARSED SUCCESSFULLY</div>
            <div class="ds-test-grid">
              <div><span class="ds-tl">Merchant</span><span class="mono">${d.normalized_merchant || d.merchant || '-'}</span></div>
              <div><span class="ds-tl">Amount</span><span class="mono ${d.transaction_direction==='debit'?'amount-debit':'amount-credit'}">${d.transaction_direction==='debit'?'-':'+'}${App.fmt(d.amount)}</span></div>
              <div><span class="ds-tl">Date</span><span class="mono">${d.transaction_date}</span></div>
              <div><span class="ds-tl">Category</span><span class="cat-pill">${d.category}</span></div>
              <div><span class="ds-tl">Payment</span><span class="mono">${d.payment_method || '-'}</span></div>
              <div><span class="ds-tl">Status</span><span class="badge ${d.status==='duplicate'?'badge-danger':'badge-accent'}">${d.status?.toUpperCase()}</span></div>
            </div>
            <p class="empty-sub" style="margin-top:.5rem">Transaction queued in Import Center → Pending.</p>
          </div>`;
      } else {
        el.innerHTML = `<p class="form-error">❌ ${res?.error || 'Parse failed. Try a different SMS.'}</p>`;
      }
    } catch(e) {
      el.innerHTML = `<p class="form-error">Error: ${e.message}</p>`;
    }
  }

  // ── Utility ───────────────────────────────────────────────────────────────

  function copyText(elementId, btn) {
    const el = document.getElementById(elementId);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'COPIED!';
      setTimeout(() => btn.textContent = orig, 2000);
    });
  }

  return {
    render,
    startPolling,
    stopPolling,
    openGenerateKey,
    generateKey,
    showSetupGuide,
    revokeKey,
    testSms,
    copyText,
  };
})();
