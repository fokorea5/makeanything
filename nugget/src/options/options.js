/**
 * Nugget – Options JS
 * DESIGN.md 섹션 4(메시징), 8(통합 계약) 준수
 * CSP: 인라인 스크립트 금지 (AC-29)
 */

'use strict';

// =============================================
// 메시지 타입 (DESIGN.md 8.2)
// =============================================

const MSG = {
  GET_SETTINGS: 'GET_SETTINGS',
  UPDATE_SETTINGS: 'UPDATE_SETTINGS',
  GET_JUNK_KEYWORDS: 'GET_JUNK_KEYWORDS',
  UPDATE_JUNK_KEYWORDS: 'UPDATE_JUNK_KEYWORDS',
  GET_PRO_STATUS: 'GET_PRO_STATUS',
  OPEN_PAYMENT_PAGE: 'OPEN_PAYMENT_PAGE',
  EXPORT_JSON: 'EXPORT_JSON',
  IMPORT_JSON: 'IMPORT_JSON',
  EXPORT_MARKDOWN_FILE: 'EXPORT_MARKDOWN_FILE',
  EXPORT_PDF: 'EXPORT_PDF',
  GET_ENTRIES: 'GET_ENTRIES',
};

// =============================================
// 상태
// =============================================

const state = {
  settings: null,
  keywords: [],
  isPro: false,
  proExpired: false,
  entryCount: 0,
};

// =============================================
// DOM 참조
// =============================================

const $ = id => document.getElementById(id);

const els = {
  proVerifyBanner: $('pro-verify-banner'),
  toggleToast: $('toggle-toast'),
  toggleJunkFilter: $('toggle-junk-filter'),
  shortcutDisplay: $('shortcut-display'),
  btnChangeShortcut: $('btn-change-shortcut'),
  // [v1.1] 언어/테마 설정
  selectLanguage: $('select-language'),
  langSavedIndicator: $('lang-saved-indicator'),
  btnThemeLight: $('btn-theme-light'),
  btnThemeDark: $('btn-theme-dark'),
  btnThemeSystem: $('btn-theme-system'),
  themeSavedIndicator: $('theme-saved-indicator'),
  keywordsContainer: $('keywords-container'),
  keywordInput: $('keyword-input'),
  btnAddKeyword: $('btn-add-keyword'),
  storageCount: $('storage-count'),
  storagePercent: $('storage-percent'),
  storageProgressBar: $('storage-progress-bar'),
  storageProgressFill: $('storage-progress-fill'),
  btnExportJson: $('btn-export-json'),
  btnImportJson: $('btn-import-json'),
  btnExportMd: $('btn-export-md'),
  btnExportPdf: $('btn-export-pdf'),
  proPlanLabel: $('pro-plan-label'),
  upgradeSection: $('upgrade-section'),
  proActiveSection: $('pro-active-section'),
  btnProUpgrade: $('btn-pro-upgrade'),
  versionInfo: $('version-info'),
  importFileInput: $('import-file-input'),
  optionsToast: $('options-toast'),
  modalOverlay: $('modal-overlay'),
  modalBody: $('modal-body'),
  btnModalClose: $('btn-modal-close'),
};

// =============================================
// 메시지 전송
// =============================================

async function sendMsg(type, payload = {}) {
  try {
    return await chrome.runtime.sendMessage({ type, payload });
  } catch (err) {
    console.error('[Nugget Options] sendMsg error:', type, err);
    return null;
  }
}

// =============================================
// [v1.1] i18n / 테마 초기화
// =============================================

function initI18nAndTheme() {
  if (typeof applyTheme === 'function') {
    applyTheme();
  }
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
  await loadAll();
}

async function loadAll() {
  const [settingsRes, keywordsRes, proRes, entriesRes] = await Promise.all([
    sendMsg(MSG.GET_SETTINGS),
    sendMsg(MSG.GET_JUNK_KEYWORDS),
    sendMsg(MSG.GET_PRO_STATUS),
    sendMsg(MSG.GET_ENTRIES, { filters: { includeArchived: true } }),
  ]);

  if (settingsRes) {
    state.settings = settingsRes.settings;
    applySettings();
  }

  if (keywordsRes) {
    state.keywords = keywordsRes.keywords || [];
    renderKeywords();
  }

  if (proRes) {
    state.isPro = proRes.isPro;
    state.proExpired = !!proRes.expired;
    updateProUI();
  }

  if (entriesRes && entriesRes.entries) {
    state.entryCount = entriesRes.entries.filter(e => !e.archived).length;
    updateStorageUI();
  }

  // 버전 정보
  try {
    const manifest = chrome.runtime.getManifest();
    els.versionInfo.textContent = `Nugget v${manifest.version}`;
  } catch {
    els.versionInfo.textContent = 'Nugget v1.0.0';
  }
}

// =============================================
// 설정 적용 (UI)
// =============================================

function applySettings() {
  if (!state.settings) return;
  els.toggleToast.checked = !!state.settings.toastEnabled;
  els.toggleJunkFilter.checked = !!state.settings.junkFilterEnabled;
  els.shortcutDisplay.textContent = state.settings.shortcutKey || 'Ctrl+Shift+S';

  // [v1.1] 언어 설정 UI 동기화
  if (els.selectLanguage) {
    const lang = state.settings.language || 'auto';
    els.selectLanguage.value = lang;
  }

  // [v1.1] 테마 설정 UI 동기화
  const theme = state.settings.theme || 'system';
  updateThemeButtons(theme);
}

// =============================================
// [v1.1] 테마 버튼 UI 업데이트
// =============================================

function updateThemeButtons(activeTheme) {
  const buttons = [els.btnThemeLight, els.btnThemeDark, els.btnThemeSystem];
  buttons.forEach(btn => {
    if (!btn) return;
    const val = btn.getAttribute('data-theme-value');
    const isActive = val === activeTheme;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
}

// =============================================
// [v1.1] 저장 완료 인디케이터 표시
// =============================================

function showSavedIndicator(indicatorEl) {
  if (!indicatorEl) return;
  indicatorEl.classList.add('visible');
  setTimeout(() => {
    indicatorEl.classList.remove('visible');
  }, 500);
}

// =============================================
// 설정 저장
// =============================================

async function saveSetting(key, value) {
  const res = await sendMsg(MSG.UPDATE_SETTINGS, { key, value });
  if (res && res.success) {
    // 저장 완료 시각적 피드백 (ui_design.md 5.4)
    showToast('설정이 저장됐어요', 'success');
  }
}

// =============================================
// [v1.1] 언어 변경 핸들러
// =============================================

async function handleLanguageChange() {
  const lang = els.selectLanguage.value;

  // 즉시 i18n 재적용
  if (typeof setLanguage === 'function') {
    setLanguage(lang);
  } else if (typeof initI18n === 'function') {
    initI18n(lang);
  }

  // 저장 완료 인디케이터 표시
  showSavedIndicator(els.langSavedIndicator);

  // chrome.storage에 저장
  await sendMsg(MSG.UPDATE_SETTINGS, { key: 'language', value: lang });
}

// =============================================
// [v1.1] 테마 변경 핸들러
// =============================================

async function handleThemeChange(e) {
  const themeValue = e.currentTarget.getAttribute('data-theme-value');
  if (!themeValue) return;

  // 즉시 테마 적용
  if (typeof applyTheme === 'function') {
    applyTheme(themeValue);
  }

  // 버튼 UI 업데이트
  updateThemeButtons(themeValue);

  // 저장 완료 인디케이터 표시
  showSavedIndicator(els.themeSavedIndicator);

  // chrome.storage에 저장
  await sendMsg(MSG.UPDATE_SETTINGS, { key: 'theme', value: themeValue });
}

// =============================================
// 잡담 키워드 관리 (AC-6)
// =============================================

function renderKeywords() {
  els.keywordsContainer.innerHTML = '';
  state.keywords.forEach((kw, idx) => {
    const chip = createKeywordChip(kw, idx);
    els.keywordsContainer.appendChild(chip);
  });
}

function createKeywordChip(keyword, idx) {
  const chip = document.createElement('div');
  chip.className = 'keyword-chip';
  chip.setAttribute('data-keyword', keyword);

  const text = document.createElement('span');
  text.textContent = keyword;

  const delBtn = document.createElement('button');
  delBtn.className = 'keyword-chip__delete';
  delBtn.setAttribute('aria-label', `${keyword} 삭제`);
  delBtn.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
      <line x1="2" y1="2" x2="10" y2="10"/>
      <line x1="10" y1="2" x2="2" y2="10"/>
    </svg>
  `;
  delBtn.addEventListener('click', () => deleteKeyword(keyword));

  chip.appendChild(text);
  chip.appendChild(delBtn);
  return chip;
}

function showAddKeywordInput() {
  els.keywordInput.hidden = false;
  els.keywordInput.focus();
  els.btnAddKeyword.textContent = '완료';
  els.btnAddKeyword.onclick = addKeyword;
}

async function addKeyword() {
  const kw = els.keywordInput.value.trim().toLowerCase();
  if (!kw) {
    els.keywordInput.hidden = true;
    els.btnAddKeyword.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <line x1="7" y1="2" x2="7" y2="12"/>
        <line x1="2" y1="7" x2="12" y2="7"/>
      </svg>
      추가
    `;
    els.btnAddKeyword.onclick = showAddKeywordInput;
    return;
  }

  if (state.keywords.includes(kw)) {
    showToast('이미 있는 키워드예요', 'error');
    return;
  }

  state.keywords.push(kw);
  await saveKeywords();
  els.keywordInput.value = '';
  els.keywordInput.hidden = true;
  els.btnAddKeyword.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
      <line x1="7" y1="2" x2="7" y2="12"/>
      <line x1="2" y1="7" x2="12" y2="7"/>
    </svg>
    추가
  `;
  els.btnAddKeyword.onclick = showAddKeywordInput;
  renderKeywords();
}

async function deleteKeyword(keyword) {
  state.keywords = state.keywords.filter(k => k !== keyword);
  await saveKeywords();
  renderKeywords();
  showToast(`'${keyword}' 삭제됨`, 'success');
}

async function saveKeywords() {
  const res = await sendMsg(MSG.UPDATE_JUNK_KEYWORDS, { keywords: state.keywords });
  if (!res || !res.success) {
    showToast('저장 실패. 다시 시도해 주세요.', 'error');
  }
}

// =============================================
// 저장 현황 UI (AC-18)
// =============================================

function updateStorageUI() {
  const maxFree = (state.settings && state.settings.maxFreeEntries) || 500;
  const count = state.entryCount;
  const percent = state.isPro ? 0 : Math.min(100, Math.round(count / maxFree * 100));

  if (state.isPro) {
    els.storageCount.textContent = `저장된 대화: ${count}개 (무제한)`;
    els.storagePercent.textContent = '';
    els.storageProgressFill.style.width = '0%';
  } else {
    els.storageCount.textContent = `저장된 대화: ${count} / ${maxFree}개`;
    els.storagePercent.textContent = `${percent}%`;
    els.storageProgressFill.style.width = `${percent}%`;
    els.storageProgressBar.setAttribute('aria-valuenow', percent);

    // 색상 (ui_design.md 3.2.3)
    els.storageProgressFill.classList.remove('progress-bar__fill--warning', 'progress-bar__fill--error');
    if (percent >= 100) {
      els.storageProgressFill.classList.add('progress-bar__fill--error');
    } else if (percent >= 80) {
      els.storageProgressFill.classList.add('progress-bar__fill--warning');
    }
  }
}

// =============================================
// Pro UI
// =============================================

function updateProUI() {
  if (state.isPro) {
    els.proPlanLabel.textContent = 'Pro 플랜 (활성)';
    els.proPlanLabel.classList.add('is-pro');
    els.upgradeSection.hidden = true;
    els.proActiveSection.hidden = false;
    // Pro 전용 내보내기 버튼 활성화
    els.btnExportMd.disabled = false;
    els.btnExportPdf.disabled = false;
  } else {
    els.proPlanLabel.textContent = '현재: 무료 플랜';
    els.proPlanLabel.classList.remove('is-pro');
    els.upgradeSection.hidden = false;
    els.proActiveSection.hidden = true;
    els.btnExportMd.disabled = true;
    els.btnExportPdf.disabled = true;
  }

  if (state.proExpired) {
    els.proVerifyBanner.hidden = false;
  }
}

// =============================================
// 백업 / 복원 (AC-17)
// =============================================

async function handleExportJson() {
  setButtonLoading(els.btnExportJson, true);
  const res = await sendMsg(MSG.EXPORT_JSON);
  setButtonLoading(els.btnExportJson, false);

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

function handleImportClick() {
  els.importFileInput.click();
}

async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  els.importFileInput.value = '';

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

    setButtonLoading(els.btnImportJson, true);
    const res = await sendMsg(MSG.IMPORT_JSON, { data });
    setButtonLoading(els.btnImportJson, false);

    if (res && res.success) {
      showToast(`복원 완료! ${res.imported}개 대화가 추가됐어요`, 'success');
      // 저장 현황 업데이트
      const entriesRes = await sendMsg(MSG.GET_ENTRIES, { filters: { includeArchived: true } });
      if (entriesRes && entriesRes.entries) {
        state.entryCount = entriesRes.entries.filter(e => !e.archived).length;
        updateStorageUI();
      }
    } else {
      showToast('복원 실패. 다시 시도해 주세요.', 'error');
    }
  };
  reader.readAsText(file);
}

// Pro 전용 내보내기 (AC-18)
async function handleExportMd() {
  if (!state.isPro) return;
  setButtonLoading(els.btnExportMd, true);
  const res = await sendMsg(MSG.EXPORT_MARKDOWN_FILE);
  setButtonLoading(els.btnExportMd, false);

  if (res && res.success && res.markdown) {
    const blob = new Blob([res.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const dateStr = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `nugget-export-${dateStr}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Markdown 내보내기 완료!', 'success');
  } else {
    showToast('내보내기 실패. 다시 시도해 주세요.', 'error');
  }
}

async function handleExportPdf() {
  if (!state.isPro) return;
  setButtonLoading(els.btnExportPdf, true);
  const res = await sendMsg(MSG.EXPORT_PDF);
  setButtonLoading(els.btnExportPdf, false);

  if (res && res.success) {
    showToast('PDF 내보내기 완료!', 'success');
  } else {
    showToast('PDF 내보내기 실패. 다시 시도해 주세요.', 'error');
  }
}

// =============================================
// Pro 업그레이드 (AC-22)
// @risk: payment — 결제 페이지 열기
// =============================================

async function handleUpgrade() {
  // @risk: payment
  await sendMsg(MSG.OPEN_PAYMENT_PAGE);
}

// =============================================
// 단축키 변경 안내
// =============================================

function handleChangeShortcut() {
  // chrome://extensions/shortcuts 로 이동 안내
  // 직접 열 수 없으므로 안내 토스트 표시
  showToast('Chrome 설정 > 확장 > 단축키에서 변경할 수 있어요', 'info');
  // @confidence: low — chrome://extensions/shortcuts는 직접 열 수 없어 안내만 함
}

// =============================================
// 유틸리티
// =============================================

function setButtonLoading(btn, loading) {
  btn.disabled = loading;
  if (loading) {
    btn._originalContent = btn.innerHTML;
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span> 처리 중...`;
  } else if (btn._originalContent) {
    btn.innerHTML = btn._originalContent;
    btn.disabled = false;
  }
}

let toastTimer = null;

function showToast(message, type = 'success') {
  clearTimeout(toastTimer);
  els.optionsToast.textContent = message;
  els.optionsToast.className = 'options-toast show';
  if (type === 'error') els.optionsToast.classList.add('toast-error');
  els.optionsToast.hidden = false;

  toastTimer = setTimeout(() => {
    els.optionsToast.classList.remove('show');
    setTimeout(() => { els.optionsToast.hidden = true; }, 300);
  }, 2000);
}

function showModal(title, body) {
  document.getElementById('modal-title').textContent = title;
  els.modalBody.textContent = body;
  els.modalOverlay.hidden = false;
}

function closeModal() {
  els.modalOverlay.hidden = true;
}

// =============================================
// 이벤트 바인딩
// =============================================

function bindEvents() {
  // [v1.1] 언어 변경
  if (els.selectLanguage) {
    els.selectLanguage.addEventListener('change', handleLanguageChange);
  }

  // [v1.1] 테마 변경 버튼들
  [els.btnThemeLight, els.btnThemeDark, els.btnThemeSystem].forEach(btn => {
    if (btn) btn.addEventListener('click', handleThemeChange);
  });

  // 토스트 알림 토글 (AC-27)
  els.toggleToast.addEventListener('change', () => {
    saveSetting('toastEnabled', els.toggleToast.checked);
  });

  // 잡담 필터 토글 (AC-27)
  els.toggleJunkFilter.addEventListener('change', () => {
    saveSetting('junkFilterEnabled', els.toggleJunkFilter.checked);
  });

  // 단축키 변경
  els.btnChangeShortcut.addEventListener('click', handleChangeShortcut);

  // 키워드 추가 버튼
  els.btnAddKeyword.addEventListener('click', showAddKeywordInput);

  // 키워드 입력 Enter
  els.keywordInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') addKeyword();
    if (e.key === 'Escape') {
      els.keywordInput.hidden = true;
      els.keywordInput.value = '';
    }
  });

  // 데이터 내보내기/가져오기
  els.btnExportJson.addEventListener('click', handleExportJson);
  els.btnImportJson.addEventListener('click', handleImportClick);
  els.importFileInput.addEventListener('change', handleImportFile);
  els.btnExportMd.addEventListener('click', handleExportMd);
  els.btnExportPdf.addEventListener('click', handleExportPdf);

  // Pro 업그레이드
  els.btnProUpgrade.addEventListener('click', handleUpgrade);

  // 모달
  els.btnModalClose.addEventListener('click', closeModal);
  els.modalOverlay.addEventListener('click', e => {
    if (e.target === els.modalOverlay) closeModal();
  });
}

// =============================================
// 진입점
// =============================================

document.addEventListener('DOMContentLoaded', init);
