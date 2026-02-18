/**
 * Nugget – AI Chat Memory: 테마 관리 유틸리티
 *
 * DESIGN.md 섹션 16, 17.4 기준.
 * CSS 커스텀 속성(변수)으로 라이트/다크/시스템 3가지 테마를 관리한다 (AC-V11-15 ~ AC-V11-20).
 *
 * 적용 방식:
 *   1. initTheme() 호출 → nugget_settings.theme 읽기
 *   2. resolveTheme()로 실제 테마 결정 ('light' | 'dark')
 *   3. applyTheme()로 <html data-theme="..."> 설정
 *   4. CSS [data-theme] 셀렉터가 변수 자동 전환
 *   5. 'system' 모드: prefers-color-scheme 미디어쿼리 리스너 등록 (AC-V11-20)
 */

'use strict';

// ============================================================
// 상수
// ============================================================

const SUPPORTED_THEMES = ['light', 'dark', 'system'];
const DEFAULT_THEME = 'system';

// ============================================================
// 내부 상태
// ============================================================

/** 현재 테마 설정 ('light' | 'dark' | 'system') @type {string} */
let _currentThemeSetting = DEFAULT_THEME;

/** 시스템 테마 변경 미디어쿼리 리스너 참조 (제거용) @type {Function|null} */
let _systemThemeListener = null;

/** prefers-color-scheme 미디어쿼리 @type {MediaQueryList|null} */
let _darkModeQuery = null;

// ============================================================
// 테마 resolve (AC-V11-16, AC-V11-17)
// ============================================================

/**
 * 테마 설정을 resolve하여 실제 테마 반환
 * 'system'이면 OS 다크모드 여부로 판별
 * @param {string} themeSetting - 'light' | 'dark' | 'system'
 * @returns {string} 'light' | 'dark'
 */
function resolveTheme(themeSetting) {
  if (themeSetting === 'light') return 'light';
  if (themeSetting === 'dark') return 'dark';

  // 'system' 또는 알 수 없는 값: OS 다크모드 감지 (AC-V11-20)
  try {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  } catch (e) {
    // matchMedia 미지원 환경 → 라이트 폴백
    return 'light';
  }
}

// ============================================================
// 테마 적용 (AC-V11-15, AC-V11-18)
// ============================================================

/**
 * 테마 변경 적용: <html>의 data-theme 속성 변경
 * CSS [data-theme="dark"] 셀렉터가 변수 값을 자동 전환
 * @param {string} theme - 'light' | 'dark'
 */
function applyTheme(theme) {
  try {
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    console.warn('[Nugget/theme] applyTheme 오류:', e);
  }
}

// ============================================================
// 시스템 테마 감지 리스너 (AC-V11-20)
// ============================================================

/**
 * 시스템 테마 변경 감지 리스너 등록
 * 'system' 설정일 때만 활성화
 * prefers-color-scheme 변경 시 applyTheme() 자동 호출
 * @param {string} themeSetting - 현재 테마 설정 ('light'|'dark'|'system')
 */
function watchSystemTheme(themeSetting) {
  // 이전 리스너 제거
  if (_darkModeQuery && _systemThemeListener) {
    try {
      _darkModeQuery.removeEventListener('change', _systemThemeListener);
    } catch (e) {
      // 구형 브라우저: removeListener 사용
      try {
        _darkModeQuery.removeListener(_systemThemeListener);
      } catch (e2) {
        // 무시
      }
    }
    _systemThemeListener = null;
  }

  // 'system' 모드에서만 리스너 등록 (AC-V11-20)
  if (themeSetting !== 'system') return;

  try {
    _darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

    _systemThemeListener = (e) => {
      // OS 다크모드 변경 시 실시간 반영 (AC-V11-20)
      applyTheme(e.matches ? 'dark' : 'light');
    };

    // 모던 방식
    try {
      _darkModeQuery.addEventListener('change', _systemThemeListener);
    } catch (e) {
      // 구형 Safari 등 — addListener 사용
      _darkModeQuery.addListener(_systemThemeListener);
    }
  } catch (e) {
    console.debug('[Nugget/theme] watchSystemTheme 등록 오류:', e);
  }
}

// ============================================================
// 초기화 (AC-V11-15 ~ AC-V11-20)
// ============================================================

/**
 * 테마 초기화: 설정 로드 → <html>에 data-theme 속성 설정
 * system 모드일 때 prefers-color-scheme 미디어쿼리 리스너 등록
 * @returns {Promise<void>}
 */
async function initTheme() {
  try {
    // storage에서 테마 설정 로드
    const result = await new Promise((resolve) => {
      chrome.storage.local.get(['nugget_settings'], resolve);
    });

    const settings = result.nugget_settings;
    const themeSetting = (settings && settings.theme) ? settings.theme : DEFAULT_THEME;

    _currentThemeSetting = SUPPORTED_THEMES.includes(themeSetting) ? themeSetting : DEFAULT_THEME;

    // 실제 테마 결정 및 적용
    const resolvedTheme = resolveTheme(_currentThemeSetting);
    applyTheme(resolvedTheme);

    // 시스템 모드인 경우 OS 변경 리스너 등록 (AC-V11-20)
    watchSystemTheme(_currentThemeSetting);
  } catch (e) {
    console.warn('[Nugget/theme] initTheme 오류:', e);
    // 오류 시 라이트 테마 폴백
    applyTheme('light');
  }
}

/**
 * 테마 설정 변경 적용 (Options 페이지 즉시 반영용)
 * @param {string} themeSetting - 'light' | 'dark' | 'system'
 */
function changeTheme(themeSetting) {
  _currentThemeSetting = SUPPORTED_THEMES.includes(themeSetting) ? themeSetting : DEFAULT_THEME;
  const resolved = resolveTheme(_currentThemeSetting);
  applyTheme(resolved);
  watchSystemTheme(_currentThemeSetting);
}

/**
 * 현재 테마 설정 반환
 * @returns {string} 'light' | 'dark' | 'system'
 */
function getCurrentThemeSetting() {
  return _currentThemeSetting;
}

// ============================================================
// storage 변경 감지 (Options → 다른 페이지 동기화)
// ============================================================

/**
 * storage.onChanged 리스너로 테마 설정 변경 감지
 * @param {Function} [callback] - 테마 변경 시 호출할 함수 (theme 문자열 전달)
 */
function onThemeChange(callback) {
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== 'local') return;
      if (!changes.nugget_settings) return;

      const newSettings = changes.nugget_settings.newValue;
      if (!newSettings || !newSettings.theme) return;

      const newThemeSetting = newSettings.theme;
      if (newThemeSetting !== _currentThemeSetting) {
        changeTheme(newThemeSetting);
        if (typeof callback === 'function') {
          callback(resolveTheme(newThemeSetting));
        }
      }
    });
  } catch (e) {
    console.debug('[Nugget/theme] onThemeChange 등록 오류:', e);
  }
}
