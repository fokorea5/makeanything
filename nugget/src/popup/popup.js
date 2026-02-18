/**
 * Nugget – Popup JS
 * DESIGN.md 섹션 4(메시징), 8(통합 계약), 9(시그니처) 준수
 * CSP: 인라인 스크립트 금지 (AC-29)
 */

'use strict';

// =============================================
// 상수 (DESIGN.md 8.3 Storage 키 이름)
// =============================================

const STORAGE_KEYS = {
  ENTRIES: 'nugget_entries',
  SETTINGS: 'nugget_settings',
  JUNK_KEYWORDS: 'nugget_junk_keywords',
  PRO_CACHE: 'nugget_pro_cache',
  TODAYS_NUGGET_DISMISSED: 'nugget_todays_nugget_dismissed',
  CUSTOM_TAGS: 'nugget_custom_tags',
};

// DESIGN.md 8.2 메시지 타입
const MSG = {
  GET_ENTRIES: 'GET_ENTRIES',
  SEARCH_ENTRIES: 'SEARCH_ENTRIES',
  TOGGLE_STAR: 'TOGGLE_STAR',
  UPDATE_NOTE: 'UPDATE_NOTE',
  COPY_MARKDOWN: 'COPY_MARKDOWN',
  GET_TODAYS_NUGGET: 'GET_TODAYS_NUGGET',
  DISMISS_TODAYS_NUGGET: 'DISMISS_TODAYS_NUGGET',
  GET_SETTINGS: 'GET_SETTINGS',
  UPDATE_SETTINGS: 'UPDATE_SETTINGS',
  GET_PRO_STATUS: 'GET_PRO_STATUS',
  OPEN_PAYMENT_PAGE: 'OPEN_PAYMENT_PAGE',
  EXPORT_JSON: 'EXPORT_JSON',
  IMPORT_JSON: 'IMPORT_JSON',
  ADD_CUSTOM_TAG: 'ADD_CUSTOM_TAG',
};

// 한도 상수 (DESIGN.md 8.4)
const MAX_FREE_MD_COPIES = 20;
const MAX_FREE_NOTE_LENGTH = 200;

// =============================================
// 상태
// =============================================

const state = {
  entries: [],
  settings: null,
  isPro: false,
  proExpired: false,
  searchQuery: '',
  filters: {
    platforms: [],      // [] = 전체
    period: 'all',
    dateFrom: null,
    dateTo: null,
    tags: [],           // [] = 전체
    starredOnly: false,
    includeJunk: false,
  },
  filterPanelOpen: false,
  todaysNuggetEntry: null,
  isLoading: true,
  searchDebounceTimer: null,
};

// =============================================
// DOM 요소 참조
// =============================================

const $ = id => document.getElementById(id);

const els = {
  todaysNugget: $('todays-nugget'),
  todaysNuggetText: $('todays-nugget-text'),
  btnDismissNugget: $('btn-dismiss-nugget'),
  errorBanner: $('error-banner'),
  errorBannerText: $('error-banner-text'),
  btnCloseError: $('btn-close-error'),
  capacityBanner: $('capacity-banner'),
  capacityBannerText: $('capacity-banner-text'),
  btnUpgradeCapacity: $('btn-upgrade-capacity'),
  btnCloseCapacity: $('btn-close-capacity'),
  searchInput: $('search-input'),
  btnFilterToggle: $('btn-filter-toggle'),
  filterActiveDot: $('filter-active-dot'),
  filterPanel: $('filter-panel'),
  periodDropdown: $('period-dropdown'),
  tagDropdown: $('tag-dropdown'),
  customDateRange: $('custom-date-range'),
  dateFrom: $('date-from'),
  dateTo: $('date-to'),
  btnStarredFilter: $('btn-starred-filter'),
  btnJunkFilter: $('btn-junk-filter'),
  btnFilterReset: $('btn-filter-reset'),
  btnPeriodFilter: $('btn-period-filter'),
  btnTagFilter: $('btn-tag-filter'),
  cardList: $('card-list'),
  skeletonLoader: $('skeleton-loader'),
  emptyState: $('empty-state'),
  emptyStateTitle: $('empty-state-title'),
  emptyStateDesc: $('empty-state-desc'),
  btnEmptyResetFilter: $('btn-empty-reset-filter'),
  cardsContainer: $('cards-container'),
  statCount: $('stat-count'),
  statPlatform: $('stat-platform'),
  statTag: $('stat-tag'),
  btnBackup: $('btn-backup'),
  btnRestore: $('btn-restore'),
  btnSettings: $('btn-settings'),
  btnUpgrade: $('btn-upgrade'),
  proBadge: $('pro-badge'),
  restoreFileInput: $('restore-file-input'),
  popupToast: $('popup-toast'),
  mdLimitTooltip: $('md-limit-tooltip'),
  tagLimitTooltip: $('tag-limit-tooltip'),
  btnMdUpgrade: $('btn-md-upgrade'),
  btnTagUpgrade: $('btn-tag-upgrade'),
  modalOverlay: $('modal-overlay'),
  modalBody: $('modal-body'),
  btnModalClose: $('btn-modal-close'),
};

// =============================================
// 메시지 전송 (DESIGN.md 4.2)
// =============================================

/**
 * Background에 메시지 전송
 * @param {string} type - 메시지 타입
 * @param {object} payload - 페이로드
 * @returns {Promise<any>}
 */
async function sendMsg(type, payload = {}) {
  try {
    return await chrome.runtime.sendMessage({ type, payload });
  } catch (err) {
    console.error('[Nugget Popup] sendMsg error:', type, err);
    return null;
  }
}

// =============================================
// [v1.1] i18n / 테마 초기화
// =============================================

/**
 * i18n.js와 theme.js가 utils/에서 로드된 후 초기화
 * HTML에서 i18n.js와 theme.js가 먼저 로드되어야 함
 */
function initI18nAndTheme() {
  // theme.js가 로드되었으면 테마 적용
  if (typeof applyTheme === 'function') {
    applyTheme();
  }
  // i18n.js가 로드되었으면 번역 적용
  if (typeof initI18n === 'function') {
    initI18n();
  }
}

// =============================================
// 초기화
// =============================================

async function init() {
  initI18nAndTheme();
  bindEvents();
  await loadInitialData();
}

async function loadInitialData() {
  state.isLoading = true;
  showSkeleton(true);

  // 설정, Pro 상태, 엔트리, Today's Nugget 병렬 로드
  const [settingsRes, proRes, todayRes] = await Promise.all([
    sendMsg(MSG.GET_SETTINGS),
    sendMsg(MSG.GET_PRO_STATUS),
    sendMsg(MSG.GET_TODAYS_NUGGET),
  ]);

  if (settingsRes) {
    state.settings = settingsRes.settings;
  }

  if (proRes) {
    state.isPro = proRes.isPro;
    state.proExpired = !!proRes.expired;
  }

  if (todayRes && todayRes.entry) {
    state.todaysNuggetEntry = todayRes.entry;
    renderTodaysNugget(todayRes.entry);
  }

  updateFooterProUI();
  if (state.proExpired) {
    showProVerifyBanner();
  }

  await loadAndRenderEntries();

  state.isLoading = false;
  showSkeleton(false);

  // 용량 경고 배너 체크
  checkCapacityBanner();

  // 셀렉터 실패 뱃지 확인
  checkSelectorErrorBanner();
}

// =============================================
// Today's Nugget (AC-20)
// =============================================

function renderTodaysNugget(entry) {
  if (!entry) {
    els.todaysNugget.hidden = true;
    return;
  }
  const preview = entry.question.length > 50
    ? entry.question.slice(0, 50) + '...'
    : entry.question;
  els.todaysNuggetText.textContent = `"${preview}"`;
  els.todaysNugget.hidden = false;
}

function dismissTodaysNugget() {
  els.todaysNugget.hidden = true;
  sendMsg(MSG.DISMISS_TODAYS_NUGGET);
}

function scrollToTodaysNuggetCard() {
  if (!state.todaysNuggetEntry) return;
  const card = els.cardsContainer.querySelector(`[data-entry-id="${state.todaysNuggetEntry.id}"]`);
  if (!card) return;
  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  card.classList.add('card--nugget-highlight');
  setTimeout(() => card.classList.remove('card--nugget-highlight'), 600);
}

// =============================================
// 엔트리 로드 & 렌더링
// =============================================

async function loadAndRenderEntries() {
  const query = state.searchQuery.trim();

  let res;
  if (query) {
    res = await sendMsg(MSG.SEARCH_ENTRIES, {
      query,
      filters: buildFiltersPayload(),
    });
  } else {
    res = await sendMsg(MSG.GET_ENTRIES, {
      filters: buildFiltersPayload(),
    });
  }

  state.entries = (res && res.entries) ? res.entries : [];
  renderCards(state.entries);
  updateStats();
}

function buildFiltersPayload() {
  const f = state.filters;
  return {
    platforms: f.platforms.length > 0 ? f.platforms : null,
    period: f.period,
    dateFrom: f.dateFrom,
    dateTo: f.dateTo,
    tags: f.tags.length > 0 ? f.tags : null,
    starredOnly: f.starredOnly,
    includeJunk: f.includeJunk,
  };
}

// =============================================
// 카드 렌더링
// =============================================

function renderCards(entries) {
  showSkeleton(false);

  if (!entries || entries.length === 0) {
    showEmptyState();
    els.cardsContainer.innerHTML = '';
    return;
  }

  hideEmptyState();
  els.cardsContainer.innerHTML = '';

  const fragment = document.createDocumentFragment();
  entries.forEach(entry => {
    const card = createCard(entry);
    fragment.appendChild(card);
  });
  els.cardsContainer.appendChild(fragment);
}

function createCard(entry) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.entryId = entry.id;
  card.dataset.platform = entry.platform;

  const dateStr = formatDate(entry.date);
  const tagsHtml = renderTagsHtml(entry.tags);
  const questionHtml = highlightText(escapeHtml(entry.question), state.searchQuery);
  const answerHtml = highlightText(escapeHtml(entry.answer), state.searchQuery);

  const noteCounterHtml = !state.isPro
    ? `<div class="card__note-counter" data-note-counter="${entry.id}">
         ${(entry.note || '').length}/${MAX_FREE_NOTE_LENGTH}
       </div>`
    : '';

  const isStarred = entry.starred ? 'starred' : '';
  const starFill = entry.starred ? 'var(--nugget-primary)' : 'none';
  const starStroke = entry.starred ? 'var(--nugget-primary)' : 'currentColor';
  const hasNote = entry.note && entry.note.trim().length > 0;
  const noteFill = hasNote ? 'var(--nugget-primary)' : 'none';
  const noteStroke = hasNote ? 'var(--nugget-primary)' : 'currentColor';

  card.innerHTML = `
    <div class="card__header" tabindex="0" role="button" aria-expanded="false"
         aria-label="${escapeAttr(entry.question)}">
      <div class="card__question">${questionHtml}</div>
      <div class="card__answer">${answerHtml}</div>
    </div>
    <div class="card__detail">
      <div class="card__divider"></div>
      <div class="card__meta">
        <span class="card__date">${dateStr}</span>
        <div class="card__tags">${tagsHtml}</div>
      </div>
      <div class="card__actions">
        <button class="card-action-btn btn-star ${isStarred}" data-action="star"
                aria-pressed="${entry.starred}" aria-label="별표 토글" title="별표">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="${starFill}"
               stroke="${starStroke}" stroke-width="1.5" aria-hidden="true">
            <polygon points="8,2 10,6 14,6.5 11,9.5 12,14 8,11.5 4,14 5,9.5 2,6.5 6,6"/>
          </svg>
          별표
        </button>
        <button class="card-action-btn btn-note" data-action="note"
                aria-label="메모" title="메모">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="${noteFill}"
               stroke="${noteStroke}" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
            <path d="M11 2H5a1 1 0 00-1 1v10a1 1 0 001 1h6a1 1 0 001-1V3a1 1 0 00-1-1z"/>
            <line x1="6" y1="6" x2="10" y2="6"/>
            <line x1="6" y1="9" x2="10" y2="9"/>
          </svg>
          메모
        </button>
        <button class="card-action-btn btn-md-copy" data-action="md"
                aria-label="마크다운 복사" title="MD 복사">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
               stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
            <rect x="4" y="2" width="9" height="12" rx="1"/>
            <path d="M3 4H2a1 1 0 00-1 1v9a1 1 0 001 1h9a1 1 0 001-1v-1"/>
            <line x1="6" y1="6" x2="11" y2="6"/>
            <line x1="6" y1="9" x2="11" y2="9"/>
          </svg>
          MD
        </button>
        ${entry.sourceUrl && /^https?:\/\//i.test(entry.sourceUrl) ? `<a class="card__source" href="${escapeAttr(entry.sourceUrl)}" target="_blank"
             title="${escapeAttr(entry.sourceUrl)}" rel="noopener noreferrer">원본</a>` : ''}
      </div>
      <div class="card__note-area" hidden data-note-area="${entry.id}">
        <textarea
          class="card__note-textarea"
          placeholder="메모를 남겨보세요..."
          maxlength="${!state.isPro ? MAX_FREE_NOTE_LENGTH : 99999}"
          aria-label="메모 입력"
          data-note-textarea="${entry.id}"
        >${escapeHtml(entry.note || '')}</textarea>
        ${noteCounterHtml}
      </div>
    </div>
  `;

  // 카드 이벤트 바인딩
  bindCardEvents(card, entry);

  return card;
}

function bindCardEvents(card, entry) {
  const header = card.querySelector('.card__header');
  const btnStar = card.querySelector('[data-action="star"]');
  const btnNote = card.querySelector('[data-action="note"]');
  const btnMd = card.querySelector('[data-action="md"]');
  const noteArea = card.querySelector(`[data-note-area="${entry.id}"]`);
  const noteTextarea = card.querySelector(`[data-note-textarea="${entry.id}"]`);

  // 카드 펼치기/접기
  header.addEventListener('click', () => toggleCard(card, entry));
  header.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleCard(card, entry);
    }
  });

  // 별표 토글 (AC-??)
  btnStar.addEventListener('click', e => {
    e.stopPropagation();
    handleToggleStar(card, entry);
  });

  // 메모 토글 (AC-14)
  btnNote.addEventListener('click', e => {
    e.stopPropagation();
    if (!card.classList.contains('expanded')) {
      toggleCard(card, entry);
    }
    const isVisible = !noteArea.hidden;
    noteArea.hidden = isVisible;
    if (!isVisible) {
      noteTextarea.focus();
    }
  });

  // 메모 blur 자동 저장 (AC-14)
  if (noteTextarea) {
    noteTextarea.addEventListener('blur', () => handleNoteSave(entry, noteTextarea));
    noteTextarea.addEventListener('input', () => updateNoteCounter(entry, noteTextarea));
  }

  // MD 복사 (AC-12, AC-13)
  btnMd.addEventListener('click', e => {
    e.stopPropagation();
    handleMdCopy(card, entry, btnMd);
  });
}

function toggleCard(card, entry) {
  const isExpanded = card.classList.contains('expanded');
  card.classList.toggle('expanded', !isExpanded);
  const header = card.querySelector('.card__header');
  header.setAttribute('aria-expanded', !isExpanded);
}

// =============================================
// 별표 토글 (AC-??)
// =============================================

async function handleToggleStar(card, entry) {
  const res = await sendMsg(MSG.TOGGLE_STAR, { entryId: entry.id });
  if (!res || !res.success) return;

  entry.starred = res.starred;
  const btn = card.querySelector('[data-action="star"]');
  const svg = btn.querySelector('svg polygon');

  btn.classList.toggle('starred', res.starred);
  btn.setAttribute('aria-pressed', res.starred);

  const fill = res.starred ? 'var(--nugget-primary)' : 'none';
  const stroke = res.starred ? 'var(--nugget-primary)' : 'currentColor';
  svg.setAttribute('fill', fill);
  svg.setAttribute('stroke', stroke);
}

// =============================================
// 메모 저장 (AC-14, AC-15)
// =============================================

async function handleNoteSave(entry, textarea) {
  const note = textarea.value;

  // 무료 사용자 200자 제한 (AC-15)
  if (!state.isPro && note.length > MAX_FREE_NOTE_LENGTH) {
    textarea.value = note.slice(0, MAX_FREE_NOTE_LENGTH);
    return;
  }

  const res = await sendMsg(MSG.UPDATE_NOTE, { entryId: entry.id, note: textarea.value });
  if (res && res.success) {
    entry.note = textarea.value;
    // 메모 버튼 아이콘 업데이트
    const card = els.cardsContainer.querySelector(`[data-entry-id="${entry.id}"]`);
    if (card) {
      const btnNote = card.querySelector('[data-action="note"]');
      const hasNote = textarea.value.trim().length > 0;
      const noteSvg = btnNote.querySelector('svg');
      noteSvg.setAttribute('fill', hasNote ? 'var(--nugget-primary)' : 'none');
      noteSvg.setAttribute('stroke', hasNote ? 'var(--nugget-primary)' : 'currentColor');
    }
  }
}

function updateNoteCounter(entry, textarea) {
  const counter = els.cardsContainer.querySelector(`[data-note-counter="${entry.id}"]`);
  if (!counter) return;
  const len = textarea.value.length;
  counter.textContent = `${len}/${MAX_FREE_NOTE_LENGTH}`;
  // 무료 사용자 한도 초과 시 빨간색
  counter.classList.toggle('over-limit', len >= MAX_FREE_NOTE_LENGTH);
  // 한도 초과 시 추가 입력 차단
  if (!state.isPro && len > MAX_FREE_NOTE_LENGTH) {
    textarea.value = textarea.value.slice(0, MAX_FREE_NOTE_LENGTH);
    counter.textContent = `${MAX_FREE_NOTE_LENGTH}/${MAX_FREE_NOTE_LENGTH}`;
  }
}

// =============================================
// MD 복사 (AC-12, AC-13)
// @risk: md-copy-limit — 무료 월 20회 제한
// =============================================

async function handleMdCopy(card, entry, btn) {
  // @risk: md-copy-limit
  const res = await sendMsg(MSG.COPY_MARKDOWN, { entryId: entry.id });
  if (!res) return;

  if (res.limitReached) {
    // 한도 말풍선 표시 (AC-13)
    showLimitTooltip(btn, 'md');
    return;
  }

  if (res.success && res.markdown) {
    try {
      await navigator.clipboard.writeText(res.markdown);
    } catch (e) {
      // clipboard API 실패 시 fallback
      const ta = document.createElement('textarea');
      ta.value = res.markdown;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    // "✓ 복사됨" 피드백 (AC-13)
    const originalContent = btn.innerHTML;
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
           stroke="var(--color-success)" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <polyline points="2,7 5,10 12,3"/>
      </svg>
      복사됨
    `;
    btn.classList.add('copied');
    btn.style.color = 'var(--color-success)';
    setTimeout(() => {
      btn.innerHTML = originalContent;
      btn.classList.remove('copied');
      btn.style.color = '';
    }, 1500);
  }
}

// =============================================
// 한도 말풍선 (AC-13, AC-9)
// =============================================

function showLimitTooltip(triggerEl, type) {
  const tooltip = type === 'md' ? els.mdLimitTooltip : els.tagLimitTooltip;
  const rect = triggerEl.getBoundingClientRect();
  tooltip.style.bottom = `${window.innerHeight - rect.top + 8}px`;
  tooltip.style.left = `${Math.min(rect.left, window.innerWidth - 250)}px`;
  tooltip.hidden = false;

  const closeTooltip = (e) => {
    if (!tooltip.contains(e.target) && e.target !== triggerEl) {
      tooltip.hidden = true;
      document.removeEventListener('click', closeTooltip);
    }
  };
  setTimeout(() => document.addEventListener('click', closeTooltip), 0);
}

// =============================================
// 검색 & 필터 (AC-10, AC-11)
// =============================================

function handleSearchInput(e) {
  state.searchQuery = e.target.value;
  clearTimeout(state.searchDebounceTimer);
  // 300ms debounce (ui_design.md 4.3)
  state.searchDebounceTimer = setTimeout(() => {
    loadAndRenderEntries();
  }, 300);
}

function toggleFilterPanel() {
  state.filterPanelOpen = !state.filterPanelOpen;
  els.filterPanel.hidden = !state.filterPanelOpen;
  els.btnFilterToggle.setAttribute('aria-expanded', state.filterPanelOpen);
}

function handlePlatformFilter(e) {
  const btn = e.currentTarget;
  const platform = btn.dataset.platform;
  const idx = state.filters.platforms.indexOf(platform);

  if (idx === -1) {
    state.filters.platforms.push(platform);
    btn.setAttribute('aria-pressed', 'true');
  } else {
    state.filters.platforms.splice(idx, 1);
    btn.setAttribute('aria-pressed', 'false');
  }
  updateFilterActiveDot();
  loadAndRenderEntries();
}

function handlePeriodSelect(e) {
  const btn = e.currentTarget;
  const period = btn.dataset.period;
  state.filters.period = period;

  // 선택 상태 업데이트
  els.periodDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
    item.setAttribute('aria-selected', item.dataset.period === period ? 'true' : 'false');
  });

  // 직접 설정 날짜 범위 표시
  els.customDateRange.hidden = (period !== 'custom');
  els.btnPeriodFilter.classList.toggle('active', period !== 'all');

  closePeriodDropdown();
  updateFilterActiveDot();
  if (period !== 'custom') {
    loadAndRenderEntries();
  }
}

function handleTagSelect(e) {
  const btn = e.currentTarget;
  const tag = btn.dataset.tag;

  if (tag === 'all') {
    state.filters.tags = [];
    els.tagDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
      item.setAttribute('aria-selected', item.dataset.tag === 'all' ? 'true' : 'false');
    });
  } else {
    const idx = state.filters.tags.indexOf(tag);
    if (idx === -1) {
      state.filters.tags.push(tag);
      btn.setAttribute('aria-selected', 'true');
      // "전체" 선택 해제
      els.tagDropdown.querySelector('[data-tag="all"]').setAttribute('aria-selected', 'false');
    } else {
      state.filters.tags.splice(idx, 1);
      btn.setAttribute('aria-selected', 'false');
      if (state.filters.tags.length === 0) {
        els.tagDropdown.querySelector('[data-tag="all"]').setAttribute('aria-selected', 'true');
      }
    }
  }

  els.btnTagFilter.classList.toggle('active', state.filters.tags.length > 0);
  closeTagDropdown();
  updateFilterActiveDot();
  loadAndRenderEntries();
}

function handleDateRangeChange() {
  state.filters.dateFrom = els.dateFrom.value || null;
  state.filters.dateTo = els.dateTo.value || null;
  if (state.filters.period === 'custom') {
    loadAndRenderEntries();
  }
}

function handleStarredFilter() {
  state.filters.starredOnly = !state.filters.starredOnly;
  els.btnStarredFilter.setAttribute('aria-pressed', state.filters.starredOnly);
  updateFilterActiveDot();
  loadAndRenderEntries();
}

function handleJunkFilter() {
  state.filters.includeJunk = !state.filters.includeJunk;
  els.btnJunkFilter.setAttribute('aria-pressed', state.filters.includeJunk);
  updateFilterActiveDot();
  loadAndRenderEntries();
}

function resetFilters() {
  state.filters = {
    platforms: [],
    period: 'all',
    dateFrom: null,
    dateTo: null,
    tags: [],
    starredOnly: false,
    includeJunk: false,
  };
  state.searchQuery = '';
  els.searchInput.value = '';

  // UI 초기화
  document.querySelectorAll('.platform-chip').forEach(btn => btn.setAttribute('aria-pressed', 'false'));
  els.btnStarredFilter.setAttribute('aria-pressed', 'false');
  els.btnJunkFilter.setAttribute('aria-pressed', 'false');
  els.periodDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
    item.setAttribute('aria-selected', item.dataset.period === 'all' ? 'true' : 'false');
  });
  els.tagDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
    item.setAttribute('aria-selected', item.dataset.tag === 'all' ? 'true' : 'false');
  });
  els.btnPeriodFilter.classList.remove('active');
  els.btnTagFilter.classList.remove('active');
  els.customDateRange.hidden = true;
  updateFilterActiveDot();
  loadAndRenderEntries();
}

function updateFilterActiveDot() {
  const hasFilter =
    state.filters.platforms.length > 0 ||
    state.filters.period !== 'all' ||
    state.filters.tags.length > 0 ||
    state.filters.starredOnly ||
    state.filters.includeJunk;
  els.filterActiveDot.hidden = !hasFilter;
}

// 드롭다운 토글
function togglePeriodDropdown(e) {
  e.stopPropagation();
  const isOpen = !els.periodDropdown.hidden;
  closePeriodDropdown();
  closeTagDropdown();
  if (!isOpen) {
    els.periodDropdown.hidden = false;
    els.btnPeriodFilter.setAttribute('aria-expanded', 'true');
  }
}

function toggleTagDropdown(e) {
  e.stopPropagation();
  const isOpen = !els.tagDropdown.hidden;
  closePeriodDropdown();
  closeTagDropdown();
  if (!isOpen) {
    els.tagDropdown.hidden = false;
    els.btnTagFilter.setAttribute('aria-expanded', 'true');
  }
}

function closePeriodDropdown() {
  els.periodDropdown.hidden = true;
  els.btnPeriodFilter.setAttribute('aria-expanded', 'false');
}

function closeTagDropdown() {
  els.tagDropdown.hidden = true;
  els.btnTagFilter.setAttribute('aria-expanded', 'false');
}

// =============================================
// 통계 (AC-25)
// =============================================

function updateStats() {
  const now = new Date();
  const thisMonth = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');

  const thisMonthEntries = state.entries.filter(e =>
    !e.isJunk && !e.archived && e.date && e.date.startsWith(thisMonth)
  );
  els.statCount.textContent = `이번 달: ${thisMonthEntries.length}개`;

  // 최다 플랫폼
  const platformCount = {};
  state.entries.filter(e => !e.isJunk && !e.archived).forEach(e => {
    platformCount[e.platform] = (platformCount[e.platform] || 0) + 1;
  });
  const topPlatform = Object.entries(platformCount).sort((a, b) => b[1] - a[1])[0];
  els.statPlatform.textContent = topPlatform ? `최다: ${capitalize(topPlatform[0])}` : '최다: -';

  // 최다 태그
  const tagCount = {};
  state.entries.filter(e => !e.isJunk && !e.archived).forEach(e => {
    (e.tags || []).forEach(tag => {
      tagCount[tag] = (tagCount[tag] || 0) + 1;
    });
  });
  const topTag = Object.entries(tagCount).sort((a, b) => b[1] - a[1])[0];
  els.statTag.textContent = topTag ? `#${topTag[0]}` : '태그: -';
}

// =============================================
// 빈 상태 (Empty State)
// =============================================

function showEmptyState(type = 'default') {
  const messages = {
    default: { title: '아직 저장된 대화가 없어요', desc: 'AI 사이트에서 대화를 시작해 보세요' },
    search: { title: '검색 결과가 없어요', desc: '다른 키워드로 찾아보세요' },
    filter: { title: '조건에 맞는 대화가 없어요', desc: '' },
    starred: { title: '아직 별표 친 대화가 없어요', desc: '★ 아이콘을 눌러 중요한 대화를 표시해 보세요' },
  };

  const msg = messages[type] || messages.default;
  els.emptyStateTitle.textContent = msg.title;
  els.emptyStateDesc.textContent = msg.desc;
  els.btnEmptyResetFilter.hidden = (type === 'default');
  els.emptyState.hidden = false;
}

function hideEmptyState() {
  els.emptyState.hidden = true;
}

function showSkeleton(visible) {
  els.skeletonLoader.hidden = !visible;
}

// =============================================
// 용량 경고 배너 (AC-18)
// =============================================

async function checkCapacityBanner() {
  if (state.isPro) return;

  const res = await sendMsg(MSG.GET_ENTRIES, { filters: { includeArchived: true } });
  if (!res || !res.entries) return;

  const activeCount = res.entries.filter(e => !e.archived).length;

  if (activeCount >= 500) {
    els.capacityBannerText.textContent =
      '한도에 도달했어요. 새 대화는 오래된 것을 숨겨요.';
    els.btnUpgradeCapacity.hidden = false;
    els.capacityBanner.hidden = false;
  } else if (activeCount >= 400) {
    els.capacityBannerText.textContent =
      `저장 공간이 ${Math.floor(activeCount/500*100)}%가 됐어요. 백업을 추천해요!`;
    els.capacityBanner.hidden = false;
  }
}

// =============================================
// 셀렉터 에러 배너 (AC-3)
// =============================================

async function checkSelectorErrorBanner() {
  // @confidence: low — background에서 selector error flag를 전달받는 방식은 백엔드 구현에 따라 다를 수 있음
  try {
    const res = await sendMsg(MSG.GET_SETTINGS);
    if (res && res.settings && res.settings.selectorError) {
      els.errorBanner.hidden = false;
    }
  } catch (e) {
    // 무시
  }
}

// =============================================
// Pro 상태 배너 (AC-24a)
// =============================================

function showProVerifyBanner() {
  const banner = document.createElement('div');
  banner.className = 'pro-verify-banner';
  banner.setAttribute('role', 'alert');
  banner.textContent = '구독 확인이 필요해요. 인터넷 연결 시 자동으로 확인됩니다.';
  document.body.insertBefore(banner, els.searchInput.closest('.search-bar'));
}

// =============================================
// Footer Pro UI
// =============================================

function updateFooterProUI() {
  if (state.isPro) {
    els.btnUpgrade.hidden = true;
    els.proBadge.hidden = false;
  } else {
    els.btnUpgrade.hidden = false;
    els.proBadge.hidden = true;
  }
}

// =============================================
// 백업 / 복원 (AC-17)
// =============================================

async function handleBackup() {
  setButtonLoading(els.btnBackup, true);
  const res = await sendMsg(MSG.EXPORT_JSON);
  setButtonLoading(els.btnBackup, false);

  if (!res || !res.data) {
    showToast('백업 실패. 다시 시도해 주세요.', 'error');
    return;
  }

  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const dateStr = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `nugget-backup-${dateStr}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('백업 완료!', 'success');
}

function handleRestoreClick() {
  els.restoreFileInput.click();
}

async function handleRestoreFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  // 파일 입력 초기화 (같은 파일 재선택 가능하게)
  els.restoreFileInput.value = '';

  const reader = new FileReader();
  reader.onload = async (event) => {
    let data;
    try {
      data = JSON.parse(event.target.result);
    } catch {
      showModal('파일을 읽을 수 없어요', 'Nugget JSON 백업 파일인지 확인해 주세요.');
      return;
    }

    if (!data || !Array.isArray(data.entries)) {
      showModal('파일을 읽을 수 없어요', 'Nugget JSON 백업 파일인지 확인해 주세요.');
      return;
    }

    setButtonLoading(els.btnRestore, true);
    const res = await sendMsg(MSG.IMPORT_JSON, { data });
    setButtonLoading(els.btnRestore, false);

    if (res && res.success) {
      showToast(`복원 완료! ${res.imported}개 대화가 추가됐어요`, 'success');
      await loadAndRenderEntries();
    } else {
      showToast('복원 실패. 다시 시도해 주세요.', 'error');
    }
  };
  reader.readAsText(file);
}

// =============================================
// Pro 결제 (AC-22)
// @risk: payment — 결제 페이지 열기
// =============================================

async function handleUpgrade() {
  // @risk: payment
  await sendMsg(MSG.OPEN_PAYMENT_PAGE);
}

// =============================================
// 토스트 (Popup 내 인앱)
// =============================================

let toastTimer = null;

function showToast(message, type = 'success') {
  clearTimeout(toastTimer);
  els.popupToast.textContent = message;
  els.popupToast.className = 'popup-toast show';
  if (type === 'error') els.popupToast.classList.add('toast-error');
  if (type === 'warning') els.popupToast.classList.add('toast-warning');
  els.popupToast.hidden = false;

  toastTimer = setTimeout(() => {
    els.popupToast.classList.remove('show');
    setTimeout(() => { els.popupToast.hidden = true; }, 300);
  }, 2000);
}

// =============================================
// 모달 (에러 다이얼로그)
// =============================================

function showModal(title, body) {
  document.getElementById('modal-title').textContent = title;
  els.modalBody.textContent = body;
  els.modalOverlay.hidden = false;
}

function closeModal() {
  els.modalOverlay.hidden = true;
}

// =============================================
// 설정 페이지 열기
// =============================================

function openSettings() {
  chrome.runtime.openOptionsPage();
}

// =============================================
// 버튼 로딩 상태
// =============================================

function setButtonLoading(btn, loading) {
  btn.disabled = loading;
  if (loading) {
    btn._originalContent = btn.innerHTML;
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span> 처리 중...`;
  } else if (btn._originalContent) {
    btn.innerHTML = btn._originalContent;
  }
}

// =============================================
// 유틸리티
// =============================================

/**
 * HTML 이스케이프
 */
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * 속성 이스케이프
 */
function escapeAttr(str) {
  if (!str) return '';
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/**
 * 검색 키워드 하이라이팅 (AC-11)
 * HTML 엔티티를 깨뜨리지 않도록 엔티티/태그 밖의 텍스트에서만 치환
 */
function highlightText(html, query) {
  if (!query || !query.trim()) return html;
  const escaped = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  // HTML 엔티티(&amp; &lt; 등)와 태그를 건너뛰고 순수 텍스트에서만 치환
  return html.replace(/(&[#\w]+;|<[^>]+>)|([^<&]*)/gi, (match, entity, text) => {
    if (entity) return entity;
    if (!text) return match;
    return text.replace(regex, '<mark class="highlight">$1</mark>');
  });
}

/**
 * 날짜 포맷 (한국어)
 */
function formatDate(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const hour = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${month}월 ${day}일 ${hour}:${min}`;
  } catch {
    return isoString;
  }
}

/**
 * 태그 HTML 렌더링
 */
function renderTagsHtml(tags) {
  if (!tags || tags.length === 0) return '';
  return tags.map(tag => {
    const safeTag = escapeHtml(tag);
    const cls = tag.replace(/[^가-힣a-zA-Z0-9]/g, '') || 'other';
    return `<span class="tag-chip tag-chip--${cls}">${safeTag}</span>`;
  }).join('');
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// =============================================
// 이벤트 바인딩
// =============================================

function bindEvents() {
  // Today's Nugget
  els.todaysNugget.addEventListener('click', scrollToTodaysNuggetCard);
  els.btnDismissNugget.addEventListener('click', e => {
    e.stopPropagation();
    dismissTodaysNugget();
  });

  // 에러 배너 닫기
  els.btnCloseError.addEventListener('click', () => { els.errorBanner.hidden = true; });

  // 용량 배너
  els.btnCloseCapacity.addEventListener('click', () => { els.capacityBanner.hidden = true; });
  els.btnUpgradeCapacity.addEventListener('click', handleUpgrade);

  // 검색
  els.searchInput.addEventListener('input', handleSearchInput);

  // 필터 패널 토글
  els.btnFilterToggle.addEventListener('click', toggleFilterPanel);

  // 플랫폼 필터 칩들
  document.querySelectorAll('.platform-chip').forEach(btn => {
    btn.addEventListener('click', handlePlatformFilter);
  });

  // 기간 드롭다운
  els.btnPeriodFilter.addEventListener('click', togglePeriodDropdown);
  els.periodDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
    item.addEventListener('click', handlePeriodSelect);
  });

  // 날짜 범위
  els.dateFrom.addEventListener('change', handleDateRangeChange);
  els.dateTo.addEventListener('change', handleDateRangeChange);

  // 태그 드롭다운
  els.btnTagFilter.addEventListener('click', toggleTagDropdown);
  els.tagDropdown.querySelectorAll('.filter-dropdown__item').forEach(item => {
    item.addEventListener('click', handleTagSelect);
  });

  // 별표 / 잡담 토글
  els.btnStarredFilter.addEventListener('click', handleStarredFilter);
  els.btnJunkFilter.addEventListener('click', handleJunkFilter);
  els.btnFilterReset.addEventListener('click', resetFilters);
  els.btnEmptyResetFilter.addEventListener('click', resetFilters);

  // 하단 버튼
  els.btnBackup.addEventListener('click', handleBackup);
  els.btnRestore.addEventListener('click', handleRestoreClick);
  els.restoreFileInput.addEventListener('change', handleRestoreFile);
  els.btnSettings.addEventListener('click', openSettings);
  els.btnUpgrade.addEventListener('click', handleUpgrade);

  // Pro 업그레이드 (한도 말풍선)
  els.btnMdUpgrade.addEventListener('click', handleUpgrade);
  els.btnTagUpgrade.addEventListener('click', handleUpgrade);

  // 모달 닫기
  els.btnModalClose.addEventListener('click', closeModal);
  els.modalOverlay.addEventListener('click', e => {
    if (e.target === els.modalOverlay) closeModal();
  });

  // 드롭다운 외부 클릭 닫기
  document.addEventListener('click', e => {
    if (!e.target.closest('.filter-dropdown-wrap')) {
      closePeriodDropdown();
      closeTagDropdown();
    }
  });
}

// =============================================
// 진입점
// =============================================

document.addEventListener('DOMContentLoaded', init);
