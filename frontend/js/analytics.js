/* analytics.js */
const AnalyticsModule = (() => {
  let charts = {};
  let months = 12;

  async function init() {
    const el = document.getElementById('page-analytics');
    el.innerHTML = `
      <div class="page-top"><h2>Analytics</h2></div>
      <div class="period-chips">
        <span class="period-chip" data-m="3" onclick="AnalyticsModule.setPeriod(3,this)">3M</span>
        <span class="period-chip active" data-m="12" onclick="AnalyticsModule.setPeriod(12,this)">12M</span>
      </div>
      <div class="analytics-grid">
        <div class="card big-chart-card" style="grid-column:1/-1">
          <h3>Income vs Expenses</h3>
          <div class="big-chart-wrap"><canvas id="chart-cashflow"></canvas></div>
        </div>
        <div class="card big-chart-card">
          <h3>Category Breakdown</h3>
          <div class="big-chart-wrap"><canvas id="chart-cats"></canvas></div>
        </div>
        <div class="health-card" id="health-card">
          <div class="text-muted text-sm mb-1">Financial Health</div>
          <div class="health-score" id="health-score">…</div>
          <div class="health-status" id="health-status"></div>
          <div class="health-sub" id="health-sub"></div>
        </div>
      </div>`;
    load();
  }

  async function load() {
    Object.values(charts).forEach(c => c && c.destroy && c.destroy());
    charts = {};

    const [cfRes, catRes, healthRes] = await Promise.all([
      API.get(`/api/analytics/cashflow?months=${months}`),
      API.get(`/api/analytics/categories?months=${months < 6 ? months : 3}`),
      API.get('/api/analytics/health'),
    ]);

    const gridColor = 'rgba(255,255,255,0.06)', textColor = '#94a3b8';
    const baseOpts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: textColor, font: { size: 10 } } },
        tooltip: { backgroundColor: 'rgba(15,20,40,0.95)', titleColor: '#e2e8f0', bodyColor: '#94a3b8', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 } },
      scales: { x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 9 }, maxRotation: 45 } },
                y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 9 } } } }
    };

    if (cfRes && cfRes.success) {
      const data = cfRes.data;
      const ctx = document.getElementById('chart-cashflow');
      if (ctx) charts.cashflow = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.map(d => d.month),
          datasets: [
            { label: 'Income', data: data.map(d => d.income), backgroundColor: 'rgba(34,211,165,0.7)', borderRadius: 4 },
            { label: 'Expense', data: data.map(d => d.expense), backgroundColor: 'rgba(244,63,94,0.7)', borderRadius: 4 },
            { label: 'Savings', data: data.map(d => d.savings), type: 'line', borderColor: '#7c6bff', borderWidth: 2, pointBackgroundColor: '#7c6bff', pointRadius: 3, fill: false, tension: 0.4 },
          ]
        },
        options: baseOpts,
      });
    }

    if (catRes && catRes.success && catRes.data.length) {
      const cats = catRes.data;
      const COLORS = ['#7c6bff','#22d3a5','#f43f5e','#fbbf24','#38bdf8','#a78bfa','#34d399','#fb7185','#f97316'];
      const ctx2 = document.getElementById('chart-cats');
      if (ctx2) charts.cats = new Chart(ctx2, {
        type: 'doughnut',
        data: { labels: cats.map(c=>c.category), datasets: [{ data: cats.map(c=>c.amount), backgroundColor: COLORS, borderWidth: 2, borderColor: 'rgba(10,14,26,0.8)' }] },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: true, position: 'bottom', labels: { color: textColor, font: { size: 10 }, boxWidth: 10, padding: 8 } },
            tooltip: baseOpts.plugins.tooltip } }
      });
    }

    if (healthRes && healthRes.success) {
      const h = healthRes.data;
      const scoreEl = document.getElementById('health-score');
      const statusEl = document.getElementById('health-status');
      const subEl = document.getElementById('health-sub');
      const color = h.score >= 80 ? '#22d3a5' : h.score >= 60 ? '#7c6bff' : h.score >= 40 ? '#fbbf24' : '#f43f5e';
      if (scoreEl) { scoreEl.textContent = h.score; scoreEl.style.color = color; }
      if (statusEl) { statusEl.textContent = h.status; statusEl.style.color = color; }
      if (subEl) subEl.textContent = `Based on last ${Math.min(months, 3)} months`;
    }
  }

  function setPeriod(m, el) {
    months = m;
    document.querySelectorAll('.period-chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    load();
  }

  return { init, setPeriod };
})();
