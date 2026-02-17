/**
 * Trading Hub — Main Application JavaScript
 *
 * Vanilla JS, no build tools.
 * Handles:
 *   - Tab navigation
 *   - API calls (fetch wrapper with loading/error)
 *   - Bot CRUD (list, create, start, stop, delete)
 *   - Asset data + Chart.js charts
 *   - Trade history + filters + pagination
 *   - Alerts + test send
 *   - WebSocket (/ws/status) with auto-reconnect
 *   - Toast notifications
 */

'use strict';

/* ===================================================
   CONFIG
   =================================================== */
const Config = {
  API_BASE: '',                       // same origin
  WS_URL: (() => {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${location.host}/ws/status`;
  })(),
  WS_RECONNECT_DELAY: 5000,          // ms
  POLL_INTERVAL: 5000,               // fallback polling ms
  TRADES_PAGE_SIZE: 20,
  ALERTS_PAGE_SIZE: 20,
  TOAST_DURATION: 4000,              // ms
  MAX_CHART_DAYS: 30,
};

/* ===================================================
   UTILITIES
   =================================================== */
const Utils = {
  /**
   * Format a number with commas (e.g. 1,234,567.89)
   */
  formatNumber(n, decimals = 2) {
    if (n == null || isNaN(n)) return '0';
    return Number(n).toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  },

  /**
   * Format USD currency
   */
  formatUsd(n) {
    if (n == null || isNaN(n)) return '$0.00';
    return '$' + Utils.formatNumber(n, 2);
  },

  /**
   * Format percentage
   */
  formatPercent(n) {
    if (n == null || isNaN(n)) return '0.00%';
    const sign = n >= 0 ? '+' : '';
    return sign + Number(n).toFixed(2) + '%';
  },

  /**
   * Format datetime string to YYYY-MM-DD HH:mm:ss
   */
  formatDatetime(dtStr) {
    if (!dtStr) return '-';
    const d = new Date(dtStr);
    if (isNaN(d.getTime())) return dtStr;
    const pad = (v) => String(v).padStart(2, '0');
    return (
      d.getFullYear() + '-' +
      pad(d.getMonth() + 1) + '-' +
      pad(d.getDate()) + ' ' +
      pad(d.getHours()) + ':' +
      pad(d.getMinutes()) + ':' +
      pad(d.getSeconds())
    );
  },

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  /**
   * Show / hide element
   */
  show(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.classList.remove('hidden');
  },

  hide(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.classList.add('hidden');
  },
};

/* ===================================================
   API WRAPPER
   =================================================== */
const Api = {
  /**
   * Generic fetch wrapper.
   * Returns { ok, data, error }.
   */
  async request(method, path, body = null, queryParams = null) {
    let url = Config.API_BASE + path;

    if (queryParams) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(queryParams)) {
        if (v !== '' && v !== null && v !== undefined) {
          qs.append(k, v);
        }
      }
      const qsStr = qs.toString();
      if (qsStr) url += '?' + qsStr;
    }

    const opts = {
      method,
      headers: {},
    };

    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    try {
      const resp = await fetch(url, opts);
      const data = await resp.json();
      if (!resp.ok) {
        const errMsg = data.detail || data.error || `HTTP ${resp.status}`;
        return { ok: false, data: null, error: errMsg };
      }
      return { ok: true, data, error: null };
    } catch (err) {
      return { ok: false, data: null, error: err.message || 'Network error' };
    }
  },

  get(path, query) { return Api.request('GET', path, null, query); },
  post(path, body) { return Api.request('POST', path, body); },
  patch(path, body) { return Api.request('PATCH', path, body); },
  del(path) { return Api.request('DELETE', path); },
};

/* ===================================================
   TOAST NOTIFICATIONS
   =================================================== */
const Toast = {
  _container: null,

  _getContainer() {
    if (!this._container) {
      this._container = document.getElementById('toastContainer');
    }
    return this._container;
  },

  show(type, title, message, duration) {
    duration = duration || Config.TOAST_DURATION;
    const container = this._getContainer();
    if (!container) return;

    const icons = {
      error: '!!',
      success: 'OK',
      warning: '!',
      info: 'i',
    };

    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.innerHTML = `
      <span class="toast__icon">${icons[type] || 'i'}</span>
      <div class="toast__body">
        <div class="toast__title">${Utils.escapeHtml(title)}</div>
        <div class="toast__message">${Utils.escapeHtml(message)}</div>
      </div>
      <button class="toast__close" onclick="Toast.dismiss(this.parentElement)">&times;</button>
    `;

    container.appendChild(el);

    const timer = setTimeout(() => Toast.dismiss(el), duration);
    el._timer = timer;
  },

  dismiss(el) {
    if (!el || el._dismissed) return;
    el._dismissed = true;
    if (el._timer) clearTimeout(el._timer);
    el.classList.add('toast--leaving');
    el.addEventListener('animationend', () => el.remove());
  },

  error(msg) { Toast.show('error', 'Error', msg); },
  success(msg) { Toast.show('success', 'Success', msg); },
  warning(msg) { Toast.show('warning', 'Warning', msg); },
  info(msg) { Toast.show('info', 'Info', msg); },
};

/* ===================================================
   WEBSOCKET CONNECTION
   =================================================== */
const WsClient = {
  _ws: null,
  _reconnectTimer: null,
  _pollTimer: null,
  _connected: false,

  connect() {
    if (this._ws && this._ws.readyState <= 1) return;

    this._updateStatus('connecting');

    try {
      this._ws = new WebSocket(Config.WS_URL);
    } catch (err) {
      console.warn('[WS] Failed to create WebSocket:', err);
      this._fallbackPolling();
      return;
    }

    this._ws.onopen = () => {
      console.log('[WS] Connected');
      this._connected = true;
      this._updateStatus('connected');
      this._stopPolling();
    };

    this._ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'status_update' && msg.bots) {
          App._handleWsStatusUpdate(msg.bots);
        }
      } catch (err) {
        console.warn('[WS] Invalid message:', err);
      }
    };

    this._ws.onclose = () => {
      console.log('[WS] Disconnected');
      this._connected = false;
      this._updateStatus('disconnected');
      this._scheduleReconnect();
    };

    this._ws.onerror = (err) => {
      console.warn('[WS] Error:', err);
      this._ws.close();
    };
  },

  _scheduleReconnect() {
    if (this._reconnectTimer) return;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, Config.WS_RECONNECT_DELAY);
    // start fallback polling while disconnected
    this._startPolling();
  },

  _fallbackPolling() {
    this._updateStatus('disconnected');
    this._startPolling();
  },

  _startPolling() {
    if (this._pollTimer) return;
    this._pollTimer = setInterval(async () => {
      if (this._connected) {
        this._stopPolling();
        return;
      }
      const res = await Api.get('/api/bots');
      if (res.ok && Array.isArray(res.data)) {
        const bots = res.data.map((b) => ({
          bot_id: b.id,
          name: b.name,
          status: b.status,
          exchange: b.exchange,
          last_tick_at: b.updated_at,
          error_message: null,
        }));
        App._handleWsStatusUpdate(bots);
      }
    }, Config.POLL_INTERVAL);
  },

  _stopPolling() {
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
  },

  _updateStatus(state) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    if (!dot || !text) return;

    dot.className = 'status-dot';
    switch (state) {
      case 'connected':
        dot.classList.add('status-dot--connected');
        text.textContent = 'Connected';
        break;
      case 'connecting':
        dot.classList.add('status-dot--connecting');
        text.textContent = 'Connecting...';
        break;
      default:
        dot.classList.add('status-dot--disconnected');
        text.textContent = 'Disconnected';
    }
  },

  disconnect() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this._stopPolling();
    if (this._ws) {
      this._ws.onclose = null;
      this._ws.close();
      this._ws = null;
    }
  },
};

/* ===================================================
   CHART MANAGER
   =================================================== */
const Charts = {
  _instances: {},

  /**
   * Safely destroy a chart if it exists
   */
  _destroy(key) {
    if (this._instances[key]) {
      this._instances[key].destroy();
      delete this._instances[key];
    }
  },

  /**
   * Render asset distribution doughnut chart
   */
  renderAssetDistribution(currencyMap) {
    this._destroy('assetDist');
    const canvas = document.getElementById('chartAssetDistribution');
    if (!canvas) return;

    const labels = Object.keys(currencyMap);
    const values = Object.values(currencyMap);

    if (labels.length === 0) {
      labels.push('No Data');
      values.push(1);
    }

    const colors = [
      '#4fc3f7', '#7c4dff', '#00e676', '#ff9100',
      '#ff1744', '#ffeb3b', '#26c6da', '#ab47bc',
      '#ef5350', '#66bb6a', '#42a5f5', '#ffa726',
    ];

    this._instances['assetDist'] = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors.slice(0, labels.length),
          borderColor: '#1a1a2e',
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#8892a4',
              padding: 12,
              font: { size: 11 },
            },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return `${ctx.label}: ${Utils.formatUsd(ctx.parsed)} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  },

  /**
   * Render daily P&L line chart from trade data
   */
  renderDailyPnl(trades) {
    this._destroy('dailyPnl');
    const canvas = document.getElementById('chartDailyPnl');
    if (!canvas) return;

    // Aggregate by date: buy = negative, sell = positive
    const dailyMap = {};
    for (const t of trades) {
      const dateStr = Utils.formatDatetime(t.timestamp).split(' ')[0];
      if (!dailyMap[dateStr]) dailyMap[dateStr] = 0;
      if (t.side === 'sell') {
        dailyMap[dateStr] += t.total;
      } else {
        dailyMap[dateStr] -= t.total;
      }
    }

    const sortedDates = Object.keys(dailyMap).sort();
    // Limit to last 30 days
    const recentDates = sortedDates.slice(-Config.MAX_CHART_DAYS);
    const values = recentDates.map((d) => dailyMap[d]);

    // Cumulative P&L
    const cumulative = [];
    let sum = 0;
    for (const v of values) {
      sum += v;
      cumulative.push(sum);
    }

    if (recentDates.length === 0) {
      recentDates.push('N/A');
      cumulative.push(0);
    }

    this._instances['dailyPnl'] = new Chart(canvas, {
      type: 'line',
      data: {
        labels: recentDates,
        datasets: [{
          label: 'Cumulative P&L (USD)',
          data: cumulative,
          borderColor: '#4fc3f7',
          backgroundColor: 'rgba(79, 195, 247, 0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#4fc3f7',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            grid: { color: 'rgba(42, 58, 92, 0.4)' },
            ticks: { color: '#8892a4', maxRotation: 45, font: { size: 10 } },
          },
          y: {
            grid: { color: 'rgba(42, 58, 92, 0.4)' },
            ticks: {
              color: '#8892a4',
              font: { size: 10 },
              callback: (v) => Utils.formatUsd(v),
            },
          },
        },
        plugins: {
          legend: {
            labels: { color: '#8892a4', font: { size: 11 } },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `P&L: ${Utils.formatUsd(ctx.parsed.y)}`,
            },
          },
        },
      },
    });
  },
};

/* ===================================================
   MAIN APP
   =================================================== */
const App = {
  _currentTab: 'bots',
  _bots: [],
  _botsById: {},
  _tradesPage: 1,
  _alertsPage: 1,
  _initialized: false,

  /* ── Initialization ── */
  init() {
    if (this._initialized) return;
    this._initialized = true;

    this._initTabs();
    this.loadBots();
    WsClient.connect();
  },

  /* ── Tab Navigation ── */
  _initTabs() {
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        this._switchTab(tabId);
      });
    });
  },

  _switchTab(tabId) {
    this._currentTab = tabId;

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.classList.toggle('tab-btn--active', btn.dataset.tab === tabId);
      btn.setAttribute('aria-selected', btn.dataset.tab === tabId);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach((sec) => {
      sec.classList.toggle('tab-content--active', sec.id === `tab-${tabId}`);
    });

    // Load data for the tab (if not loaded yet)
    switch (tabId) {
      case 'bots':
        this.loadBots();
        break;
      case 'assets':
        this.loadAssets();
        break;
      case 'trades':
        this.loadTrades(1);
        break;
      case 'alerts':
        this.loadAlerts(1);
        break;
    }
  },

  /* ──────────────────────────────────────────────
     BOTS
     ────────────────────────────────────────────── */
  async loadBots() {
    Utils.show('botsLoading');
    Utils.hide('botsEmpty');
    Utils.hide('botsGrid');

    const res = await Api.get('/api/bots');

    Utils.hide('botsLoading');

    if (!res.ok) {
      Toast.error('Failed to load bots: ' + res.error);
      return;
    }

    this._bots = Array.isArray(res.data) ? res.data : [];
    this._botsById = {};
    this._bots.forEach((b) => { this._botsById[b.id] = b; });

    if (this._bots.length === 0) {
      Utils.show('botsEmpty');
    } else {
      Utils.show('botsGrid');
      this._renderBotGrid();
    }

    // Populate filter dropdowns
    this._updateBotFilterDropdown();
  },

  _renderBotGrid() {
    const grid = document.getElementById('botsGrid');
    if (!grid) return;

    grid.innerHTML = this._bots.map((bot) => `
      <div class="bot-card" id="bot-card-${bot.id}">
        <div class="bot-card__header">
          <div>
            <div class="bot-card__name">${Utils.escapeHtml(bot.name)}</div>
            <div class="bot-card__exchange">${Utils.escapeHtml(bot.exchange)} &middot; ${Utils.escapeHtml(bot.type)}</div>
          </div>
          <span class="status-badge status-badge--${bot.status}">${bot.status}</span>
        </div>
        <div class="bot-card__body">
          <div class="bot-card__info">
            <span style="font-size:0.78rem;color:var(--text-muted)">
              Symbol: ${Utils.escapeHtml(bot.config?.symbol || '-')}
            </span>
            <span style="font-size:0.78rem;color:var(--text-muted)">
              Updated: ${Utils.formatDatetime(bot.updated_at)}
            </span>
          </div>
          <div class="d-flex align-center gap-1">
            <label class="toggle" title="${bot.status === 'running' ? 'Stop' : 'Start'}">
              <input type="checkbox"
                ${bot.status === 'running' ? 'checked' : ''}
                ${bot.status === 'error' ? 'disabled' : ''}
                onchange="App.toggleBot(${bot.id}, this.checked)" />
              <span class="toggle__slider"></span>
            </label>
            <button class="btn btn--danger btn--icon" title="Delete"
                    onclick="App.deleteBot(${bot.id})">&#10005;</button>
          </div>
        </div>
      </div>
    `).join('');
  },

  _updateBotCard(botData) {
    const card = document.getElementById(`bot-card-${botData.bot_id || botData.id}`);
    if (!card) return;

    const id = botData.bot_id || botData.id;
    const bot = this._botsById[id];
    if (!bot) return;

    // Update local data
    bot.status = botData.status;
    if (botData.last_tick_at) bot.updated_at = botData.last_tick_at;
    if (botData.name) bot.name = botData.name;

    // Update badge
    const badge = card.querySelector('.status-badge');
    if (badge) {
      badge.className = `status-badge status-badge--${bot.status}`;
      badge.textContent = bot.status;
    }

    // Update toggle
    const toggle = card.querySelector('.toggle input');
    if (toggle) {
      toggle.checked = bot.status === 'running';
      toggle.disabled = bot.status === 'error';
    }
  },

  async toggleBot(botId, shouldRun) {
    const endpoint = shouldRun
      ? `/api/bots/${botId}/start`
      : `/api/bots/${botId}/stop`;

    const res = await Api.patch(endpoint);
    if (!res.ok) {
      Toast.error('Failed to toggle bot: ' + res.error);
      this.loadBots(); // reload to revert
      return;
    }

    Toast.success(shouldRun ? 'Bot started' : 'Bot stopped');

    // Update local state
    if (this._botsById[botId]) {
      this._botsById[botId].status = res.data.status;
      this._updateBotCard({ bot_id: botId, ...res.data });
    }
  },

  async deleteBot(botId) {
    if (!confirm('Are you sure you want to delete this bot?')) return;

    const res = await Api.del(`/api/bots/${botId}`);
    if (!res.ok) {
      Toast.error('Failed to delete bot: ' + res.error);
      return;
    }

    Toast.success('Bot deleted');
    this.loadBots();
  },

  /* ── Add Bot Modal ── */
  openAddBotModal() {
    document.getElementById('addBotModal').classList.add('modal-overlay--active');
    document.getElementById('botName').focus();
  },

  closeAddBotModal() {
    document.getElementById('addBotModal').classList.remove('modal-overlay--active');
    // reset form
    ['botName', 'botApiKey', 'botApiSecret'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    document.getElementById('botExchange').value = 'simulation';
    document.getElementById('botType').value = 'custom';
    document.getElementById('botSymbol').value = 'BTC/KRW';
    document.getElementById('botStrategy').value = 'simple_ma';
    document.getElementById('botInterval').value = '10';
  },

  async createBot() {
    const name = document.getElementById('botName').value.trim();
    if (!name) {
      Toast.warning('Please enter a bot name');
      return;
    }

    const body = {
      name,
      exchange: document.getElementById('botExchange').value,
      type: document.getElementById('botType').value,
      config: {
        symbol: document.getElementById('botSymbol').value.trim() || 'BTC/KRW',
        strategy: document.getElementById('botStrategy').value.trim() || 'simple_ma',
        interval: parseInt(document.getElementById('botInterval').value) || 10,
        params: {},
      },
    };

    const apiKey = document.getElementById('botApiKey').value.trim();
    const apiSecret = document.getElementById('botApiSecret').value.trim();
    if (apiKey) body.api_key = apiKey;
    if (apiSecret) body.api_secret = apiSecret;

    const btn = document.getElementById('btnSubmitBot');
    btn.disabled = true;
    btn.textContent = 'Creating...';

    const res = await Api.post('/api/bots', body);

    btn.disabled = false;
    btn.textContent = 'Create Bot';

    if (!res.ok) {
      Toast.error('Failed to create bot: ' + res.error);
      return;
    }

    Toast.success('Bot created successfully');
    this.closeAddBotModal();
    this.loadBots();
  },

  /* ──────────────────────────────────────────────
     ASSETS
     ────────────────────────────────────────────── */
  async loadAssets() {
    Utils.show('assetsLoading');
    Utils.hide('assetsContent');

    // Load summary and asset list in parallel
    const [summaryRes, assetsRes, tradesRes] = await Promise.all([
      Api.get('/api/assets/summary'),
      Api.get('/api/assets'),
      Api.get('/api/trades', { page: 1, size: 500 }), // for daily P&L chart
    ]);

    Utils.hide('assetsLoading');
    Utils.show('assetsContent');

    // Summary cards
    if (summaryRes.ok && summaryRes.data) {
      const s = summaryRes.data;
      document.getElementById('totalValueUsd').textContent = Utils.formatUsd(s.total_value_usd);
      document.getElementById('activeBotCount').textContent = s.bot_count || 0;

      const currencyCount = s.assets_by_currency
        ? Object.keys(s.assets_by_currency).length
        : 0;
      document.getElementById('currencyCount').textContent = currencyCount;

      // Doughnut chart
      Charts.renderAssetDistribution(s.assets_by_currency || {});
    } else {
      Toast.error('Failed to load asset summary: ' + (summaryRes.error || 'Unknown'));
    }

    // Asset table
    if (assetsRes.ok && Array.isArray(assetsRes.data)) {
      this._renderAssetsTable(assetsRes.data);
    } else {
      Toast.error('Failed to load assets: ' + (assetsRes.error || 'Unknown'));
    }

    // Daily P&L chart
    if (tradesRes.ok && tradesRes.data) {
      const items = tradesRes.data.items || tradesRes.data;
      Charts.renderDailyPnl(Array.isArray(items) ? items : []);
    }
  },

  _renderAssetsTable(assets) {
    const tbody = document.getElementById('assetsTableBody');
    if (!tbody) return;

    if (assets.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="6" class="text-center" style="padding:32px;color:var(--text-muted)">
          No asset data available.
        </td></tr>`;
      return;
    }

    tbody.innerHTML = assets.map((a) => `
      <tr>
        <td>${Utils.escapeHtml(a.bot_name || `Bot #${a.bot_id}`)}</td>
        <td><strong>${Utils.escapeHtml(a.currency)}</strong></td>
        <td class="text-right text-mono">${Utils.formatNumber(a.balance, 6)}</td>
        <td class="text-right text-mono">${Utils.formatNumber(a.locked, 6)}</td>
        <td class="text-right text-mono">${Utils.formatUsd(a.value_usd)}</td>
        <td style="font-size:0.78rem;color:var(--text-muted)">${Utils.formatDatetime(a.updated_at)}</td>
      </tr>
    `).join('');
  },

  /* ──────────────────────────────────────────────
     TRADES
     ────────────────────────────────────────────── */
  async loadTrades(page) {
    page = page || 1;
    this._tradesPage = page;

    Utils.show('tradesLoading');
    Utils.hide('tradesEmpty');
    Utils.hide('tradesTableWrapper');
    Utils.hide('tradesPagination');

    const params = {
      page,
      size: Config.TRADES_PAGE_SIZE,
    };

    const botVal = document.getElementById('filterBot')?.value;
    if (botVal) params.bot_id = botVal;

    const symbolVal = document.getElementById('filterSymbol')?.value?.trim();
    if (symbolVal) params.symbol = symbolVal;

    const sideVal = document.getElementById('filterSide')?.value;
    if (sideVal) params.side = sideVal;

    const startDate = document.getElementById('filterStartDate')?.value;
    if (startDate) params.start_date = startDate;

    const endDate = document.getElementById('filterEndDate')?.value;
    if (endDate) params.end_date = endDate;

    const res = await Api.get('/api/trades', params);

    Utils.hide('tradesLoading');

    if (!res.ok) {
      Toast.error('Failed to load trades: ' + res.error);
      return;
    }

    const data = res.data;
    const items = data.items || [];
    const total = data.total || 0;
    const pages = data.pages || 1;

    if (items.length === 0) {
      Utils.show('tradesEmpty');
      return;
    }

    Utils.show('tradesTableWrapper');
    this._renderTradesTable(items);

    if (pages > 1) {
      Utils.show('tradesPagination');
      this._renderPagination('tradesPagination', page, pages, (p) => this.loadTrades(p));
    }
  },

  _renderTradesTable(trades) {
    const tbody = document.getElementById('tradesTableBody');
    if (!tbody) return;

    tbody.innerHTML = trades.map((t) => {
      const sideClass = t.side === 'buy' ? 'text-buy' : 'text-sell';
      const botName = this._botsById[t.bot_id]?.name || `Bot #${t.bot_id}`;
      return `
        <tr>
          <td style="font-size:0.78rem;white-space:nowrap">${Utils.formatDatetime(t.timestamp)}</td>
          <td>${Utils.escapeHtml(botName)}</td>
          <td><strong>${Utils.escapeHtml(t.symbol)}</strong></td>
          <td class="${sideClass}">${t.side.toUpperCase()}</td>
          <td class="text-right text-mono">${Utils.formatNumber(t.price)}</td>
          <td class="text-right text-mono">${Utils.formatNumber(t.quantity, 6)}</td>
          <td class="text-right text-mono">${Utils.formatUsd(t.total)}</td>
          <td class="text-right text-mono" style="color:var(--text-muted)">${Utils.formatUsd(t.fee)}</td>
        </tr>
      `;
    }).join('');
  },

  /* ──────────────────────────────────────────────
     ALERTS
     ────────────────────────────────────────────── */
  async loadAlerts(page) {
    page = page || 1;
    this._alertsPage = page;

    Utils.show('alertsLoading');
    Utils.hide('alertsEmpty');
    Utils.hide('alertsList');
    Utils.hide('alertsPagination');

    const res = await Api.get('/api/alerts', {
      page,
      size: Config.ALERTS_PAGE_SIZE,
    });

    Utils.hide('alertsLoading');

    if (!res.ok) {
      Toast.error('Failed to load alerts: ' + res.error);
      return;
    }

    const data = res.data;
    const items = data.items || [];
    const pages = data.pages || 1;

    if (items.length === 0) {
      Utils.show('alertsEmpty');
      return;
    }

    Utils.show('alertsList');
    this._renderAlertsList(items);

    if (pages > 1) {
      Utils.show('alertsPagination');
      this._renderPagination('alertsPagination', page, pages, (p) => this.loadAlerts(p));
    }
  },

  _renderAlertsList(alerts) {
    const container = document.getElementById('alertsList');
    if (!container) return;

    const iconMap = {
      error: '!!',
      large_trade: '$',
      daily_profit: '%',
    };

    container.innerHTML = alerts.map((a) => {
      const botName = a.bot_id
        ? (this._botsById[a.bot_id]?.name || `Bot #${a.bot_id}`)
        : 'System';
      return `
        <div class="alert-item">
          <div class="alert-item__icon alert-item__icon--${a.type}">
            ${iconMap[a.type] || '?'}
          </div>
          <div class="alert-item__content">
            <div class="alert-item__message">${Utils.escapeHtml(a.message)}</div>
            <div class="alert-item__meta">
              ${Utils.escapeHtml(a.type)} &middot; ${Utils.escapeHtml(botName)} &middot; ${Utils.formatDatetime(a.created_at)}
            </div>
          </div>
          <span class="alert-item__sent ${a.sent ? 'alert-item__sent--yes' : 'alert-item__sent--no'}">
            ${a.sent ? 'Sent' : 'Not sent'}
          </span>
        </div>
      `;
    }).join('');
  },

  async sendTestAlert() {
    const btn = document.getElementById('btnTestAlert');
    btn.disabled = true;
    btn.textContent = 'Sending...';

    const res = await Api.post('/api/alerts/test', {
      message: 'Trading Hub test alert',
    });

    btn.disabled = false;
    btn.textContent = 'Send Test Alert';

    if (!res.ok) {
      Toast.error('Failed to send test alert: ' + res.error);
      return;
    }

    Toast.success(res.data?.message || 'Test alert sent');
    this.loadAlerts(1);
  },

  /* ──────────────────────────────────────────────
     PAGINATION (shared)
     ────────────────────────────────────────────── */
  _renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';

    // Previous
    html += `<button class="pagination__btn" ${currentPage <= 1 ? 'disabled' : ''}
                     onclick="App._pageHandler('${containerId}', ${currentPage - 1})">
               Prev
             </button>`;

    // Page numbers
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
      html += `<button class="pagination__btn" onclick="App._pageHandler('${containerId}', 1)">1</button>`;
      if (startPage > 2) html += `<span class="pagination__info">...</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
      html += `<button class="pagination__btn ${i === currentPage ? 'pagination__btn--active' : ''}"
                       onclick="App._pageHandler('${containerId}', ${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) html += `<span class="pagination__info">...</span>`;
      html += `<button class="pagination__btn" onclick="App._pageHandler('${containerId}', ${totalPages})">${totalPages}</button>`;
    }

    // Next
    html += `<button class="pagination__btn" ${currentPage >= totalPages ? 'disabled' : ''}
                     onclick="App._pageHandler('${containerId}', ${currentPage + 1})">
               Next
             </button>`;

    // Info
    html += `<span class="pagination__info">Page ${currentPage} of ${totalPages}</span>`;

    container.innerHTML = html;

    // Store callback
    container._onPageChange = onPageChange;
  },

  _pageHandler(containerId, page) {
    const container = document.getElementById(containerId);
    if (container?._onPageChange) {
      container._onPageChange(page);
    }
  },

  /* ──────────────────────────────────────────────
     WEBSOCKET HANDLER
     ────────────────────────────────────────────── */
  _handleWsStatusUpdate(bots) {
    if (!Array.isArray(bots)) return;

    for (const botStatus of bots) {
      const id = botStatus.bot_id;
      if (this._botsById[id]) {
        this._botsById[id].status = botStatus.status;
        if (botStatus.name) this._botsById[id].name = botStatus.name;
      }
      this._updateBotCard(botStatus);
    }
  },

  /* ──────────────────────────────────────────────
     FILTER DROPDOWN UPDATES
     ────────────────────────────────────────────── */
  _updateBotFilterDropdown() {
    const select = document.getElementById('filterBot');
    if (!select) return;

    const currentVal = select.value;
    select.innerHTML = '<option value="">All Bots</option>';
    this._bots.forEach((b) => {
      const opt = document.createElement('option');
      opt.value = b.id;
      opt.textContent = b.name;
      select.appendChild(opt);
    });
    select.value = currentVal;
  },
};

/* ===================================================
   BOOTSTRAP
   =================================================== */
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
