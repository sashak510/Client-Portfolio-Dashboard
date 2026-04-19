/* ==========================================================================
   Stasha — Frontend Application
   Vanilla JS dashboard for the Personal Finance Dashboard API
   ========================================================================== */

(function () {
  'use strict';

  // ── Configuration ──────────────────────────────────────────────────────
  const API_BASE = 'http://localhost:8000';
  let allocationChart = null;
  let targetAllocationChart = null;
  let currentAccountId = null;

  // ── Multi-Currency ─────────────────────────────────────────────────────
  // Base currency of all stored values is GBP.
  const FX_RATES = { GBP: 1, USD: 1.27, EUR: 1.17 };
  var activeCurrency = localStorage.getItem('pd-currency') || 'GBP';

  function setActiveCurrency(code) {
    activeCurrency = code;
    localStorage.setItem('pd-currency', code);
    var sel = document.getElementById('currency-selector');
    if (sel) sel.value = code;
  }

  function convertAmount(gbpValue) {
    var rate = FX_RATES[activeCurrency] || 1;
    return parseFloat(gbpValue) * rate;
  }

  // Wrap the base formatCurrency so callers don't need to know the active currency
  function fmtCurrency(gbpValue) {
    return formatCurrency(convertAmount(gbpValue), activeCurrency);
  }

  // ── DOM References ─────────────────────────────────────────────────────
  const loginPanel = document.getElementById('login-panel');
  const loginForm = document.getElementById('login-form');
  const loginError = document.getElementById('login-error');
  const appShell = document.getElementById('app-shell');
  const sidebar = document.getElementById('sidebar');
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const toastContainer = document.getElementById('toast-container');

  // ── Utility: Number & Date Formatting ──────────────────────────────────
  var currencyFormatters = {};
  function formatCurrency(value, currency) {
    if (!currency) currency = 'GBP';
    var code = currency.toUpperCase();
    if (!currencyFormatters[code]) {
      try {
        currencyFormatters[code] = new Intl.NumberFormat('en-GB', {
          style: 'currency', currency: code, minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
      } catch (e) {
        currencyFormatters[code] = new Intl.NumberFormat('en-GB', {
          style: 'currency', currency: 'GBP', minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
      }
    }
    return currencyFormatters[code].format(parseFloat(value) || 0);
  }

  function formatNumber(value, decimals) {
    if (decimals === undefined) decimals = 2;
    var num = parseFloat(value) || 0;
    return num.toLocaleString('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    var d = new Date(dateStr);
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function formatPct(value) {
    return formatNumber(value) + '%';
  }

  // ── Utility: Escape HTML ───────────────────────────────────────────────
  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = String(text == null ? '' : text);
    return div.innerHTML;
  }

  // ── Utility: Mobile card list renderer ────────────────────────────────
  // cards: [{id, icon (1-2 chars), name, badge, badgeCls, sub, value, onClick}]
  function renderMobileCards(containerId, cards) {
    var el = document.getElementById(containerId);
    if (!el) return;
    if (!cards || !cards.length) { el.innerHTML = ''; return; }
    el.innerHTML = cards.map(function (c) {
      return '<div class="m-card" role="button" tabindex="0">' +
        '<div class="m-card-icon">' + escapeHtml(c.icon) + '</div>' +
        '<div class="m-card-body">' +
          '<div class="m-card-name">' + escapeHtml(c.name) + '</div>' +
          '<div class="m-card-meta">' +
            '<span class="badge ' + (c.badgeCls || '') + '">' + escapeHtml(c.badge) + '</span>' +
            (c.sub ? '<span class="m-card-sub">' + escapeHtml(c.sub) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div class="m-card-value">' + escapeHtml(c.value) + '</div>' +
        '<svg class="m-card-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>' +
      '</div>';
    }).join('');
    el.querySelectorAll('.m-card').forEach(function (card, i) {
      function activate() { if (cards[i] && cards[i].onClick) cards[i].onClick(); }
      card.addEventListener('click', activate);
      card.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); } });
    });
  }

  // ── Utility: Empty State HTML builder ─────────────────────────────────
  // iconSvg: inner SVG markup; title/body: strings; actions: array of {label, cls, handler|href}
  function emptyStateHtml(iconSvg, title, body, actions) {
    var actionsHtml = '';
    if (actions && actions.length) {
      actionsHtml = '<div class="empty-state-actions">';
      actions.forEach(function (a) {
        if (a.href) {
          actionsHtml += '<button class="empty-state-link" data-es-nav="' + a.href + '">' + escapeHtml(a.label) + '</button>';
        } else {
          actionsHtml += '<button class="btn btn-primary btn-sm" data-es-action="' + escapeHtml(a.id || '') + '">' + escapeHtml(a.label) + '</button>';
        }
      });
      actionsHtml += '</div>';
    }
    return '<div class="empty-state">' +
      '<div class="empty-state-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + iconSvg + '</svg></div>' +
      '<h3 class="empty-state-title">' + escapeHtml(title) + '</h3>' +
      '<p class="empty-state-body">' + escapeHtml(body) + '</p>' +
      actionsHtml +
    '</div>';
  }

  // ── Utility: Toast Notifications ───────────────────────────────────────
  function showToast(message, type) {
    if (!type) type = 'info';
    var toast = document.createElement('div');
    toast.className = 'toast' + (type !== 'info' ? ' toast-' + type : '');
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  }

  // ── Utility: CSRF token ────────────────────────────────────────────────
  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  // ── API: Fetch Wrapper ─────────────────────────────────────────────────
  async function apiFetch(path, options) {
    if (!options) options = {};
    var url = API_BASE + path;
    var method = (options.method || 'GET').toUpperCase();

    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});

    // Echo CSRF token on mutating requests.
    if (['POST', 'PATCH', 'PUT', 'DELETE'].indexOf(method) !== -1) {
      headers['X-CSRFToken'] = getCsrfToken();
    }

    var fetchOptions = Object.assign({}, options, {
      headers: headers,
      credentials: 'include',
    });

    var response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (err) {
      showToast('Network error — is the API running on localhost:8000?', 'error');
      throw err;
    }

    // Try to refresh token on 401, then retry once.
    if (response.status === 401) {
      var refreshed = await tryRefreshToken();
      if (refreshed) {
        response = await fetch(url, fetchOptions);
      } else {
        logout();
        return null;
      }
    }

    if (!response.ok) {
      var body = await response.json().catch(function () { return {}; });
      var msg = body.detail || body.message || 'Request failed (' + response.status + ')';
      showToast(msg, 'error');
      throw new Error(msg);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  async function tryRefreshToken() {
    try {
      var resp = await fetch(API_BASE + '/api/auth/token/refresh/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      });
      return resp.ok;
    } catch (e) { /* ignore */ }
    return false;
  }

  // ── Auth: Login / Logout ───────────────────────────────────────────────
  loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    loginError.hidden = true;
    var username = document.getElementById('username').value;
    var password = document.getElementById('password').value;

    try {
      var resp = await fetch(API_BASE + '/api/auth/token/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, password: password }),
      });

      if (!resp.ok) {
        loginError.textContent = 'Invalid username or password';
        loginError.hidden = false;
        return;
      }

      setNametag(username);

      loginPanel.hidden = true;
      appShell.hidden = false;

      loadDashboard();
    } catch (err) {
      loginError.textContent = 'Cannot connect to API. Is it running?';
      loginError.hidden = false;
    }
  });

  async function logout() {
    try {
      await fetch(API_BASE + '/api/auth/logout/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      });
    } catch (e) { /* ignore network errors on logout */ }
    loginPanel.hidden = false;
    appShell.hidden = true;
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
  }

  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('mobile-logout-btn').addEventListener('click', logout);

  (async function checkSession() {
    async function fetchMe() {
      return fetch(API_BASE + '/api/auth/me/', { credentials: 'include' });
    }
    try {
      var resp = await fetchMe();
      if (resp.status === 401) {
        var refreshed = await tryRefreshToken();
        if (refreshed) resp = await fetchMe();
      }
      if (resp.ok) {
        var me = await resp.json();
        setNametag(me.username);
        loginPanel.hidden = true;
        appShell.hidden = false;
        loadDashboard();
      }
    } catch (e) { /* network error — leave login panel visible */ }
  }());

  // ── Currency Selector ──────────────────────────────────────────────────
  function initCurrencySelector() {
    var sel = document.getElementById('currency-selector');
    var mSel = document.getElementById('mobile-currency-selector');
    var saved = localStorage.getItem('pd-currency') || 'GBP';
    activeCurrency = saved;
    if (sel) sel.value = saved;
    if (mSel) mSel.value = saved;

    function onCurrencyChange(e) {
      setActiveCurrency(e.target.value);
      // Sync the other selector
      var other = (e.target === sel) ? mSel : sel;
      if (other) other.value = e.target.value;
      // Re-render whichever view is visible
      rerenderCurrentView();
    }

    if (sel) sel.addEventListener('change', onCurrencyChange);
    if (mSel) mSel.addEventListener('change', onCurrencyChange);
  }

  function rerenderCurrentView() {
    var views = ['dashboard', 'accounts', 'assets', 'watchlist', 'net-worth', 'performance'];
    for (var i = 0; i < views.length; i++) {
      var el = document.getElementById('view-' + views[i]);
      if (el && !el.hidden) {
        if (views[i] === 'dashboard')   { loadDashboard(); return; }
        if (views[i] === 'accounts')    { loadAccountsView(); return; }
        if (views[i] === 'assets')      { loadAssets(); return; }
        if (views[i] === 'watchlist')   { loadWatchlist(); return; }
        if (views[i] === 'net-worth')   { loadNetWorth(); return; }
        if (views[i] === 'performance') { loadPerformance(); return; }
      }
    }
    var detailEl = document.getElementById('view-account-detail');
    if (detailEl && !detailEl.hidden && currentAccountId) {
      loadAccountDetail(currentAccountId);
    }
  }

  initCurrencySelector();

  // ── Dark Mode Toggle ───────────────────────────────────────────────────
  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('pd-theme', theme);

    // If an allocation chart is alive, update its legend/tooltip colour so it
    // stays legible after switching themes.
    if (allocationChart) {
      var isDark = theme !== 'dark';
      var labelColor = isDark ? '#cecece' : '#6a6b6c';
      allocationChart.options.plugins.legend.labels.color = labelColor;
      allocationChart.update();
    }
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
  document.getElementById('mobile-theme-toggle').addEventListener('click', toggleTheme);

  // ── Navigation ─────────────────────────────────────────────────────────
  var navItems = document.querySelectorAll('.nav-item[data-view]');
  navItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      e.preventDefault();
      var view = item.getAttribute('data-view');
      switchView(view);
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

  document.getElementById('back-to-accounts').addEventListener('click', function () {
    switchView('dashboard');
  });

  var viewTitles = {
    'dashboard':   'Dashboard',
    'accounts':    'Accounts',
    'assets':      'Assets',
    'watchlist':   'Watchlist',
    'net-worth':   'Net Worth',
    'goals':       'Goals',
    'performance': 'Performance',
    'import':      'Import CSV',
    'settings':    'Settings',
  };

  function switchView(viewName) {
    document.querySelectorAll('.view').forEach(function (v) { v.hidden = true; });
    navItems.forEach(function (n) { n.classList.remove('active'); });

    var activeNav = document.querySelector('.nav-item[data-view="' + viewName + '"]');
    if (activeNav) activeNav.classList.add('active');

    var target = document.getElementById('view-' + viewName);
    if (target) target.hidden = false;

    document.title = viewTitles[viewName] || viewName;

    if (viewName === 'dashboard')   loadDashboard();
    if (viewName === 'accounts')    loadAccountsView();
    if (viewName === 'assets')      loadAssets();
    if (viewName === 'watchlist')   loadWatchlist();
    if (viewName === 'import')      initImportView();
    if (viewName === 'performance') loadPerformanceView();
    if (viewName === 'net-worth')   loadNetWorth();
    if (viewName === 'goals')       loadGoals();
    if (viewName === 'settings')    loadSettings();
  }

  // ── Search & Sort: Generic Table Controller ────────────────────────────
  function makeTableController(tableId, searchInputId) {
    var table = document.getElementById(tableId);
    var searchInput = searchInputId ? document.getElementById(searchInputId) : null;
    var colCount = table ? table.querySelectorAll('thead th').length : 0;

    var state = {
      rows: [],
      sortCol: -1,
      sortDir: 'asc',
      query: '',
    };

    function render() {
      if (!table) return;
      var tbody = table.querySelector('tbody');

      // 1. Filter
      var filtered = state.rows.filter(function (row) {
        if (!state.query) return true;
        var q = state.query.toLowerCase();
        return row.cells.some(function (c) { return c.toLowerCase().indexOf(q) !== -1; });
      });

      // 2. Sort
      if (state.sortCol >= 0) {
        var col = state.sortCol;
        var dir = state.sortDir === 'asc' ? 1 : -1;
        filtered.sort(function (a, b) {
          var av = a.cells[col] || '';
          var bv = b.cells[col] || '';
          var an = parseFloat(av.replace(/[^0-9.\-]/g, ''));
          var bn = parseFloat(bv.replace(/[^0-9.\-]/g, ''));
          if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
          return av.localeCompare(bv) * dir;
        });
      }

      // 3. Render
      if (filtered.length === 0) {
        tbody.innerHTML = '<tr class="no-results-row"><td colspan="' + colCount + '">No results found</td></tr>';
      } else {
        tbody.innerHTML = filtered.map(function (r) { return r.html; }).join('');
        // Re-attach click handlers for clickable rows
        tbody.querySelectorAll('.clickable-row').forEach(function (row) {
          row.addEventListener('click', function () {
            var accountId = row.getAttribute('data-account-id');
            if (accountId) loadAccountDetail(accountId);
          });
        });
      }

      // 4. Update sort indicators in header
      table.querySelectorAll('thead th.sortable').forEach(function (th) {
        th.classList.remove('sort-asc', 'sort-desc');
        var indicator = th.querySelector('.sort-indicator');
        if (indicator) indicator.textContent = '';
      });
      if (state.sortCol >= 0) {
        var activeTh = table.querySelector('thead th[data-col="' + state.sortCol + '"]');
        if (activeTh) {
          var cls = state.sortDir === 'asc' ? 'sort-asc' : 'sort-desc';
          activeTh.classList.add(cls);
          var ind = activeTh.querySelector('.sort-indicator');
          if (ind) ind.textContent = state.sortDir === 'asc' ? '▲' : '▼';
        }
      }
    }

    // Wire up search input
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        state.query = searchInput.value;
        render();
      });
    }

    // Wire up sortable column headers
    if (table) {
      table.querySelectorAll('thead th.sortable').forEach(function (th) {
        th.addEventListener('click', function () {
          var col = parseInt(th.getAttribute('data-col'), 10);
          if (state.sortCol === col) {
            state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
          } else {
            state.sortCol = col;
            state.sortDir = 'asc';
          }
          render();
        });
      });
    }

    return {
      state: state,
      render: render,
      load: function (rows) {
        state.rows = rows;
        state.query = '';
        state.sortCol = -1;
        state.sortDir = 'asc';
        if (searchInput) searchInput.value = '';
        render();
      },
    };
  }

  // ── Table Controllers (initialised once, reused across loads) ──────────
  var ctrlDashboardAccounts = makeTableController('table-dashboard-accounts', 'search-dashboard-accounts');
  var ctrlAccounts          = makeTableController('table-accounts',           'search-accounts');
  var ctrlAssets            = makeTableController('table-assets',             'search-assets');
  var ctrlTransactions      = makeTableController('table-transactions',       'search-transactions');

  // Holdings controller is special — it renders grouped rows.
  var holdingsSearchInput = document.getElementById('search-holdings');
  var holdingsTable = document.getElementById('table-holdings');
  var holdingsState = {
    groups: [],
    query: '',
    sortCol: -1,
    sortDir: 'asc',
  };

  function renderGroupedHoldings() {
    if (!holdingsTable) return;
    var tbody = holdingsTable.querySelector('tbody');
    var totalRows = holdingsState.groups.reduce(function (s, g) { return s + g.rows.length; }, 0);

    if (totalRows === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="loading-cell" style="color:var(--text-muted)">No holdings</td></tr>';
      return;
    }

    var html = '';
    var anyVisible = false;

    holdingsState.groups.forEach(function (group) {
      var filtered = group.rows.filter(function (row) {
        if (!holdingsState.query) return true;
        var q = holdingsState.query.toLowerCase();
        return row.cells.some(function (c) { return c.toLowerCase().indexOf(q) !== -1; });
      });

      if (holdingsState.sortCol >= 0) {
        var col = holdingsState.sortCol;
        var dir = holdingsState.sortDir === 'asc' ? 1 : -1;
        filtered.sort(function (a, b) {
          var av = a.cells[col] || '';
          var bv = b.cells[col] || '';
          var an = parseFloat(av.replace(/[^0-9.\-]/g, ''));
          var bn = parseFloat(bv.replace(/[^0-9.\-]/g, ''));
          if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
          return av.localeCompare(bv) * dir;
        });
      }

      if (filtered.length === 0) return;

      anyVisible = true;
      html += group.headerHtml;
      filtered.forEach(function (r) { html += r.html; });
      html += group.subtotalHtml;
    });

    if (!anyVisible) {
      tbody.innerHTML = '<tr class="no-results-row"><td colspan="10">No results found</td></tr>';
    } else {
      tbody.innerHTML = html;
      // Wire up inline notes editing
      tbody.querySelectorAll('.notes-display').forEach(function (span) {
        span.addEventListener('click', function () {
          startNotesEdit(span);
        });
      });
      // Wire up holding edit/delete
      tbody.querySelectorAll('.holding-edit-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          openHoldingModal({
            id: btn.getAttribute('data-id'),
            asset: btn.getAttribute('data-asset'),
            quantity: btn.getAttribute('data-qty'),
            average_buy_price: btn.getAttribute('data-avg'),
            notes: btn.getAttribute('data-notes'),
          });
        });
      });
      tbody.querySelectorAll('.holding-delete-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          var id = btn.getAttribute('data-id');
          var symbol = btn.getAttribute('data-symbol');
          if (!confirm('Delete holding "' + symbol + '"? This cannot be undone.')) return;
          apiFetch('/api/holdings/' + id + '/', { method: 'DELETE' }).then(function () {
            showToast('Holding deleted', 'success');
            if (currentAccountId) loadAccountDetail(currentAccountId);
          }).catch(function () {});
        });
      });
    }

    // Update sort indicators
    holdingsTable.querySelectorAll('thead th.sortable').forEach(function (th) {
      th.classList.remove('sort-asc', 'sort-desc');
      var indicator = th.querySelector('.sort-indicator');
      if (indicator) indicator.textContent = '';
    });
    if (holdingsState.sortCol >= 0) {
      var activeTh = holdingsTable.querySelector('thead th[data-col="' + holdingsState.sortCol + '"]');
      if (activeTh) {
        activeTh.classList.add(holdingsState.sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
        var ind = activeTh.querySelector('.sort-indicator');
        if (ind) ind.textContent = holdingsState.sortDir === 'asc' ? '▲' : '▼';
      }
    }
  }

  if (holdingsSearchInput) {
    holdingsSearchInput.addEventListener('input', function () {
      holdingsState.query = holdingsSearchInput.value;
      renderGroupedHoldings();
    });
  }

  if (holdingsTable) {
    holdingsTable.querySelectorAll('thead th.sortable').forEach(function (th) {
      th.addEventListener('click', function () {
        var col = parseInt(th.getAttribute('data-col'), 10);
        if (holdingsState.sortCol === col) {
          holdingsState.sortDir = holdingsState.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          holdingsState.sortCol = col;
          holdingsState.sortDir = 'asc';
        }
        renderGroupedHoldings();
      });
    });
  }

  // ── Dashboard Charts ───────────────────────────────────────────────────
  var dashboardLineChart = null;
  var dashboardDonutChart = null;
  var dashboardActiveRange = '3M';
  var dashboardAllSnapshots = [];

  function filterSnapshotsByRange(snapshots, range) {
    var now = new Date();
    var cutoff = null;
    if (range === '1M') { cutoff = new Date(now); cutoff.setMonth(cutoff.getMonth() - 1); }
    else if (range === '3M') { cutoff = new Date(now); cutoff.setMonth(cutoff.getMonth() - 3); }
    else if (range === 'YTD') { cutoff = new Date(now.getFullYear(), 0, 1); }
    else if (range === '1Y') { cutoff = new Date(now); cutoff.setFullYear(cutoff.getFullYear() - 1); }
    if (!cutoff) return snapshots;
    return snapshots.filter(function (s) { return new Date(s.date) >= cutoff; });
  }

  function renderDashboardLineChart(snapshots) {
    var canvas = document.getElementById('dashboard-line-chart');
    var emptyEl = document.getElementById('dashboard-line-empty');
    if (!canvas) return;
    if (dashboardLineChart) { dashboardLineChart.destroy(); dashboardLineChart = null; }
    var filtered = filterSnapshotsByRange(snapshots, dashboardActiveRange);
    if (!filtered.length) {
      canvas.style.display = 'none';
      if (emptyEl) emptyEl.style.display = '';
      return;
    }
    if (emptyEl) emptyEl.style.display = 'none';
    canvas.style.display = '';
    var labels = filtered.map(function (s) { return s.date; });
    var values = filtered.map(function (s) { return parseFloat(s.total_value) || 0; });
    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var labelColor = isDark ? '#cecece' : '#6a6b6c';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    dashboardLineChart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Portfolio Value',
          data: values,
          borderColor: '#86C232',
          backgroundColor: 'rgba(134,194,50,0.1)',
          borderWidth: 2,
          pointRadius: filtered.length > 60 ? 0 : 3,
          pointHoverRadius: 5,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (c) { return ' ' + fmtCurrency(c.parsed.y); } } },
        },
        scales: {
          x: { ticks: { color: labelColor, font: { family: "'Geist', sans-serif", size: 12 }, maxTicksLimit: 8, maxRotation: 0 }, grid: { color: gridColor } },
          y: { ticks: { color: labelColor, font: { family: "'Geist', sans-serif", size: 12 }, callback: function (v) { return fmtCurrency(v); } }, grid: { color: gridColor } },
        },
      },
    });
  }

  function renderDashboardDonutChart(accounts) {
    var canvas = document.getElementById('dashboard-donut-chart');
    var emptyEl = document.getElementById('dashboard-donut-empty');
    if (!canvas) return;
    if (dashboardDonutChart) { dashboardDonutChart.destroy(); dashboardDonutChart = null; }

    var totals = { equity: 0, bond: 0, cash: 0 };
    accounts.forEach(function (a) {
      if (!a.holdings) return;
      a.holdings.forEach(function (h) {
        var type = (h.asset_detail && h.asset_detail.asset_type) || '';
        var val = parseFloat(h.current_value) || 0;
        if (type === 'equity') totals.equity += val;
        else if (type === 'bond') totals.bond += val;
        else if (type === 'cash') totals.cash += val;
        else totals.equity += val;
      });
    });

    var aLabels = ['Equity', 'Bonds', 'Cash'];
    var aValues = [totals.equity, totals.bond, totals.cash];
    var aColors = ['rgba(134,194,50,0.9)', 'rgba(134,194,50,0.48)', 'rgba(134,194,50,0.18)'];
    var fL = [], fV = [], fC = [];
    for (var i = 0; i < aLabels.length; i++) {
      if (aValues[i] > 0) { fL.push(aLabels[i]); fV.push(aValues[i]); fC.push(aColors[i]); }
    }

    if (fL.length === 0) {
      canvas.style.display = 'none';
      if (emptyEl) emptyEl.style.display = '';
      return;
    }
    if (emptyEl) emptyEl.style.display = 'none';
    canvas.style.display = '';

    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var lc = isDark ? '#cecece' : '#6a6b6c';
    dashboardDonutChart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: { labels: fL, datasets: [{ data: fV, backgroundColor: fC, borderWidth: 0, hoverOffset: 8 }] },
      options: {
        responsive: true, maintainAspectRatio: true, cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: lc, padding: 12, usePointStyle: true, pointStyle: 'circle', font: { family: "'Geist', sans-serif", size: 13 } } },
          tooltip: { callbacks: { label: function (c) { return c.label + ': ' + fmtCurrency(c.parsed); } } },
        },
      },
    });
  }

  // ── Data Loading: Dashboard ────────────────────────────────────────────
  async function loadDashboard() {
    try {
      var results = await Promise.all([
        apiFetch('/api/accounts/?page_size=100'),
        apiFetch('/api/snapshots/?page_size=365'),
        apiFetch('/api/holdings/?page_size=500'),
      ]);
      var accountsData = results[0];
      var snapshotsData = results[1];
      var holdingsData = results[2];
      if (!accountsData) return;
      var accounts = accountsData.results || accountsData;
      var snapshots = snapshotsData ? (snapshotsData.results || snapshotsData) : [];
      var holdings = holdingsData ? (holdingsData.results || holdingsData) : [];
      snapshots.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      dashboardAllSnapshots = snapshots;

      var holdingsByAccount = {};
      holdings.forEach(function (h) {
        if (!holdingsByAccount[h.account]) holdingsByAccount[h.account] = [];
        holdingsByAccount[h.account].push(h);
      });
      accounts.forEach(function (a) { a.holdings = holdingsByAccount[a.id] || []; });

      renderDashboardSummary(accounts, snapshots);
      renderDashboardLineChart(snapshots);
      renderDashboardDonutChart(accounts);
      loadAccountsIntoController(accounts, ctrlDashboardAccounts);
    } catch (err) { /* toast already shown */ }
  }

  function renderDashboardGreeting() {
    var el = document.getElementById('dashboard-greeting-text');
    var dateEl = document.getElementById('dashboard-greeting-date');
    if (!el) return;
    var firstName = (getSettings().firstName || '').trim();
    var fallback  = document.getElementById('profile-display-name') ? document.getElementById('profile-display-name').textContent : '';
    var greetName = firstName || fallback;
    var hour = new Date().getHours();
    var greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    el.textContent = greeting + (greetName ? ', ' + greetName : '') + '.';
    if (dateEl) {
      var now = new Date();
      dateEl.textContent = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    }
  }

  function trendBadge(diff, pct, sign, cls) {
    var arrow = diff >= 0
      ? '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>'
      : '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>';
    return '<div class="summary-card-trend ' + cls + '">' + arrow + sign + pct.toFixed(2) + '%</div>';
  }

  function renderDashboardSummary(accounts, snapshots) {
    var totalValue = 0;
    accounts.forEach(function (a) { totalValue += parseFloat(a.total_portfolio_value) || 0; });

    var changeValueHtml = '<span style="color:var(--text-faint)">\u2014</span>';
    var changeTrendHtml = '';
    var totalGLValue = '<span style="color:var(--text-faint)">\u2014</span>';
    var totalGLTrend = '';

    if (snapshots && snapshots.length >= 2) {
      var latest = parseFloat(snapshots[snapshots.length - 1].total_value) || 0;
      var prev   = parseFloat(snapshots[snapshots.length - 2].total_value) || 0;
      var diff   = latest - prev;
      var pct    = prev > 0 ? (diff / prev * 100) : 0;
      var sign   = diff >= 0 ? '+' : '';
      var cls    = diff >= 0 ? 'positive' : 'negative';
      changeValueHtml = '<span class="' + cls + '">' + sign + fmtCurrency(diff) + '</span>';
      changeTrendHtml = trendBadge(diff, pct, sign, cls);
    }

    renderDashboardGreeting();

    document.getElementById('dashboard-summary').innerHTML =
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Portfolio Value</div>' +
        '<div class="summary-card-value">' + fmtCurrency(totalValue) + '</div>' +
        '<div class="summary-card-sub">across ' + accounts.length + ' account' + (accounts.length !== 1 ? 's' : '') + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Change (last snapshot)</div>' +
        '<div class="summary-card-value">' + changeValueHtml + '</div>' +
        changeTrendHtml +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Accounts tracked</div>' +
        '<div class="summary-card-value">' + accounts.length + '</div>' +
        '<div class="summary-card-sub">investment accounts</div>' +
      '</div>';
  }

  document.querySelectorAll('#dashboard-range-btns .range-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('#dashboard-range-btns .range-btn').forEach(function (b) { b.classList.remove('active-range'); });
      btn.classList.add('active-range');
      dashboardActiveRange = btn.getAttribute('data-range');
      renderDashboardLineChart(dashboardAllSnapshots);
    });
  });

  function loadAccountsIntoController(accounts, ctrl) {
    var isDashboard = (ctrl === ctrlDashboardAccounts);
    var tableId = isDashboard ? 'table-dashboard-accounts' : 'table-accounts';
    var colSpan = isDashboard ? 5 : 6;

    if (accounts.length === 0) {
      ctrl.state.rows = [];
      var tbody = document.querySelector('#' + tableId + ' tbody');
      if (tbody) {
        var esIcon = '<path d="M19 21H5a2 2 0 01-2-2V7l5-4h11a2 2 0 012 2v14a2 2 0 01-2 2z"/><polyline points="9 3 9 9 15 9"/>';
        var esActions = isDashboard
          ? [{ label: 'Add your first account', id: 'es-add-account' }, { label: 'or import a CSV', href: 'import' }]
          : [{ label: 'Add your first account', id: 'es-add-account' }];
        tbody.innerHTML = '<tr class="empty-state-cell"><td colspan="' + colSpan + '">' +
          emptyStateHtml(esIcon, 'No accounts yet', 'Add an investment account to start tracking your portfolio.', esActions) +
          '</td></tr>';
        tbody.querySelector('[data-es-action="es-add-account"]') && tbody.querySelector('[data-es-action="es-add-account"]').addEventListener('click', function () {
          if (isDashboard) { switchView('accounts'); } else { openAccountModal(null); }
        });
        tbody.querySelectorAll('[data-es-nav]').forEach(function (btn) {
          btn.addEventListener('click', function () { switchView(btn.getAttribute('data-es-nav')); });
        });
      }
      return;
    }

    var rows = accounts.map(function (a) {
      var name     = a.account_name;
      var type     = (a.account_type || '').toUpperCase();
      var provider = a.provider || '—';
      var value    = fmtCurrency(a.total_portfolio_value);
      var date     = formatDate(a.created_at);

      var actionsHtml = isDashboard ? '' :
        '<td style="white-space:nowrap;">' +
          '<div class="row-actions">' +
            '<button class="btn-icon acc-edit-btn" data-id="' + a.id + '" data-name="' + escapeHtml(a.account_name) + '" data-type="' + escapeHtml(a.account_type || '') + '" data-provider="' + escapeHtml(a.provider || '') + '" data-currency="' + escapeHtml(a.currency || 'GBP') + '" title="Edit">' +
              '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
            '</button>' +
            '<button class="btn-icon btn-icon-danger acc-delete-btn" data-id="' + a.id + '" data-name="' + escapeHtml(a.account_name) + '" title="Delete">' +
              '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>' +
            '</button>' +
          '</div>' +
        '</td>';

      var html = '<tr class="clickable-row" data-account-id="' + a.id + '">';
      html += '<td>' + escapeHtml(name) + '</td>';
      html += '<td><span class="badge">' + escapeHtml(type) + '</span></td>';
      html += '<td class="text-muted">' + escapeHtml(provider) + '</td>';
      html += '<td class="text-right">' + value + '</td>';
      html += '<td class="text-muted">' + date + '</td>';
      html += actionsHtml;
      html += '</tr>';

      var cells = [name, type, provider, value, date];
      return { cells: cells, html: html };
    });

    ctrl.load(rows);

    // Mobile card list (hidden ≥768px via CSS; accounts already mapped above)
    var mobileCardContainerId = isDashboard ? 'mobile-cards-dashboard-accounts' : 'mobile-cards-accounts';
    renderMobileCards(mobileCardContainerId, accounts.map(function (a) {
      var initials = (a.account_name || '?').slice(0, 2).toUpperCase();
      return {
        icon: initials,
        name: a.account_name,
        badge: (a.account_type || '').toUpperCase(),
        badgeCls: '',
        sub: a.provider || '',
        value: fmtCurrency(a.total_portfolio_value),
        onClick: function () { loadAccountDetail(a.id); },
      };
    }));

    // Wire up edit/delete after load for the accounts view
    if (!isDashboard) {
      var table = document.getElementById(tableId);
      if (table) {
        table.querySelectorAll('.acc-edit-btn').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            openAccountModal({
              id: btn.getAttribute('data-id'),
              account_name: btn.getAttribute('data-name'),
              account_type: btn.getAttribute('data-type'),
              provider: btn.getAttribute('data-provider'),
              currency: btn.getAttribute('data-currency'),
            });
          });
        });
        table.querySelectorAll('.acc-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var id = btn.getAttribute('data-id');
            var name = btn.getAttribute('data-name');
            if (!confirm('Delete account "' + name + '"? This cannot be undone.')) return;
            apiFetch('/api/accounts/' + id + '/', { method: 'DELETE' }).then(function () {
              showToast('Account deleted', 'success');
              loadAccountsView();
            }).catch(function () {});
          });
        });
      }
    }
  }

  // ── Data Loading: Accounts View ────────────────────────────────────────
  async function loadAccountsView() {
    try {
      var data = await apiFetch('/api/accounts/?page_size=100');
      if (!data) return;
      var accounts = data.results || data;

      var totalValue = 0;
      accounts.forEach(function (a) { totalValue += parseFloat(a.total_portfolio_value) || 0; });

      document.getElementById('accounts-summary').innerHTML =
        '<div class="summary-card">' +
          '<div class="summary-card-label">Total Accounts</div>' +
          '<div class="summary-card-value">' + accounts.length + '</div>' +
        '</div>' +
        '<div class="summary-card">' +
          '<div class="summary-card-label">Total Value</div>' +
          '<div class="summary-card-value">' + fmtCurrency(totalValue) + '</div>' +
        '</div>';

      loadAccountsIntoController(accounts, ctrlAccounts);
    } catch (err) { /* toast already shown */ }
  }

  // ── Data Loading: Assets ───────────────────────────────────────────────
  async function loadAssets() {
    try {
      var data = await apiFetch('/api/assets/?page_size=100');
      if (!data) return;
      var assets = data.results || data;

      if (assets.length === 0) {
        ctrlAssets.state.rows = [];
        var assetIcon = '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>';
        document.getElementById('assets-table-body').innerHTML = '<tr class="empty-state-cell"><td colspan="5">' +
          emptyStateHtml(assetIcon, 'No assets in registry', 'Assets are added automatically when you import transactions or create holdings.', []) +
          '</td></tr>';
        return;
      }

      var rows = assets.map(function (a) {
        var symbol = a.symbol;
        var name   = a.name;
        var type   = a.asset_type;
        var price  = a.asset_type === 'cash' ? '1.00' : (a.asset_type === 'bond' ? (a.face_value || '0.00') : a.last_price);
        var priceFormatted = fmtCurrency(price);
        var updated = a.price_updated_at ? formatDate(a.price_updated_at) : '—';
        var badgeClass = 'badge-' + type;

        var html = '<tr>';
        html += '<td><strong>' + escapeHtml(symbol) + '</strong></td>';
        html += '<td>' + escapeHtml(name) + '</td>';
        html += '<td><span class="badge ' + badgeClass + '">' + escapeHtml(type) + '</span></td>';
        html += '<td class="text-right">' + priceFormatted + '</td>';
        html += '<td class="text-muted">' + updated + '</td>';
        html += '</tr>';

        return { cells: [symbol, name, type, priceFormatted, updated], html: html };
      });

      ctrlAssets.load(rows);

      // Mobile card list for assets
      renderMobileCards('mobile-cards-assets', assets.map(function (a) {
        var price = a.asset_type === 'cash' ? '1.00' : (a.asset_type === 'bond' ? (a.face_value || '0.00') : a.last_price);
        return {
          icon: (a.symbol || '?').slice(0, 3).toUpperCase(),
          name: a.name,
          badge: a.asset_type,
          badgeCls: 'badge-' + a.asset_type,
          sub: a.price_updated_at ? formatDate(a.price_updated_at) : '',
          value: fmtCurrency(price),
          onClick: function () {},
        };
      }));
    } catch (err) { /* toast already shown */ }
  }

  // ── Data Loading: Account Detail ───────────────────────────────────────
  async function loadAccountDetail(accountId) {
    currentAccountId = accountId;
    document.querySelectorAll('.view').forEach(function (v) { v.hidden = true; });
    document.getElementById('view-account-detail').hidden = false;
    document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });

    document.getElementById('account-detail-name').textContent = 'Loading...';
    document.getElementById('account-detail-meta').textContent = '';
    document.getElementById('portfolio-summary-cards').innerHTML =
      '<div class="summary-card"><div class="loading-cell"><div class="spinner"></div></div></div>';
    document.getElementById('holdings-table-body').innerHTML =
      '<tr><td colspan="10" class="loading-cell"><div class="spinner"></div></td></tr>';
    document.getElementById('transactions-table-body').innerHTML =
      '<tr><td colspan="7" class="loading-cell"><div class="spinner"></div></td></tr>';
    document.getElementById('dividends-table-body').innerHTML =
      '<tr><td colspan="6" class="loading-cell"><div class="spinner"></div></td></tr>';

    // Reset search fields
    if (holdingsSearchInput) holdingsSearchInput.value = '';
    holdingsState.query = '';
    holdingsState.sortCol = -1;
    holdingsState.sortDir = 'asc';
    var txSearch = document.getElementById('search-transactions');
    if (txSearch) txSearch.value = '';

    try {
      var detailPromise  = apiFetch('/api/accounts/' + accountId + '/');
      var summaryPromise = apiFetch('/api/accounts/' + accountId + '/portfolio-summary/');
      var targetPromise  = apiFetch('/api/target-allocations/?account=' + accountId);
      var dividendPromise = apiFetch('/api/dividends/?page_size=100');
      var results = await Promise.all([detailPromise, summaryPromise, targetPromise, dividendPromise]);
      var account = results[0];
      var summary = results[1];
      var targets = results[2];
      var dividends = results[3];
      if (!account || !summary) return;
      renderAccountDetail(account, summary);
      renderTargetAllocationChart(summary, targets);
      renderDividendHistory(dividends, accountId);
      loadRecurringContributions(accountId);
    } catch (err) { /* toast already shown */ }
  }

  function renderAccountDetail(account, summary) {
    // Header
    document.getElementById('account-detail-name').textContent = account.account_name;
    var metaParts = [];
    if (account.account_type) metaParts.push(account.account_type.toUpperCase());
    if (account.provider) metaParts.push(account.provider);
    document.getElementById('account-detail-meta').textContent = metaParts.join(' · ');

    // Summary cards
    var totalValue = parseFloat(summary.total_value) || 0;
    var totalGL    = parseFloat(summary.total_gain_loss) || 0;
    var glClass    = totalGL >= 0 ? 'positive' : 'negative';
    var glPrefix   = totalGL >= 0 ? '+' : '';

    document.getElementById('portfolio-summary-cards').innerHTML =
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Value</div>' +
        '<div class="summary-card-value">' + fmtCurrency(totalValue) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">Total Gain/Loss</div>' +
        '<div class="summary-card-value ' + glClass + '">' + glPrefix + fmtCurrency(totalGL) + '</div>' +
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

    renderAllocationChart(summary);
    renderHoldings(account.holdings || [], totalValue);
    renderTransactions(account.recent_transactions || []);
  }

  function renderAllocationChart(summary) {
    var canvas = document.getElementById('allocation-chart');
    var ctx = canvas.getContext('2d');

    if (allocationChart) {
      allocationChart.destroy();
    }

    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var labelColor = isDark ? '#cecece' : '#6a6b6c';

    var equity = parseFloat(summary.equity_allocation_pct) || 0;
    var bond   = parseFloat(summary.bond_allocation_pct)   || 0;
    var cash   = parseFloat(summary.cash_allocation_pct)   || 0;

    var canvasHeight = canvas.height || 300;
    function makeGradient(from, to) {
      var g = ctx.createLinearGradient(0, 0, 0, canvasHeight);
      g.addColorStop(0, from);
      g.addColorStop(1, to);
      return g;
    }
    var equityFill = makeGradient('rgba(134,194,50,1)',    'rgba(111,168,42,1)');
    var bondFill   = makeGradient('rgba(134,194,50,0.48)', 'rgba(111,168,42,0.48)');
    var cashFill   = makeGradient('rgba(134,194,50,0.18)', 'rgba(111,168,42,0.18)');

    allocationChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Equity', 'Bonds', 'Cash'],
        datasets: [{
          data: [equity, bond, cash],
          backgroundColor: [equityFill, bondFill, cashFill],
          borderWidth: 0,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: labelColor,
              padding: 16,
              usePointStyle: true,
              pointStyle: 'circle',
              pointStyleWidth: 10,
              font: { family: "'Geist', sans-serif", size: 13 },
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

  // ── Holdings: Grouped by Asset Type ───────────────────────────────────
  var ASSET_TYPE_ORDER = ['equity', 'bond', 'cash'];
  var ASSET_TYPE_LABELS = { equity: 'Equity', bond: 'Bonds', cash: 'Cash' };

  function renderHoldings(holdings, totalValue) {
    if (holdings.length === 0) {
      holdingsState.groups = [];
      document.getElementById('holdings-table-body').innerHTML =
        '<tr><td colspan="9" class="loading-cell" style="color:var(--text-muted)">No holdings</td></tr>';
      return;
    }

    // Group holdings by asset_type
    var grouped = {};
    holdings.forEach(function (h) {
      var type = (h.asset_detail && h.asset_detail.asset_type) || h.asset_type || 'equity';
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(h);
    });

    var orderedTypes = ASSET_TYPE_ORDER.filter(function (t) { return grouped[t]; });
    Object.keys(grouped).forEach(function (t) {
      if (orderedTypes.indexOf(t) === -1) orderedTypes.push(t);
    });

    holdingsState.groups = orderedTypes.map(function (type) {
      var typeHoldings = grouped[type];
      var label = ASSET_TYPE_LABELS[type] || (type.charAt(0).toUpperCase() + type.slice(1));
      var badgeClass = 'badge-' + type;

      var groupValue = 0;
      typeHoldings.forEach(function (h) { groupValue += parseFloat(h.current_value) || 0; });
      var groupAllocPct = totalValue > 0 ? ((groupValue / totalValue) * 100) : 0;

      var headerHtml =
        '<tr class="holdings-group-header">' +
          '<td colspan="10">' +
            '<span class="badge ' + badgeClass + '">' + escapeHtml(label) + '</span>' +
          '</td>' +
        '</tr>';

      var rows = typeHoldings.map(function (h) {
        var asset      = h.asset_detail || {};
        var symbol     = asset.symbol || '';
        var name       = asset.name || '';
        var assetType  = asset.asset_type || type;
        var qty        = formatNumber(h.quantity, 4);
        var avgCost    = fmtCurrency(h.average_cost);
        var currentVal = parseFloat(h.current_value) || 0;
        var gainLoss   = parseFloat(h.gain_loss) || 0;
        var glClass    = gainLoss >= 0 ? 'text-positive' : 'text-negative';
        var glPrefix   = gainLoss >= 0 ? '+' : '';
        var allocPct   = totalValue > 0 ? ((currentVal / totalValue) * 100) : 0;
        var valFmt     = fmtCurrency(currentVal);
        var glFmt      = glPrefix + fmtCurrency(gainLoss);
        var allocFmt   = formatPct(allocPct);
        var notes      = h.notes || '';

        var html = '<tr>';
        html += '<td><strong>' + escapeHtml(symbol) + '</strong></td>';
        html += '<td>' + escapeHtml(name) + '</td>';
        html += '<td><span class="badge badge-' + escapeHtml(assetType) + '">' + escapeHtml(assetType) + '</span></td>';
        html += '<td class="text-right">' + qty + '</td>';
        html += '<td class="text-right">' + avgCost + '</td>';
        html += '<td class="text-right">' + valFmt + '</td>';
        html += '<td class="text-right ' + glClass + '">' + glFmt + '</td>';
        html += '<td class="text-right">' + allocFmt + '</td>';
        html += '<td class="notes-cell"><span class="notes-display" data-holding-id="' + h.id + '" title="Click to edit">' + escapeHtml(notes || 'Click to add notes') + '</span></td>';
        html += '<td style="white-space:nowrap;">' +
          '<div class="row-actions">' +
            '<button class="btn-icon holding-edit-btn" data-id="' + h.id + '" data-asset="' + (asset.id || '') + '" data-qty="' + escapeHtml(h.quantity || '') + '" data-avg="' + escapeHtml(h.average_buy_price || h.average_cost || '') + '" data-notes="' + escapeHtml(notes) + '" title="Edit">' +
              '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
            '</button>' +
            '<button class="btn-icon btn-icon-danger holding-delete-btn" data-id="' + h.id + '" data-symbol="' + escapeHtml(symbol) + '" title="Delete">' +
              '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>' +
            '</button>' +
          '</div>' +
        '</td>';
        html += '</tr>';

        return {
          cells: [symbol, name, assetType, qty, avgCost, valFmt, glFmt, allocFmt],
          html: html,
        };
      });

      var subtotalHtml =
        '<tr class="holdings-group-subtotal">' +
          '<td colspan="4"></td>' +
          '<td class="text-right" style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;">Subtotal</td>' +
          '<td class="text-right">' + fmtCurrency(groupValue) + '</td>' +
          '<td></td>' +
          '<td class="text-right">' + formatPct(groupAllocPct) + '</td>' +
          '<td colspan="2"></td>' +
        '</tr>';

      return { type: type, headerHtml: headerHtml, rows: rows, subtotalHtml: subtotalHtml };
    });

    renderGroupedHoldings();
  }

  // ── Recent Transactions ────────────────────────────────────────────────
  function renderTransactions(transactions) {
    if (transactions.length === 0) {
      ctrlTransactions.state.rows = [];
      document.getElementById('transactions-table-body').innerHTML =
        '<tr><td colspan="7" class="loading-cell" style="color:var(--text-muted)">No transactions</td></tr>';
      return;
    }

    var rows = transactions.map(function (t) {
      var asset      = t.asset_detail || {};
      var dateStr    = formatDate(t.executed_at);
      var txType     = (t.transaction_type || '').toUpperCase();
      var symbol     = asset.symbol || '';
      var qty        = formatNumber(t.quantity, 4);
      var price      = fmtCurrency(t.price);
      var totalVal   = fmtCurrency(t.total_value);
      var badgeClass = 'badge-' + (t.transaction_type || 'buy');

      var html = '<tr>';
      html += '<td>' + dateStr + '</td>';
      html += '<td><span class="badge ' + badgeClass + '">' + escapeHtml(txType) + '</span></td>';
      html += '<td><strong>' + escapeHtml(symbol) + '</strong></td>';
      html += '<td class="text-right">' + qty + '</td>';
      html += '<td class="text-right">' + price + '</td>';
      html += '<td class="text-right">' + totalVal + '</td>';
      html += '<td style="white-space:nowrap;">' +
        '<div class="row-actions">' +
          '<button class="btn-icon tx-edit-btn" data-id="' + t.id + '" data-asset="' + (asset.id || '') + '" data-type="' + escapeHtml(t.transaction_type || '') + '" data-qty="' + escapeHtml(t.quantity || '') + '" data-price="' + escapeHtml(t.price || '') + '" data-date="' + escapeHtml((t.executed_at || '').slice(0, 10)) + '" title="Edit">' +
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          '</button>' +
          '<button class="btn-icon btn-icon-danger tx-delete-btn" data-id="' + t.id + '" data-symbol="' + escapeHtml(symbol) + '" title="Delete">' +
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>' +
          '</button>' +
        '</div>' +
      '</td>';
      html += '</tr>';

      return { cells: [dateStr, txType, symbol, qty, price, totalVal], html: html };
    });

    ctrlTransactions.load(rows);

    // Wire up edit/delete after load
    var txTbody = document.getElementById('transactions-table-body');
    if (txTbody) {
      txTbody.querySelectorAll('.tx-edit-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          openTransactionModal({
            id: btn.getAttribute('data-id'),
            asset: btn.getAttribute('data-asset'),
            transaction_type: btn.getAttribute('data-type'),
            quantity: btn.getAttribute('data-qty'),
            price: btn.getAttribute('data-price'),
            executed_at: btn.getAttribute('data-date'),
          });
        });
      });
      txTbody.querySelectorAll('.tx-delete-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          var id = btn.getAttribute('data-id');
          var symbol = btn.getAttribute('data-symbol');
          if (!confirm('Delete transaction for "' + symbol + '"? This cannot be undone.')) return;
          apiFetch('/api/transactions/' + id + '/', { method: 'DELETE' }).then(function () {
            showToast('Transaction deleted', 'success');
            if (currentAccountId) loadAccountDetail(currentAccountId);
          }).catch(function () {});
        });
      });
    }
  }

  // ── Inline Notes Editing ────────────────────────────────────────────────
  function startNotesEdit(span) {
    var holdingId = span.getAttribute('data-holding-id');
    var currentText = span.textContent === 'Click to add notes' ? '' : span.textContent;
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'notes-edit-input';
    input.value = currentText;
    input.style.cssText = 'width:100%;padding:4px 8px;font-size:13px;font-family:var(--font-family);background:var(--input-bg);color:var(--text-primary);border:1px solid var(--accent);border-radius:4px;outline:none;';
    span.replaceWith(input);
    input.focus();

    function save() {
      var newVal = input.value.trim();
      apiFetch('/api/holdings/' + holdingId + '/', {
        method: 'PATCH',
        body: JSON.stringify({ notes: newVal }),
      }).then(function () {
        var newSpan = document.createElement('span');
        newSpan.className = 'notes-display';
        newSpan.setAttribute('data-holding-id', holdingId);
        newSpan.setAttribute('title', 'Click to edit');
        newSpan.textContent = newVal || 'Click to add notes';
        input.replaceWith(newSpan);
        newSpan.addEventListener('click', function () { startNotesEdit(newSpan); });
        showToast('Notes saved', 'success');
      }).catch(function () {
        var newSpan = document.createElement('span');
        newSpan.className = 'notes-display';
        newSpan.setAttribute('data-holding-id', holdingId);
        newSpan.setAttribute('title', 'Click to edit');
        newSpan.textContent = currentText || 'Click to add notes';
        input.replaceWith(newSpan);
        newSpan.addEventListener('click', function () { startNotesEdit(newSpan); });
      });
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { input.blur(); }
      if (e.key === 'Escape') {
        var newSpan = document.createElement('span');
        newSpan.className = 'notes-display';
        newSpan.setAttribute('data-holding-id', holdingId);
        newSpan.setAttribute('title', 'Click to edit');
        newSpan.textContent = currentText || 'Click to add notes';
        input.replaceWith(newSpan);
        newSpan.addEventListener('click', function () { startNotesEdit(newSpan); });
      }
    });
  }

  // ── Target Allocation vs Actual Chart ─────────────────────────────────
  function renderTargetAllocationChart(summary, targetsData) {
    var canvas = document.getElementById('target-allocation-chart');
    var emptyMsg = document.getElementById('target-allocation-empty');
    var targets = (targetsData && targetsData.results) ? targetsData.results : (targetsData || []);

    if (targetAllocationChart) {
      targetAllocationChart.destroy();
      targetAllocationChart = null;
    }

    if (!targets || targets.length === 0) {
      canvas.style.display = 'none';
      emptyMsg.hidden = false;
      return;
    }

    canvas.style.display = '';
    emptyMsg.hidden = true;

    var assetTypes = ['equity', 'bond', 'cash'];
    var labels = ['Equity', 'Bonds', 'Cash'];
    var actualData = [
      parseFloat(summary.equity_allocation_pct) || 0,
      parseFloat(summary.bond_allocation_pct) || 0,
      parseFloat(summary.cash_allocation_pct) || 0,
    ];

    var targetMap = {};
    targets.forEach(function (t) { targetMap[t.asset_type] = parseFloat(t.target_percentage) || 0; });
    var targetData = assetTypes.map(function (at) { return targetMap[at] || 0; });

    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var labelColor = isDark ? '#cecece' : '#6a6b6c';

    var ctx = canvas.getContext('2d');
    targetAllocationChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Actual %',
            data: actualData,
            backgroundColor: ['rgba(134,194,50,0.85)', 'rgba(134,194,50,0.48)', 'rgba(134,194,50,0.18)'],
            borderRadius: 4,
          },
          {
            label: 'Target %',
            data: targetData,
            backgroundColor: ['rgba(134,194,50,0.2)', 'rgba(232,197,71,0.2)', 'rgba(236,234,229,0.12)'],
            borderWidth: 2,
            borderColor: ['#86C232', '#E8C547', '#ECEAE5'],
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: labelColor,
              font: { family: "'Geist', sans-serif", size: 13 },
              usePointStyle: true,
              pointStyleWidth: 8,
              padding: 16,
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: { color: labelColor, font: { family: "'Geist', sans-serif", size: 12 }, callback: function (v) { return v + '%'; } },
            grid: { color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' },
          },
          x: {
            ticks: { color: labelColor, font: { family: "'Geist', sans-serif", size: 12 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  // ── Dividend History ──────────────────────────────────────────────────
  function renderDividendHistory(dividendsData, accountId) {
    var tbody = document.getElementById('dividends-table-body');
    var allDividends = (dividendsData && dividendsData.results) ? dividendsData.results : (dividendsData || []);

    // Filter to only dividends for this account
    var dividends = allDividends.filter(function (d) {
      return d.holding_detail && String(d.holding_detail.account_id) === String(accountId);
    });

    if (dividends.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-cell" style="color:var(--text-muted)">No dividends recorded</td></tr>';
      return;
    }

    var html = '';
    dividends.forEach(function (d) {
      var detail = d.holding_detail || {};
      html += '<tr>';
      html += '<td>' + formatDate(d.payment_date) + '</td>';
      html += '<td>' + formatDate(d.ex_date) + '</td>';
      html += '<td><strong>' + escapeHtml(detail.symbol || '') + '</strong></td>';
      html += '<td>' + escapeHtml(detail.name || '') + '</td>';
      html += '<td class="text-right">' + fmtCurrency(d.per_share_amount) + '</td>';
      html += '<td class="text-right">' + fmtCurrency(d.amount) + '</td>';
      html += '</tr>';
    });

    tbody.innerHTML = html;
  }

  // ── Watchlist ──────────────────────────────────────────────────────────
  async function loadWatchlist() {
    var tbody = document.getElementById('watchlist-table-body');
    tbody.innerHTML = '<tr><td colspan="8" class="loading-cell"><div class="spinner"></div></td></tr>';

    try {
      var data = await apiFetch('/api/watchlist/?page_size=100');
      if (!data) return;
      var items = data.results || data;
      renderWatchlist(items);
    } catch (err) { /* toast shown */ }
  }

  function renderWatchlist(items) {
    var tbody = document.getElementById('watchlist-table-body');

    if (items.length === 0) {
      var wlIcon = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
      tbody.innerHTML = '<tr class="empty-state-cell"><td colspan="8">' +
        emptyStateHtml(wlIcon, 'Your watchlist is empty', 'Track assets you\'re interested in and get alerted when they hit your target price.', [{ label: 'Add your first watched asset', id: 'es-add-watchlist' }]) +
        '</td></tr>';
      var esBtn = tbody.querySelector('[data-es-action="es-add-watchlist"]');
      if (esBtn) esBtn.addEventListener('click', function () {
        var addBtn = document.getElementById('add-watchlist-btn');
        if (addBtn) addBtn.click();
      });
      return;
    }

    var html = '';
    items.forEach(function (item) {
      var asset = item.asset_detail || {};
      var currentPrice = parseFloat(asset.last_price) || 0;
      var targetPrice = item.target_price ? parseFloat(item.target_price) : null;
      var signal = '';
      if (targetPrice !== null && targetPrice > 0) {
        if (currentPrice >= targetPrice) {
          signal = '<span class="text-positive" title="At or above target">&#9650; Above</span>';
        } else {
          signal = '<span class="text-negative" title="Below target">&#9660; Below</span>';
        }
      } else {
        signal = '<span style="color:var(--text-muted)">—</span>';
      }

      html += '<tr>';
      html += '<td><strong>' + escapeHtml(asset.symbol || '') + '</strong></td>';
      html += '<td>' + escapeHtml(asset.name || '') + '</td>';
      html += '<td><span class="badge badge-' + escapeHtml(asset.asset_type || 'equity') + '">' + escapeHtml(asset.asset_type || '') + '</span></td>';
      html += '<td class="text-right">' + fmtCurrency(currentPrice) + '</td>';
      html += '<td class="text-right">' + (targetPrice !== null ? fmtCurrency(targetPrice) : '—') + '</td>';
      html += '<td class="text-center">' + signal + '</td>';
      html += '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(item.notes || '') + '</td>';
      html += '<td><button class="btn btn-secondary btn-sm wl-remove-btn" data-id="' + item.id + '" title="Remove">✕</button></td>';
      html += '</tr>';
    });

    tbody.innerHTML = html;

    // Wire up remove buttons
    tbody.querySelectorAll('.wl-remove-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var id = btn.getAttribute('data-id');
        try {
          await apiFetch('/api/watchlist/' + id + '/', { method: 'DELETE' });
          showToast('Removed from watchlist', 'success');
          loadWatchlist();
        } catch (err) { /* toast shown */ }
      });
    });
  }

  // Watchlist add form
  var addWlBtn = document.getElementById('add-watchlist-btn');
  var addWlForm = document.getElementById('add-watchlist-form');
  var wlCancelBtn = document.getElementById('wl-cancel-btn');
  var wlSaveBtn = document.getElementById('wl-save-btn');

  if (addWlBtn) {
    addWlBtn.addEventListener('click', async function () {
      addWlForm.hidden = !addWlForm.hidden;
      if (!addWlForm.hidden) {
        // Load assets into dropdown
        var select = document.getElementById('wl-asset-id');
        select.innerHTML = '<option value="">Loading...</option>';
        try {
          var data = await apiFetch('/api/assets/?page_size=100');
          var assets = (data && data.results) || data || [];
          select.innerHTML = '<option value="">Select asset...</option>';
          assets.forEach(function (a) {
            select.innerHTML += '<option value="' + a.id + '">' + escapeHtml(a.symbol + ' — ' + a.name) + '</option>';
          });
        } catch (err) { select.innerHTML = '<option value="">Error loading</option>'; }
      }
    });
  }

  if (wlCancelBtn) {
    wlCancelBtn.addEventListener('click', function () { addWlForm.hidden = true; });
  }

  if (wlSaveBtn) {
    wlSaveBtn.addEventListener('click', async function () {
      var assetId = document.getElementById('wl-asset-id').value;
      var targetPrice = document.getElementById('wl-target-price').value;
      var notes = document.getElementById('wl-notes').value;

      if (!assetId) { showToast('Select an asset', 'error'); return; }

      var body = { asset: parseInt(assetId) };
      if (targetPrice) body.target_price = targetPrice;
      if (notes) body.notes = notes;

      try {
        await apiFetch('/api/watchlist/', { method: 'POST', body: JSON.stringify(body) });
        showToast('Added to watchlist', 'success');
        addWlForm.hidden = true;
        document.getElementById('wl-target-price').value = '';
        document.getElementById('wl-notes').value = '';
        loadWatchlist();
      } catch (err) { /* toast shown */ }
    });
  }

  // ── Net Worth ─────────────────────────────────────────────────────────
  var netWorthChart = null;

  async function loadNetWorth() {
    var summaryEl = document.getElementById('net-worth-summary');
    var niaTbody  = document.getElementById('nia-table-body');
    var liabilityTbody = document.getElementById('liability-table-body');
    if (summaryEl) summaryEl.innerHTML = '<div class="summary-card"><div class="loading-cell"><div class="spinner"></div></div></div>';
    if (niaTbody)  niaTbody.innerHTML  = '<tr><td colspan="5" class="loading-cell"><div class="spinner"></div></td></tr>';
    if (liabilityTbody) liabilityTbody.innerHTML = '<tr><td colspan="5" class="loading-cell"><div class="spinner"></div></td></tr>';
    try {
      var results = await Promise.all([
        apiFetch('/api/net-worth/'),
        apiFetch('/api/net-worth-accounts/?page_size=100'),
        apiFetch('/api/liabilities/?page_size=100'),
      ]);
      var summaryData = results[0];
      var niaData = results[1];
      var liabilityData = results[2];
      if (!summaryData) return;
      renderNetWorthSummary(summaryData);
      renderNetWorthChart(summaryData);
      renderNiaTable((niaData && niaData.results) ? niaData.results : (niaData || []));
      renderLiabilityTable((liabilityData && liabilityData.results) ? liabilityData.results : (liabilityData || []));
    } catch (err) { /* toast shown */ }
  }

  function renderNetWorthSummary(data) {
    var el = document.getElementById('net-worth-summary');
    if (!el) return;
    el.innerHTML =
      '<div class="summary-card"><div class="summary-card-label">Total Net Worth</div><div class="summary-card-value">' + formatCurrency(parseFloat(data.total_net_worth) || 0) + '</div></div>' +
      '<div class="summary-card"><div class="summary-card-label">Investment Total</div><div class="summary-card-value">' + formatCurrency(parseFloat(data.investment_total) || 0) + '</div></div>' +
      '<div class="summary-card"><div class="summary-card-label">Non-Investment Total</div><div class="summary-card-value">' + formatCurrency(parseFloat(data.non_investment_total) || 0) + '</div></div>' +
      '<div class="summary-card"><div class="summary-card-label">Total Liabilities</div><div class="summary-card-value text-negative">-' + formatCurrency(parseFloat(data.liabilities_total) || 0) + '</div></div>';
  }

  function renderNetWorthChart(data) {
    var canvas = document.getElementById('net-worth-chart');
    if (!canvas) return;
    if (netWorthChart) { netWorthChart.destroy(); netWorthChart = null; }
    var breakdown = data.breakdown || [];
    var byType = data.investment_by_asset_type || {};
    var equityVal = parseFloat(byType.equity) || 0;
    var bondVal = parseFloat(byType.bond) || 0;
    var cashVal = parseFloat(byType.cash) || 0;
    var debtVal = 0, savVal = 0, propVal = 0, otherVal = 0;
    breakdown.forEach(function (item) {
      if (item.category === 'non_investment') {
        var b = parseFloat(item.balance) || 0;
        if (item.type === 'debt') debtVal += b;
        else if (item.type === 'savings') savVal += b;
        else if (item.type === 'property') propVal += b;
        else otherVal += b;
      }
    });
    var aL = ['Equity','Bonds','Cash','Savings','Property','Other','Debt'];
    var aV = [equityVal, bondVal, cashVal, savVal, propVal, otherVal, debtVal];
    var aC = ['rgba(134,194,50,0.85)','rgba(232,197,71,0.85)','rgba(236,234,229,0.85)','rgba(86,180,233,0.85)','rgba(217,119,6,0.85)','rgba(156,163,175,0.85)','rgba(255,99,99,0.85)'];
    var fL = [], fV = [], fC = [];
    for (var i = 0; i < aL.length; i++) { if (aV[i] > 0) { fL.push(aL[i]); fV.push(aV[i]); fC.push(aC[i]); } }
    if (fL.length < 2) {
      canvas.style.display = 'none';
      var emptyMsg = document.getElementById('net-worth-chart-empty');
      if (!emptyMsg) {
        emptyMsg = document.createElement('div');
        emptyMsg.id = 'net-worth-chart-empty';
        emptyMsg.style.cssText = 'padding:40px 20px;text-align:center;color:var(--text-muted);font-size:14px;';
        emptyMsg.textContent = 'Add accounts with varied asset types or net-worth accounts to see a breakdown.';
        canvas.parentNode.insertBefore(emptyMsg, canvas);
      }
      emptyMsg.style.display = '';
      return;
    }
    var emptyMsgExisting = document.getElementById('net-worth-chart-empty');
    if (emptyMsgExisting) emptyMsgExisting.style.display = 'none';
    canvas.style.display = '';
    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var lc = isDark ? '#cecece' : '#6a6b6c';
    netWorthChart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: { labels: fL, datasets: [{ data: fV, backgroundColor: fC, borderColor: isDark ? '#1e2124' : '#f0ede8', borderWidth: 3, hoverOffset: 8 }] },
      options: {
        responsive: true, maintainAspectRatio: true, cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: lc, padding: 14, usePointStyle: true, pointStyle: 'circle', font: { family: "'Geist', sans-serif", size: 13 } } },
          tooltip: { callbacks: { label: function (c) { return c.label + ': ' + formatCurrency(c.parsed); } } },
        },
      },
    });
  }

  function renderNiaTable(items) {
    var tbody = document.getElementById('nia-table-body');
    if (!tbody) return;
    if (!items.length) {
      var niaIcon = '<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>';
      tbody.innerHTML = '<tr class="empty-state-cell"><td colspan="5">' +
        emptyStateHtml(niaIcon, 'No non-investment accounts', 'Track savings, property, and debt alongside your portfolio for a complete net worth picture.', [{ label: 'Add a non-investment account', id: 'es-add-nia' }]) +
        '</td></tr>';
      var esBtn = tbody.querySelector('[data-es-action="es-add-nia"]');
      if (esBtn) esBtn.addEventListener('click', function () {
        var addBtn = document.getElementById('add-nia-btn');
        if (addBtn) addBtn.click();
      });
      return;
    }
    var html = '';
    items.forEach(function (item) {
      var balClass = item.account_type === 'debt' ? 'text-negative' : '';
      html += '<tr><td><strong>' + escapeHtml(item.name) + '</strong></td>';
      html += '<td><span class="badge">' + escapeHtml(item.account_type) + '</span></td>';
      html += '<td class="text-right ' + balClass + '">' + formatCurrency(parseFloat(item.balance) || 0) + '</td>';
      html += '<td class="text-muted">' + escapeHtml(item.notes || '') + '</td>';
      html += '<td style="white-space:nowrap;"><button class="btn btn-secondary btn-sm" style="margin-right:4px;" data-nia-edit="' + item.id + '">Edit</button><button class="btn btn-secondary btn-sm" style="color:var(--danger);" data-nia-delete="' + item.id + '">Delete</button></td></tr>';
    });
    tbody.innerHTML = html;
    tbody.querySelectorAll('[data-nia-edit]').forEach(function (b) { b.addEventListener('click', function () { niaEditItem(+b.getAttribute('data-nia-edit')); }); });
    tbody.querySelectorAll('[data-nia-delete]').forEach(function (b) { b.addEventListener('click', function () { niaDeleteItem(+b.getAttribute('data-nia-delete')); }); });
  }

  function niaEditItem(id) {
    apiFetch('/api/net-worth-accounts/' + id + '/').then(function (item) {
      if (!item) return;
      document.getElementById('nia-name').value = item.name;
      document.getElementById('nia-type').value = item.account_type;
      document.getElementById('nia-balance').value = item.balance;
      document.getElementById('nia-notes').value = item.notes || '';
      document.getElementById('nia-edit-id').value = item.id;
      var wrap = document.getElementById('nia-form-wrap'); if (wrap) wrap.hidden = false;
    }).catch(function () {});
  }
  function niaDeleteItem(id) {
    if (!confirm('Delete this account?')) return;
    apiFetch('/api/net-worth-accounts/' + id + '/', { method: 'DELETE' }).then(function () { showToast('Account deleted', 'success'); loadNetWorth(); }).catch(function () {});
  }

  var niaFormWrap = document.getElementById('nia-form-wrap');
  var addNiaBtn   = document.getElementById('add-nia-btn');
  if (addNiaBtn) addNiaBtn.addEventListener('click', function () {
    ['nia-name','nia-balance','nia-notes','nia-edit-id'].forEach(function (id) { var e = document.getElementById(id); if (e) e.value = ''; });
    var t = document.getElementById('nia-type'); if (t) t.value = 'savings';
    if (niaFormWrap) niaFormWrap.hidden = !niaFormWrap.hidden;
  });
  var niaCancelBtn = document.getElementById('nia-cancel-btn');
  if (niaCancelBtn) niaCancelBtn.addEventListener('click', function () { if (niaFormWrap) niaFormWrap.hidden = true; });
  var niaSaveBtn = document.getElementById('nia-save-btn');
  if (niaSaveBtn) niaSaveBtn.addEventListener('click', async function () {
    var name = (document.getElementById('nia-name').value || '').trim();
    var type = document.getElementById('nia-type').value;
    var balance = document.getElementById('nia-balance').value;
    var notes = (document.getElementById('nia-notes').value || '').trim();
    var editId = document.getElementById('nia-edit-id').value;
    if (!name) { showToast('Account name is required', 'error'); return; }
    if (!balance) { showToast('Balance is required', 'error'); return; }
    var method = editId ? 'PATCH' : 'POST';
    var path = editId ? '/api/net-worth-accounts/' + editId + '/' : '/api/net-worth-accounts/';
    try {
      await apiFetch(path, { method: method, body: JSON.stringify({ name: name, account_type: type, balance: balance, notes: notes }) });
      showToast(editId ? 'Account updated' : 'Account added', 'success');
      if (niaFormWrap) niaFormWrap.hidden = true;
      loadNetWorth();
    } catch (err) { /* toast shown */ }
  });

  // ── Liabilities ───────────────────────────────────────────────────────
  function renderLiabilityTable(items) {
    var tbody = document.getElementById('liability-table-body');
    if (!tbody) return;
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="5" class="loading-cell" style="color:var(--text-muted)">No liabilities added yet</td></tr>'; return; }
    var html = '';
    items.forEach(function (item) {
      html += '<tr><td><strong>' + escapeHtml(item.name) + '</strong></td>';
      html += '<td><span class="badge">' + escapeHtml(item.liability_type) + '</span></td>';
      html += '<td class="text-right text-negative">' + formatCurrency(parseFloat(item.balance) || 0) + '</td>';
      html += '<td class="text-muted">' + escapeHtml(item.notes || '') + '</td>';
      html += '<td style="white-space:nowrap;"><button class="btn btn-secondary btn-sm" style="margin-right:4px;" data-liab-edit="' + item.id + '">Edit</button><button class="btn btn-secondary btn-sm" style="color:var(--danger);" data-liab-delete="' + item.id + '">Delete</button></td></tr>';
    });
    tbody.innerHTML = html;
    tbody.querySelectorAll('[data-liab-edit]').forEach(function (b) { b.addEventListener('click', function () { liabEditItem(+b.getAttribute('data-liab-edit')); }); });
    tbody.querySelectorAll('[data-liab-delete]').forEach(function (b) { b.addEventListener('click', function () { liabDeleteItem(+b.getAttribute('data-liab-delete')); }); });
  }

  function liabEditItem(id) {
    apiFetch('/api/liabilities/' + id + '/').then(function (item) {
      if (!item) return;
      document.getElementById('liability-name').value = item.name;
      document.getElementById('liability-type').value = item.liability_type;
      document.getElementById('liability-balance').value = item.balance;
      document.getElementById('liability-notes').value = item.notes || '';
      document.getElementById('liability-edit-id').value = item.id;
      var wrap = document.getElementById('liability-form-wrap'); if (wrap) wrap.hidden = false;
    }).catch(function () {});
  }
  function liabDeleteItem(id) {
    if (!confirm('Delete this liability?')) return;
    apiFetch('/api/liabilities/' + id + '/', { method: 'DELETE' }).then(function () { showToast('Liability deleted', 'success'); loadNetWorth(); }).catch(function () {});
  }

  var liabilityFormWrap = document.getElementById('liability-form-wrap');
  var addLiabilityBtn   = document.getElementById('add-liability-btn');
  if (addLiabilityBtn) addLiabilityBtn.addEventListener('click', function () {
    ['liability-name', 'liability-balance', 'liability-notes', 'liability-edit-id'].forEach(function (id) { var e = document.getElementById(id); if (e) e.value = ''; });
    var t = document.getElementById('liability-type'); if (t) t.value = 'mortgage';
    if (liabilityFormWrap) liabilityFormWrap.hidden = !liabilityFormWrap.hidden;
  });
  var liabilityCancelBtn = document.getElementById('liability-cancel-btn');
  if (liabilityCancelBtn) liabilityCancelBtn.addEventListener('click', function () { if (liabilityFormWrap) liabilityFormWrap.hidden = true; });
  var liabilitySaveBtn = document.getElementById('liability-save-btn');
  if (liabilitySaveBtn) liabilitySaveBtn.addEventListener('click', async function () {
    var name = (document.getElementById('liability-name').value || '').trim();
    var type = document.getElementById('liability-type').value;
    var balance = document.getElementById('liability-balance').value;
    var notes = (document.getElementById('liability-notes').value || '').trim();
    var editId = document.getElementById('liability-edit-id').value;
    if (!name) { showToast('Name is required', 'error'); return; }
    if (!balance) { showToast('Balance is required', 'error'); return; }
    var method = editId ? 'PATCH' : 'POST';
    var apiPath = editId ? '/api/liabilities/' + editId + '/' : '/api/liabilities/';
    try {
      await apiFetch(apiPath, { method: method, body: JSON.stringify({ name: name, liability_type: type, balance: balance, notes: notes }) });
      showToast(editId ? 'Liability updated' : 'Liability added', 'success');
      if (liabilityFormWrap) liabilityFormWrap.hidden = true;
      loadNetWorth();
    } catch (err) { /* toast shown */ }
  });

  // ── Goals ─────────────────────────────────────────────────────────────
  async function loadGoals() {
    var grid = document.getElementById('goals-grid');
    if (grid) grid.innerHTML = '<div class="loading-cell"><div class="spinner"></div></div>';
    try {
      var data = await apiFetch('/api/goals/?page_size=100');
      if (!data) return;
      renderGoals(data.results ? data.results : data);
    } catch (err) { /* toast shown */ }
  }

  function renderGoals(goals) {
    var grid = document.getElementById('goals-grid');
    if (!grid) return;
    if (!goals.length) {
      var goalIcon = '<path d="M12 2a10 10 0 100 20A10 10 0 0012 2z"/><path d="M12 8v4l3 3"/>';
      grid.innerHTML = emptyStateHtml(goalIcon, 'No goals yet', 'Set a savings target and track your progress toward it over time.', [{ label: 'Create a goal', id: 'es-add-goal' }]);
      var esBtn = grid.querySelector('[data-es-action="es-add-goal"]');
      if (esBtn) esBtn.addEventListener('click', function () {
        var addBtn = document.getElementById('add-goal-btn');
        if (addBtn) addBtn.click();
      });
      return;
    }
    var html = '<div class="goals-grid">';
    goals.forEach(function (g) {
      var current = parseFloat(g.current_value) || 0;
      var pct = Math.min(parseFloat(g.progress_pct) || 0, 100);
      var badgeClass = g.on_track ? 'goal-badge-green' : (pct > 50 ? 'goal-badge-amber' : 'goal-badge-red');
      html += '<div class="goal-card">';
      html += '<div class="goal-card-header"><span class="goal-card-name">' + escapeHtml(g.name) + '</span><span class="goal-badge ' + badgeClass + '">' + (g.on_track ? 'On Track' : 'Behind') + '</span></div>';
      html += '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">' + (g.account_name ? escapeHtml(g.account_name) : 'Portfolio-wide') + '</div>';
      html += '<div style="margin-top:10px;font-size:13px;color:var(--text-secondary);">' + formatCurrency(current) + ' / ' + formatCurrency(parseFloat(g.target_amount) || 0) + '</div>';
      html += '<div class="goal-progress-bar-wrap"><div class="goal-progress-bar" style="width:' + pct.toFixed(1) + '%"></div></div>';
      html += '<div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;color:var(--text-muted);"><span>' + pct.toFixed(1) + '% complete</span><span>' + g.days_remaining + ' days · ' + formatDate(g.target_date) + '</span></div>';
      if (g.notes) html += '<div style="margin-top:8px;font-size:12px;color:var(--text-muted);">' + escapeHtml(g.notes) + '</div>';
      html += '<div style="margin-top:12px;display:flex;gap:6px;"><button class="btn btn-secondary btn-sm" data-goal-edit="' + g.id + '">Edit</button><button class="btn btn-secondary btn-sm" style="color:var(--danger);" data-goal-delete="' + g.id + '">Delete</button></div>';
      html += '</div>';
    });
    html += '</div>';
    grid.innerHTML = html;
    grid.querySelectorAll('[data-goal-edit]').forEach(function (b) { b.addEventListener('click', function () { goalEditItem(+b.getAttribute('data-goal-edit')); }); });
    grid.querySelectorAll('[data-goal-delete]').forEach(function (b) { b.addEventListener('click', function () { goalDeleteItem(+b.getAttribute('data-goal-delete')); }); });
  }

  function goalEditItem(id) {
    apiFetch('/api/goals/' + id + '/').then(function (g) {
      if (!g) return;
      document.getElementById('goal-name').value = g.name;
      document.getElementById('goal-account').value = g.account || '';
      document.getElementById('goal-target').value = g.target_amount;
      document.getElementById('goal-date').value = g.target_date;
      document.getElementById('goal-notes').value = g.notes || '';
      document.getElementById('goal-edit-id').value = g.id;
      var wrap = document.getElementById('goal-form-wrap'); if (wrap) wrap.hidden = false;
    }).catch(function () {});
  }
  function goalDeleteItem(id) {
    if (!confirm('Delete this goal?')) return;
    apiFetch('/api/goals/' + id + '/', { method: 'DELETE' }).then(function () { showToast('Goal deleted', 'success'); loadGoals(); }).catch(function () {});
  }

  var goalFormWrap = document.getElementById('goal-form-wrap');
  var addGoalBtn   = document.getElementById('add-goal-btn');
  if (addGoalBtn) addGoalBtn.addEventListener('click', async function () {
    var select = document.getElementById('goal-account');
    if (select) {
      select.innerHTML = '<option value="">Portfolio-wide</option>';
      try {
        var d = await apiFetch('/api/accounts/?page_size=100');
        var accs = (d && d.results) || d || [];
        accs.forEach(function (a) { select.innerHTML += '<option value="' + a.id + '">' + escapeHtml(a.account_name) + '</option>'; });
      } catch (e) { /* ignore */ }
    }
    ['goal-name','goal-target','goal-date','goal-notes','goal-edit-id'].forEach(function (id) { var e = document.getElementById(id); if (e) e.value = ''; });
    if (goalFormWrap) goalFormWrap.hidden = !goalFormWrap.hidden;
  });
  var goalCancelBtn = document.getElementById('goal-cancel-btn');
  if (goalCancelBtn) goalCancelBtn.addEventListener('click', function () { if (goalFormWrap) goalFormWrap.hidden = true; });
  var goalSaveBtn = document.getElementById('goal-save-btn');
  if (goalSaveBtn) goalSaveBtn.addEventListener('click', async function () {
    var name = (document.getElementById('goal-name').value || '').trim();
    var account = document.getElementById('goal-account').value;
    var target = document.getElementById('goal-target').value;
    var date = document.getElementById('goal-date').value;
    var notes = (document.getElementById('goal-notes').value || '').trim();
    var editId = document.getElementById('goal-edit-id').value;
    if (!name)   { showToast('Goal name is required', 'error'); return; }
    if (!target) { showToast('Target amount is required', 'error'); return; }
    if (!date)   { showToast('Target date is required', 'error'); return; }
    var body = { name: name, target_amount: target, target_date: date, notes: notes };
    if (account) body.account = parseInt(account, 10);
    var method = editId ? 'PATCH' : 'POST';
    var path = editId ? '/api/goals/' + editId + '/' : '/api/goals/';
    try {
      await apiFetch(path, { method: method, body: JSON.stringify(body) });
      showToast(editId ? 'Goal updated' : 'Goal created', 'success');
      if (goalFormWrap) goalFormWrap.hidden = true;
      loadGoals();
    } catch (err) { /* toast shown */ }
  });

  // ── Recurring Contributions ───────────────────────────────────────────
  var contributionsChart = null;

  function loadRecurringContributions(accountId) {
    var tbody = document.getElementById('rc-table-body');
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="loading-cell"><div class="spinner"></div></td></tr>';
    Promise.all([
      apiFetch('/api/recurring-contributions/?page_size=100'),
      apiFetch('/api/contribution-history/?account=' + accountId),
    ]).then(function (results) {
      var rcData = results[0], histData = results[1];
      var rcItems = (rcData && rcData.results) ? rcData.results : (rcData || []);
      rcItems = rcItems.filter(function (r) { return String(r.account) === String(accountId); });
      renderRcTable(rcItems);
      renderContributionsChart(histData || []);
    }).catch(function () {});
  }

  function renderRcTable(items) {
    var tbody = document.getElementById('rc-table-body');
    if (!tbody) return;
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="7" class="loading-cell" style="color:var(--text-muted)">No recurring contributions set up</td></tr>'; return; }
    var html = '';
    items.forEach(function (item) {
      var statusBadge = item.is_active ? '<span class="badge badge-buy">Active</span>' : '<span class="badge" style="color:var(--text-muted)">Paused</span>';
      html += '<tr><td class="text-right"><strong>' + formatCurrency(item.amount) + '</strong></td>';
      html += '<td>' + escapeHtml(item.frequency) + '</td>';
      html += '<td>' + formatDate(item.start_date) + '</td>';
      html += '<td>' + formatDate(item.next_due_date) + '</td>';
      html += '<td>' + statusBadge + '</td>';
      html += '<td class="text-muted">' + escapeHtml(item.notes || '') + '</td>';
      html += '<td style="white-space:nowrap;"><button class="btn btn-secondary btn-sm" style="margin-right:4px;" data-rc-edit="' + item.id + '">Edit</button><button class="btn btn-secondary btn-sm" style="color:var(--danger);" data-rc-delete="' + item.id + '">Delete</button></td></tr>';
    });
    tbody.innerHTML = html;
    tbody.querySelectorAll('[data-rc-edit]').forEach(function (b) { b.addEventListener('click', function () { rcEditItem(+b.getAttribute('data-rc-edit')); }); });
    tbody.querySelectorAll('[data-rc-delete]').forEach(function (b) { b.addEventListener('click', function () { rcDeleteItem(+b.getAttribute('data-rc-delete')); }); });
  }

  function renderContributionsChart(historyData) {
    var canvas = document.getElementById('contributions-chart');
    if (!canvas) return;
    if (contributionsChart) { contributionsChart.destroy(); contributionsChart = null; }
    if (!historyData || !historyData.length) { canvas.style.display = 'none'; return; }
    canvas.style.display = '';
    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var lc = isDark ? '#cecece' : '#6a6b6c';
    contributionsChart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: { labels: historyData.map(function (d) { return d.month; }), datasets: [{ label: 'Contributed (£)', data: historyData.map(function (d) { return parseFloat(d.total_contributed) || 0; }), backgroundColor: 'rgba(134,194,50,0.75)', borderRadius: 4 }] },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return fmtCurrency(c.parsed.y); } } } },
        scales: {
          y: { beginAtZero: true, ticks: { color: lc, font: { family: "'Geist', sans-serif", size: 12 }, callback: function (v) { return fmtCurrency(v); } }, grid: { color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' } },
          x: { ticks: { color: lc, font: { family: "'Geist', sans-serif", size: 12 } }, grid: { display: false } },
        },
      },
    });
  }

  function rcEditItem(id) {
    apiFetch('/api/recurring-contributions/' + id + '/').then(function (item) {
      if (!item) return;
      document.getElementById('rc-amount').value = item.amount;
      document.getElementById('rc-frequency').value = item.frequency;
      document.getElementById('rc-start-date').value = item.start_date;
      document.getElementById('rc-notes').value = item.notes || '';
      document.getElementById('rc-edit-id').value = item.id;
      var wrap = document.getElementById('rc-form-wrap'); if (wrap) wrap.hidden = false;
    }).catch(function () {});
  }
  function rcDeleteItem(id) {
    if (!confirm('Delete this contribution?')) return;
    apiFetch('/api/recurring-contributions/' + id + '/', { method: 'DELETE' }).then(function () {
      showToast('Contribution deleted', 'success');
      if (currentAccountId) loadRecurringContributions(currentAccountId);
    }).catch(function () {});
  }

  var rcFormWrap = document.getElementById('rc-form-wrap');
  var addRcBtn   = document.getElementById('add-rc-btn');
  if (addRcBtn) addRcBtn.addEventListener('click', function () {
    ['rc-amount','rc-notes','rc-edit-id'].forEach(function (id) { var e = document.getElementById(id); if (e) e.value = ''; });
    var f = document.getElementById('rc-frequency'); if (f) f.value = 'monthly';
    var s = document.getElementById('rc-start-date'); if (s) s.value = new Date().toISOString().split('T')[0];
    if (rcFormWrap) rcFormWrap.hidden = !rcFormWrap.hidden;
  });
  var rcCancelBtn = document.getElementById('rc-cancel-btn');
  if (rcCancelBtn) rcCancelBtn.addEventListener('click', function () { if (rcFormWrap) rcFormWrap.hidden = true; });
  var rcSaveBtn = document.getElementById('rc-save-btn');
  if (rcSaveBtn) rcSaveBtn.addEventListener('click', async function () {
    var amount = document.getElementById('rc-amount').value;
    var frequency = document.getElementById('rc-frequency').value;
    var startDate = document.getElementById('rc-start-date').value;
    var notes = (document.getElementById('rc-notes').value || '').trim();
    var editId = document.getElementById('rc-edit-id').value;
    if (!amount)    { showToast('Amount is required', 'error'); return; }
    if (!startDate) { showToast('Start date is required', 'error'); return; }
    if (!currentAccountId) { showToast('No account selected', 'error'); return; }
    var body = { account: parseInt(currentAccountId, 10), amount: amount, frequency: frequency, start_date: startDate, next_due_date: startDate, notes: notes, is_active: true };
    var method = editId ? 'PATCH' : 'POST';
    var path = editId ? '/api/recurring-contributions/' + editId + '/' : '/api/recurring-contributions/';
    try {
      await apiFetch(path, { method: method, body: JSON.stringify(body) });
      showToast(editId ? 'Contribution updated' : 'Contribution set up', 'success');
      if (rcFormWrap) rcFormWrap.hidden = true;
      loadRecurringContributions(currentAccountId);
    } catch (err) { /* toast shown */ }
  });

  // ── CSV Import ────────────────────────────────────────────────────────
  var csvDropZone = document.getElementById('csv-drop-zone');
  var csvFileInput = document.getElementById('csv-file-input');
  var csvUploadBtn = document.getElementById('csv-upload-btn');
  var csvFileName = document.getElementById('csv-file-name');
  var csvResults = document.getElementById('csv-results');
  var csvBrokerSelect = document.getElementById('csv-broker-select');
  var csvColumnsHint = document.getElementById('csv-columns-hint');
  var csvSampleLinkWrap = document.getElementById('csv-sample-link-wrap');
  var csvSampleLink = document.getElementById('csv-sample-link');
  var selectedFile = null;

  var BROKER_HINTS = {
    generic:     'Upload a CSV file with columns: <code style="background:var(--bg-surface-2);padding:2px 6px;border-radius:3px;font-size:12px;">symbol, quantity, price, date, type, account_id</code>',
    trading212:  'Trading 212 activity export columns: <code style="background:var(--bg-surface-2);padding:2px 6px;border-radius:3px;font-size:12px;">Action, Time, ISIN, Ticker, Name, No.\u00a0of\u00a0shares, Price\u00a0/\u00a0share, Currency, Total, \u2026</code>',
    vanguard_uk: 'Vanguard UK preset is coming soon.',
    aj_bell:     'AJ Bell preset is coming soon.',
  };

  function updateBrokerUI() {
    var broker = csvBrokerSelect ? csvBrokerSelect.value : 'generic';
    if (csvColumnsHint) csvColumnsHint.innerHTML = BROKER_HINTS[broker] || BROKER_HINTS.generic;
    if (csvSampleLinkWrap && csvSampleLink) {
      csvSampleLinkWrap.style.display = 'block';
      csvSampleLink.href = API_BASE + '/api/import/sample/' + broker + '/';
      csvSampleLink.download = 'sample_' + broker + '.csv';
    }
  }

  function initImportView() {
    selectedFile = null;
    if (csvUploadBtn) csvUploadBtn.disabled = true;
    if (csvFileName) { csvFileName.hidden = true; csvFileName.textContent = ''; }
    if (csvFileInput) csvFileInput.value = '';
    if (csvResults) {
      csvResults.hidden = false;
      csvResults.innerHTML =
        '<div class="empty-tip">' +
          '<span class="empty-tip-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></span>' +
          '<span class="empty-tip-text">Choose a broker above for a sample file — the download link will appear once you select a format.</span>' +
        '</div>';
    }
    updateBrokerUI();
  }

  if (csvBrokerSelect) {
    csvBrokerSelect.addEventListener('change', updateBrokerUI);
  }

  if (csvDropZone) {
    csvDropZone.addEventListener('click', function () { csvFileInput.click(); });

    csvDropZone.addEventListener('dragover', function (e) {
      e.preventDefault();
      csvDropZone.classList.add('drag-over');
    });

    csvDropZone.addEventListener('dragleave', function () {
      csvDropZone.classList.remove('drag-over');
    });

    csvDropZone.addEventListener('drop', function (e) {
      e.preventDefault();
      csvDropZone.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) {
        selectFile(e.dataTransfer.files[0]);
      }
    });
  }

  if (csvFileInput) {
    csvFileInput.addEventListener('change', function () {
      if (csvFileInput.files.length > 0) selectFile(csvFileInput.files[0]);
    });
  }

  function selectFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please select a CSV file', 'error');
      return;
    }
    selectedFile = file;
    csvFileName.textContent = 'Selected: ' + file.name;
    csvFileName.hidden = false;
    csvUploadBtn.disabled = false;
    csvResults.hidden = true;
  }

  if (csvUploadBtn) {
    csvUploadBtn.addEventListener('click', async function () {
      if (!selectedFile) return;
      csvUploadBtn.disabled = true;
      csvUploadBtn.textContent = 'Uploading...';

      var broker = csvBrokerSelect ? csvBrokerSelect.value : 'generic';
      var formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('broker', broker);

      try {
        var resp = await fetch(API_BASE + '/api/import/', {
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: formData,
        });
        var data = await resp.json();

        var html = '<div style="padding:16px;border-radius:6px;background:var(--bg-surface-2);border:1px solid var(--border-color);">';
        html += '<h3 style="margin:0 0 8px;font-size:14px;color:var(--text-primary);">Import Results</h3>';
        html += '<div style="display:flex;gap:16px;margin-bottom:8px;">';
        html += '<span class="text-positive" style="font-weight:600;">' + (data.imported || 0) + ' imported</span>';
        html += '<span class="text-negative" style="font-weight:600;">' + (data.skipped || 0) + ' skipped</span>';
        html += '</div>';

        if (data.errors && data.errors.length > 0) {
          html += '<details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--text-muted);">Show errors (' + data.errors.length + ')</summary>';
          html += '<ul style="margin:8px 0 0;padding-left:20px;font-size:12px;color:var(--text-secondary);">';
          data.errors.forEach(function (err) { html += '<li>' + escapeHtml(err) + '</li>'; });
          html += '</ul></details>';
        }

        html += '</div>';
        csvResults.innerHTML = html;
        csvResults.hidden = false;

        if (data.imported > 0) {
          showToast(data.imported + ' transaction(s) imported', 'success');
        }
      } catch (err) {
        showToast('Import failed — check the file format', 'error');
      }

      csvUploadBtn.disabled = false;
      csvUploadBtn.textContent = 'Upload & Import';
    });
  }

  // ── Performance View ───────────────────────────────────────────────────
  var performanceLineChart = null;

  async function loadPerformanceView() {
    var summaryEl = document.getElementById('performance-summary');
    var emptyEl = document.getElementById('performance-empty');
    var canvas = document.getElementById('performance-chart');

    if (summaryEl) {
      summaryEl.innerHTML =
        '<div class="summary-card"><div class="loading-cell"><div class="spinner"></div></div></div>';
    }

    try {
      var data = await apiFetch('/api/snapshots/?page_size=365');
      if (!data) return;
      var snapshots = (data.results || data);
      snapshots.sort(function (a, b) { return a.date < b.date ? -1 : 1; });

      renderPerformanceSummary(snapshots);

      if (!snapshots.length) {
        if (canvas) canvas.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'block';
        return;
      }

      if (canvas) canvas.style.display = '';
      if (emptyEl) emptyEl.style.display = 'none';
      renderPerformanceChart(snapshots);
    } catch (err) { /* toast shown */ }
  }

  function renderPerformanceSummary(snapshots) {
    var summaryEl = document.getElementById('performance-summary');
    if (!summaryEl) return;

    if (!snapshots.length) {
      summaryEl.innerHTML =
        '<div class="summary-card"><div class="summary-card-label">No snapshots yet</div>' +
        '<div class="summary-card-value">—</div></div>';
      return;
    }

    var latest = snapshots[snapshots.length - 1];
    var currentVal = parseFloat(latest.total_value) || 0;

    // Value 30 days ago
    var thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    var snap30 = null;
    for (var i = snapshots.length - 1; i >= 0; i--) {
      if (new Date(snapshots[i].date) <= thirtyDaysAgo) { snap30 = snapshots[i]; break; }
    }
    var val30 = snap30 ? (parseFloat(snap30.total_value) || 0) : null;
    var change30 = val30 !== null ? currentVal - val30 : null;
    var changePct30 = (val30 !== null && val30 > 0) ? (change30 / val30 * 100) : null;

    // Start of year
    var yearStart = new Date(new Date().getFullYear(), 0, 1);
    var snapYTD = null;
    for (var j = snapshots.length - 1; j >= 0; j--) {
      if (new Date(snapshots[j].date) <= yearStart) { snapYTD = snapshots[j]; break; }
    }
    var valYTD = snapYTD ? (parseFloat(snapYTD.total_value) || 0) : null;
    var changeYTD = valYTD !== null ? currentVal - valYTD : null;
    var changeYTDPct = (valYTD !== null && valYTD > 0) ? (changeYTD / valYTD * 100) : null;

    function fmtChange(val, pct) {
      if (val === null) return '—';
      var sign = val >= 0 ? '+' : '';
      var cls = val >= 0 ? 'positive' : 'negative';
      var pctStr = pct !== null ? ' (' + sign + pct.toFixed(1) + '%)' : '';
      return '<span class="' + cls + '">' + sign + fmtCurrency(val) + pctStr + '</span>';
    }

    summaryEl.innerHTML =
      '<div class="summary-card">' +
        '<div class="summary-card-label">Current Value</div>' +
        '<div class="summary-card-value">' + fmtCurrency(currentVal) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">30-Day Change</div>' +
        '<div class="summary-card-value">' + fmtChange(change30, changePct30) + '</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-label">YTD Change</div>' +
        '<div class="summary-card-value">' + fmtChange(changeYTD, changeYTDPct) + '</div>' +
      '</div>';
  }

  function renderPerformanceChart(snapshots) {
    var canvas = document.getElementById('performance-chart');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');

    if (performanceLineChart) {
      performanceLineChart.destroy();
      performanceLineChart = null;
    }

    var labels = snapshots.map(function (s) { return s.date; });
    var values = snapshots.map(function (s) { return parseFloat(s.total_value) || 0; });
    var isDark = document.documentElement.getAttribute('data-theme') !== 'dark';
    var labelColor = isDark ? '#cecece' : '#6a6b6c';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

    performanceLineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Portfolio Value (£)',
          data: values,
          borderColor: '#86C232',
          backgroundColor: 'rgba(134,194,50,0.1)',
          borderWidth: 2,
          pointRadius: snapshots.length > 60 ? 0 : 3,
          pointHoverRadius: 5,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return ' ' + fmtCurrency(context.parsed.y);
              },
            },
          },
        },
        scales: {
          x: {
            ticks: { color: labelColor, font: { family: "'Geist', sans-serif", size: 12 }, maxTicksLimit: 8, maxRotation: 0 },
            grid: { color: gridColor },
          },
          y: {
            ticks: {
              color: labelColor,
              font: { family: "'Geist', sans-serif", size: 12 },
              callback: function (v) { return fmtCurrency(v); },
            },
            grid: { color: gridColor },
          },
        },
      },
    });
  }

  // Wire up Take Snapshot button
  var takeSnapshotBtn = document.getElementById('take-snapshot-btn');
  if (takeSnapshotBtn) {
    takeSnapshotBtn.addEventListener('click', async function () {
      takeSnapshotBtn.disabled = true;
      takeSnapshotBtn.textContent = 'Taking snapshot...';
      try {
        await apiFetch('/api/snapshots/take/', { method: 'POST', body: JSON.stringify({}) });
        showToast('Snapshot taken successfully', 'success');
        loadPerformanceView();
      } catch (err) {
        showToast('Could not take snapshot', 'error');
      }
      takeSnapshotBtn.disabled = false;
      takeSnapshotBtn.textContent = 'Take Snapshot';
    });
  }

  // ── Send Monthly Summary Email ─────────────────────────────────────────
  var sendSummaryBtn = document.getElementById('send-summary-btn');
  if (sendSummaryBtn) {
    sendSummaryBtn.addEventListener('click', async function () {
      sendSummaryBtn.disabled = true;
      try {
        await apiFetch('/api/auth/send-monthly-summary/', { method: 'POST', body: JSON.stringify({}) });
        showToast('Monthly summary email sent', 'success');
      } catch (err) {
        showToast('Failed to send summary email', 'error');
      }
      sendSummaryBtn.disabled = false;
    });
  }

  // ── Modal Utilities ───────────────────────────────────────────────────
  function openModal(id) {
    var el = document.getElementById(id);
    if (el) { el.hidden = false; }
  }
  function closeModal(id) {
    var el = document.getElementById(id);
    if (el) { el.hidden = true; }
  }

  // Close on overlay click or close/cancel buttons
  document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });
  document.querySelectorAll('.modal-close-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var modalId = btn.getAttribute('data-modal');
      if (modalId) closeModal(modalId);
    });
  });
  document.querySelectorAll('.modal-footer .btn-secondary[data-modal]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      closeModal(btn.getAttribute('data-modal'));
    });
  });

  // ── Modal: Add / Edit Account ──────────────────────────────────────────
  var addAccBtn = document.getElementById('add-account-btn');
  if (addAccBtn) {
    addAccBtn.addEventListener('click', function () { openAccountModal(null); });
  }

  function openAccountModal(account) {
    document.getElementById('modal-account-title').textContent = account ? 'Edit Account' : 'Add Account';
    document.getElementById('acc-name').value = account ? account.account_name : '';
    document.getElementById('acc-type').value = account ? (account.account_type || 'ISA') : 'ISA';
    document.getElementById('acc-provider').value = account ? (account.provider || '') : '';
    document.getElementById('acc-currency').value = account ? (account.currency || 'GBP') : 'GBP';
    document.getElementById('acc-edit-id').value = account ? account.id : '';
    openModal('modal-account');
    setTimeout(function () {
      var nameField = document.getElementById('acc-name');
      if (nameField) nameField.focus();
    }, 50);
  }

  document.getElementById('modal-account-save').addEventListener('click', async function () {
    var name = document.getElementById('acc-name').value.trim();
    if (!name) { showToast('Account name is required', 'error'); return; }

    var body = {
      account_name: name,
      account_type: document.getElementById('acc-type').value,
      provider: document.getElementById('acc-provider').value.trim() || null,
      currency: document.getElementById('acc-currency').value,
    };

    var editId = document.getElementById('acc-edit-id').value;
    try {
      if (editId) {
        await apiFetch('/api/accounts/' + editId + '/', { method: 'PATCH', body: JSON.stringify(body) });
        showToast('Account updated', 'success');
      } else {
        await apiFetch('/api/accounts/', { method: 'POST', body: JSON.stringify(body) });
        showToast('Account created', 'success');
      }
      closeModal('modal-account');
      loadAccountsView();
    } catch (err) { /* toast already shown */ }
  });

  // ── Modal: Add / Edit Holding ──────────────────────────────────────────
  var addHoldingBtn = document.getElementById('add-holding-btn');
  if (addHoldingBtn) {
    addHoldingBtn.addEventListener('click', function () { openHoldingModal(null); });
  }

  async function populateAssetSelect(selectId, selectedAssetId) {
    var select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">Loading assets...</option>';
    try {
      var data = await apiFetch('/api/assets/?page_size=200');
      var assets = (data && data.results) || data || [];
      select.innerHTML = '<option value="">Select asset...</option>';
      assets.forEach(function (a) {
        var opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.symbol + ' — ' + a.name;
        if (String(a.id) === String(selectedAssetId)) opt.selected = true;
        select.appendChild(opt);
      });
    } catch (err) {
      select.innerHTML = '<option value="">Error loading assets</option>';
    }
  }

  function openHoldingModal(holding) {
    document.getElementById('modal-holding-title').textContent = holding ? 'Edit Holding' : 'Add Holding';
    document.getElementById('holding-qty').value = holding ? (holding.quantity || '') : '';
    document.getElementById('holding-avg-price').value = holding ? (holding.average_buy_price || '') : '';
    document.getElementById('holding-notes').value = holding ? (holding.notes || '') : '';
    document.getElementById('holding-edit-id').value = holding ? holding.id : '';
    populateAssetSelect('holding-asset', holding ? holding.asset : null);
    openModal('modal-holding');
  }

  document.getElementById('modal-holding-save').addEventListener('click', async function () {
    var assetId = document.getElementById('holding-asset').value;
    var qty = document.getElementById('holding-qty').value;
    if (!assetId) { showToast('Select an asset', 'error'); return; }
    if (!qty || parseFloat(qty) <= 0) { showToast('Enter a valid quantity', 'error'); return; }
    if (!currentAccountId) { showToast('No account selected', 'error'); return; }

    var body = {
      account: parseInt(currentAccountId),
      asset: parseInt(assetId),
      quantity: qty,
      average_buy_price: document.getElementById('holding-avg-price').value || '0',
      notes: document.getElementById('holding-notes').value.trim() || null,
    };

    var editId = document.getElementById('holding-edit-id').value;
    try {
      if (editId) {
        await apiFetch('/api/holdings/' + editId + '/', { method: 'PATCH', body: JSON.stringify(body) });
        showToast('Holding updated', 'success');
      } else {
        await apiFetch('/api/holdings/', { method: 'POST', body: JSON.stringify(body) });
        showToast('Holding added', 'success');
      }
      closeModal('modal-holding');
      loadAccountDetail(currentAccountId);
    } catch (err) { /* toast already shown */ }
  });

  // ── Modal: Add / Edit Transaction ──────────────────────────────────────
  var addTxBtn = document.getElementById('add-transaction-btn');
  if (addTxBtn) {
    addTxBtn.addEventListener('click', function () { openTransactionModal(null); });
  }

  function openTransactionModal(tx) {
    document.getElementById('modal-transaction-title').textContent = tx ? 'Edit Transaction' : 'Add Transaction';
    document.getElementById('tx-type').value = tx ? (tx.transaction_type || 'buy') : 'buy';
    document.getElementById('tx-qty').value = tx ? (tx.quantity || '') : '';
    document.getElementById('tx-price').value = tx ? (tx.price || '') : '';
    document.getElementById('tx-date').value = tx ? (tx.executed_at || '') : new Date().toISOString().slice(0, 10);
    document.getElementById('tx-edit-id').value = tx ? tx.id : '';
    populateAssetSelect('tx-asset', tx ? tx.asset : null);
    openModal('modal-transaction');
  }

  document.getElementById('modal-transaction-save').addEventListener('click', async function () {
    var assetId = document.getElementById('tx-asset').value;
    var qty = document.getElementById('tx-qty').value;
    var price = document.getElementById('tx-price').value;
    var date = document.getElementById('tx-date').value;
    if (!assetId) { showToast('Select an asset', 'error'); return; }
    if (!qty || parseFloat(qty) <= 0) { showToast('Enter a valid quantity', 'error'); return; }
    if (!price || parseFloat(price) < 0) { showToast('Enter a valid price', 'error'); return; }
    if (!currentAccountId) { showToast('No account selected', 'error'); return; }

    var body = {
      account: parseInt(currentAccountId),
      asset: parseInt(assetId),
      transaction_type: document.getElementById('tx-type').value,
      quantity: qty,
      price: price,
      executed_at: date,
    };

    var editId = document.getElementById('tx-edit-id').value;
    try {
      if (editId) {
        await apiFetch('/api/transactions/' + editId + '/', { method: 'PATCH', body: JSON.stringify(body) });
        showToast('Transaction updated', 'success');
      } else {
        await apiFetch('/api/transactions/', { method: 'POST', body: JSON.stringify(body) });
        showToast('Transaction recorded', 'success');
      }
      closeModal('modal-transaction');
      loadAccountDetail(currentAccountId);
    } catch (err) { /* toast already shown */ }
  });

  // ── Nametag ────────────────────────────────────────────────────────────
  function setNametag(username) {
    // Topbar nametag
    var profileAvatar = document.getElementById('profile-avatar');
    var profileName   = document.getElementById('profile-display-name');
    var roleEl        = document.getElementById('user-job-title');
    var savedPhoto    = localStorage.getItem('pd-avatar-photo');

    if (profileAvatar) {
      if (savedPhoto) {
        profileAvatar.textContent = '';
        profileAvatar.style.backgroundImage = 'url(' + savedPhoto + ')';
      } else {
        var s3 = getSettings();
        var initials = ([s3.firstName || '', s3.lastName || ''].map(function(p){return p.trim();}).filter(Boolean).join(' ') || username).trim();
        var parts = initials.split(' ').filter(Boolean);
        var avatarText = parts.length >= 2
          ? parts[0][0].toUpperCase() + parts[parts.length - 1][0].toUpperCase()
          : initials.charAt(0).toUpperCase();
        profileAvatar.textContent = avatarText;
        profileAvatar.style.backgroundImage = '';
      }
    }
    var s2 = getSettings();
    var fullName = [s2.firstName || '', s2.lastName || ''].map(function(p){return p.trim();}).filter(Boolean).join(' ');
    var displayName = fullName || username;
    if (profileName) profileName.textContent = displayName;

    if (roleEl) {
      var jobTitle = (getSettings().jobTitle || '').trim();
      if (jobTitle) {
        roleEl.textContent = jobTitle;
        roleEl.hidden = false;
      } else {
        roleEl.hidden = true;
      }
    }
  }

  // Avatar photo upload
  document.addEventListener('DOMContentLoaded', function () {
    var wrap  = document.getElementById('sidebar-avatar-wrap');
    var input = document.getElementById('avatar-file-input');
    if (wrap && input) {
      wrap.addEventListener('click', function () { input.click(); });
      input.addEventListener('change', function () {
        var file = input.files && input.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function (e) {
          localStorage.setItem('pd-avatar-photo', e.target.result);
          var username = document.getElementById('profile-display-name').textContent || 'U';
          setNametag(username);
        };
        reader.readAsDataURL(file);
      });
    }
  });

  // ── Settings ───────────────────────────────────────────────────────────
  var SETTINGS_KEY = 'pd-settings';

  function getSettings() {
    try { return JSON.parse(localStorage.getItem(SETTINGS_KEY)) || {}; } catch { return {}; }
  }

  function saveSettingsLocal(patch) {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(Object.assign(getSettings(), patch)));
  }

  async function loadSettings() {
    var s = getSettings();

    // Populate profile from /me
    try {
      var me = await apiFetch('/api/auth/me/');
      document.getElementById('settings-username').value = me.username || '';
      document.getElementById('settings-email').value = me.email || '';
      if (me.region) {
        var regionSel = document.getElementById('settings-region');
        if (regionSel) regionSel.value = me.region;
      }
    } catch {}

    // Name + job title from localStorage
    var firstNameEl = document.getElementById('settings-first-name');
    if (firstNameEl) firstNameEl.value = s.firstName || '';
    var lastNameEl = document.getElementById('settings-last-name');
    if (lastNameEl) lastNameEl.value = s.lastName || '';
    var jobTitleEl = document.getElementById('settings-job-title');
    if (jobTitleEl) jobTitleEl.value = s.jobTitle || '';

    // Display prefs
    var curr = document.getElementById('settings-default-currency');
    var landing = document.getElementById('settings-landing-view');
    var dateFmt = document.getElementById('settings-date-format');
    if (s.defaultCurrency) curr.value = s.defaultCurrency;
    if (s.landingView) landing.value = s.landingView;
    if (s.dateFormat) dateFmt.value = s.dateFormat;

    // Portfolio toggles
    document.getElementById('settings-hide-zero').checked = !!s.hideZeroHoldings;

    // Notifications
    var freq = document.getElementById('settings-summary-freq');
    if (s.summaryFreq) freq.value = s.summaryFreq;
    document.getElementById('settings-price-alerts').checked = !!s.priceAlerts;
  }

  // Profile save
  document.getElementById('settings-profile-save').addEventListener('click', async function () {
    var username = document.getElementById('settings-username').value.trim();
    var email = document.getElementById('settings-email').value.trim();
    if (!username) return showToast('Username cannot be empty', 'error');
    try {
      var regionEl = document.getElementById('settings-region');
      var region = regionEl ? regionEl.value : 'uk';
      var firstName = (document.getElementById('settings-first-name').value || '').trim();
      var lastName  = (document.getElementById('settings-last-name').value || '').trim();
      var jobTitle  = (document.getElementById('settings-job-title').value || '').trim();
      saveSettingsLocal({ firstName, lastName, jobTitle });
      var me = await apiFetch('/api/auth/me/', { method: 'PATCH', body: JSON.stringify({ username, email, region }) });
      setNametag(me.username);
      showToast('Profile updated', 'success');
    } catch {}
  });

  // Password save
  document.getElementById('settings-pw-save').addEventListener('click', async function () {
    var current = document.getElementById('settings-current-pw').value;
    var newPw = document.getElementById('settings-new-pw').value;
    var confirm = document.getElementById('settings-confirm-pw').value;
    if (!current || !newPw) return showToast('All password fields are required', 'error');
    if (newPw !== confirm) return showToast('New passwords do not match', 'error');
    try {
      await apiFetch('/api/auth/change-password/', { method: 'POST', body: JSON.stringify({ current_password: current, new_password: newPw }) });
      document.getElementById('settings-current-pw').value = '';
      document.getElementById('settings-new-pw').value = '';
      document.getElementById('settings-confirm-pw').value = '';
      showToast('Password changed', 'success');
    } catch {}
  });

  // Display prefs save
  document.getElementById('settings-display-save').addEventListener('click', function () {
    var currency = document.getElementById('settings-default-currency').value;
    var landing = document.getElementById('settings-landing-view').value;
    var dateFmt = document.getElementById('settings-date-format').value;
    saveSettingsLocal({ defaultCurrency: currency, landingView: landing, dateFormat: dateFmt });
    // Apply currency immediately
    var selectors = document.querySelectorAll('.currency-select');
    selectors.forEach(function (s) { s.value = currency; });
    showToast('Display preferences saved', 'success');
  });

  // Portfolio save
  document.getElementById('settings-portfolio-save').addEventListener('click', function () {
    var hideZero = document.getElementById('settings-hide-zero').checked;
    saveSettingsLocal({ hideZeroHoldings: hideZero });
    showToast('Portfolio preferences saved', 'success');
  });

  // Notifications save
  document.getElementById('settings-notifications-save').addEventListener('click', function () {
    var freq = document.getElementById('settings-summary-freq').value;
    var alerts = document.getElementById('settings-price-alerts').checked;
    saveSettingsLocal({ summaryFreq: freq, priceAlerts: alerts });
    showToast('Notification preferences saved', 'success');
  });

  // Export
  document.getElementById('settings-export-btn').addEventListener('click', async function () {
    try {
      var response = await fetch(API_BASE + '/api/export/', {
        credentials: 'include',
        headers: { 'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '' }
      });
      if (!response.ok) throw new Error();
      var blob = await response.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'stash-export.zip';
      a.click();
      URL.revokeObjectURL(url);
      showToast('Export downloaded', 'success');
    } catch {
      showToast('Export failed', 'error');
    }
  });

  // Delete account
  document.getElementById('settings-delete-account-btn').addEventListener('click', async function () {
    if (!confirm('This will permanently delete your account and all data. This cannot be undone.')) return;
    try {
      await apiFetch('/api/auth/me/', { method: 'DELETE' });
      showToast('Account deleted', 'success');
      setTimeout(function () { window.location.reload(); }, 1000);
    } catch {}
  });

  // Apply saved landing view and currency on init
  (function applyStoredPrefs() {
    var s = getSettings();
    if (s.defaultCurrency) {
      document.querySelectorAll('.currency-select').forEach(function (el) { el.value = s.defaultCurrency; });
    }
  })();

  // ── AI Chat Widget ─────────────────────────────────────────────────────
  (function initAiChat() {
    var CHAT_SESSIONS_KEY     = 'pd-chat-sessions';
    var CHAT_SESSION_DATE_KEY = 'pd-chat-session-date';
    var CHAT_STATE_KEY        = 'pd-chat-state'; // 'closed' | 'panel' | 'expanded'

    var todayStr  = new Date().toISOString().slice(0, 10);
    var chatHistory = [];
    var chatState = localStorage.getItem(CHAT_STATE_KEY) || 'closed';

    var widget     = document.getElementById('ai-chat-widget');
    var messages   = document.getElementById('ai-chat-messages');
    var input      = document.getElementById('ai-chat-input');
    var sendBtn    = document.getElementById('ai-chat-send');
    var triggerBtn = document.getElementById('ai-chat-trigger');
    var expandBtn  = document.getElementById('ai-chat-expand-btn');
    var closeBtn   = document.getElementById('ai-chat-close-btn');

    if (!widget) return;

    // ── Session management ────────────────────────────────────────────────
    function loadSessions() {
      try { return JSON.parse(localStorage.getItem(CHAT_SESSIONS_KEY)) || []; }
      catch (e) { return []; }
    }

    function saveSessions(sessions) {
      try { localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(sessions)); }
      catch (e) {}
    }

    function archiveCurrentSession() {
      if (!chatHistory.length) return;
      var sessions = loadSessions();
      // Replace existing entry for today if present, otherwise prepend
      var idx = sessions.findIndex(function (s) { return s.date === todayStr; });
      if (idx >= 0) { sessions[idx].messages = chatHistory.slice(); }
      else { sessions.unshift({ date: todayStr, messages: chatHistory.slice() }); }
      // Keep last 30 days of sessions
      if (sessions.length > 30) sessions = sessions.slice(0, 30);
      saveSessions(sessions);
    }

    // Remove legacy key from old implementation
    localStorage.removeItem('pd-chat-history');

    // On load: if last session date !== today, start fresh (new session)
    var lastDate = localStorage.getItem(CHAT_SESSION_DATE_KEY);
    if (lastDate === todayStr) {
      // Same day — restore current session
      var sessions = loadSessions();
      var todaySession = sessions.find(function (s) { return s.date === todayStr; });
      if (todaySession) chatHistory = todaySession.messages.slice();
    }
    // Always stamp today so next visit knows what "last session" was
    localStorage.setItem(CHAT_SESSION_DATE_KEY, todayStr);

    // ── Rendering ────────────────────────────────────────────────────────
    function renderWelcome() {
      messages.innerHTML = '<div class="ai-chat-welcome"><p>Hi! Ask me about stock prices, portfolio analysis, or investment strategy. <span class="ai-chat-disclaimer">Not a financial advisor — for guidance only.</span></p></div>';
    }

    function renderMessage(role, text, isThinking) {
      var div = document.createElement('div');
      div.className = 'ai-chat-msg ' + role;
      var bubble = document.createElement('div');
      bubble.className = 'ai-chat-bubble' + (isThinking ? ' thinking' : '');
      bubble.textContent = isThinking ? 'Thinking' : text;
      div.appendChild(bubble);
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
      return bubble;
    }

    function renderHistory(msgs) {
      messages.innerHTML = '';
      if (!msgs || !msgs.length) { renderWelcome(); return; }
      msgs.forEach(function (msg) { renderMessage(msg.role, msg.content, false); });
      messages.scrollTop = messages.scrollHeight;
    }

    // ── Previous sessions panel ──────────────────────────────────────────
    function buildPastSessionsPanel() {
      var sessions = loadSessions().filter(function (s) { return s.date !== todayStr && s.messages.length; });
      if (!sessions.length) { showToast('No previous conversations yet', 'info'); return; }

      var existing = document.getElementById('ai-chat-history-panel');
      if (existing) { existing.remove(); return; } // toggle off

      var panel = document.createElement('div');
      panel.id = 'ai-chat-history-panel';
      panel.className = 'ai-chat-history-panel';

      var heading = document.createElement('div');
      heading.className = 'ai-chat-history-heading';
      heading.textContent = 'Previous conversations';
      panel.appendChild(heading);

      sessions.forEach(function (s) {
        var row = document.createElement('div');
        row.className = 'ai-chat-history-row';

        var btn = document.createElement('button');
        btn.className = 'ai-chat-history-item';
        var d = new Date(s.date + 'T00:00:00');
        var label = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
        var preview = s.messages[0] ? s.messages[0].content.slice(0, 60) + (s.messages[0].content.length > 60 ? '…' : '') : '';
        btn.innerHTML = '<span class="ai-chat-history-date">' + escapeHtml(label) + '</span><span class="ai-chat-history-preview">' + escapeHtml(preview) + '</span>';
        btn.addEventListener('click', function () {
          renderHistory(s.messages);
          panel.remove();
        });

        var delBtn = document.createElement('button');
        delBtn.className = 'ai-chat-history-delete';
        delBtn.title = 'Delete conversation';
        delBtn.setAttribute('aria-label', 'Delete conversation');
        delBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>';
        delBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          var all = loadSessions();
          all = all.filter(function (x) { return x.date !== s.date; });
          saveSessions(all);
          row.remove();
          if (!panel.querySelectorAll('.ai-chat-history-row').length) {
            panel.remove();
            showToast('All conversations deleted', 'info');
          }
        });

        row.appendChild(btn);
        row.appendChild(delBtn);
        panel.appendChild(row);
      });

      // Insert above messages area
      messages.parentNode.insertBefore(panel, messages);
    }

    // ── Wire up static header buttons ────────────────────────────────────
    var historyBtn = document.getElementById('ai-chat-history-btn');
    var newBtn     = document.getElementById('ai-chat-new-btn');

    historyBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (chatState === 'closed') setState('panel');
      buildPastSessionsPanel();
    });

    newBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      archiveCurrentSession();
      todayStr = new Date().toISOString().slice(0, 10);
      chatHistory = [];
      var panel = document.getElementById('ai-chat-history-panel');
      if (panel) panel.remove();
      renderWelcome();
      input.focus();
    });

    // ── Three-state machine ──────────────────────────────────────────────
    function setState(state) {
      chatState = state;
      localStorage.setItem(CHAT_STATE_KEY, state);
      widget.dataset.state = state;
    }

    setState(chatState);

    triggerBtn.addEventListener('click', function () {
      setState('panel');
      setTimeout(function () { input.focus(); }, 50);
    });

    expandBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      setState(chatState === 'expanded' ? 'panel' : 'expanded');
    });

    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      setState('closed');
    });

    // ── Initial render ───────────────────────────────────────────────────
    renderHistory(chatHistory);

    // ── Send message ─────────────────────────────────────────────────────
    async function sendMessage() {
      var text = input.value.trim();
      if (!text) return;

      input.value = '';
      sendBtn.disabled = true;

      var panel = document.getElementById('ai-chat-history-panel');
      if (panel) panel.remove();

      chatHistory.push({ role: 'user', content: text });
      archiveCurrentSession();
      renderMessage('user', text, false);

      if (chatState === 'closed') setState('panel');

      var thinkBubble = renderMessage('assistant', '', true);

      try {
        var resp = await apiFetch('/api/chat/', {
          method: 'POST',
          body: JSON.stringify({
            message: text,
            history: chatHistory.slice(-20, -1),
          }),
        });

        thinkBubble.classList.remove('thinking');

        if (resp && resp.reply) {
          thinkBubble.textContent = resp.reply;
          chatHistory.push({ role: 'assistant', content: resp.reply });
          archiveCurrentSession();
        } else {
          thinkBubble.textContent = 'Sorry, I could not process that.';
        }
      } catch (e) {
        thinkBubble.classList.remove('thinking');
        thinkBubble.textContent = 'Error connecting to AI. Please try again.';
      }

      sendBtn.disabled = false;
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
  })();

})();
