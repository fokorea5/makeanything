/**
 * Nugget – Onboarding JS
 * AC-21: 설치 시 온보딩 페이지 안내
 * CSP: 인라인 스크립트 금지 (AC-29)
 */

'use strict';

// =============================================
// [v1.1] i18n / 테마 초기화
// =============================================

function initI18nAndTheme() {
  if (typeof initTheme === 'function') {
    initTheme();
  }
  if (typeof initI18n === 'function') {
    initI18n();
  }
}

// =============================================
// 초기화
// =============================================

function init() {
  initI18nAndTheme();
  bindEvents();
  // 온보딩 완료 여부와 무관하게 항상 표시
}

// =============================================
// 이벤트 바인딩
// =============================================

function bindEvents() {
  const btnStart = document.getElementById('btn-start');
  const btnProLater = document.getElementById('btn-pro-later');

  // "Nugget 시작하기" 클릭 → 탭 닫기 (AC-21)
  if (btnStart) {
    btnStart.addEventListener('click', handleStart);
  }

  // "나중에 알아보기" 클릭 → 온보딩 계속 (스크롤 무시)
  if (btnProLater) {
    btnProLater.addEventListener('click', () => {
      // Pro 섹션 스크롤
      btnStart.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }
}

// =============================================
// "시작하기" 핸들러 (AC-21)
// =============================================

async function handleStart() {
  // 온보딩 완료 플래그 저장
  try {
    await chrome.storage.local.set({ nugget_onboarding_done: true });
  } catch (e) {
    // 무시
  }

  // 현재 탭 닫기
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      await chrome.tabs.remove(tabs[0].id);
    }
  } catch (e) {
    // 탭을 닫을 수 없으면 팝업으로 이동
    window.close();
  }
}

// =============================================
// 진입점
// =============================================

document.addEventListener('DOMContentLoaded', init);
