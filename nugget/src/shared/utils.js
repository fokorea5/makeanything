/**
 * Nugget – AI Chat Memory: 공유 유틸리티
 *
 * DESIGN.md 섹션 9.1 시그니처 사양 기준.
 * 함수명과 파라미터를 임의로 변경하지 마세요.
 *
 * 주의: 이 파일은 Content Script와 Background 양쪽에서 로드됩니다.
 * DOM API나 chrome.* API를 직접 사용하지 마세요.
 */

// ============================================================
// 언어 판별
// ============================================================

/**
 * CJK 문자 포함 여부 판별 (AC-5)
 * CJK: U+3000~U+9FFF (한중일 통합 한자 등), U+AC00~U+D7AF (한글 음절)
 * @param {string} text
 * @returns {boolean}
 */
function isCJK(text) {
  if (typeof text !== 'string') return false;
  // CJK Unified Ideographs, Katakana, Hiragana, 한글 음절 블록 포함
  return /[\u3000-\u9FFF\uAC00-\uD7AF]/.test(text);
}

// ============================================================
// 잡담 필터 (AC-5)
// ============================================================

/**
 * 잡담 여부 분류 (AC-5)
 * 1단계(길이) OR 2단계(키워드) 중 하나라도 해당하면 isJunk:true
 *
 * @param {string} question
 * @param {string} answer
 * @param {string[]} keywords - 잡담 키워드 목록
 * @returns {boolean} isJunk
 */
function classifyJunk(question, answer, keywords) {
  if (typeof question !== 'string' || typeof answer !== 'string') return false;
  if (!Array.isArray(keywords)) keywords = [];

  const q = question.trim();
  const a = answer.trim();

  // 1단계: 길이 기준
  // CJK 포함 → 글자 수 15 미만 AND 답변 200자 미만
  // CJK 없음  → 단어 수 5 미만 AND 답변 200자 미만
  let isShort = false;
  if (isCJK(q)) {
    isShort = q.length < 15 && a.length < 200;
  } else {
    const wordCount = q.split(/\s+/).filter(w => w.length > 0).length;
    isShort = wordCount < 5 && a.length < 200;
  }
  if (isShort) return true;

  // 2단계: 키워드 exact match (대소문자 무시)
  const qLower = q.toLowerCase();
  for (const kw of keywords) {
    if (typeof kw === 'string' && qLower === kw.toLowerCase()) {
      return true;
    }
  }

  return false;
}

// ============================================================
// 자동 태깅 (AC-8)
// ============================================================

/**
 * 자동 태깅 (AC-8)
 * 질문+답변 텍스트에서 키워드 매칭으로 복수 태그 자동 부여
 *
 * @param {string} question
 * @param {string} answer
 * @returns {string[]} tags - 매칭된 태그 배열 (없으면 ["기타"])
 */
function autoTag(question, answer) {
  if (typeof question !== 'string') question = '';
  if (typeof answer !== 'string') answer = '';

  const combined = (question + ' ' + answer).toLowerCase();

  const TAG_MAP = {
    '코딩': [
      'code', '코드', 'function', '함수', 'bug', '버그', 'error', '에러',
      'api', 'python', 'javascript', 'html', 'css', 'react', '프로그래밍',
      '개발', '배열', '변수', '알고리즘', '데이터베이스', 'sql', 'git'
    ],
    '글쓰기': [
      '글', 'write', 'writing', '에세이', 'essay', '블로그', 'blog',
      '소설', '시', 'poem', '번역', 'translate', '문법', 'grammar',
      '작문', '요약', 'summary'
    ],
    '업무': [
      '이메일', 'email', '보고서', 'report', '회의', 'meeting',
      '일정', 'schedule', '기획', 'proposal', '업무', 'work',
      '프레젠테이션', 'ppt', '엑셀', 'excel'
    ],
    '학습': [
      '설명', 'explain', '뜻', 'meaning', '차이', 'difference',
      '배우', 'learn', '공부', 'study', '개념', 'concept',
      '이론', 'theory', '강의', 'tutorial', '원리'
    ],
    '크리에이티브': [
      '아이디어', 'idea', '디자인', 'design', '이미지', 'image',
      '그림', '로고', 'logo', '브레인스토밍', 'brainstorm',
      '창작', 'creative', '영감'
    ]
  };

  const matched = [];
  for (const [tag, keywords] of Object.entries(TAG_MAP)) {
    for (const kw of keywords) {
      if (combined.includes(kw)) {
        matched.push(tag);
        break; // 해당 태그 한 번만 추가
      }
    }
  }

  return matched.length > 0 ? matched : ['기타'];
}

// ============================================================
// 중복 방지 해시 (AC-4)
// ============================================================

/**
 * 중복 방지 해시 생성 (AC-4)
 * djb2 알고리즘 기반 간단한 문자열 해시
 *
 * @param {string} question
 * @param {string} answer
 * @param {string} dateString - ISO 8601
 * @returns {string} hash
 */
function generateHash(question, answer, dateString) {
  if (typeof question !== 'string') question = '';
  if (typeof answer !== 'string') answer = '';
  if (typeof dateString !== 'string') dateString = '';

  // answer 앞 200자만 사용 (긴 답변 해싱 비용 절감, DESIGN.md 6.4)
  const input = question.trim() + '|' + answer.trim().substring(0, 200) + '|' + dateString;

  // djb2 해시
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    // hash * 33 + charCode (비트 연산으로 정수 유지)
    hash = ((hash << 5) + hash) + input.charCodeAt(i);
    hash = hash & hash; // 32-bit integer
  }

  // 부호 없는 16진수 문자열로 변환
  return (hash >>> 0).toString(16);
}

// ============================================================
// 마크다운 변환 (AC-12)
// ============================================================

/**
 * 마크다운 형식으로 엔트리 변환 (AC-12)
 * 코드블록 유지. 메모 있으면 블록쿼트 추가.
 *
 * @param {Object} entry - NuggetEntry
 * @returns {string} markdown
 */
function entryToMarkdown(entry) {
  if (!entry || typeof entry !== 'object') return '';

  const date = entry.date ? entry.date.slice(0, 10) : '';
  const platform = entry.platform || '';
  const tags = Array.isArray(entry.tags) ? entry.tags.join(', ') : '';
  const question = entry.question || '';
  const answer = entry.answer || '';
  const note = entry.note || '';
  const sourceUrl = entry.sourceUrl || '';

  let md = '';
  md += `## ${question.slice(0, 80)}${question.length > 80 ? '...' : ''}\n\n`;
  md += `> **플랫폼:** ${platform} | **날짜:** ${date} | **태그:** ${tags}\n\n`;
  md += `### 질문\n\n${question}\n\n`;
  md += `### 답변\n\n${answer}\n\n`;

  if (note.trim()) {
    // 메모는 블록쿼트로 추가 (AC-12)
    const noteLines = note.split('\n').map(l => `> ${l}`).join('\n');
    md += `### 메모\n\n${noteLines}\n\n`;
  }

  if (sourceUrl) {
    md += `---\n*출처: ${sourceUrl}*\n`;
  }

  return md.trim();
}

// ============================================================
// 검색 하이라이팅 (AC-11)
// ============================================================

/**
 * 검색 키워드 하이라이팅용 정규식 생성 (AC-11)
 * 특수 문자를 이스케이프하여 안전한 정규식 생성
 *
 * @param {string} query
 * @returns {RegExp}
 */
function buildHighlightRegex(query) {
  if (typeof query !== 'string' || !query.trim()) {
    // 빈 쿼리는 매칭 안 되는 정규식 반환
    return /(?!)/;
  }
  // 정규식 특수 문자 이스케이프
  const escaped = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(escaped, 'gi');
}
