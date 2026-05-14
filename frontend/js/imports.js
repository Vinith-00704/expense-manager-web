/**
 * imports.js — Import Center UI
 * Handles bank statement upload, pending review, history, and SMS status.
 */

const Imports = (() => {
  let _pendingPage = 1;
  let _historyPage = 1;
  let _selectedIds  = new Set();

  // ── Entry point ──────────────────────────────────────────────────────────

  function render() {
    const el = document.getElementById('page-imports');
    el.innerHTML = `
      <div class="page-header">
        <h2 class="page-title">&gt; IMPORT_CENTER</h2>
        <p class="page-subtitle">Upload bank statements · Review transactions · Sync SMS</p>
      </div>

      <div class="import-tabs">
        <button class="itab active" id="itab-upload"  onclick="Imports.switchTab('upload')"> [UPLOAD]  </button>
        <button class="itab"        id="itab-pending" onclick="Imports.switchTab('pending')">[PENDING] </button>
        <button class="itab"        id="itab-ai"      onclick="Imports.switchTab('ai')">[AI ANALYSE]</button>
        <button class="itab"        id="itab-history" onclick="Imports.switchTab('history')">[HISTORY] </button>
        <button class="itab"        id="itab-sms"     onclick="Imports.switchTab('sms')">   [SMS]     </button>
      </div>

      <div id="import-panel-upload"  class="import-panel active">${_uploadPanel()}</div>
      <div id="import-panel-pending" class="import-panel hidden"></div>
      <div id="import-panel-ai"      class="import-panel hidden"></div>
      <div id="import-panel-history" class="import-panel hidden"></div>
      <div id="import-panel-sms"     class="import-panel hidden"></div>
    `;
    _bindDropzone();
  }

  function switchTab(tab) {
    document.querySelectorAll('.itab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.import-panel').forEach(p => { p.classList.add('hidden'); p.classList.remove('active'); });
    document.getElementById('itab-' + tab).classList.add('active');
    const panel = document.getElementById('import-panel-' + tab);
    panel.classList.remove('hidden');
    panel.classList.add('active');

    if (tab === 'pending' && !panel.innerHTML.trim()) _loadPending();
    if (tab === 'history' && !panel.innerHTML.trim()) _loadHistory();
    if (tab === 'sms'     && !panel.innerHTML.trim()) _loadSmsStatus();
    if (tab === 'ai'      && !panel.innerHTML.trim()) _loadAiPanel();
  }

  // ── Upload panel ─────────────────────────────────────────────────────────

  function _uploadPanel() {
    return `
      <div class="upload-zone" id="drop-zone">
        <div class="upload-zone-inner">
          <div class="upload-icon">[+]</div>
          <p class="upload-title">DROP_FILE_HERE</p>
          <p class="upload-sub">CSV / XLSX / PDF · Max 10 MB</p>
          <p class="upload-sub">Supported banks: HDFC · SBI · ICICI · AXIS</p>
          <label class="btn btn-primary upload-btn" for="file-input">SELECT_FILE</label>
          <input type="file" id="file-input" accept=".csv,.xlsx,.xls,.pdf" style="display:none" onchange="Imports.handleFileSelect(this)" />
        </div>
      </div>
      <div id="upload-result" class="upload-result hidden"></div>
    `;
  }

  function _bindDropzone() {
    const zone = document.getElementById('drop-zone');
    if (!zone) return;
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) _uploadFile(file);
    });
  }

  function handleFileSelect(input) {
    if (input.files[0]) _uploadFile(input.files[0]);
  }

  async function _uploadFile(file) {
    const zone = document.getElementById('drop-zone');
    const result = document.getElementById('upload-result');
    zone.classList.add('uploading');
    zone.querySelector('.upload-title').textContent = 'UPLOADING...';

    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await API.postForm('/api/imports/upload', fd);
      zone.classList.remove('uploading');
      zone.querySelector('.upload-title').textContent = 'DROP_FILE_HERE';

      if (res.success) {
        const d = res.data;
        result.classList.remove('hidden');
        result.innerHTML = `
          <div class="upload-stats">
            <div class="stat-badge success">PARSED: ${d.total_parsed}</div>
            <div class="stat-badge pending">PENDING: ${d.pending_created}</div>
            <div class="stat-badge warn">DUPLICATES: ${d.duplicates}</div>
            <div class="stat-badge error">FAILED: ${d.failed}</div>
            ${d.bank_detected ? `<div class="stat-badge info">BANK: ${d.bank_detected.toUpperCase()}</div>` : ''}
          </div>
          <p class="upload-ok">File "${file.name}" processed. Review pending transactions below.</p>
          <button class="btn btn-primary" onclick="Imports.switchTab('pending')">REVIEW PENDING &gt;</button>
        `;
        App.toast(`Imported ${d.pending_created} transactions from ${file.name}`, 'success');
      } else {
        result.classList.remove('hidden');
        result.innerHTML = `<p class="form-error">ERROR: ${res.error || 'Upload failed'}</p>`;
      }
    } catch (e) {
      zone.classList.remove('uploading');
      zone.querySelector('.upload-title').textContent = 'DROP_FILE_HERE';
      App.toast('Upload failed: ' + e.message, 'error');
    }
  }

  // ── Pending panel ─────────────────────────────────────────────────────────

  async function _loadPending() {
    const panel = document.getElementById('import-panel-pending');
    panel.innerHTML = `<p class="loading-text">LOADING PENDING TRANSACTIONS...</p>`;
    try {
      const res = await API.get(`/api/imports/pending?page=${_pendingPage}&per_page=50`);
      if (!res.success) { panel.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      _selectedIds.clear();
      panel.innerHTML = _buildPendingTable(res.data);
    } catch(e) {
      panel.innerHTML = `<p class="form-error">Failed to load: ${e.message}</p>`;
    }
  }

  const CATEGORIES = [
    'Food & Dining','Transportation','Shopping','Bills & Utilities',
    'Healthcare','Entertainment','Education','Travel',
    'Investments','Home & Rent','Personal Care','Salary',
    'Freelance','Business','Gift','Other'
  ];

  function _buildPendingTable(data) {
    if (!data.items || data.items.length === 0) {
      return `<div class="empty-state">
        <p class="empty-title">NO_PENDING_TRANSACTIONS</p>
        <p class="empty-sub">Upload a bank statement to get started.</p>
        <button class="btn btn-primary" onclick="Imports.switchTab('upload')">GO TO UPLOAD</button>
      </div>`;
    }

    const rows = data.items.map(tx => `
      <tr class="pending-row ${tx.status === 'duplicate' ? 'is-dup' : ''}" id="row-${tx.id}" data-id="${tx.id}">
        <td><input type="checkbox" class="row-check" data-id="${tx.id}" onchange="Imports.toggleSelect(${tx.id})" /></td>
        <td class="mono">${tx.transaction_date}</td>
        <td class="merchant-cell">
          <span class="norm-merchant">${tx.normalized_merchant || tx.merchant || '-'}</span>
          ${tx.status === 'duplicate' ? '<span class="dup-badge">DUP</span>' : ''}
        </td>
        <td><span class="confidence-bar" title="${Math.round((tx.confidence_score||0)*100)}% conf">${_catBadge(tx.category)}</span></td>
        <td class="${tx.transaction_direction === 'debit' ? 'amount-debit' : 'amount-credit'}">
          ${tx.transaction_direction === 'debit' ? '-' : '+'}${App.fmt(tx.amount)}
        </td>
        <td class="row-actions">
          <button class="btn-xs" onclick="Imports.openEditRow(${tx.id})">EDIT</button>
          <button class="btn-xs btn-confirm" onclick="Imports.confirmOne(${tx.id})">CONFIRM</button>
          <button class="btn-xs btn-reject"  onclick="Imports.rejectOne(${tx.id})">REJECT</button>
        </td>
      </tr>
      <tr class="edit-row hidden" id="edit-row-${tx.id}">
        <td colspan="6">
          <div class="inline-edit-form">
            <div class="ie-grid">
              <div class="ie-field">
                <label>MERCHANT</label>
                <input id="ie-merchant-${tx.id}" value="${(tx.normalized_merchant||tx.merchant||'').replace(/"/g,'&quot;')}" placeholder="Merchant name" />
              </div>
              <div class="ie-field">
                <label>CATEGORY</label>
                <select id="ie-cat-${tx.id}">
                  ${CATEGORIES.map(c => `<option ${c===tx.category?'selected':''}>${c}</option>`).join('')}
                </select>
              </div>
              <div class="ie-field">
                <label>AMOUNT</label>
                <input id="ie-amt-${tx.id}" type="number" step="0.01" min="0.01" value="${tx.amount}" />
              </div>
              <div class="ie-field">
                <label>DATE</label>
                <input id="ie-date-${tx.id}" type="date" value="${tx.transaction_date}" />
              </div>
              <div class="ie-field">
                <label>TYPE</label>
                <select id="ie-dir-${tx.id}">
                  <option value="debit"  ${tx.transaction_direction==='debit' ?'selected':''}>DEBIT</option>
                  <option value="credit" ${tx.transaction_direction==='credit'?'selected':''}>CREDIT</option>
                </select>
              </div>
              <div class="ie-field">
                <label>PAYMENT</label>
                <select id="ie-pay-${tx.id}">
                  ${['UPI','NEFT','IMPS','RTGS','Card','NetBanking','ATM','Wallet','Cash','Other']
                    .map(m=>`<option ${m===(tx.payment_method||'')? 'selected':''}>${m}</option>`).join('')}
                </select>
              </div>
            </div>
            <div class="ie-actions">
              <button class="btn btn-primary btn-sm" onclick="Imports.saveEdit(${tx.id})">SAVE</button>
              <button class="btn btn-sm"             onclick="Imports.closeEditRow(${tx.id})">CANCEL</button>
              <button class="btn btn-sm btn-confirm" onclick="Imports.saveAndConfirm(${tx.id})">SAVE & CONFIRM</button>
            </div>
          </div>
        </td>
      </tr>
    `).join('');

    return `
      <div class="pending-toolbar">
        <span class="pending-count">${data.total} pending transaction(s)</span>
        <div class="toolbar-actions">
          <button class="btn btn-sm btn-confirm" onclick="Imports.confirmSelected()">CONFIRM SELECTED</button>
          <button class="btn btn-sm btn-reject"  onclick="Imports.rejectSelected()">REJECT SELECTED</button>
          <button class="btn btn-sm"             onclick="Imports.selectAll()">SELECT ALL</button>
        </div>
      </div>
      <div class="table-wrapper">
        <table class="data-table pending-table">
          <thead><tr>
            <th></th><th>DATE</th><th>MERCHANT</th><th>CATEGORY</th><th>AMOUNT</th><th>ACTION</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      ${data.pages > 1 ? `<div class="pagination">
        <button class="btn btn-sm" onclick="Imports.pendingPage(${_pendingPage - 1})" ${_pendingPage <= 1 ? 'disabled' : ''}>PREV</button>
        <span>Page ${data.page} / ${data.pages}</span>
        <button class="btn btn-sm" onclick="Imports.pendingPage(${_pendingPage + 1})" ${_pendingPage >= data.pages ? 'disabled' : ''}>NEXT</button>
      </div>` : ''}
    `;
  }

  function _catBadge(cat) {
    return `<span class="cat-pill">${cat || 'Other'}</span>`;
  }

  function toggleSelect(id) {
    if (_selectedIds.has(id)) _selectedIds.delete(id);
    else _selectedIds.add(id);
  }

  function selectAll() {
    document.querySelectorAll('.row-check').forEach(cb => {
      cb.checked = true;
      _selectedIds.add(parseInt(cb.dataset.id));
    });
  }

  // ── Inline edit functions ─────────────────────────────────────────────────

  function openEditRow(id) {
    // Close any other open edit rows
    document.querySelectorAll('.edit-row').forEach(r => r.classList.add('hidden'));
    document.getElementById(`edit-row-${id}`)?.classList.remove('hidden');
    document.getElementById(`row-${id}`)?.classList.add('editing');
  }

  function closeEditRow(id) {
    document.getElementById(`edit-row-${id}`)?.classList.add('hidden');
    document.getElementById(`row-${id}`)?.classList.remove('editing');
  }

  async function saveEdit(id) {
    const body = _buildEditBody(id);
    try {
      const res = await API.patch(`/api/imports/pending/${id}`, body);
      if (res.success) {
        App.toast('Transaction updated.', 'success');
        closeEditRow(id);
        _loadPending();   // refresh table
      } else {
        App.toast(res.error || 'Save failed.', 'error');
      }
    } catch(e) { App.toast(e.message, 'error'); }
  }

  async function saveAndConfirm(id) {
    const body = _buildEditBody(id);
    try {
      const editRes = await API.patch(`/api/imports/pending/${id}`, body);
      if (!editRes.success) { App.toast(editRes.error, 'error'); return; }
      const confRes = await API.post('/api/imports/confirm', { ids: [id] });
      if (confRes.success) {
        App.toast('Saved and confirmed!', 'success');
        _loadPending();
      } else {
        App.toast(confRes.error || 'Confirm failed.', 'error');
      }
    } catch(e) { App.toast(e.message, 'error'); }
  }

  function _buildEditBody(id) {
    return {
      merchant:          document.getElementById(`ie-merchant-${id}`)?.value?.trim(),
      category:          document.getElementById(`ie-cat-${id}`)?.value,
      amount:            parseFloat(document.getElementById(`ie-amt-${id}`)?.value || 0),
      transaction_date:  document.getElementById(`ie-date-${id}`)?.value,
      direction:         document.getElementById(`ie-dir-${id}`)?.value,
      payment_method:    document.getElementById(`ie-pay-${id}`)?.value,
    };
  }

  async function confirmOne(id) { await _bulkAction([id], 'confirm'); }
  async function rejectOne(id)  { await _bulkAction([id], 'reject'); }
  async function confirmSelected() { await _bulkAction([..._selectedIds], 'confirm'); }
  async function rejectSelected()  { await _bulkAction([..._selectedIds], 'reject'); }

  async function _bulkAction(ids, action) {
    if (!ids.length) { App.toast('No transactions selected.', 'warn'); return; }
    try {
      const res = await API.post(`/api/imports/${action}`, { ids });
      if (res.success) {
        const count = res.data.confirmed ?? res.data.rejected ?? ids.length;
        App.toast(`${count} transaction(s) ${action}ed.`, 'success');
        _loadPending();
      } else {
        App.toast(res.error || 'Action failed.', 'error');
      }
    } catch(e) { App.toast(e.message, 'error'); }
  }

  function pendingPage(p) { _pendingPage = p; _loadPending(); }

  // ── History panel ─────────────────────────────────────────────────────────

  async function _loadHistory() {
    const panel = document.getElementById('import-panel-history');
    panel.innerHTML = `<p class="loading-text">LOADING IMPORT HISTORY...</p>`;
    try {
      const res = await API.get(`/api/imports/history?page=${_historyPage}`);
      if (!res.success) { panel.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      panel.innerHTML = _buildHistoryTable(res.data);
    } catch(e) {
      panel.innerHTML = `<p class="form-error">Failed to load: ${e.message}</p>`;
    }
  }

  function _buildHistoryTable(data) {
    if (!data.items || !data.items.length) {
      return `<div class="empty-state"><p class="empty-title">NO_IMPORT_HISTORY</p><p class="empty-sub">No statements uploaded yet.</p></div>`;
    }
    const rows = data.items.map(h => `
      <tr>
        <td class="mono">${h.created_at ? h.created_at.substring(0,16).replace('T',' ') : '-'}</td>
        <td>${h.filename}</td>
        <td><span class="type-badge">${h.file_type.toUpperCase()}</span>${h.bank_detected ? ` · ${h.bank_detected.toUpperCase()}` : ''}</td>
        <td class="mono">${h.imported_count}</td>
        <td class="amount-credit">${h.success_count}</td>
        <td class="amount-debit">${h.failed_count}</td>
        <td class="text-warn">${h.duplicate_count}</td>
      </tr>
    `).join('');

    return `
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>DATE</th><th>FILE</th><th>TYPE/BANK</th><th>TOTAL</th><th class="amount-credit">OK</th><th class="amount-debit">FAILED</th><th>DUPS</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  // ── SMS Status panel ──────────────────────────────────────────────────────

  async function _loadSmsStatus() {
    const panel = document.getElementById('import-panel-sms');
    panel.innerHTML = `<p class="loading-text">LOADING SMS STATUS...</p>`;
    try {
      const res = await API.get('/api/sms/status');
      if (!res.success) { panel.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      const d = res.data;
      const deviceRows = d.devices.length ? d.devices.map(dv => `
        <div class="device-card">
          <div class="device-name">[${dv.device_type.toUpperCase()}] ${dv.device_name || dv.device_id}</div>
          <div class="device-meta">Last sync: ${dv.last_sync_at ? dv.last_sync_at.substring(0,16).replace('T',' ') : 'Never'} &nbsp;|&nbsp; Total synced: ${dv.total_synced}</div>
          <span class="device-status ${dv.status === 'active' ? 'status-active' : 'status-revoked'}">${dv.status.toUpperCase()}</span>
        </div>
      `).join('') : `<p class="empty-sub">No devices registered yet.</p><p class="empty-sub">Connect the FinanceOS Android app to enable SMS sync.</p>`;

      panel.innerHTML = `
        <div class="sms-overview">
          <div class="stat-card-row">
            <div class="stat-card"><div class="stat-val">${d.total_sms_imported}</div><div class="stat-lbl">SMS IMPORTED</div></div>
            <div class="stat-card"><div class="stat-val">${d.devices.length}</div><div class="stat-lbl">DEVICES LINKED</div></div>
          </div>
          <h3 class="section-subtitle">REGISTERED DEVICES</h3>
          <div class="device-list">${deviceRows}</div>
        </div>
        <div class="sms-raw-test">
          <h3 class="section-subtitle">TEST SMS PARSER</h3>
          <p class="empty-sub">Paste an SMS from your bank to test parsing:</p>
          <textarea id="sms-test-input" class="sms-textarea" rows="4" placeholder="Paste bank SMS here..."></textarea>
          <button class="btn btn-primary" onclick="Imports.testSms()">PARSE SMS</button>
          <div id="sms-parse-result" class="sms-result hidden"></div>
        </div>
      `;
    } catch(e) {
      panel.innerHTML = `<p class="form-error">Failed: ${e.message}</p>`;
    }
  }

  async function testSms() {
    const txt = document.getElementById('sms-test-input').value.trim();
    const resEl = document.getElementById('sms-parse-result');
    if (!txt) return;
    resEl.classList.remove('hidden');
    resEl.innerHTML = 'PARSING...';
    try {
      const res = await API.post('/api/sms/raw', { sms_text: txt });
      if (res.success) {
        const d = res.data;
        resEl.innerHTML = `
          <div class="parse-ok">
            <div>MERCHANT: <strong>${d.normalized_merchant || d.merchant}</strong></div>
            <div>AMOUNT:   <strong class="${d.transaction_direction === 'debit' ? 'amount-debit' : 'amount-credit'}">${d.transaction_direction === 'debit' ? '-' : '+'}${App.fmt(d.amount)}</strong></div>
            <div>CATEGORY: <strong>${d.category}</strong></div>
            <div>DATE:     <strong>${d.transaction_date}</strong></div>
            <div>STATUS:   <strong>${d.status}</strong></div>
          </div>
        `;
        App.toast('SMS parsed and queued!', 'success');
      } else {
        resEl.innerHTML = `<p class="form-error">${res.error}</p>`;
      }
    } catch(e) { resEl.innerHTML = `<p class="form-error">${e.message}</p>`; }
  }


  // ── AI Analyser panel ─────────────────────────────────────────────────────

  async function _loadAiPanel() {
    const panel = document.getElementById('import-panel-ai');
    panel.innerHTML = `<p class="loading-text">CHECKING AI STATUS...</p>`;
    try {
      const status = await API.get('/api/ai/status');
      const d = status.data || {};
      panel.innerHTML = `
        <div class="ai-panel">
          <div class="ai-status-bar ${d.configured ? 'ai-ready' : 'ai-not-ready'}">
            <span class="ai-status-dot"></span>
            <span class="ai-status-text">${d.configured ? 'AI READY — ' + d.model : 'AI NOT CONFIGURED'}</span>
            ${!d.configured ? `<a href="https://aistudio.google.com/app/apikey" target="_blank" class="ai-key-link">GET FREE KEY</a>` : ''}
          </div>
          ${!d.configured ? `
            <div class="ai-setup-card">
              <h3 class="section-subtitle">SETUP — 2 MINUTES</h3>
              <ol class="ai-setup-steps">
                <li>Go to <a href="https://aistudio.google.com/app/apikey" target="_blank" class="ai-key-link">aistudio.google.com/app/apikey</a></li>
                <li>Click <strong>Create API Key</strong> (it is FREE)</li>
                <li>Copy the key and paste it in your <code>.env</code> file:</li>
              </ol>
              <code class="env-snippet">GEMINI_API_KEY=AIza...your-key-here</code>
              <p class="empty-sub" style="margin-top:.5rem">Then restart the server and come back here.</p>
            </div>
          ` : `
            <div class="ai-actions-card">
              <h3 class="section-subtitle">ANALYSE PENDING TRANSACTIONS</h3>
              <p class="empty-sub">Select which transactions to analyse, or analyse all pending at once.</p>
              <div class="ai-btn-row">
                <button class="btn btn-primary" onclick="Imports.runAiAnalysis()">ANALYSE ALL PENDING</button>
              </div>
            </div>
            <div id="ai-result-panel" class="ai-result-panel hidden"></div>
          `}
        </div>
      `;
    } catch(e) {
      panel.innerHTML = `<p class="form-error">Failed to check AI status: ${e.message}</p>`;
    }
  }

  async function runAiAnalysis() {
    const resultPanel = document.getElementById('ai-result-panel');
    if (!resultPanel) return;

    // First fetch pending IDs
    resultPanel.classList.remove('hidden');
    resultPanel.innerHTML = `<div class="ai-thinking">
      <div class="ai-spinner"></div>
      <p>Fetching pending transactions...</p>
    </div>`;

    try {
      const pendingRes = await API.get('/api/imports/pending?per_page=100');
      if (!pendingRes.success || !pendingRes.data.items?.length) {
        resultPanel.innerHTML = `<div class="empty-state"><p class="empty-title">NO_PENDING_TRANSACTIONS</p><p class="empty-sub">Upload a bank statement first to analyse transactions.</p></div>`;
        return;
      }
      const ids = pendingRes.data.items.map(t => t.id);

      resultPanel.innerHTML = `<div class="ai-thinking">
        <div class="ai-spinner"></div>
        <p>Analysing ${ids.length} transactions with Gemini AI...</p>
        <p class="ai-sub">This may take 5–15 seconds.</p>
      </div>`;

      const res = await API.post('/api/ai/analyse-batch', { ids });
      if (!res.success) {
        resultPanel.innerHTML = `<p class="form-error">AI Error: ${res.error}</p>`;
        return;
      }
      _renderAiResult(resultPanel, res.data, ids, pendingRes.data.items);
    } catch(e) {
      resultPanel.innerHTML = `<p class="form-error">Analysis failed: ${e.message}</p>`;
    }
  }

  function _renderAiResult(el, data, ids, txList) {
    const corrections = data.corrections || {};
    const anomalies  = data.anomalies || [];
    const insights   = data.insights || [];

    const correctionRows = Object.keys(corrections).map(id => {
      const c  = corrections[id];
      const tx = txList.find(t => t.id == id);
      return `<tr>
        <td class="mono">${tx ? (tx.normalized_merchant || tx.merchant) : id}</td>
        <td><span class="cat-pill">${tx ? tx.category : '?'}</span></td>
        <td><span class="cat-pill ai-cat">${c.category}</span></td>
        <td class="ai-reason">${c.reason}</td>
      </tr>`;
    }).join('');

    const anomalyCards = anomalies.map(a => `
      <div class="anomaly-card">
        <div class="anomaly-merchant">${a.merchant}</div>
        <div class="anomaly-amount amount-debit">${App.fmt(a.amount)}</div>
        <div class="anomaly-reason">${a.reason}</div>
      </div>
    `).join('');

    const insightItems = insights.map(i => `<li class="insight-item">&gt; ${i}</li>`).join('');

    el.innerHTML = `
      <!-- Summary -->
      <div class="ai-summary-card">
        <div class="ai-label">AI SUMMARY</div>
        <p class="ai-summary-text">${data.summary}</p>
        <div class="ai-totals">
          <span class="amount-debit">SPENT: ${App.fmt(data.total_debit)}</span>
          <span class="amount-credit">EARNED: ${App.fmt(data.total_credit)}</span>
        </div>
      </div>

      <!-- Insights -->
      ${insights.length ? `
      <div class="ai-section">
        <h3 class="section-subtitle">INSIGHTS</h3>
        <ul class="insight-list">${insightItems}</ul>
      </div>` : ''}

      <!-- Category corrections -->
      ${correctionRows ? `
      <div class="ai-section">
        <h3 class="section-subtitle">CATEGORY CORRECTIONS (${Object.keys(corrections).length})</h3>
        <div class="table-wrapper">
          <table class="data-table">
            <thead><tr><th>MERCHANT</th><th>WAS</th><th>AI SUGGESTS</th><th>REASON</th></tr></thead>
            <tbody>${correctionRows}</tbody>
          </table>
        </div>
        <button class="btn btn-primary" style="margin-top:.65rem" onclick="Imports.applyCorrections(${JSON.stringify(corrections).replace(/"/g,'&quot;')})">APPLY ALL CORRECTIONS</button>
      </div>` : '<div class="ai-section"><p class="empty-sub">No category corrections needed.</p></div>'}

      <!-- Anomalies -->
      ${anomalyCards ? `
      <div class="ai-section">
        <h3 class="section-subtitle">ANOMALIES DETECTED (${anomalies.length})</h3>
        <div class="anomaly-grid">${anomalyCards}</div>
      </div>` : ''}

      <!-- Top merchants -->
      ${data.top_merchants?.length ? `
      <div class="ai-section">
        <h3 class="section-subtitle">TOP MERCHANTS</h3>
        <div class="merchant-chips">
          ${data.top_merchants.map(m => `<span class="cat-pill">${m}</span>`).join('')}
        </div>
      </div>` : ''}
    `;
  }

  async function applyCorrections(corrections) {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'APPLYING...';
    try {
      const res = await API.post('/api/ai/apply-corrections', { corrections });
      if (res.success) {
        App.toast(`Applied ${res.data.applied} AI correction(s).`, 'success');
        btn.textContent = `APPLIED (${res.data.applied})`;
        // Refresh pending table if visible
        const pendingPanel = document.getElementById('import-panel-pending');
        if (pendingPanel && !pendingPanel.classList.contains('hidden')) _loadPending();
      } else {
        App.toast(res.error, 'error');
        btn.disabled = false;
        btn.textContent = 'APPLY ALL CORRECTIONS';
      }
    } catch(e) {
      App.toast(e.message, 'error');
      btn.disabled = false;
    }
  }

  return { render, switchTab, handleFileSelect, toggleSelect, selectAll,
           confirmOne, rejectOne, confirmSelected, rejectSelected,
           pendingPage, testSms, runAiAnalysis, applyCorrections,
           openEditRow, closeEditRow, saveEdit, saveAndConfirm };
})();
