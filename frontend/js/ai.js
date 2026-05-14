/**
 * ai.js — Global AI assistant for FinanceOS
 * Provides AI widgets for Dashboard, Expenses, Budgets, Goals.
 * All UI is inline — no separate page needed.
 */

const AI = (() => {
  let _aiReady = null;  // cached status

  // ── API status check ─────────────────────────────────────────────────────

  async function isReady() {
    if (_aiReady !== null) return _aiReady;
    try {
      const res = await API.get('/api/ai/status');
      _aiReady = res.success && res.data.configured;
    } catch { _aiReady = false; }
    return _aiReady;
  }

  // ── Dashboard: financial health widget ──────────────────────────────────

  async function renderDashboardWidget(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const ready = await isReady();
    if (!ready) {
      el.innerHTML = `
        <div class="ai-widget-disabled">
          <span class="ai-dot-off"></span>
          <span>AI Insights unavailable — <a href="https://aistudio.google.com/app/apikey" target="_blank" class="ai-key-link">add GEMINI_API_KEY</a></span>
        </div>`;
      return;
    }

    el.innerHTML = `
      <div class="ai-widget-header">
        <span class="ai-dot-on"></span>
        <span class="ai-widget-title">AI FINANCIAL HEALTH</span>
        <button class="btn-xs" onclick="AI.refreshDashboard('${containerId}')">REFRESH</button>
      </div>
      <div class="ai-thinking" style="padding:1rem 0">
        <div class="ai-spinner"></div>
        <p>Analysing your finances...</p>
      </div>`;

    try {
      const res = await API.get('/api/ai/dashboard-insights');
      if (!res.success) { el.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      _renderHealthWidget(el, res.data);
    } catch(e) {
      el.innerHTML = `<p class="form-error">AI Error: ${e.message}</p>`;
    }
  }

  function refreshDashboard(containerId) {
    renderDashboardWidget(containerId);
  }

  function _renderHealthWidget(el, d) {
    if (!d.health_score && d.score_label === 'INSUFFICIENT_DATA') {
      el.innerHTML = `
        <div class="ai-widget-header">
          <span class="ai-dot-on"></span>
          <span class="ai-widget-title">AI FINANCIAL HEALTH</span>
        </div>
        <p class="empty-sub" style="padding:.5rem 0">Add transactions to get AI insights.</p>`;
      return;
    }

    const score = d.health_score || 0;
    const label = d.score_label || 'UNKNOWN';
    const scoreClass = score >= 80 ? 'score-great' : score >= 60 ? 'score-good' : score >= 40 ? 'score-fair' : 'score-poor';
    const insightItems = (d.insights || []).map(i => `<li class="insight-item">> ${i}</li>`).join('');

    el.innerHTML = `
      <div class="ai-widget-header">
        <span class="ai-dot-on"></span>
        <span class="ai-widget-title">AI FINANCIAL HEALTH</span>
        <button class="btn-xs" onclick="AI.refreshDashboard('${el.id}')">REFRESH</button>
      </div>
      <div class="ai-health-row">
        <div class="ai-score-ring ${scoreClass}">
          <span class="ai-score-num">${score}</span>
          <span class="ai-score-lbl">${label}</span>
        </div>
        <div class="ai-health-right">
          <p class="ai-summary-text" style="margin-bottom:.5rem">${d.summary || ''}</p>
          <div class="ai-totals">
            <span class="amount-credit">IN: ${App.fmt(d.total_credit)}</span>
            <span class="amount-debit">OUT: ${App.fmt(d.total_debit)}</span>
          </div>
        </div>
      </div>
      ${insightItems ? `<ul class="insight-list" style="margin-top:.65rem">${insightItems}</ul>` : ''}
      ${d.tip ? `<div class="ai-tip-bar">> TIP: ${d.tip}</div>` : ''}`;
  }

  // ── Expenses: inline category suggestion ────────────────────────────────

  let _catDebounce = null;

  function attachCategorySuggestion(descInputId, catSelectId, amtInputId) {
    const descInput = document.getElementById(descInputId);
    if (!descInput) return;

    descInput.addEventListener('input', () => {
      clearTimeout(_catDebounce);
      _catDebounce = setTimeout(async () => {
        const merchant = descInput.value.trim();
        if (merchant.length < 3) return;

        const ready = await isReady();
        if (!ready) return;

        const amount    = parseFloat(document.getElementById(amtInputId)?.value || 0);
        const direction = document.querySelector('input[name=entry_type]:checked')?.value === 'income'
                          ? 'credit' : 'debit';
        try {
          const res = await API.post('/api/ai/categorise', { merchant, amount, direction });
          if (res.success && res.data.category) {
            const catSelect = document.getElementById(catSelectId);
            if (catSelect) {
              // Try to set the option
              const opt = Array.from(catSelect.options).find(o => o.value === res.data.category);
              if (opt) {
                catSelect.value = res.data.category;
                _showCatSuggestion(catSelectId, res.data.category, res.data.confidence);
              }
            }
          }
        } catch { /* silent fail */ }
      }, 700);  // 700ms debounce
    });
  }

  function _showCatSuggestion(catSelectId, category, confidence) {
    const existingBadge = document.getElementById('ai-cat-badge');
    if (existingBadge) existingBadge.remove();

    const catSelect = document.getElementById(catSelectId);
    if (!catSelect) return;

    const badge = document.createElement('div');
    badge.id = 'ai-cat-badge';
    badge.className = 'ai-cat-suggestion';
    badge.innerHTML = `<span class="ai-dot-on" style="width:5px;height:5px"></span> AI: <strong>${category}</strong> <span style="color:var(--text3)">(${Math.round((confidence||0.8)*100)}% conf.)</span>`;
    catSelect.parentNode.insertBefore(badge, catSelect.nextSibling);

    // Fade out after 4s
    setTimeout(() => badge.style.opacity = '0', 3500);
    setTimeout(() => badge.remove(), 4200);
  }

  // ── Budgets: AI suggest button ───────────────────────────────────────────

  async function suggestBudgets(resultContainerId) {
    const el = document.getElementById(resultContainerId);
    if (!el) return;

    el.innerHTML = `<div class="ai-thinking"><div class="ai-spinner"></div><p>Analysing 3 months of spending...</p></div>`;
    el.classList.remove('hidden');

    try {
      const res = await API.get('/api/ai/suggest-budgets');
      if (!res.success) { el.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      _renderBudgetSuggestions(el, res.data);
    } catch(e) {
      el.innerHTML = `<p class="form-error">AI Error: ${e.message}</p>`;
    }
  }

  function _renderBudgetSuggestions(el, d) {
    if (!d.budgets || !Object.keys(d.budgets).length) {
      el.innerHTML = `<p class="empty-sub">${d.message || 'No data available.'}</p>`;
      return;
    }

    const rows = Object.entries(d.budgets).map(([cat, limit]) => {
      const current = d.current_monthly_avg?.[cat] || 0;
      const diff    = current - limit;
      return `<tr>
        <td class="mono">${cat}</td>
        <td class="mono">${App.fmt(current)}</td>
        <td class="amount-credit mono">${App.fmt(limit)}</td>
        <td class="${diff > 0 ? 'amount-credit' : 'amount-debit'} mono">${diff > 0 ? '-' : '+'}${App.fmt(Math.abs(diff))}</td>
        <td><button class="btn-xs btn-confirm" onclick="AI.applyBudget('${cat}', ${limit})">APPLY</button></td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      <div class="ai-summary-card" style="margin-bottom:.75rem">
        <div class="ai-label">AI BUDGET RECOMMENDATIONS</div>
        <p class="ai-summary-text">${d.rationale || ''}</p>
        ${d.savings_target ? `<div class="ai-totals"><span class="amount-credit">Savings target: ${App.fmt(d.savings_target)}/month</span></div>` : ''}
      </div>
      <div class="table-wrapper" style="margin-bottom:.65rem">
        <table class="data-table">
          <thead><tr><th>CATEGORY</th><th>CURRENT AVG</th><th>AI SUGGESTS</th><th>SAVING</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <button class="btn btn-primary" onclick="AI.applyAllBudgets(${JSON.stringify(d.budgets).replace(/"/g,'&quot;')})">APPLY ALL SUGGESTIONS</button>`;
  }

  async function applyBudget(category, limit) {
    // Delegate to Budgets module if it's open
    if (typeof Budgets !== 'undefined' && Budgets.createFromAI) {
      await Budgets.createFromAI(category, limit);
    } else {
      App.toast(`Set budget for ${category}: ${App.fmt(limit)}/month`, 'success');
    }
  }

  async function applyAllBudgets(budgets) {
    if (typeof Budgets !== 'undefined' && Budgets.createFromAI) {
      for (const [cat, limit] of Object.entries(budgets)) {
        await Budgets.createFromAI(cat, limit);
      }
      App.toast(`Applied ${Object.keys(budgets).length} AI budget suggestions!`, 'success');
    }
  }

  // ── Goals: AI advice card ────────────────────────────────────────────────

  async function showGoalAdvice(goalId, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    el.innerHTML = `<div class="ai-thinking"><div class="ai-spinner"></div><p>Getting AI advice for this goal...</p></div>`;
    el.classList.remove('hidden');

    try {
      const res = await API.post('/api/ai/goal-advice', { goal_id: goalId });
      if (!res.success) { el.innerHTML = `<p class="form-error">${res.error}</p>`; return; }
      _renderGoalAdvice(el, res.data);
    } catch(e) {
      el.innerHTML = `<p class="form-error">AI Error: ${e.message}</p>`;
    }
  }

  function _renderGoalAdvice(el, d) {
    const feasColors = {
      ON_TRACK: 'amount-credit', NEEDS_EFFORT: 'text-warn',
      CHALLENGING: 'amount-debit', DEADLINE_MISSED: 'amount-debit'
    };
    const fClass = feasColors[d.feasibility] || '';
    const adviceItems = (d.advice || []).map(a => `<li class="insight-item">> ${a}</li>`).join('');

    el.innerHTML = `
      <div class="ai-summary-card">
        <div class="ai-label">AI GOAL ADVICE — ${d.goal_name || ''}</div>
        <div style="display:flex;align-items:center;gap:1rem;margin:.5rem 0">
          <span class="${fClass}" style="font-weight:700;font-family:'IBM Plex Mono',monospace;font-size:.85rem">${d.feasibility?.replace(/_/g,' ')}</span>
          ${d.monthly_required ? `<span class="mono" style="font-size:.78rem;color:var(--text2)">Need: ${App.fmt(d.monthly_required)}/month</span>` : ''}
        </div>
        ${adviceItems ? `<ul class="insight-list">${adviceItems}</ul>` : ''}
        ${d.motivational_message ? `<div class="ai-tip-bar" style="margin-top:.5rem">> ${d.motivational_message}</div>` : ''}
      </div>`;
  }

  return {
    isReady,
    renderDashboardWidget,
    refreshDashboard,
    attachCategorySuggestion,
    suggestBudgets,
    applyBudget,
    applyAllBudgets,
    showGoalAdvice,
  };
})();
