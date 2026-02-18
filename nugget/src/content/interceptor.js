/**
 * Nugget – AI Chat Memory: API 가로채기 (MAIN world)
 *
 * DESIGN.md 섹션 13, 17 기준.
 * MAIN world에서 window.fetch를 오버라이드하여 AI 사이트의 SSE 스트리밍 응답을 캡처.
 * 캡처된 데이터는 CustomEvent('__nugget_api_capture__')로 bridge.js에 전달.
 *
 * 실행 환경: MAIN world, document_start
 * 통합 계약: API_CAPTURE_EVENT_NAME = '__nugget_api_capture__' (constants.js)
 *
 * @confidence: low — AI 사이트 API 응답 형식은 수시로 변경됩니다.
 */

(function installFetchInterceptor() {
  'use strict';

  // ============================================================
  // 플랫폼 판별 (AC-V11-1, DESIGN.md 섹션 13.2)
  // ============================================================

  const host = window.location.hostname;

  /** @type {'claude' | 'chatgpt' | 'gemini' | null} */
  let PLATFORM = null;

  if (host === 'claude.ai') {
    PLATFORM = 'claude';
  } else if (host === 'chatgpt.com' || host === 'chat.openai.com') {
    PLATFORM = 'chatgpt';
  } else if (host.endsWith('gemini.google.com')) {
    PLATFORM = 'gemini';
  }

  // 지원 플랫폼이 아니면 오버라이드 설치하지 않음
  if (!PLATFORM) return;

  // ============================================================
  // API 엔드포인트 패턴 (DESIGN.md 섹션 13.2)
  // ============================================================

  const API_PATTERNS = {
    claude: /\/api\/.*\/completion/,
    chatgpt: /\/backend-api\/conversation/,
    gemini: /\/batchexecute[?]/
  };

  // ============================================================
  // 통합 계약: CustomEvent 이름
  // ============================================================

  // constants.js는 MAIN world에서 로드되지 않으므로 직접 정의
  const API_CAPTURE_EVENT_NAME = '__nugget_api_capture__';

  // ============================================================
  // 유틸리티
  // ============================================================

  /**
   * URL이 API 엔드포인트 패턴과 매칭되는지 확인
   * @param {string} url
   * @param {string} platform
   * @returns {boolean}
   */
  function isApiEndpoint(url, platform) {
    try {
      const pattern = API_PATTERNS[platform];
      if (!pattern) return false;
      return pattern.test(url);
    } catch (e) {
      return false;
    }
  }

  /**
   * 파싱된 대화 데이터를 CustomEvent로 bridge.js에 전달
   * @param {string} platform
   * @param {string} question
   * @param {string} answer
   */
  function dispatchCapture(platform, question, answer) {
    try {
      document.dispatchEvent(new CustomEvent(API_CAPTURE_EVENT_NAME, {
        detail: { platform, question, answer }
      }));
    } catch (e) {
      console.debug('[Nugget/interceptor] dispatchCapture 오류:', e);
    }
  }

  // ============================================================
  // Claude SSE 파서 (DESIGN.md 섹션 13.3)
  // ============================================================

  /**
   * 복제된 ReadableStream에서 Claude SSE 데이터 파싱
   * SSE 형식: event: content_block_delta / data: {"delta":{"type":"text_delta","text":"..."}}
   * @param {ReadableStream} stream - tee()로 복제된 스트림
   * @param {string} requestBody - fetch 요청 body (질문 추출용)
   * @returns {Promise<{ question: string, answer: string } | null>}
   */
  async function parseClaudeSSE(stream, requestBody) {
    try {
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let answer = '';
      let question = '';

      // 질문 추출: requestBody에서 마지막 user 메시지
      try {
        const body = JSON.parse(requestBody || '{}');
        if (Array.isArray(body.messages)) {
          const userMsgs = body.messages.filter(m => m.role === 'user');
          if (userMsgs.length > 0) {
            const lastUser = userMsgs[userMsgs.length - 1];
            if (typeof lastUser.content === 'string') {
              question = lastUser.content.trim();
            } else if (Array.isArray(lastUser.content)) {
              // content가 배열인 경우 (Claude 멀티모달 메시지)
              question = lastUser.content
                .filter(c => c.type === 'text')
                .map(c => c.text || '')
                .join('\n')
                .trim();
            }
          }
        } else if (typeof body.prompt === 'string') {
          question = body.prompt.trim();
        }
      } catch (e) {
        // 질문 파싱 실패 — 빈 문자열로 진행 (answer 추출은 시도)
      }

      // SSE 스트림 읽기
      let lastEventWasContentBlockDelta = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 마지막 불완전 줄은 버퍼에 유지

        for (const line of lines) {
          if (line.startsWith('event: content_block_delta')) {
            lastEventWasContentBlockDelta = true;
          } else if (line.startsWith('data: ') && lastEventWasContentBlockDelta) {
            lastEventWasContentBlockDelta = false;
            try {
              const json = JSON.parse(line.slice(6));
              if (json.delta && json.delta.type === 'text_delta' && typeof json.delta.text === 'string') {
                answer += json.delta.text;
              }
            } catch (e) {
              // JSON 파싱 실패 — 해당 줄 스킵
            }
          } else if (line.startsWith('event: ')) {
            lastEventWasContentBlockDelta = false;
          }
        }
      }

      if (!answer.trim()) return null;
      return { question: question || '', answer: answer.trim() };
    } catch (e) {
      console.debug('[Nugget/interceptor] parseClaudeSSE 오류:', e);
      return null;
    }
  }

  // ============================================================
  // ChatGPT SSE 파서 (DESIGN.md 섹션 13.3)
  // ============================================================

  /**
   * 복제된 ReadableStream에서 ChatGPT SSE 데이터 파싱
   * SSE 형식: data: {"message":{"content":{"parts":["..."]}}}
   * 마지막 유효한 data의 parts가 최종 답변
   * @param {ReadableStream} stream
   * @param {string} requestBody
   * @returns {Promise<{ question: string, answer: string } | null>}
   */
  async function parseChatGPTSSE(stream, requestBody) {
    try {
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let answer = '';
      let question = '';

      // 질문 추출: requestBody에서 마지막 user role content
      try {
        const body = JSON.parse(requestBody || '{}');
        if (Array.isArray(body.messages)) {
          const userMsgs = body.messages.filter(m => m.role === 'user');
          if (userMsgs.length > 0) {
            const lastUser = userMsgs[userMsgs.length - 1];
            if (typeof lastUser.content === 'string') {
              question = lastUser.content.trim();
            } else if (Array.isArray(lastUser.content)) {
              question = lastUser.content
                .filter(c => c.type === 'text')
                .map(c => c.text || '')
                .join('\n')
                .trim();
            }
          }
        }
      } catch (e) {
        // 질문 파싱 실패
      }

      // SSE 스트림 읽기
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();
          if (dataStr === '[DONE]') break;

          try {
            const json = JSON.parse(dataStr);
            // ChatGPT SSE: message.content.parts[] 또는 delta.content (stream delta 방식)
            const parts = json.message && json.message.content && Array.isArray(json.message.content.parts)
              ? json.message.content.parts
              : null;
            if (parts && parts.length > 0) {
              const text = parts.filter(p => typeof p === 'string').join('');
              if (text) answer = text; // 마지막 완전한 answer로 덮어쓰기
            }
            // delta 방식 처리 (일부 ChatGPT API 버전)
            const delta = json.choices && json.choices[0] && json.choices[0].delta;
            if (delta && typeof delta.content === 'string') {
              answer += delta.content;
            }
          } catch (e) {
            // JSON 파싱 실패 — 스킵
          }
        }
      }

      if (!answer.trim()) return null;
      return { question: question || '', answer: answer.trim() };
    } catch (e) {
      console.debug('[Nugget/interceptor] parseChatGPTSSE 오류:', e);
      return null;
    }
  }

  // ============================================================
  // Gemini 응답 파서 (DESIGN.md 섹션 13.3)
  // ============================================================

  /**
   * 복제된 ReadableStream에서 Gemini 응답 파싱
   * Gemini는 표준 SSE가 아닌 JSON 배열 응답 사용
   * 파싱 실패가 가장 빈번한 플랫폼 — 실패 시 null 반환
   * @param {ReadableStream} stream
   * @param {string} requestBody
   * @returns {Promise<{ question: string, answer: string } | null>}
   */
  async function parseGeminiResponse(stream, requestBody) {
    try {
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let rawText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        rawText += decoder.decode(value, { stream: true });
      }

      if (!rawText.trim()) return null;

      let answer = '';
      let question = '';

      // Gemini 응답 파싱 시도 (여러 형식 지원)
      try {
        // batchexecute 응답 형식: )]}'\\n[["wrb.fr","..."]]
        // 또는 순수 JSON 배열
        let jsonStr = rawText;

        // XSSI 방어 prefix 제거 )]}'
        if (jsonStr.startsWith(")]}'")) {
          jsonStr = jsonStr.slice(4).trim();
        }
        // \n으로 시작하는 경우
        if (jsonStr.startsWith('\n')) {
          jsonStr = jsonStr.trim();
        }

        const parsed = JSON.parse(jsonStr);

        // Gemini batchexecute 응답 구조 파싱
        // [[["wrb.fr","...",\"[[...]]\",...]],...]]
        const extractTextFromNested = (obj) => {
          if (typeof obj === 'string' && obj.length > 0) {
            // 텍스트 후보
            return obj;
          }
          if (Array.isArray(obj)) {
            const texts = [];
            for (const item of obj) {
              const t = extractTextFromNested(item);
              if (t) texts.push(t);
            }
            // 가장 긴 텍스트를 답변으로 사용
            if (texts.length > 0) {
              return texts.reduce((a, b) => a.length >= b.length ? a : b, '');
            }
          }
          return '';
        };

        if (Array.isArray(parsed)) {
          // 첫 번째 배열 항목에서 텍스트 추출 시도
          for (const item of parsed) {
            if (Array.isArray(item) && item.length >= 3 && typeof item[2] === 'string') {
              try {
                const inner = JSON.parse(item[2]);
                const text = extractTextFromNested(inner);
                if (text && text.length > 10) {
                  answer = text;
                  break;
                }
              } catch (e) {
                // inner JSON 파싱 실패
              }
            }
          }
        }
      } catch (e) {
        // JSON 파싱 실패 — null 반환 (폴백)
        console.debug('[Nugget/interceptor] Gemini JSON 파싱 실패:', e);
        return null;
      }

      // 질문 추출 시도 (requestBody)
      try {
        const body = JSON.parse(requestBody || '{}');
        // Gemini batchexecute 요청 형식은 복잡하므로 간단히 시도
        if (body && body.query) {
          question = String(body.query).trim();
        }
      } catch (e) {
        // 질문 파싱 실패 — 빈 문자열
      }

      if (!answer.trim()) return null;
      return { question: question || '', answer: answer.trim() };
    } catch (e) {
      console.debug('[Nugget/interceptor] parseGeminiResponse 오류:', e);
      return null;
    }
  }

  // ============================================================
  // fetch 오버라이드 (AC-V11-1, DESIGN.md 섹션 13.2)
  // ============================================================

  const _originalFetch = window.fetch;

  window.fetch = async function (input, init) {
    // 원본 fetch 호출
    const response = await _originalFetch.call(this, input, init);

    try {
      // URL 추출
      const url = typeof input === 'string'
        ? input
        : (input instanceof URL ? input.href : (input instanceof Request ? input.url : String(input)));

      // API 엔드포인트 패턴 매칭 (AC-V11-1)
      if (!isApiEndpoint(url, PLATFORM)) {
        return response;
      }

      // ReadableStream.tee() 지원 확인 (AC-V11-5)
      if (!response.body || typeof response.body.tee !== 'function') {
        return response;
      }

      // 스트림 복제 (AC-V11-5: 원본 페이지 기능에 영향 없음)
      const [stream1, stream2] = response.body.tee();

      // 원본 Response는 stream1으로 복원하여 페이지에 반환
      const clonedResponse = new Response(stream1, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers
      });

      // 요청 body 추출 (질문 추출용)
      let requestBody = '';
      try {
        if (init && init.body) {
          if (typeof init.body === 'string') {
            requestBody = init.body;
          } else if (init.body instanceof ArrayBuffer) {
            requestBody = new TextDecoder().decode(init.body);
          }
        } else if (input instanceof Request) {
          // Request 객체에서 body는 이미 소비되었을 수 있으므로 시도만
          try {
            const clonedReq = input.clone();
            requestBody = await clonedReq.text();
          } catch (e) {
            // 무시
          }
        }
      } catch (e) {
        // body 추출 실패 — 빈 문자열
      }

      // 복제된 스트림(stream2)을 플랫폼별 SSE 파서에 전달 (비동기, 결과 기다리지 않음)
      (async () => {
        try {
          let result = null;

          if (PLATFORM === 'claude') {
            result = await parseClaudeSSE(stream2, requestBody);
          } else if (PLATFORM === 'chatgpt') {
            result = await parseChatGPTSSE(stream2, requestBody);
          } else if (PLATFORM === 'gemini') {
            result = await parseGeminiResponse(stream2, requestBody);
          }

          // 파싱 성공 시 CustomEvent 발송 (AC-V11-2)
          if (result && result.answer && result.answer.trim()) {
            dispatchCapture(PLATFORM, result.question || '', result.answer);
          }
          // 파싱 실패(null) 시 DOM 셀렉터 폴백 자동 작동 (AC-V11-4)
        } catch (parseErr) {
          console.debug('[Nugget/interceptor] 스트림 파싱 오류:', parseErr);
          // 파싱 실패 — DOM 셀렉터 폴백 작동
        }
      })();

      return clonedResponse;
    } catch (e) {
      console.debug('[Nugget/interceptor] fetch 오버라이드 오류:', e);
      // 오버라이드 중 오류 발생 시 원본 response 반환 시도
      // (이미 body가 소비되었을 수 있으므로 그냥 반환)
      return response;
    }
  };

  console.debug('[Nugget/interceptor] fetch 오버라이드 설치 완료:', PLATFORM);

})();
