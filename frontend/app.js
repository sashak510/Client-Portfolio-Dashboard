/* ==========================================================================
   PortfolioDash — Frontend Application
   Vanilla JS dashboard for the Client Portfolio Dashboard API
   ========================================================================== */

(function () {
  'use strict';

  // ── Configuration ──────────────────────────────────────────────────────
  const API_BASE = 'http://localhost:8000';
  let accessToken = null;
  let refreshToken = null;
  let allocationChart = null;

  // ── DOM References ─────────────────────────────────────────────────────
  const loginPanel = document.getElementById('login-panel');
  const loginForm = document.getElementById('login-form');
  const loginError = document.getElementById('login-error');
  const appShell = document.getElementById('app-shell');
  const sidebar = document.getElementById('sidebar');
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const toastContainer = document.getElementById('toast-container');

  // ── Utility: Number & Date Formatting ──────────────────────────────────
  function formatCurrency(value) {
    const num = parseFloat(value) || 0;
    return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatNumber(value, decimals) {
    if (decimals === undefined) decimals = 2;
    const num = parseFloat(value) || 0;
    return num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function formatPct(value) {
    return formatNumber(value) + '%';
  }

  // ── Utility: Toast Notifications ───────────────────────────────────────
  function showToast(message, type) {
    if (!type) type = 'info';
    const toast = document.createElement('div');
    toast.className = 'toast' + (type !== 'info' ? ' toast-' + type : '');
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  }

  // ── API: Fetch Wrapper ─────────────────────────────────────────────────
  async function apiFetch(path, options) {
    if (!options) options = {};
    const url = API_BASE + path;
    const headers = Object.assign({
      'Content-Type': 'application/json',
    }, options.headers || {});

    if (accessToken) {
      headers['Authorization'] = 'Bearer ' + accessToken;
    }

    const fetchOptions = Object.assign({}, options, { headers: headers });

    let response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (err) {
      showToast('Network error — is the API running on localhost:8000?', 'error');
      throw err;
    }

    // Try to refresh token on 401
    if (response.status === 401 && refreshToken) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        headers['Authorization'] = 'Bearer ' + accessToken;
        response = await fetch(url, Object.assign({}, options, { headers: headers }));
      } else {
        logout();
        return null;
      }
    }

    if (!response.ok) {
      const body = await response.json().catch(function () { return {}; });
      const msg = body.detail || body.message || 'Request failed (' + response.status + ')';
      showToast(msg, 'error');
      throw new Error(msg);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  async function tryRefreshToken() {
    try {
      const resp = await fetch(API_BASE + '/api/auth/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (resp.ok) {
        const data = await resp.json();
        accessToken = data.access;
        return true;
      }
    } catch (e) { /* ignore */ }
    return false;
  }

  // ── Auth: Login / Logout ───────────────────────────────────────────────
  loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    loginError.hidden = true;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
      const resp = await fetch(API_BASE + '/api/auth/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, password: password }),
      });

      if (!resp.ok) {
        loginError.textContent = 'Invalid username or password';
        loginError.hidden = false;
        return;
      }

      const data = await resp.json();
      accessToken = data.access;
      refreshToken = data.refresh;

      document.getElementById('user-display').textContent = username;
      document.getElementById('user-avatar').textContent = username.charAt(0).toUpperCase();

      loginPanel.hidden = true;
      appShell.hidden = false;

      loadDashboard();
    } catch (err) {
      loginError.textContent = 'Cannot connect to API. Is it running?';
      loginError.hidden = false;
    }
  });

  function logout() {
    accessToken = null;
    refreshToken = null;
    loginPanel.hidden = false;
    appShell.hidden = true;
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
  }

  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('mobile-logout-btn').addEventListener('click', logout);

  // ── Navigation ─────────────────────────────────────────────────────────
  var navItems = document.querySelectorAll('.nav-item[data-view]');
  navItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      e.preventDefault();
      var view = item.getAttribute('data-view');
      switchView(view);
      // Close mobile sidebar
      sidebar.classList.remove('open');
    });
  });

  mobileMenuBtn.addEventListener('click', function () {
    sidebar.classList.toggle('open');
  });

  // Close sidebar on outside click (mobile)
  document.addEventListener('click', function (e) {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && e.target !== mobileMenuBtn && !mobileMenuBtn.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    }
  });

  document.getElementById('back-to-clients').addEventListener('click', function () {
    switchView('dashboard');
  });

  function switchView(viewName) {
    var views = document.querySelectorAll('.view');
    views.forEach(function (v) { v.hidden = true; });

    navItems.forEach(function (n) { n.classList.remove('active'); });
    var activeNav = document.querySelector('.nav-item[data-view="' + viewName + '"]');
    if (activeNav) activeNav.classList.add('active');

    var target = document.getElementById('view-' + viewName);
    if (target) target.hidden = false;

    if (viewName === 'dashboard') loadDashboard();
    if (viewName === 'clients') loadClientsView();
    if (viewName === 'assets') loadAssets();
  }

  // ── Data Loading: Dashboard ────────────────────────────────────────────
  async function loadDashboard() {
    try {
      const data = await apiFetch('/api/clients/?page_size=100');
      if (!data) return;

      const clients = data.results || data;
      renderDashboardSummary(clients);
      renderClientsTable(clients, 'clients-table-body', false);
    } catch (err) { /* toast already shown */ }
  }

  function renderDashboardSummary(clients) {
    var totalValue = 0;
    clients.forEach(function (c) {
      totalValue += parseFloat(c.total_portfolio_value) || 0;
    });

    var container = document.getElementById('dashboard-summary');
    container.innerHTML =
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Clients</div>' +
        '<div class="summary-card-value">' + clients.length + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Portfolio Value</div>' +
        '<div class="summary-card-value">' + formatCurrency(totalValue) + '</div>' +
      '</div>';
  }

  function renderClientsTable(clients, tbodyId, showPhone) {
    var tbody = document.getElementById(tbodyId);
    if (clients.length === 0) {
      tbody.innerHTML = '<tr><td colspan="' + (showPhone ? 5 : 4) + '" class="loading-cell" style="color:var(--slate-500)">No clients found</td></tr>';
      return;
    }

    var html = '';
    clients.forEach(function (c) {
      html += '<tr class="clickable-row" data-client-id="' + c.id + '">';
      html += '<td>' + escapeHtml(c.first_name + ' ' + c.last_name) + '</td>';
      html += '<td class="text-muted">' + escapeHtml(c.email) + '</td>';
      if (showPhone) html += '<td class="text-muted">' + escapeHtml(c.phone || '—') + '</td>';
      html += '<td class="text-right">' + formatCurrency(c.total_portfolio_value) + '</td>';
      html += '<td class="text-muted">' + formatDate(c.created_at) + '</td>';
      html += '</tr>';
    });
    tbody.innerHTML = html;

    // Attach click handlers
    tbody.querySelectorAll('.clickable-row').forEach(function (row) {
      row.addEventListener('click', function () {
        var clientId = row.getAttribute('data-client-id');
        loadClientDetail(clientId);
      });
    });
  }

  // ── Data Loading: Clients View ─────────────────────────────────────────
  async function loadClientsView() {
    try {
      const data = await apiFetch('/api/clients/?page_size=100');
      if (!data) return;

      const clients = data.results || data;

      var totalValue = 0;
      clients.forEach(function (c) {
        totalValue += parseFloat(c.total_portfolio_value) || 0;
      });

      var container = document.getElementById('clients-summary');
      container.innerHTML =
        '<div class="summary-card">' +
          '<div class="summary-card-label">Total Clients</div>' +
          '<div class="summary-card-value">' + clients.length + '</div>' +
        '</div>' +
        '<div class="summary-card">' +
          '<div class="summary-card-label">Total AUM</div>' +
          '<div class="summary-card-value">' + formatCurrency(totalValue) + '</div>' +
        '</div>';

      renderClientsTable(clients, 'clients-list-body', true);
    } catch (err) { /* toast already shown */ }
  }

  // ── Data Loading: Assets ───────────────────────────────────────────────
  async function loadAssets() {
    try {
      const data = await apiFetch('/api/assets/?page_size=100');
      if (!data) return;

      const assets = data.results || data;
      var tbody = document.getElementById('assets-table-body');

      if (assets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell" style="color:var(--slate-500)">No assets found</td></tr>';
        return;
      }

      var html = '';
      assets.forEach(function (a) {
        var badgeClass = 'badge-' + a.asset_type;
        var price = a.last_price;
        if (a.asset_type === 'cash') price = '1.00';
        else if (a.asset_type === 'bond') price = a.face_value || '0.00';

        html += '<tr>';
        html += '<td><strong>' + escapeHtml(a.symbol) + '</strong></td>';
        html += '<td>' + escapeHtml(a.name) + '</td>';
        html += '<td><span class="badge ' + badgeClass + '">' + a.asset_type + '</span></td>';
        html += '<td class="text-right">' + formatCurrency(price) + '</td>';
        html += '<td class="text-muted">' + (a.price_updated_at ? formatDate(a.price_updated_at) : '—') + '</td>';
        html += '</tr>';
      });
      tbody.innerHTML = html;
    } catch (err) { /* toast already shown */ }
  }

  // ── Data Loading: Client Detail ────────────────────────────────────────
  async function loadClientDetail(clientId) {
    // Switch to detail view
    document.querySelectorAll('.view').forEach(function (v) { v.hidden = true; });
    document.getElementById('view-client-detail').hidden = false;
    document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });

    // Show loading state
    document.getElementById('client-detail-name').textContent = 'Loading...';
    document.getElementById('client-detail-meta').textContent = '';
    document.getElementById('portfolio-summary-cards').innerHTML = '<div class="summary-card"><div class="loading-cell"><div class="spinner"></div></div></div>';
    document.getElementById('holdings-table-body').innerHTML = '<tr><td colspan="8" class="loading-cell"><div class="spinner"></div></td></tr>';
    document.getElementById('transactions-table-body').innerHTML = '<tr><td colspan="6" class="loading-cell"><div class="spinner"></div></td></tr>';

    try {
      // Fetch client detail and portfolio summary in parallel
      var detailPromise = apiFetch('/api/clients/' + clientId + '/');
      var summaryPromise = apiFetch('/api/clients/' + clientId + '/portfolio-summary/');
      var results = await Promise.all([detailPromise, summaryPromise]);
      var client = results[0];
      var summary = results[1];

      if (!client || !summary) return;

      renderClientDetail(client, summary);
    } catch (err) { /* toast already shown */ }
  }

  function renderClientDetail(client, summary) {
    // Header
    document.getElementById('client-detail-name').textContent = client.first_name + ' ' + client.last_name;
    var metaParts = [client.email];
    if (client.phone) metaParts.push(client.phone);
    document.getElementById('client-detail-meta').textContent = metaParts.join(' · ');

    // Summary cards
    var totalValue = parseFloat(summary.total_value) || 0;
    var totalGL = parseFloat(summary.total_gain_loss) || 0;
    var glClass = totalGL >= 0 ? 'positive' : 'negative';
    var glPrefix = totalGL >= 0 ? '+' : '';

    var cardsHtml =
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Value</div>' +
        '<div class="summary-card-value">' + formatCurrency(totalValue) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Gain/Loss</div>' +
        '<div class="summary-card-value ' + glClass + '">' + glPrefix + formatCurrency(totalGL) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Equity</div>' +
        '<div class="summary-card-value">' + formatPct(summary.equity_allocation_pct) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Bonds</div>' +
        '<div class="summary-card-value">' + formatPct(summary.bond_allocation_pct) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Cash</div>' +
        '<div class="summary-card-value">' + formatPct(summary.cash_allocation_pct) + '</div>' +
      '</div>';

    document.getElementById('portfolio-summary-cards').innerHTML = cardsHtml;

    // Allocation chart
    renderAllocationChart(summary);

    // Holdings table
    renderHoldings(client.holdings || [], totalValue);

    // Recent transactions
    renderTransactions(client.recent_transactions || []);
  }

  function renderAllocationChart(summary) {
    var ctx = document.getElementById('allocation-chart').getContext('2d');

    if (allocationChart) {
      allocationChart.destroy();
    }

    var equity = parseFloat(summary.equity_allocation_pct) || 0;
    var bond = parseFloat(summary.bond_allocation_pct) || 0;
    var cash = parseFloat(summary.cash_allocation_pct) || 0;

    allocationChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Equity', 'Bonds', 'Cash'],
        datasets: [{
          data: [equity, bond, cash],
          backgroundColor: ['#0066FF', '#f59e0b', '#16a34a'],
          borderWidth: 0,
          hoverOffset: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 8,
              font: { family: "'Inter', sans-serif", size: 12 },
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.label + ': ' + context.parsed.toFixed(1) + '%';
              },
            },
          },
        },
      },
    });
  }

  function renderHoldings(holdings, totalValue) {
    var tbody = document.getElementById('holdings-table-body');
    if (holdings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-cell" style="color:var(--slate-500)">No holdings</td></tr>';
      return;
    }

    var html = '';
    holdings.forEach(function (h) {
      var asset = h.asset_detail || {};
      var currentValue = parseFloat(h.current_value) || 0;
      var gainLoss = parseFloat(h.gain_loss) || 0;
      var glClass = gainLoss >= 0 ? 'text-positive' : 'text-negative';
      var glPrefix = gainLoss >= 0 ? '+' : '';
      var allocPct = totalValue > 0 ? ((currentValue / totalValue) * 100) : 0;
      var badgeClass = 'badge-' + (asset.asset_type || 'equity');

      html += '<tr>';
      html += '<td><strong>' + escapeHtml(asset.symbol || '') + '</strong></td>';
      html += '<td>' + escapeHtml(asset.name || '') + '</td>';
      html += '<td><span class="badge ' + badgeClass + '">' + (asset.asset_type || '') + '</span></td>';
      html += '<td class="text-right">' + formatNumber(h.quantity, 4) + '</td>';
      html += '<td class="text-right">' + formatCurrency(h.average_cost) + '</td>';
      html += '<td class="text-right">' + formatCurrency(currentValue) + '</td>';
      html += '<td class="text-right ' + glClass + '">' + glPrefix + formatCurrency(gainLoss) + '</td>';
      html += '<td class="text-right">' + formatPct(allocPct) + '</td>';
      html += '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderTransactions(transactions) {
    var tbody = document.getElementById('transactions-table-body');
    if (transactions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-cell" style="color:var(--slate-500)">No transactions</td></tr>';
      return;
    }

    var html = '';
    transactions.forEach(function (t) {
      var asset = t.asset_detail || {};
      var badgeClass = 'badge-' + (t.transaction_type || 'buy');

      html += '<tr>';
      html += '<td>' + formatDate(t.executed_at) + '</td>';
      html += '<td><span class="badge ' + badgeClass + '">' + (t.transaction_type || '').toUpperCase() + '</span></td>';
      html += '<td><strong>' + escapeHtml(asset.symbol || '') + '</strong></td>';
      html += '<td class="text-right">' + formatNumber(t.quantity, 4) + '</td>';
      html += '<td class="text-right">' + formatCurrency(t.price) + '</td>';
      html += '<td class="text-right">' + formatCurrency(t.total_value) + '</td>';
      html += '</tr>';
    });
    tbody.innerHTML = html;
  }

  // ── Utility: Escape HTML ───────────────────────────────────────────────
  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

})();
