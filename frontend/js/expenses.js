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
      <div class="page-top" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
        <h2>Transactions</h2>
        <button class="btn btn-ghost btn-sm ai-trigger-btn" onclick="ExpensesModule.toggleInsights()" id="ai-insights-btn">
          <span class="ai-dot"></span> AI INSIGHTS
        </button>
      </div>

      <!-- AI Insights Panel (hidden by default) -->
      <div id="exp-ai-panel" class="exp-ai-panel hidden">
        <div class="exp-ai-header">
          <span class="ds-section-label">AI EXPENSE ANALYSIS</span>
          <div class="exp-ai-period">
            <label>PERIOD</label>
            <select id="ai-period" onchange="ExpensesModule.loadInsights()">
              <option value="30">Last 30 days</option>
              <option value="90" selected>Last 3 months</option>
              <option value="180">Last 6 months</option>
            </select>
          </div>
        </div>
        <div id="exp-ai-content">
          <div class="ai-thinking"><div class="ai-spinner"></div><p>Analysing your expenses...</p></div>
        </div>
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

  let _insightsLoaded = false;
  let _panelOpen = false;

  function toggleInsights() {
    const panel = document.getElementById('exp-ai-panel');
    const btn   = document.getElementById('ai-insights-btn');
    _panelOpen = !_panelOpen;
    panel.classList.toggle('hidden', !_panelOpen);
    btn.classList.toggle('active', _panelOpen);
    if (_panelOpen && !_insightsLoaded) loadInsights();
  }

  async function loadInsights() {
    const el     = document.getElementById('exp-ai-content');
    const period = document.getElementById('ai-period')?.value || 90;
    if (!el) return;
    _insightsLoaded = false;
    el.innerHTML = '<div class="ai-thinking"><div class="ai-spinner"></div><p>Analysing your expenses with AI...</p></div>';

    try {
      const res = await API.get(`/api/ai/expense-insights?period=${period}`);
      if (!res || !res.success) {
        el.innerHTML = `<p class="form-error">AI Error: ${res?.error || 'Failed'}</p>`;
        return;
      }
      const d = res.data;
      if (!d.has_data) {
        el.innerHTML = `<div class="ai-tip-bar">${d.message}</div>`;
        return;
      }
      _insightsLoaded = true;

      const healthColor = { EXCELLENT: 'var(--green)', GOOD: 'var(--accent)', FAIR: '#f59e0b', POOR: 'var(--red)' }[d.overall_health] || 'var(--text2)';
      const trendIcon   = { IMPROVING: '📈', STABLE: '➡️', WORSENING: '📉' }[d.month_trend] || '➡️';

      const anomalyCards = (d.anomalies || []).map(a => `
        <div class="ai-anomaly ${a.severity?.toLowerCase()}">
          <span class="anom-sev">${a.severity}</span>
          <span>${a.description}</span>
          ${a.amount ? `<span class="mono">Rs.${Number(a.amount).toLocaleString('en-IN')}</span>` : ''}
        </div>`).join('');

      const oppCards = (d.opportunities || []).map(o => `
        <div class="opp-card">
          <div class="opp-cat">${o.category}</div>
          <div class="opp-action">${o.action}</div>
          <div class="opp-save">Save ~Rs.${Number(o.potential_saving || 0).toLocaleString('en-IN')}/mo</div>
        </div>`).join('');

      const patternItems = (d.spending_patterns || []).map(p => `<li class="insight-item">> ${p}</li>`).join('');
      const habitItems   = (d.positive_habits || []).map(p => `<li class="insight-item">✓ ${p}</li>`).join('');

      el.innerHTML = `
        <!-- Summary row -->
        <div class="ai-summary-row">
          <div class="ai-health-mini" style="border-color:${healthColor}">
            <div class="ai-score" style="color:${healthColor}">${d.health_score ?? '—'}</div>
            <div class="ai-label">${d.overall_health}</div>
          </div>
          <div class="ai-summary-stats">
            <div class="ai-stat-row"><span>Total Income</span><span class="mono amount-credit">+${App.fmt(d.total_income)}</span></div>
            <div class="ai-stat-row"><span>Total Spent</span><span class="mono amount-debit">-${App.fmt(d.total_spent)}</span></div>
            <div class="ai-stat-row"><span>Net Savings</span><span class="mono ${d.net_savings >= 0 ? 'amount-credit' : 'amount-debit'}">${d.net_savings >= 0 ? '+' : ''}${App.fmt(d.net_savings)}</span></div>
            <div class="ai-stat-row"><span>Savings Rate</span><span class="mono">${d.savings_rate}%</span></div>
          </div>
        </div>

        <!-- AI Summary -->
        <div class="ai-insight-box">
          <div class="ds-section-label">SUMMARY</div>
          <p style="font-size:.85rem;color:var(--text2);line-height:1.5">${d.summary}</p>
          <div class="ai-top-insight">💡 ${d.top_insight}</div>
        </div>

        <!-- Trend + Savings -->
        <div class="ai-row-2col">
          <div class="ai-insight-box">
            <div class="ds-section-label">MONTHLY TREND ${trendIcon}</div>
            <div style="font-size:.9rem;font-weight:700;color:${d.month_trend === 'IMPROVING' ? 'var(--green)' : d.month_trend === 'WORSENING' ? 'var(--red)' : 'var(--text2)'}">${d.month_trend}</div>
            <div style="font-size:.78rem;color:var(--text3);margin-top:.25rem">${d.trend_reason}</div>
          </div>
          <div class="ai-insight-box">
            <div class="ds-section-label">SAVINGS HEALTH</div>
            <p style="font-size:.78rem;color:var(--text2)">${d.savings_assessment}</p>
          </div>
        </div>

        <!-- Spending patterns -->
        ${patternItems ? `
        <div class="ai-insight-box">
          <div class="ds-section-label">SPENDING PATTERNS</div>
          <ul class="insight-list">${patternItems}</ul>
        </div>` : ''}

        <!-- Anomalies -->
        ${anomalyCards ? `
        <div class="ai-insight-box">
          <div class="ds-section-label">ANOMALIES DETECTED</div>
          <div>${anomalyCards}</div>
        </div>` : ''}

        <!-- Savings opportunities -->
        ${oppCards ? `
        <div class="ai-insight-box">
          <div class="ds-section-label">SAVINGS OPPORTUNITIES</div>
          <div class="opp-grid">${oppCards}</div>
        </div>` : ''}

        <!-- Positive habits -->
        ${habitItems ? `
        <div class="ai-insight-box">
          <div class="ds-section-label">YOUR GOOD HABITS</div>
          <ul class="insight-list">${habitItems}</ul>
        </div>` : ''}

        <!-- Smart budget CTA -->
        <div class="ai-insight-box ai-cta-box">
          <div class="ds-section-label">READY FOR A SMARTER BUDGET?</div>
          <p style="font-size:.78rem;color:var(--text3);margin-bottom:.5rem">
            Get AI-generated monthly budget limits based on your exact income and spending history.
          </p>
          <button class="btn btn-primary" onclick="ExpensesModule.openSmartBudget()">
            ✦ GENERATE SMART BUDGET
          </button>
        </div>`;
    } catch(e) {
      el.innerHTML = `<p class="form-error">Error: ${e.message}</p>`;
    }
  }

  async function openSmartBudget() {
    App.openModal('AI SMART BUDGET', '<div class="ai-thinking"><div class="ai-spinner"></div><p>Generating your personalised budget...</p></div>');
    try {
      const res = await API.get('/api/ai/smart-budget');
      if (!res || !res.success) { App.toast(res?.error || 'Failed', 'error'); App.closeModal(); return; }
      const d = res.data;
      if (!d.has_data) { App.toast(d.message, 'error'); App.closeModal(); return; }

      const budgets = d.recommended_budgets || {};
      const rows = Object.entries(budgets).map(([cat, b]) => {
        const dir   = b.change >= 0 ? '+' : '';
        const color = b.change < 0 ? 'var(--green)' : b.change > 0 ? 'var(--red)' : 'var(--text3)';
        return `
          <tr>
            <td>${cat}</td>
            <td class="mono">${App.fmt(b.current_avg || 0)}</td>
            <td class="mono" style="font-weight:700">${App.fmt(b.limit)}</td>
            <td class="mono" style="color:${color}">${dir}${App.fmt(Math.abs(b.change || 0))}</td>
            <td style="font-size:.7rem;color:var(--text3)">${b.reason}</td>
            <td><button class="btn-xs" onclick="ExpensesModule.applySmartBudget('${cat}', ${b.limit})">APPLY</button></td>
          </tr>`;
      }).join('');

      const alloc = d.income_allocation || {};

      document.getElementById('modal-body').innerHTML = `
        <div class="ds-stats-grid" style="margin-bottom:.75rem">
          <div class="ds-stat"><div class="ds-stat-val">${App.fmt(d.monthly_income)}</div><div class="ds-stat-lbl">INCOME</div></div>
          <div class="ds-stat"><div class="ds-stat-val" style="color:var(--red)">${App.fmt(d.total_budget)}</div><div class="ds-stat-lbl">BUDGET</div></div>
          <div class="ds-stat"><div class="ds-stat-val" style="color:var(--green)">${App.fmt(d.savings_target)}</div><div class="ds-stat-lbl">SAVINGS TARGET</div></div>
        </div>

        <div class="ai-tip-bar" style="margin-bottom:.75rem">
          💡 ${d.strategy}
        </div>

        <div class="allocation-bar-wrap">
          <div class="alloc-seg" style="width:${alloc.needs_pct||50}%;background:var(--red)" title="Needs ${alloc.needs_pct}%"></div>
          <div class="alloc-seg" style="width:${alloc.wants_pct||30}%;background:var(--accent)" title="Wants ${alloc.wants_pct}%"></div>
          <div class="alloc-seg" style="width:${alloc.savings_pct||20}%;background:var(--green)" title="Savings ${alloc.savings_pct}%"></div>
        </div>
        <div class="alloc-legend">
          <span><span class="alloc-dot" style="background:var(--red)"></span>Needs ${alloc.needs_pct||50}%</span>
          <span><span class="alloc-dot" style="background:var(--accent)"></span>Wants ${alloc.wants_pct||30}%</span>
          <span><span class="alloc-dot" style="background:var(--green)"></span>Savings ${alloc.savings_pct||20}%</span>
        </div>

        <div class="table-wrapper" style="margin:.75rem 0">
          <table class="data-table">
            <thead><tr><th>CATEGORY</th><th>CURRENT</th><th>SUGGESTED</th><th>CHANGE</th><th>REASON</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        <button class="btn btn-primary btn-full" onclick="ExpensesModule.applyAllSmartBudgets(${JSON.stringify(budgets).replace(/"/g,'&quot;')})">
          APPLY ALL BUDGETS
        </button>`;
    } catch(e) {
      App.toast(e.message, 'error'); App.closeModal();
    }
  }

  async function applySmartBudget(category, limit) {
    const now   = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    const res   = await API.post('/api/budgets/', { category, monthly_limit: limit, month });
    if (res && res.success) {
      App.toast(`Budget set: ${category} = ${App.fmt(limit)}/month`, 'success');
    } else {
      App.toast(res?.error || 'Failed', 'error');
    }
  }

  async function applyAllSmartBudgets(budgets) {
    const now   = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    let ok = 0, fail = 0;
    for (const [cat, b] of Object.entries(budgets)) {
      const res = await API.post('/api/budgets/', { category: cat, monthly_limit: b.limit, month });
      res && res.success ? ok++ : fail++;
    }
    App.closeModal();
    App.toast(`Applied ${ok} budgets${fail ? `, ${fail} failed` : ''}.`, ok > 0 ? 'success' : 'error');
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
        <label>Category <span id="ai-cat-badge" class="ai-cat-suggestion" style="display:none"></span></label>
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

  function openAdd() {
    App.openModal('Add Transaction', formHtml());
    // Attach AI category suggestion after modal renders
    setTimeout(() => {
      if (typeof AI !== 'undefined') {
        AI.attachCategorySuggestion('ef-desc', 'ef-cat', 'ef-amount');
      }
    }, 100);
  }

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

  return { init, load, setFilter, openAdd, openEdit, save, del,
           toggleInsights, loadInsights, openSmartBudget, applySmartBudget, applyAllSmartBudgets };
})();
