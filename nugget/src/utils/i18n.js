/**
 * Nugget – AI Chat Memory: 자체 i18n 시스템
 *
 * DESIGN.md 섹션 15, 17.3 기준.
 * Chrome의 chrome.i18n.getMessage()는 런타임 언어 변경 불가이므로
 * 자체 i18n 시스템을 구현한다 (AC-V11-10 ~ AC-V11-14).
 *
 * 지원 언어: 'ko' | 'en' (AC-V11-11)
 * 기본값: 'auto' → navigator.language 기반 감지 (AC-V11-13)
 * 폴백: 'ko' (FALLBACK_LANGUAGE, AC-V11-11)
 *
 * 사용 패턴 (HTML):
 *   <span data-i18n="popup_title">Nugget</span>
 *   <input data-i18n-placeholder="popup_search_placeholder">
 *
 * 사용 패턴 (JS):
 *   await initI18n();
 *   toast.textContent = t('toast_saved');
 */

'use strict';

// ============================================================
// 상수
// ============================================================

const SUPPORTED_LANGUAGES = ['ko', 'en'];
const FALLBACK_LANGUAGE = 'ko';

// ============================================================
// 내부 상태
// ============================================================

/** 현재 활성 언어 코드 @type {string} */
let _currentLang = FALLBACK_LANGUAGE;

/** 로드된 번역 사전 캐시 @type {Object.<string, Object>} */
const _translationCache = {};

// ============================================================
// 언어 감지 및 resolve (AC-V11-13)
// ============================================================

/**
 * 현재 언어 설정을 resolve하여 실제 언어 코드 반환
 * 'auto'이면 navigator.language 기반으로 판별
 * @param {string} langSetting - 'ko' | 'en' | 'auto'
 * @returns {string} 'ko' | 'en'
 */
function resolveLanguage(langSetting) {
  if (langSetting === 'ko' || langSetting === 'en') {
    return langSetting;
  }

  // 'auto' 또는 알 수 없는 값: navigator.language 기반 감지 (AC-V11-13)
  try {
    const navLang = navigator.language || '';
    if (navLang.startsWith('ko')) return 'ko';
    if (navLang.startsWith('en')) return 'en';
    // 미지원 언어 → ko 폴백 (AC-V11-13)
    return FALLBACK_LANGUAGE;
  } catch (e) {
    return FALLBACK_LANGUAGE;
  }
}

// ============================================================
// 번역 사전 로드 (AC-V11-10)
// ============================================================

/**
 * 번역 사전을 로드 (chrome.runtime.getURL로 JSON fetch)
 * 이미 로드된 언어면 캐시 반환
 * @param {string} lang - 'ko' | 'en'
 * @returns {Promise<Object>} 번역 키-값 객체
 */
async function loadTranslations(lang) {
  // 캐시 히트
  if (_translationCache[lang]) {
    return _translationCache[lang];
  }

  try {
    const url = chrome.runtime.getURL(`src/i18n/${lang}.json`);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    _translationCache[lang] = data;
    return data;
  } catch (e) {
    console.warn(`[Nugget/i18n] ${lang}.json 로드 실패:`, e);
    // 폴백: 빈 객체 (키를 그대로 반환)
    _translationCache[lang] = {};
    return {};
  }
}

// ============================================================
// 번역 키 조회 (AC-V11-10)
// ============================================================

/**
 * 번역 키에 해당하는 텍스트 반환
 * 키가 없으면 폴백 언어(ko)에서 찾고, 그래도 없으면 키 자체를 반환
 * @param {string} key - 번역 키 (예: 'popup_title')
 * @param {Object} [params] - 치환 파라미터 (예: { count: 5 } → "{count}개" 에서 치환)
 * @returns {string} 번역된 문자열
 */
function t(key, params) {
  // 현재 언어에서 조회
  const current = _translationCache[_currentLang];
  let text = current && typeof current[key] === 'string' ? current[key] : null;

  // 현재 언어에 없으면 폴백 언어(ko)에서 조회
  if (text === null && _currentLang !== FALLBACK_LANGUAGE) {
    const fallback = _translationCache[FALLBACK_LANGUAGE];
    text = fallback && typeof fallback[key] === 'string' ? fallback[key] : null;
  }

  // 그래도 없으면 키 자체를 반환
  if (text === null) {
    text = key;
  }

  // 파라미터 치환 (예: "{count}개" → "5개")
  if (params && typeof params === 'object') {
    text = text.replace(/\{(\w+)\}/g, (match, paramKey) => {
      return Object.prototype.hasOwnProperty.call(params, paramKey)
        ? String(params[paramKey])
        : match;
    });
  }

  return text;
}

/**
 * 현재 로드된 언어 코드 반환
 * @returns {string} 'ko' | 'en'
 */
function getCurrentLang() {
  return _currentLang;
}

// ============================================================
// DOM 적용 (AC-V11-10, AC-V11-12)
// ============================================================

/**
 * DOM의 data-i18n 속성을 기반으로 텍스트 업데이트
 * 언어 변경 시 호출하여 페이지 전체를 갱신
 * @param {Element} [root=document] - 탐색 루트 요소
 */
function applyI18nToDOM(root) {
  const searchRoot = root || document;

  // data-i18n 속성: textContent 교체
  try {
    const els = searchRoot.querySelectorAll('[data-i18n]');
    for (const el of els) {
      const key = el.getAttribute('data-i18n');
      if (key) {
        el.textContent = t(key);
      }
    }
  } catch (e) {
    console.warn('[Nugget/i18n] data-i18n 적용 오류:', e);
  }

  // data-i18n-placeholder 속성: placeholder 교체
  try {
    const els = searchRoot.querySelectorAll('[data-i18n-placeholder]');
    for (const el of els) {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) {
        el.setAttribute('placeholder', t(key));
      }
    }
  } catch (e) {
    console.warn('[Nugget/i18n] data-i18n-placeholder 적용 오류:', e);
  }

  // data-i18n-title 속성: title 교체
  try {
    const els = searchRoot.querySelectorAll('[data-i18n-title]');
    for (const el of els) {
      const key = el.getAttribute('data-i18n-title');
      if (key) {
        el.setAttribute('title', t(key));
      }
    }
  } catch (e) {
    console.warn('[Nugget/i18n] data-i18n-title 적용 오류:', e);
  }

  // data-i18n-aria-label 속성: aria-label 교체
  try {
    const els = searchRoot.querySelectorAll('[data-i18n-aria-label]');
    for (const el of els) {
      const key = el.getAttribute('data-i18n-aria-label');
      if (key) {
        el.setAttribute('aria-label', t(key));
      }
    }
  } catch (e) {
    console.warn('[Nugget/i18n] data-i18n-aria-label 적용 오류:', e);
  }
}

// ============================================================
// 초기화 (AC-V11-10, AC-V11-13)
// ============================================================

/**
 * i18n 초기화: 설정에서 언어 로드 → 번역 사전 로드 → DOM 적용
 * HTML에서 data-i18n 속성을 가진 요소의 textContent를 번역으로 교체
 * @returns {Promise<void>}
 */
async function initI18n() {
  try {
    // storage에서 언어 설정 로드
    const result = await new Promise((resolve) => {
      chrome.storage.local.get(['nugget_settings'], resolve);
    });

    const settings = result.nugget_settings;
    const langSetting = (settings && settings.language) ? settings.language : 'auto';
    const resolvedLang = resolveLanguage(langSetting);

    // 번역 사전 로드 (현재 언어 + 폴백 언어)
    await loadTranslations(resolvedLang);
    if (resolvedLang !== FALLBACK_LANGUAGE) {
      await loadTranslations(FALLBACK_LANGUAGE);
    }

    _currentLang = resolvedLang;

    // DOM에 번역 적용
    applyI18nToDOM(document);
  } catch (e) {
    console.warn('[Nugget/i18n] initI18n 오류:', e);
    // 오류 시 폴백 언어 유지
    try {
      await loadTranslations(FALLBACK_LANGUAGE);
      _currentLang = FALLBACK_LANGUAGE;
      applyI18nToDOM(document);
    } catch (e2) {
      // 조용히 실패
    }
  }
}

/**
 * 언어 변경 적용: 새 언어로 번역 사전 로드 후 DOM 갱신
 * Options 페이지에서 즉시 반영용 (AC-V11-12)
 * @param {string} lang - 'ko' | 'en'
 * @returns {Promise<void>}
 */
async function changeLanguage(lang) {
  const resolved = resolveLanguage(lang);
  await loadTranslations(resolved);
  if (resolved !== FALLBACK_LANGUAGE) {
    await loadTranslations(FALLBACK_LANGUAGE);
  }
  _currentLang = resolved;
  applyI18nToDOM(document);
}

// ============================================================
// Content Script 토스트용 언어 변경 감지 (AC-V11-12, AC-V11-14)
// ============================================================

/**
 * storage.onChanged 리스너로 언어 설정 변경 감지
 * Content Script 토스트 메시지에 새 언어 자동 적용
 * @param {Function} callback - 언어 변경 시 호출할 함수 (lang 문자열 전달)
 */
function onLanguageChange(callback) {
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== 'local') return;
      if (!changes.nugget_settings) return;

      const newSettings = changes.nugget_settings.newValue;
      if (!newSettings || !newSettings.language) return;

      const newLang = resolveLanguage(newSettings.language);
      if (newLang !== _currentLang) {
        // 번역 사전 로드 후 콜백 호출
        loadTranslations(newLang).then(() => {
          if (newLang !== FALLBACK_LANGUAGE) {
            return loadTranslations(FALLBACK_LANGUAGE);
          }
        }).then(() => {
          _currentLang = newLang;
          if (typeof callback === 'function') {
            callback(newLang);
          }
        }).catch(e => {
          console.debug('[Nugget/i18n] 언어 변경 처리 오류:', e);
        });
      }
    });
  } catch (e) {
    console.debug('[Nugget/i18n] onLanguageChange 등록 오류:', e);
  }
}
