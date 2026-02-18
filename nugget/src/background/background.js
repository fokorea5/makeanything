/**
 * Nugget – AI Chat Memory: Background Service Worker
 *
 * DESIGN.md 섹션 9.2 시그니처 사양 기준.
 * 모든 데이터 조작의 단일 진입점 (AC-28: Service Worker 상태는 chrome.storage에만 저장).
 *
 * ExtensionPay 연동 (DESIGN.md 섹션 7):
 *   - importScripts로 ExtPay.js 로드
 *   - startBackground() 최초 1회 호출
 *   - 콜백 내부에서 반드시 재선언 (MV3 컨텍스트 손실 대응)
 */

// @risk: 결제
// ExtPay 라이브러리 로드 (번들러 없이 직접 복사 방식, DESIGN.md 섹션 11 제약 6)
importScripts('src/lib/ExtPay.js');

// ExtensionPay 초기화 (최초 1회, AC-22)
// @risk: 결제 exception_policy: fail-open (startBackground 실패해도 무료 기능은 동작해야 함)
const extpay = ExtPay('nugget-ai-chat-memory'); // NUGGET_EXTENSION_ID
try {
  extpay.startBackground();
} catch (e) {
  console.error('[Nugget] ExtPay startBackground 실패:', e);
  // 결제 연동 실패해도 무료 기능은 동작
}

// ============================================================
// Storage 키 상수 (DESIGN.md 섹션 8.3)
// ============================================================
const STORAGE_KEYS = {
  ENTRIES: 'nugget_entries',
  SETTINGS: 'nugget_settings',
  JUNK_KEYWORDS: 'nugget_junk_keywords',
  PRO_CACHE: 'nugget_pro_cache',
  TODAYS_NUGGET_DISMISSED: 'nugget_todays_nugget_dismissed',
  CUSTOM_TAGS: 'nugget_custom_tags'
};

// ============================================================
// 기본값
// ============================================================

/** @returns {NuggetSettings} */
function defaultSettings() {
  const now = new Date();
  const firstOfMonth = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  return {
    toastEnabled: true,
    junkFilterEnabled: true,
    shortcutKey: 'Ctrl+Shift+S',
    maxFreeEntries: 500,
    isPro: false,
    mdCopyCount: 0,
    mdCopyResetDate: firstOfMonth.toISOString().slice(0, 10)
  };
}

const DEFAULT_JUNK_KEYWORDS = [
  '안녕', '고마워', '감사', 'ㅋㅋ', 'ㅎㅎ', 'ㅠㅠ', '오케이', 'ㅇㅋ', '굿',
  'hi', 'hello', 'thanks', 'thank you', 'ok', 'okay', 'bye', 'lol', 'haha',
  'good', 'nice', 'cool', 'yes', 'no', 'sure', 'yep', 'nope'
];

// ============================================================
// Storage 헬퍼
// ============================================================

/**
 * chrome.storage.local에서 여러 키를 한 번에 로드
 * @param {string[]} keys
 * @returns {Promise<Object>}
 */
function storageGet(keys) {
  return new Promise((resolve, reject) => {
    chrome.storage.local.get(keys, (result) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(result);
      }
    });
  });
}

/**
 * chrome.storage.local에 데이터 저장
 * @param {Object} data
 * @returns {Promise<void>}
 */
function storageSet(data) {
  return new Promise((resolve, reject) => {
    chrome.storage.local.set(data, () => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve();
      }
    });
  });
}

/**
 * 설정 로드 (없으면 기본값으로 초기화)
 * @returns {Promise<NuggetSettings>}
 */
async function loadSettings() {
  const result = await storageGet([STORAGE_KEYS.SETTINGS]);
  const stored = result[STORAGE_KEYS.SETTINGS];
  if (!stored) {
    const defaults = defaultSettings();
    await storageSet({ [STORAGE_KEYS.SETTINGS]: defaults });
    return defaults;
  }
  // 기본값과 병합 (신규 필드 대응)
  return Object.assign({}, defaultSettings(), stored);
}

/**
 * 엔트리 목록 로드
 * @returns {Promise<NuggetEntry[]>}
 */
async function loadEntries() {
  const result = await storageGet([STORAGE_KEYS.ENTRIES]);
  const entries = result[STORAGE_KEYS.ENTRIES];
  return Array.isArray(entries) ? entries : [];
}

/**
 * 잡담 키워드 목록 로드
 * @returns {Promise<string[]>}
 */
async function loadJunkKeywords() {
  const result = await storageGet([STORAGE_KEYS.JUNK_KEYWORDS]);
  const kws = result[STORAGE_KEYS.JUNK_KEYWORDS];
  return Array.isArray(kws) ? kws : DEFAULT_JUNK_KEYWORDS;
}

// ============================================================
// 유틸리티 (utils.js 로드 없이 Service Worker에서 직접 구현)
// Service Worker는 importScripts를 통해 별도로 로드할 수 없으므로
// utils.js의 핵심 함수를 인라인으로 구현합니다.
// @confidence: low — utils.js와 동기화 유지 필요
// ============================================================

/** CJK 문자 포함 여부 */
function _isCJK(text) {
  return /[\u3000-\u9FFF\uAC00-\uD7AF]/.test(text);
}

/** djb2 해시 */
function _generateHash(question, answer, dateString) {
  const input = (question || '').trim() + '|' + (answer || '').trim().substring(0, 200) + '|' + (dateString || '');
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) + hash) + input.charCodeAt(i);
    hash = hash & hash;
  }
  return (hash >>> 0).toString(16);
}

/** 잡담 분류 */
function _classifyJunk(question, answer, keywords) {
  const q = (question || '').trim();
  const a = (answer || '').trim();
  if (!Array.isArray(keywords)) keywords = [];

  // 1단계: 길이 기준
  if (_isCJK(q)) {
    if (q.length < 15 && a.length < 200) return true;
  } else {
    const wordCount = q.split(/\s+/).filter(w => w.length > 0).length;
    if (wordCount < 5 && a.length < 200) return true;
  }

  // 2단계: 키워드 exact match
  const qLower = q.toLowerCase();
  for (const kw of keywords) {
    if (typeof kw === 'string' && qLower === kw.toLowerCase()) return true;
  }

  return false;
}

/** 자동 태깅 */
function _autoTag(question, answer) {
  const combined = ((question || '') + ' ' + (answer || '')).toLowerCase();
  const TAG_MAP = {
    '코딩': ['code', '코드', 'function', '함수', 'bug', '버그', 'error', '에러', 'api', 'python', 'javascript', 'html', 'css', 'react', '프로그래밍', '개발', '배열', '변수', '알고리즘', '데이터베이스', 'sql', 'git'],
    '글쓰기': ['글', 'write', 'writing', '에세이', 'essay', '블로그', 'blog', '소설', '시', 'poem', '번역', 'translate', '문법', 'grammar', '작문', '요약', 'summary'],
    '업무': ['이메일', 'email', '보고서', 'report', '회의', 'meeting', '일정', 'schedule', '기획', 'proposal', '업무', 'work', '프레젠테이션', 'ppt', '엑셀', 'excel'],
    '학습': ['설명', 'explain', '뜻', 'meaning', '차이', 'difference', '배우', 'learn', '공부', 'study', '개념', 'concept', '이론', 'theory', '강의', 'tutorial', '원리'],
    '크리에이티브': ['아이디어', 'idea', '디자인', 'design', '이미지', 'image', '그림', '로고', 'logo', '브레인스토밍', 'brainstorm', '창작', 'creative', '영감']
  };
  const matched = [];
  for (const [tag, kws] of Object.entries(TAG_MAP)) {
    for (const kw of kws) {
      if (combined.includes(kw)) { matched.push(tag); break; }
    }
  }
  return matched.length > 0 ? matched : ['기타'];
}

/** URL 프로토콜 검증 — https:만 허용 (javascript: 등 차단) */
function _sanitizeUrl(url) {
  if (!url || typeof url !== 'string') return '';
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return ''; // 허용되지 않은 프로토콜은 빈 문자열로
}

/** 마크다운 변환 */
function _entryToMarkdown(entry) {
  if (!entry) return '';
  const date = (entry.date || '').slice(0, 10);
  const platform = entry.platform || '';
  const tags = Array.isArray(entry.tags) ? entry.tags.join(', ') : '';
  const q = entry.question || '';
  const a = entry.answer || '';
  const note = entry.note || '';
  const url = entry.sourceUrl || '';

  let md = `## ${q.slice(0, 80)}${q.length > 80 ? '...' : ''}\n\n`;
  md += `> **플랫폼:** ${platform} | **날짜:** ${date} | **태그:** ${tags}\n\n`;
  md += `### 질문\n\n${q}\n\n`;
  md += `### 답변\n\n${a}\n\n`;
  if (note.trim()) {
    const noteLines = note.split('\n').map(l => `> ${l}`).join('\n');
    md += `### 메모\n\n${noteLines}\n\n`;
  }
  if (url) md += `---\n*출처: ${url}*\n`;
  return md.trim();
}

// ============================================================
// 핵심 비즈니스 로직
// ============================================================

/**
 * 무료 한도 적용 — 아카이브 처리 (AC-23)
 * @param {NuggetEntry[]} entries
 * @param {boolean} isPro
 * @returns {NuggetEntry[]}
 */
function enforceFreeLimits(entries, isPro) {
  if (!Array.isArray(entries)) return [];

  if (isPro) {
    // Pro: 모든 archived 해제
    return entries.map(e => ({ ...e, archived: false }));
  }

  const MAX = 500; // MAX_FREE_ENTRIES

  // 무료: active(non-junk, non-archived) + 이전 archived를 모두 고려하여 재계산
  // 1) isJunk가 아닌 엔트리만 추출하여 날짜 내림차순 정렬
  const nonJunk = entries
    .filter(e => !e.isJunk)
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  // 2) 상위 MAX개는 archived:false, 나머지는 archived:true
  const keepActiveIds = new Set(nonJunk.slice(0, MAX).map(e => e.id));

  return entries.map(e => {
    if (e.isJunk) return e; // 잡담은 archived 상태 유지
    return { ...e, archived: !keepActiveIds.has(e.id) };
  });
}

/**
 * MD 복사 한도 확인 및 카운트 증가 (AC-13, AC-23)
 * @param {NuggetSettings} settings
 * @returns {{ limitReached: boolean, updatedSettings: NuggetSettings }}
 */
function checkAndIncrementMdCopy(settings) {
  const now = new Date();
  const currentMonthFirst = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1))
    .toISOString().slice(0, 10);

  let updated = { ...settings };

  // 새 달이면 카운터 리셋
  if (!updated.mdCopyResetDate || updated.mdCopyResetDate < currentMonthFirst) {
    updated.mdCopyCount = 0;
    updated.mdCopyResetDate = currentMonthFirst;
  }

  // Pro는 무제한
  if (updated.isPro) {
    return { limitReached: false, updatedSettings: updated };
  }

  const MAX_COPIES = 20; // MAX_FREE_MD_COPIES_PER_MONTH
  if (updated.mdCopyCount >= MAX_COPIES) {
    return { limitReached: true, updatedSettings: updated };
  }

  updated.mdCopyCount = (updated.mdCopyCount || 0) + 1;
  return { limitReached: false, updatedSettings: updated };
}

/**
 * 백업 경고 뱃지 업데이트 (AC-18)
 * @param {NuggetEntry[]} entries
 * @param {boolean} isPro
 */
function updateBadge(entries, isPro) {
  const activeCount = entries.filter(e => !e.archived).length;

  if (isPro) {
    // Pro: 500 단위 마일스톤 (뱃지는 클리어)
    if (activeCount > 0 && activeCount % 500 === 0) {
      chrome.action.setBadgeText({ text: String(activeCount) });
      chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
    } else {
      chrome.action.setBadgeText({ text: '' });
    }
    return;
  }

  // 무료: 400개(80%) 이상 경고
  const THRESHOLD = 400;  // FREE_ARCHIVE_WARNING_THRESHOLD
  const MAX = 500;        // MAX_FREE_ENTRIES
  if (activeCount >= MAX) {
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setBadgeBackgroundColor({ color: '#F44336' }); // 빨간색
  } else if (activeCount >= THRESHOLD) {
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setBadgeBackgroundColor({ color: '#FF9800' }); // 노란색
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// ============================================================
// 공개 API 함수 (DESIGN.md 섹션 9.2)
// ============================================================

/**
 * 엔트리 저장 (중복 체크 + 잡담 필터 + 태깅 + 한도 체크) (AC-1~AC-8)
 * @param {{ question: string, answer: string, platform: string, sourceUrl: string }} data
 * @returns {Promise<{ success: boolean, entry?: NuggetEntry, error?: string }>}
 */
async function saveEntry(data) {
  // 입력 검증
  if (!data || typeof data !== 'object') {
    return { success: false, error: '유효하지 않은 데이터' };
  }
  const { question, answer, platform, sourceUrl } = data;
  if (!question || !answer || !platform) {
    return { success: false, error: '필수 필드 누락: question, answer, platform' };
  }
  if (!['claude', 'chatgpt', 'gemini'].includes(platform)) {
    return { success: false, error: `알 수 없는 플랫폼: ${platform}` };
  }

  try {
    const dateString = new Date().toISOString();
    const hash = _generateHash(question, answer, dateString);

    // 기존 엔트리 로드
    const entries = await loadEntries();

    // 중복 체크 (AC-4)
    if (entries.some(e => e.hash === hash)) {
      return { success: false, error: '중복 엔트리' };
    }

    // 설정 및 잡담 키워드 로드
    const [settings, keywords] = await Promise.all([loadSettings(), loadJunkKeywords()]);

    // 잡담 필터 (AC-5)
    const isJunk = settings.junkFilterEnabled
      ? _classifyJunk(question, answer, keywords)
      : false;

    // 자동 태깅 (AC-8)
    const tags = _autoTag(question, answer);

    // sourceUrl 프로토콜 검증 (javascript: 등 차단)
    const safeUrl = _sanitizeUrl(sourceUrl);

    // 새 엔트리 생성
    /** @type {NuggetEntry} */
    const entry = {
      id: (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).substring(2),
      date: dateString,
      platform: platform,
      question: question,
      answer: answer,
      tags: tags,
      starred: false,
      isJunk: isJunk,
      archived: false,
      sourceUrl: safeUrl,
      note: '',
      hash: hash
    };

    // 한도 체크 + 아카이브 적용 (AC-23)
    const updatedEntries = enforceFreeLimits([entry, ...entries], settings.isPro);

    // 저장 (AC-28: 모든 상태는 chrome.storage에)
    await storageSet({ [STORAGE_KEYS.ENTRIES]: updatedEntries });

    // 뱃지 업데이트 (AC-18)
    updateBadge(updatedEntries, settings.isPro);

    return { success: true, entry, toastEnabled: settings.toastEnabled };
  } catch (err) {
    console.error('[Nugget] saveEntry 오류:', err);
    return { success: false, error: err.message };
  }
}

/**
 * 엔트리 목록 조회 (필터 적용) (AC-10)
 * @param {SearchFilters} [filters]
 * @returns {Promise<NuggetEntry[]>}
 */
async function getEntries(filters) {
  try {
    const entries = await loadEntries();
    return applyFilters(entries, filters || {});
  } catch (err) {
    console.error('[Nugget] getEntries 오류:', err);
    return [];
  }
}

/**
 * 엔트리 검색 (키워드 + 필터) (AC-10, AC-11)
 * @param {string} query
 * @param {SearchFilters} [filters]
 * @returns {Promise<NuggetEntry[]>}
 */
async function searchEntries(query, filters) {
  try {
    const entries = await loadEntries();
    const filtered = applyFilters(entries, filters || {});

    if (!query || !query.trim()) return filtered;

    const q = query.trim().toLowerCase();
    return filtered.filter(e =>
      (e.question || '').toLowerCase().includes(q) ||
      (e.answer || '').toLowerCase().includes(q) ||
      (e.note || '').toLowerCase().includes(q)
    );
  } catch (err) {
    console.error('[Nugget] searchEntries 오류:', err);
    return [];
  }
}

/**
 * 필터 적용 헬퍼
 * @param {NuggetEntry[]} entries
 * @param {SearchFilters} filters
 * @returns {NuggetEntry[]}
 */
function applyFilters(entries, filters) {
  let result = entries;

  // 기본: archived 제외 (includeArchived가 true이면 포함)
  if (!filters.includeArchived) {
    result = result.filter(e => !e.archived);
  }
  if (!filters.includeJunk) {
    result = result.filter(e => !e.isJunk);
  }

  // 플랫폼 필터 — 배열(platforms) 또는 단일(platform) 지원 (AC-10)
  if (Array.isArray(filters.platforms) && filters.platforms.length > 0) {
    result = result.filter(e => filters.platforms.includes(e.platform));
  } else if (filters.platform) {
    result = result.filter(e => e.platform === filters.platform);
  }

  // 기간 필터 — period 프리셋을 dateFrom/dateTo로 변환 (AC-10)
  let dateFrom = filters.dateFrom;
  let dateTo = filters.dateTo;
  if (filters.period && filters.period !== 'all' && filters.period !== 'custom') {
    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);
    if (filters.period === 'today') {
      dateFrom = todayStr;
      dateTo = todayStr;
    } else if (filters.period === 'week') {
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      dateFrom = weekAgo.toISOString().slice(0, 10);
      dateTo = todayStr;
    } else if (filters.period === 'month') {
      const monthAgo = new Date(now);
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      dateFrom = monthAgo.toISOString().slice(0, 10);
      dateTo = todayStr;
    }
  }

  if (dateFrom) {
    result = result.filter(e => e.date >= dateFrom);
  }
  if (dateTo) {
    const to = dateTo + 'T23:59:59.999Z';
    result = result.filter(e => e.date <= to);
  }

  // 태그 필터 — 배열(tags) 또는 단일(tag) 지원
  if (Array.isArray(filters.tags) && filters.tags.length > 0) {
    result = result.filter(e => Array.isArray(e.tags) && e.tags.some(t => filters.tags.includes(t)));
  } else if (filters.tag) {
    result = result.filter(e => Array.isArray(e.tags) && e.tags.includes(filters.tag));
  }

  // 별표 필터
  if (filters.starredOnly) {
    result = result.filter(e => e.starred);
  }

  // 최신순 정렬
  result.sort((a, b) => new Date(b.date) - new Date(a.date));

  return result;
}

/**
 * 별표 토글 (AC-16)
 * @param {string} entryId
 * @returns {Promise<{ success: boolean, starred: boolean }>}
 */
async function toggleStar(entryId) {
  if (!entryId) return { success: false, starred: false };

  try {
    const entries = await loadEntries();
    const idx = entries.findIndex(e => e.id === entryId);
    if (idx === -1) return { success: false, starred: false };

    entries[idx].starred = !entries[idx].starred;
    const starred = entries[idx].starred;

    await storageSet({ [STORAGE_KEYS.ENTRIES]: entries });
    return { success: true, starred };
  } catch (err) {
    console.error('[Nugget] toggleStar 오류:', err);
    return { success: false, starred: false };
  }
}

/**
 * 메모 업데이트 (AC-14, AC-15)
 * 무료: 카드당 200자 제한 / Pro: 무제한
 * @param {string} entryId
 * @param {string} note
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function updateNote(entryId, note) {
  if (!entryId) return { success: false, error: 'entryId 누락' };
  if (typeof note !== 'string') return { success: false, error: 'note는 문자열이어야 합니다' };

  try {
    const [entries, settings] = await Promise.all([loadEntries(), loadSettings()]);
    const idx = entries.findIndex(e => e.id === entryId);
    if (idx === -1) return { success: false, error: '엔트리를 찾을 수 없습니다' };

    // 무료 200자 제한 (AC-15)
    const MAX_NOTE = 200; // MAX_FREE_NOTE_LENGTH
    if (!settings.isPro && note.length > MAX_NOTE) {
      return { success: false, error: `무료 플랜은 메모를 ${MAX_NOTE}자까지 입력할 수 있습니다. Pro로 업그레이드하면 무제한으로 사용할 수 있어요.` };
    }

    entries[idx].note = note;
    await storageSet({ [STORAGE_KEYS.ENTRIES]: entries });
    return { success: true };
  } catch (err) {
    console.error('[Nugget] updateNote 오류:', err);
    return { success: false, error: err.message };
  }
}

/**
 * MD 복사 처리 — 한도 체크 후 마크다운 반환 (AC-13)
 * @param {string} entryId
 * @returns {Promise<{ success: boolean, markdown?: string, limitReached?: boolean }>}
 */
async function copyMarkdown(entryId) {
  if (!entryId) return { success: false, limitReached: false };

  try {
    const [entries, settings] = await Promise.all([loadEntries(), loadSettings()]);
    const entry = entries.find(e => e.id === entryId);
    if (!entry) return { success: false, limitReached: false };

    const { limitReached, updatedSettings } = checkAndIncrementMdCopy(settings);
    if (limitReached) {
      return { success: false, limitReached: true };
    }

    // 카운트 저장
    await storageSet({ [STORAGE_KEYS.SETTINGS]: updatedSettings });

    const markdown = _entryToMarkdown(entry);
    return { success: true, markdown, limitReached: false };
  } catch (err) {
    console.error('[Nugget] copyMarkdown 오류:', err);
    return { success: false, limitReached: false };
  }
}

/**
 * Pro 상태 확인 (캐시 + ExtensionPay) (AC-24a)
 * @returns {Promise<{ isPro: boolean, cached: boolean, expired?: boolean }>}
 */
async function checkProStatus() {
  // @risk: 결제 exception_policy: fail-open (오프라인 시 캐시로 폴백, 기능 차단하지 않음)
  try {
    const result = await storageGet([STORAGE_KEYS.PRO_CACHE, STORAGE_KEYS.SETTINGS]);
    const cache = result[STORAGE_KEYS.PRO_CACHE];
    const settings = result[STORAGE_KEYS.SETTINGS] || defaultSettings();

    const VALIDITY_MS = 7 * 24 * 60 * 60 * 1000; // PRO_CACHE_VALIDITY_DAYS
    const now = Date.now();
    const cacheAge = cache && cache.checkedAt
      ? now - new Date(cache.checkedAt).getTime()
      : Infinity;
    const cacheValid = cache && cacheAge < VALIDITY_MS;

    if (cacheValid) {
      // 유효한 캐시: 온라인이면 백그라운드에서 갱신 (비동기, 결과 안 기다림)
      _refreshProCacheInBackground(settings);
      return { isPro: cache.paid, cached: true };
    }

    // 캐시 없거나 만료: ExtensionPay에서 직접 확인
    try {
      // @risk: 결제 — MV3 콜백 내 재선언 필수
      const extpayInner = ExtPay('nugget-ai-chat-memory');
      const user = await extpayInner.getUser();
      const newCache = { paid: user.paid, checkedAt: new Date().toISOString() };
      await storageSet({
        [STORAGE_KEYS.PRO_CACHE]: newCache,
        [STORAGE_KEYS.SETTINGS]: { ...settings, isPro: user.paid }
      });
      return { isPro: user.paid, cached: false };
    } catch (netErr) {
      // 오프라인 또는 ExtensionPay 서버 오류
      console.warn('[Nugget] getUser() 실패 (오프라인?):', netErr);
      if (cache) {
        // 만료된 캐시라도 Pro 기능 유지 + 배너 표시 (AC-24a)
        return { isPro: cache.paid, cached: true, expired: true };
      }
      // 캐시 없음: 무료로 폴백
      return { isPro: false, cached: false };
    }
  } catch (err) {
    console.error('[Nugget] checkProStatus 오류:', err);
    return { isPro: false, cached: false };
  }
}

/**
 * 백그라운드에서 Pro 캐시 갱신 (비동기, 결과 무시)
 * @param {NuggetSettings} settings
 */
function _refreshProCacheInBackground(settings) {
  // @risk: 결제 exception_policy: fail-open (갱신 실패해도 캐시 유지)
  try {
    const extpayInner = ExtPay('nugget-ai-chat-memory'); // MV3 재선언
    extpayInner.getUser().then(user => {
      const newCache = { paid: user.paid, checkedAt: new Date().toISOString() };
      storageSet({
        [STORAGE_KEYS.PRO_CACHE]: newCache,
        [STORAGE_KEYS.SETTINGS]: { ...settings, isPro: user.paid }
      }).catch(e => console.error('[Nugget] 캐시 갱신 저장 실패:', e));
    }).catch(e => {
      // 오프라인 등 — 조용히 실패
      console.debug('[Nugget] 백그라운드 Pro 캐시 갱신 실패 (오프라인?):', e);
    });
  } catch (e) {
    console.debug('[Nugget] _refreshProCacheInBackground 오류:', e);
  }
}

/**
 * JSON 내보내기 (AC-17)
 * @returns {Promise<{ entries: NuggetEntry[], settings: NuggetSettings, exportDate: string }>}
 */
async function exportJSON() {
  try {
    const [entries, settings] = await Promise.all([loadEntries(), loadSettings()]);
    return {
      entries: entries,
      settings: settings,
      exportDate: new Date().toISOString()
    };
  } catch (err) {
    console.error('[Nugget] exportJSON 오류:', err);
    throw err;
  }
}

/**
 * JSON 가져오기 — 병합 (AC-17, AC-23a)
 * @param {{ entries: NuggetEntry[] }} data
 * @returns {Promise<{ success: boolean, imported: number, skipped: number }>}
 */
async function importJSON(data) {
  // 입력 검증
  if (!data || !Array.isArray(data.entries)) {
    return { success: false, imported: 0, skipped: 0 };
  }

  try {
    const [existing, settings] = await Promise.all([loadEntries(), loadSettings()]);
    const existingIds = new Set(existing.map(e => e.id));

    let imported = 0;
    let skipped = 0;
    const toImport = [];

    for (const entry of data.entries) {
      // 기본 유효성 체크
      if (!entry || !entry.id || !entry.question || !entry.answer || !entry.platform) {
        skipped++;
        continue;
      }
      if (existingIds.has(entry.id)) {
        skipped++;
        continue;
      }
      // sourceUrl 프로토콜 검증
      entry.sourceUrl = _sanitizeUrl(entry.sourceUrl);
      toImport.push(entry);
      imported++;
    }

    // 병합 후 한도 적용 (AC-23a)
    const merged = enforceFreeLimits([...existing, ...toImport], settings.isPro);
    await storageSet({ [STORAGE_KEYS.ENTRIES]: merged });

    return { success: true, imported, skipped };
  } catch (err) {
    console.error('[Nugget] importJSON 오류:', err);
    return { success: false, imported: 0, skipped: 0 };
  }
}

/**
 * 오늘의 너겟 조회 (AC-20)
 * @returns {Promise<NuggetEntry|null>}
 */
async function getTodaysNugget() {
  try {
    const result = await storageGet([STORAGE_KEYS.ENTRIES, STORAGE_KEYS.TODAYS_NUGGET_DISMISSED]);
    const entries = Array.isArray(result[STORAGE_KEYS.ENTRIES]) ? result[STORAGE_KEYS.ENTRIES] : [];
    const dismissedDate = result[STORAGE_KEYS.TODAYS_NUGGET_DISMISSED];

    const today = new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
    const thisYear = today.slice(0, 4);
    const todayMMDD = today.slice(5, 10); // "MM-DD"

    // 오늘 이미 닫았으면 null
    if (dismissedDate === today) return null;

    // 잡담, 아카이브 제외
    const candidates = entries.filter(e => !e.isJunk && !e.archived);
    if (candidates.length === 0) return null;

    // "과거의 오늘" 우선 (같은 월일, 다른 연도)
    const pastTodays = candidates.filter(e =>
      e.date.slice(5, 10) === todayMMDD && e.date.slice(0, 4) !== thisYear
    );

    const pool = pastTodays.length > 0 ? pastTodays : candidates;
    const randomIdx = Math.floor(Math.random() * pool.length);
    return pool[randomIdx];
  } catch (err) {
    console.error('[Nugget] getTodaysNugget 오류:', err);
    return null;
  }
}

/**
 * 커스텀 태그 추가 (Pro 전용) (AC-9)
 * @param {string} entryId
 * @param {string} tag
 * @returns {Promise<{ success: boolean, limitReached?: boolean }>}
 */
async function addCustomTag(entryId, tag) {
  if (!entryId || !tag) return { success: false };
  if (typeof tag !== 'string' || !tag.trim()) return { success: false };

  try {
    const [entries, settings] = await Promise.all([loadEntries(), loadSettings()]);

    // Pro 전용 (AC-9)
    if (!settings.isPro) {
      return { success: false, limitReached: true };
    }

    const idx = entries.findIndex(e => e.id === entryId);
    if (idx === -1) return { success: false };

    const cleanTag = tag.trim();
    if (!entries[idx].tags.includes(cleanTag)) {
      entries[idx].tags.push(cleanTag);
    }

    await storageSet({ [STORAGE_KEYS.ENTRIES]: entries });
    return { success: true };
  } catch (err) {
    console.error('[Nugget] addCustomTag 오류:', err);
    return { success: false };
  }
}

// ============================================================
// 메시지 라우터 (DESIGN.md 섹션 4.2 / 8.2)
// ============================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    sendResponse({ success: false, error: '유효하지 않은 메시지 형식' });
    return false;
  }

  const { type, payload } = message;

  // 비동기 응답을 위해 true 반환
  (async () => {
    try {
      switch (type) {
        // ── Content Script → Background ──────────────────────
        case 'SAVE_ENTRY': {
          const result = await saveEntry(payload);
          sendResponse(result);
          break;
        }

        case 'SELECTOR_FAILED': {
          // 셀렉터 실패: 뱃지에 "!" 표시 (AC-3)
          console.warn(`[Nugget] 셀렉터 실패 - 플랫폼: ${payload && payload.platform}, 셀렉터: ${payload && payload.selector}`);
          chrome.action.setBadgeText({ text: '!' });
          chrome.action.setBadgeBackgroundColor({ color: '#F44336' });
          sendResponse({ success: true });
          break;
        }

        // ── Popup → Background ───────────────────────────────
        case 'GET_ENTRIES': {
          const entries = await getEntries(payload && payload.filters);
          sendResponse({ entries });
          break;
        }

        case 'SEARCH_ENTRIES': {
          if (!payload || !payload.query) {
            const entries = await getEntries(payload && payload.filters);
            sendResponse({ entries });
            break;
          }
          const entries = await searchEntries(payload.query, payload.filters);
          sendResponse({ entries });
          break;
        }

        case 'TOGGLE_STAR': {
          if (!payload || !payload.entryId) {
            sendResponse({ success: false, starred: false });
            break;
          }
          const result = await toggleStar(payload.entryId);
          sendResponse(result);
          break;
        }

        case 'UPDATE_NOTE': {
          if (!payload || !payload.entryId) {
            sendResponse({ success: false, error: 'entryId 누락' });
            break;
          }
          const result = await updateNote(payload.entryId, payload.note || '');
          sendResponse(result);
          break;
        }

        case 'COPY_MARKDOWN': {
          if (!payload || !payload.entryId) {
            sendResponse({ success: false, limitReached: false });
            break;
          }
          const result = await copyMarkdown(payload.entryId);
          sendResponse(result);
          break;
        }

        case 'GET_TODAYS_NUGGET': {
          const entry = await getTodaysNugget();
          sendResponse({ entry: entry || null });
          break;
        }

        case 'DISMISS_TODAYS_NUGGET': {
          const today = new Date().toISOString().slice(0, 10);
          await storageSet({ [STORAGE_KEYS.TODAYS_NUGGET_DISMISSED]: today });
          sendResponse({ success: true });
          break;
        }

        case 'ADD_CUSTOM_TAG': {
          if (!payload || !payload.entryId || !payload.tag) {
            sendResponse({ success: false });
            break;
          }
          const result = await addCustomTag(payload.entryId, payload.tag);
          sendResponse(result);
          break;
        }

        // ── Popup/Options → Background ───────────────────────
        case 'GET_SETTINGS': {
          const settings = await loadSettings();
          sendResponse({ settings });
          break;
        }

        case 'UPDATE_SETTINGS': {
          // 보안: 허용된 설정 키만 변경 가능 (isPro, maxFreeEntries 등은 직접 변경 불가)
          const ALLOWED_SETTINGS_KEYS = ['toastEnabled', 'junkFilterEnabled', 'shortcutKey'];
          if (!payload || !payload.key || !ALLOWED_SETTINGS_KEYS.includes(payload.key)) {
            sendResponse({ success: false, error: '허용되지 않은 설정 키' });
            break;
          }
          const settings = await loadSettings();
          settings[payload.key] = payload.value;
          await storageSet({ [STORAGE_KEYS.SETTINGS]: settings });
          sendResponse({ success: true });
          break;
        }

        case 'GET_PRO_STATUS': {
          // @risk: 결제 exception_policy: fail-open
          const status = await checkProStatus();
          sendResponse(status);
          break;
        }

        case 'OPEN_PAYMENT_PAGE': {
          // @risk: 결제 exception_policy: fail-open (결제 페이지 열기 실패 시 무시)
          try {
            const extpayInner = ExtPay('nugget-ai-chat-memory'); // MV3 재선언
            extpayInner.openPaymentPage();
            sendResponse({ success: true });
          } catch (e) {
            console.error('[Nugget] OPEN_PAYMENT_PAGE 오류:', e);
            sendResponse({ success: false });
          }
          break;
        }

        // ── Options → Background ─────────────────────────────
        case 'GET_JUNK_KEYWORDS': {
          const keywords = await loadJunkKeywords();
          sendResponse({ keywords });
          break;
        }

        case 'UPDATE_JUNK_KEYWORDS': {
          if (!payload || !Array.isArray(payload.keywords)) {
            sendResponse({ success: false, error: 'keywords 배열 필요' });
            break;
          }
          // 각 키워드가 문자열인지 검증
          const validated = payload.keywords.filter(k => typeof k === 'string' && k.trim().length > 0);
          await storageSet({ [STORAGE_KEYS.JUNK_KEYWORDS]: validated });
          sendResponse({ success: true });
          break;
        }

        case 'EXPORT_JSON': {
          const data = await exportJSON();
          sendResponse({ data });
          break;
        }

        case 'IMPORT_JSON': {
          if (!payload || !payload.data) {
            sendResponse({ success: false, imported: 0, skipped: 0 });
            break;
          }
          const result = await importJSON(payload.data);
          sendResponse(result);
          break;
        }

        case 'EXPORT_MARKDOWN_FILE': {
          // @risk: 결제 — Pro 전용 기능
          // exception_policy: fail-closed (Pro 미검증 시 거부)
          const settings = await loadSettings();
          if (!settings.isPro) {
            sendResponse({ success: false, markdown: null });
            break;
          }
          const entries = await loadEntries();
          const activeEntries = entries.filter(e => !e.archived);
          const md = activeEntries.map(e => _entryToMarkdown(e)).join('\n\n---\n\n');
          sendResponse({ success: true, markdown: md });
          break;
        }

        case 'EXPORT_PDF': {
          // @risk: 결제 — Pro 전용 기능
          // exception_policy: fail-closed
          // PDF 생성은 Frontend에서 처리. Background는 Pro 체크만.
          const settings = await loadSettings();
          if (!settings.isPro) {
            sendResponse({ success: false });
            break;
          }
          sendResponse({ success: true });
          break;
        }

        // ── ExtensionPay Content Script → Background ─────────
        case 'PRO_STATUS_CHANGED': {
          // @risk: 결제 exception_policy: fail-open
          try {
            const settings = await loadSettings();
            const isPaid = payload && typeof payload.paid === 'boolean' ? payload.paid : true;
            const newCache = { paid: isPaid, checkedAt: new Date().toISOString() };
            const updatedSettings = { ...settings, isPro: isPaid };

            await storageSet({
              [STORAGE_KEYS.PRO_CACHE]: newCache,
              [STORAGE_KEYS.SETTINGS]: updatedSettings
            });

            // Pro 업그레이드 시 archived 해제 (AC-23)
            if (isPaid) {
              const entries = await loadEntries();
              const unlocked = enforceFreeLimits(entries, true);
              await storageSet({ [STORAGE_KEYS.ENTRIES]: unlocked });
            }

            sendResponse({ success: true });
          } catch (e) {
            console.error('[Nugget] PRO_STATUS_CHANGED 처리 오류:', e);
            sendResponse({ success: false });
          }
          break;
        }

        default:
          console.warn(`[Nugget] 알 수 없는 메시지 타입: ${type}`);
          sendResponse({ success: false, error: `알 수 없는 메시지 타입: ${type}` });
      }
    } catch (err) {
      console.error(`[Nugget] 메시지 처리 오류 (${type}):`, err);
      sendResponse({ success: false, error: err.message });
    }
  })();

  return true; // 비동기 sendResponse를 위해 필수
});

// ============================================================
// 별표 단축키 (AC-16)
// ============================================================

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'toggle-star') return;

  try {
    const entries = await loadEntries();
    if (entries.length === 0) return;

    // 가장 최근 엔트리 (date 기준)
    const sorted = [...entries].sort((a, b) => new Date(b.date) - new Date(a.date));
    const latest = sorted[0];
    const idx = entries.findIndex(e => e.id === latest.id);
    if (idx === -1) return;

    entries[idx].starred = !entries[idx].starred;
    await storageSet({ [STORAGE_KEYS.ENTRIES]: entries });

    const msg = entries[idx].starred ? '⭐ 별표 추가됨' : '별표 해제됨';

    // 현재 활성 탭에 토스트 전송
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, {
          type: 'SHOW_TOAST',
          payload: { message: msg }
        }).catch(() => {
          // Content Script 없는 탭에서는 조용히 실패
        });
      }
    } catch (tabErr) {
      // 탭 접근 실패 — 무시
      console.debug('[Nugget] 단축키 토스트 탭 접근 실패:', tabErr);
    }
  } catch (err) {
    console.error('[Nugget] toggle-star 처리 오류:', err);
  }
});

// ============================================================
// 설치/업데이트 이벤트
// ============================================================

chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    // 최초 설치: 기본값 초기화
    await storageSet({
      [STORAGE_KEYS.ENTRIES]: [],
      [STORAGE_KEYS.SETTINGS]: defaultSettings(),
      [STORAGE_KEYS.JUNK_KEYWORDS]: DEFAULT_JUNK_KEYWORDS,
      [STORAGE_KEYS.CUSTOM_TAGS]: []
    });

    // 온보딩 페이지 열기 (AC-21)
    chrome.tabs.create({ url: chrome.runtime.getURL('src/onboarding/onboarding.html') });
  }
});
