/* reports.js */
const ReportsModule = (() => {
  async function init() {
    const el = document.getElementById('page-reports');
    el.innerHTML = `
      <div class="page-top"><h2>Export Reports</h2></div>
      <p class="text-muted text-sm mb-2">Download your data as CSV or Excel files.</p>
      <div style="display:flex;flex-direction:column;gap:.75rem">
        ${[
          { icon:'💳', title:'Expenses & Income', desc:'All transactions with category and payment mode', key:'expenses' },
          { icon:'🔁', title:'Subscriptions', desc:'All recurring subscriptions with renewal dates', key:'subscriptions' },
          { icon:'📈', title:'Cash Flow History', desc:'12-month income vs expense trend', key:'cashflow' },
        ].map(r => `
          <div class="report-card">
            <div class="report-icon">${r.icon}</div>
            <div class="report-info">
              <div class="report-title">${r.title}</div>
              <div class="report-desc">${r.desc}</div>
            </div>
            <div class="report-actions">
              <a class="btn btn-ghost btn-sm" href="/api/reports/${r.key}?format=csv" download onclick="ReportsModule.attachToken(this)">CSV</a>
              <a class="btn btn-success btn-sm" href="/api/reports/${r.key}?format=xlsx" download onclick="ReportsModule.attachToken(this)">Excel</a>
            </div>
          </div>`).join('')}
      </div>`;

    // Attach tokens on load
    document.querySelectorAll('#page-reports a[download]').forEach(a => attachToken(a));
  }

  function attachToken(a) {
    const base = a.href.split('?')[0];
    const params = new URLSearchParams(a.href.split('?')[1] || '');
    params.set('token', API.token() || '');
    // Note: JWT must be sent via header, use fetch-based download instead
    a.addEventListener('click', async (e) => {
      e.preventDefault();
      const url = base + '?' + params.toString();
      const res = await fetch(url, { headers: { Authorization: 'Bearer ' + API.token() } });
      if (!res.ok) { App.toast('Export failed', 'error'); return; }
      const blob = await res.blob();
      const dl = document.createElement('a');
      dl.href = URL.createObjectURL(blob);
      dl.download = a.href.includes('xlsx') ? base.split('/').pop() + '.xlsx' : base.split('/').pop() + '.csv';
      dl.click();
      App.toast('Downloaded!');
    });
  }

  return { init, attachToken };
})();
