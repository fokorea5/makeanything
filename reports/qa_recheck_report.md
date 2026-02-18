# 2차 QA 재검증 리포트

**검증일시**: 2026-02-18
**검증 대상**: 1차 CHECK FAIL 10개 항목 수정 확인

---

## 항목별 재검증 결과

| # | 원래 FAIL | 수정 확인 | 새 버그 | 판정 |
|---|-----------|-----------|---------|------|
| 1 | FREEZE-01: `types.js` 누락 | 파일 존재 확인. `nugget/src/shared/types.js` (228줄). manifest.json에서 각 content_scripts에 첫 번째로 주입됨 (`"src/shared/types.js"`) | 없음 | **PASS** |
| 2 | FAIL-02 [AC-10]: `applyFilters()` period/platforms/tags/includeArchived 미지원 | `applyFilters()` (463~527줄)에 모두 구현됨: `includeArchived` 필터(467~469줄), `platforms` 배열(475~479줄), `period` 프리셋 today/week/month(484~501줄), `tags` 배열(512~516줄) | 없음 | **PASS** |
| 3 | FAIL-09 / Security FAIL-04: `UPDATE_SETTINGS` 임의 키 변경 가능 | allowlist 적용 확인: `ALLOWED_SETTINGS_KEYS = ['toastEnabled', 'junkFilterEnabled', 'shortcutKey']` (932줄). payload.key가 allowlist에 없으면 `"허용되지 않은 설정 키"` 에러 반환 (933~935줄). `isPro`, `maxFreeEntries` 등 민감 키 변경 차단됨 | 없음 | **PASS** |
| 4 | FAIL-04 [AC-23]: `enforceFreeLimits()` active < 500이면 archived 해제 안 됨 | 올바르게 수정됨 (244~267줄): 무료 사용자는 nonJunk 엔트리를 날짜 내림차순 정렬 후 상위 500개는 `archived:false`, 나머지는 `archived:true`로 설정. 기존 archived 상태를 무시하고 전체 재계산하므로 active < 500이면 archived가 자동 해제됨. Pro는 모든 archived 해제 (249줄) | 없음 | **PASS** |
| 5 | Security FAIL-02: `_sanitizeUrl()` javascript: 등 미차단 | `_sanitizeUrl()` (204~209줄): `http://` 또는 `https://`로 시작하는 URL만 허용, 나머지는 빈 문자열 반환. `javascript:`, `data:`, `vbscript:` 등 모두 차단됨. `saveEntry()`(380줄)와 `importJSON()`(735줄)에서 호출 확인 | 없음 | **PASS** |
| 6 | FAIL-01 [AC-1]: Content scripts 50자 → 10자 가드 | 세 파일 모두 확인: `claude.js` 140줄 `if (answer.length < 10) return;`, `chatgpt.js` 125줄 동일, `gemini.js` 128줄 동일. 주석도 `// 최소 10자 (AC-1: 짧은 답변도 저장)`으로 통일 | 없음 | **PASS** |
| 7 | FAIL-03 [AC-19]: SAVE_ENTRY 응답에 `toastEnabled` 누락 + Content scripts 미확인 | background.js `saveEntry()` 410줄: `return { success: true, entry, toastEnabled: settings.toastEnabled };` 확인. Content scripts 3개 모두 `response.toastEnabled !== false` 체크 확인: claude.js 158줄, chatgpt.js 141줄, gemini.js 144줄 | 없음 | **PASS** |
| 8 | Security FAIL-01: `highlightText()` HTML 엔티티 깨짐 | popup.js `highlightText()` (1031~1041줄): 정규식 `(&[#\w]+;|<[^>]+>)|([^<&]*)` 으로 HTML 엔티티와 태그를 건너뛰고 순수 텍스트에서만 치환. 입력은 이미 `escapeHtml()` 처리된 문자열이며(`createCard()`의 295~296줄에서 `highlightText(escapeHtml(entry.question), ...)`), 엔티티(`&amp;`, `&lt;` 등)가 보존됨 | 없음 | **PASS** |
| 9 | Security FAIL-02 frontend: popup.js sourceUrl 링크에 프로토콜 체크 없음 | popup.js `createCard()` 353줄: `${entry.sourceUrl && /^https?:\/\//i.test(entry.sourceUrl) ? \`<a ...>\` : ''}`. https?:// 프로토콜 체크 후에만 링크 렌더링. 추가로 `rel="noopener noreferrer"`, `target="_blank"` 적용됨. 백엔드에서도 `_sanitizeUrl()`이 이중 방어 | 없음 | **PASS** |
| 10 | WARN-01: `renderTagsHtml()` CSS 클래스명에 `cls` 사용 | popup.js `renderTagsHtml()` (1063~1070줄): `const cls = tag.replace(/[^가-힣a-zA-Z0-9]/g, '') || 'other';`로 특수문자 제거 후 CSS 클래스명에 사용. 변수명 `cls`는 class의 약어로 적절함. CSS 안전한 클래스명 생성 확인 | 없음 | **PASS** |

---

## 신규 발견 이슈

없음. 수정 과정에서 새로운 버그나 보안 취약점이 도입되지 않았습니다.

### 추가 확인 사항 (정보성)

1. **manifest.json 주입 순서 정합성**: `types.js` → `selectors.js` → `{platform}.js` 순서로 3개 플랫폼 모두 올바르게 설정됨 (manifest.json 41~53줄)
2. **`enforceFreeLimits()` 호출 지점 일관성**: `saveEntry()`(402줄), `importJSON()`(741줄), `PRO_STATUS_CHANGED`(1044줄) 세 곳에서 모두 호출 확인
3. **`_sanitizeUrl()` 이중 방어**: 백엔드(`saveEntry`, `importJSON`)와 프론트엔드(`createCard` 렌더링 시) 모두에서 프로토콜 검증

---

## 최종 판정: **PASS**

1차 CHECK에서 발견된 FAIL 10개 항목이 모두 올바르게 수정되었으며, 수정 과정에서 새로운 버그나 보안 취약점이 도입되지 않았습니다.
