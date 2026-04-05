/* dashboard.js — v3: no emojis, green/red amounts, retro style */
const DashboardModule = (() => {
  let charts = {};

  async function init() {
    const el = document.getElementById('page-dashboard');
    el.innerHTML = `
      <div class="greeting" id="dash-greeting"></div>
      <div class="summary-grid" id="dash-summary">
        ${['income','expense','savings'].map(t=>`<div class="summary-card ${t} skeleton" style="height:100px"></div>`).join('')}
      </div>
      <div id="dash-alerts"></div>
      <div class="chart-grid">
        <div class="card chart-card"><h3>Savings Trend</h3><div class="chart-wrap"><canvas id="chart-savings"></canvas></div></div>
        <div class="card chart-card"><h3>This Month</h3><div class="chart-wrap"><canvas id="chart-category"></canvas></div></div>
      </div>
      <div class="section-title">Upcoming Payments</div>
      <div id="dash-upcoming" class="upcoming-list"></div>`;

    const user = App.getUser();
    const hour = new Date().getHours();
    const greet = hour < 12 ? 'GOOD MORNING' : hour < 17 ? 'GOOD AFTERNOON' : 'GOOD EVENING';
    document.getElementById('dash-greeting').innerHTML = `
      <div class="greeting-hello">${greet}, ${user ? user.full_name.split(' ')[0].toUpperCase() : ''}</div>
      <div class="greeting-date">${new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long'})}</div>`;

    Object.values(charts).forEach(c => c.destroy && c.destroy());
    charts = {};

    const res = await API.get('/api/dashboard/summary');
    if (!res || !res.success) { App.toast('Failed to load dashboard', 'error'); return; }
    const d = res.data;

    renderSummary(d.summary);
    renderAlerts(d.alerts);
    renderCharts(d.savings_history, d.category_breakdown);
    renderUpcoming(d.upcoming);
  }

  function renderSummary(s) {
    document.getElementById('dash-summary').innerHTML = `
      <div class="summary-card income">
        <div class="sc-label">INCOME</div>
        <div class="sc-value income-val">+${App.fmt(s.income)}</div>
        <div class="sc-sub">${s.month}</div>
      </div>
      <div class="summary-card expense">
        <div class="sc-label">SPENT</div>
        <div class="sc-value expense-val">-${App.fmt(s.spent)}</div>
        <div class="sc-sub">${s.month}</div>
      </div>
      <div class="summary-card savings">
        <div class="sc-label">SAVED</div>
        <div class="sc-value ${s.saved >= 0 ? 'income-val' : 'expense-val'}">${s.saved >= 0 ? '+' : ''}${App.fmt(s.saved)}</div>
        <div class="sc-sub">${s.savings_pct}% of income</div>
      </div>`;
  }

  function renderAlerts(alerts) {
    const el = document.getElementById('dash-alerts');
    if (!alerts || !alerts.length) { el.innerHTML = ''; return; }
    el.innerHTML = alerts.map(a =>
      `<div class="alert-banner ${a.severity}">
        <span class="alert-icon">${a.severity === 'danger' ? '[!!]' : '[!]'}</span>
        <span>${a.message}</span>
      </div>`
    ).join('');
  }

  function renderCharts(history, categories) {
    const GREEN = '#00ff88', RED = '#ff4444', WHITE = '#e8e8e8';
    const gridColor = 'rgba(255,255,255,0.06)';
    const textColor = '#888888';
    const monoFont = { family: 'IBM Plex Mono', size: 10 };
    const defaults = {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 800, easing: 'easeInOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(0,0,0,0.95)',
          titleColor: WHITE,
          bodyColor: textColor,
          borderColor: 'rgba(255,255,255,0.15)',
          borderWidth: 1,
          titleFont: monoFont,
          bodyFont: monoFont,
        }
      },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, font: monoFont } },
        y: { grid: { color: gridColor }, ticks: { color: textColor, font: monoFont } }
      }
    };

    // Savings trend — green line
    const ctx1 = document.getElementById('chart-savings');
    if (ctx1) {
      const labels = (history || []).map(h => h.month);
      const savings = (history || []).map(h => h.savings);
      charts.savings = new Chart(ctx1, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Savings',
              data: savings,
              backgroundColor: savings.map(v => v >= 0 ? 'rgba(0,255,136,0.25)' : 'rgba(255,68,68,0.25)'),
              borderColor: savings.map(v => v >= 0 ? GREEN : RED),
              borderWidth: 1,
              borderRadius: 2,
            },
            {
              label: 'Income',
              data: (history || []).map(h => h.income),
              type: 'line',
              borderColor: 'rgba(255,255,255,0.35)',
              borderWidth: 1,
              borderDash: [4, 4],
              pointRadius: 2,
              pointBackgroundColor: WHITE,
              tension: 0.3,
              fill: false,
            }
          ]
        },
        options: defaults,
      });
    }

    // Category doughnut
    const ctx2 = document.getElementById('chart-category');
    if (ctx2 && categories && categories.length) {
      // Monochrome step palette
      const GRAYS = ['#ffffff','#cccccc','#aaaaaa','#888888','#666666','#444444','#333333','#222222'];
      charts.category = new Chart(ctx2, {
        type: 'doughnut',
        data: {
          labels: categories.map(c => c.category),
          datasets: [{ data: categories.map(c => c.amount), backgroundColor: GRAYS, borderWidth: 1, borderColor: '#111' }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 800 },
          plugins: {
            legend: { display: true, position: 'bottom', labels: { color: textColor, font: monoFont, boxWidth: 10, padding: 8 } },
            tooltip: defaults.plugins.tooltip
          }
        }
      });
    } else if (ctx2) {
      ctx2.parentElement.innerHTML = '<div class="empty-state" style="padding:1.5rem"><div class="empty-title">NO DATA</div><div class="empty-sub">no expenses this month</div></div>';
    }
  }

  function renderUpcoming(upcoming) {
    const el = document.getElementById('dash-upcoming');
    if (!upcoming || !upcoming.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-title">CLEAR</div><div class="empty-sub">no upcoming payments</div></div>';
      return;
    }
    el.innerHTML = upcoming.map(u => {
      const badge = u.days_left <= 3 ? 'badge-danger' : u.days_left <= 7 ? 'badge-warning' : 'badge-accent';
      const typeLabel = u.type === 'subscription' ? '[SUB]' : '[TRIP]';
      return `<div class="upcoming-item">
        <span class="upcoming-type">${typeLabel}</span>
        <div style="flex:1"><div class="ui-title">${u.title}</div><div class="ui-date">${App.fmtDate(u.due_date)}</div></div>
        <span class="badge ${badge}">${u.days_left}d</span>
        <div class="ui-amount expense-val">-${App.fmt(u.amount)}</div>
      </div>`;
    }).join('');
  }

  return { init };
})();
