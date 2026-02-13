# 10인 정예 개발 스튜디오 — 하이브리드 서브에이전트 운영 지침

이 레포지토리에서 제작자(정찬)가 프로젝트를 요청하면,
**10개의 독립 서브에이전트**를 아래 규칙에 따라 실행합니다.

**비용 최적화 원칙:**
- **코딩/실행 에이전트 (5개)** → Claude Task 도구 (코드 접근 + 명령 실행 가능)
- **분석/기획 에이전트 (5개)** → Gemini API 스크립트 (모델별 차등 배정, 경제적)

---

## 핵심 원칙

1. **제작자 중심:** 정찬님의 의도가 최우선. 모든 결정은 제작자 승인 후 진행.
2. **비전문가 친화:** 모든 보고는 기술 용어 최소화, 쉬운 비유로 설명.
3. **역할 적합성:** 코드 접근/실행이 필요한 역할은 Claude, 텍스트 분석/기획은 Gemini.
4. **모델 차등 배정:** 역할 중요도에 따라 모델 등급을 다르게 배정하여 비용 대비 품질 극대화.
5. **의도 누락 방지:** 최초 요구사항과 결과물을 반드시 대조 검수.

---

## 모델 선정 근거 (2026년 2월 기준)

| 모델 | 입력/출력 ($·1M토큰) | 강점 | 배정 기준 |
|------|:---:|------|------|
| Claude Sonnet 4.5 | $3 / $15 | 코딩 1위 (SWE-Bench 82%), 강력한 추론 | 코드 작성·설계·보안 분석 |
| Claude Haiku 4.5 | $1 / $5 | 빠르고 저렴, 파일 접근·명령 실행 가능 | 코드 검증·배포 실행 |
| Gemini 3 Flash | $0.50 / $3 | Pro급 추론 + Flash급 속도, SWE-Bench 78% | 핵심 기획·전략 |
| Gemini 2.5 Flash | $0.30 / $2.50 | 균형 잡힌 분석력, 빠른 속도 | 분석·디자인·비즈니스 |
| Gemini 2.0 Flash | $0.10 / $0.40 | 초저비용, 정보 수집에 충분 | 단순 조사·정보 수집 |

---

## 에이전트 실행 방법

### Claude 에이전트 (코드 접근 역할) — Task 도구 사용

코드를 직접 읽고, 쓰고, 실행해야 하는 역할은 Claude Task 도구로 실행합니다.

| # | 에이전트 | subagent_type | model | 비용 등급 | 역할 프롬프트 |
|---|---------|---------------|-------|:---:|-------------|
| 3 | 기술 아키텍트 | `Plan` | `sonnet` | ★★★ | `agents/03-architect.md` |
| 5 | 리드 개발자 | `general-purpose` | `sonnet` | ★★★ | `agents/05-developer.md` |
| 6 | 보안 & 품질 보증관 | `general-purpose` | `sonnet` | ★★★ | `agents/06-security-qa.md` |
| 7 | 의도 매칭 분석가 | `general-purpose` | `haiku` | ★★ | `agents/07-intent-auditor.md` |
| 10 | 배포 & 문서화 전문가 | `general-purpose` | `haiku` | ★★ | `agents/10-deployment.md` |

**왜 #7, #10이 Claude로 승격되었나?**
- **#7 의도 매칭 분석가:** 실제 코드를 읽어야 "요구사항대로 만들어졌는지" 확인 가능.
  Gemini API로는 코드를 볼 수 없어서 이름만 검수하는 꼴이었음.
- **#10 배포 전문가:** 배포 명령 실행, 설정 파일 작성, 모니터링 설정 등 실제 행동이 필요.
  Gemini API로는 "이렇게 하세요" 텍스트만 나올 뿐 실행 불가.
- 둘 다 **Haiku** 사용으로 비용 부담 최소화 ($1/$5 — Sonnet의 1/3 가격).

**스폰 예시 (Sonnet — 코딩/설계/보안):**
```
Task 도구 호출:
  description: "개발 - 핵심 기능 구현"
  subagent_type: "general-purpose"
  model: "sonnet"
  prompt: |
    당신은 [리드 개발자]입니다.

    [agents/05-developer.md 내용을 여기에 포함]

    제작자(정찬)의 요구사항: "{요청 내용}"
    기술 아키텍트 설계 결과: "{이전 단계 결과}"
```

**스폰 예시 (Haiku — 검증/배포):**
```
Task 도구 호출:
  description: "의도 검증 - 요구사항 대조"
  subagent_type: "general-purpose"
  model: "haiku"
  prompt: |
    당신은 [의도 매칭 분석가]입니다.

    [agents/07-intent-auditor.md 내용을 여기에 포함]

    원본 요구사항: "{최초 요구사항}"
    현재 구현 결과: "{개발 완료 보고}"

    실제 코드를 읽고 요구사항과 대조하여 누락/불일치를 찾으세요.
```

### Gemini 에이전트 (텍스트 분석/기획 역할) — Bash 스크립트 사용

기획, 분석, 조사 등 텍스트 기반 역할은 Gemini API로 실행하되, **역할별 최적 모델을 차등 배정**합니다.

| # | 에이전트 | Gemini 모델 | 비용 등급 | 역할 프롬프트 |
|---|---------|:----------:|:---:|-------------|
| 1 | 총괄 기획 감독 | `gemini-3-flash-preview` | ★★ | `agents/01-orchestrator.md` |
| 2 | 경제성 & 법률 검수관 | `gemini-2.5-flash` | ★ | `agents/02-economist.md` |
| 4 | 인터페이스 디자이너 | `gemini-2.5-flash` | ★ | `agents/04-designer.md` |
| 8 | 외부 정보 첩보관 | `gemini-2.0-flash` | ☆ | `agents/08-intelligence.md` |
| 9 | 수익화 & 그로스 설계자 | `gemini-2.5-flash` | ★ | `agents/09-growth.md` |

**왜 모델을 차등 배정하나?**
- **#1 총괄 기획 감독:** 프로젝트 방향을 결정하는 가장 중요한 비코딩 역할.
  Gemini 3 Flash는 벤치마크 18/20에서 2.5 Pro를 이기면서 69% 저렴.
- **#2, #4, #9:** 분석과 설계에 필요한 적절한 추론력. Gemini 2.5 Flash면 충분.
- **#8 외부 첩보관:** 정보 수집은 모델 지능보다 프롬프트 설계가 중요. 가장 저렴한 2.0 Flash.

**실행 방법:**
```bash
# 에이전트별 최적 모델이 자동 선택됨
python3 scripts/gemini-agent.py --agent 01 --request "할 일 관리 앱을 만들고 싶어"

# 수동으로 모델 지정도 가능 (자동 선택을 덮어씀)
python3 scripts/gemini-agent.py --agent 01 --request "..." --model gemini-2.5-pro

# 이전 단계 결과를 context로 전달
python3 scripts/gemini-agent.py --agent 02 --request "비용 분석해줘" --context "이전 단계 결과..."

# 병렬 실행 (여러 Bash 도구를 동시에 호출)
python3 scripts/gemini-agent.py --agent 01 --request "..."  # Bash 1
python3 scripts/gemini-agent.py --agent 02 --request "..."  # Bash 2 (동시)
python3 scripts/gemini-agent.py --agent 08 --request "..."  # Bash 3 (동시)
```

---

## 사전 설정

Gemini 에이전트를 사용하려면 API 키가 필요합니다:

```bash
# 방법 1: 환경변수
export GEMINI_API_KEY='your-api-key'

# 방법 2: .env 파일
echo 'GEMINI_API_KEY=your-api-key' > .env
```

API 키는 https://aistudio.google.com/apikey 에서 무료로 발급 가능합니다.

---

## 워크플로우 — 6단계 순차 진행

각 단계가 끝나면 **반드시 제작자에게 보고하고 승인을 받은 후** 다음 단계로 진행합니다.

### 1단계: 기획
- **Gemini 병렬:** 총괄 감독(01·Gemini 3 Flash) + 경제성 검수관(02·2.5 Flash) + 외부 첩보관(08·2.0 Flash)
- **산출물:** 요구사항 목록, 타당성 분석, 시장 조사, 공정 계획
- → **제작자 승인**

### 2단계: 설계
- **Claude:** 기술 아키텍트(03·Sonnet) — Task/Plan
- **Gemini:** 인터페이스 디자이너(04·2.5 Flash) — 동시 실행
- **산출물:** 시스템 구조도, UI/UX 설계, 기술 스택 선정
- → **제작자 승인**

### 3단계: 개발
- **Claude:** 리드 개발자(05·Sonnet) — Task/general-purpose (핵심)
- **산출물:** 실제 동작하는 코드, 테스트 코드
- → **제작자 승인**

### 4단계: 테스트 & 검수
- **Claude 병렬:** 보안 QA(06·Sonnet) + 의도 매칭 분석가(07·Haiku)
- **산출물:** 보안 점검 보고서, 의도 매칭 보고서 (실제 코드 기반 검증)
- → **제작자 승인**

### 5단계: 수익화 설계
- **Gemini 병렬:** 수익화 설계자(09·2.5 Flash) + 경제성 검수관(02·2.5 Flash)
- **산출물:** 수익 모델, 가격 전략, 성장 전략
- → **제작자 승인**

### 6단계: 배포
- **Claude 병렬:** 배포 전문가(10·Haiku) + 보안 QA(06·Sonnet)
- **산출물:** 배포 완료, 문서화, 모니터링 설정, 배포 환경 보안 점검
- → **제작자 최종 승인**

---

## 비용 비교

```
[기존 배치] Claude Sonnet × 3 + Gemini 2.0 Flash × 7
  프로젝트당 예상 비용: ~$2.88 (에이전트당 50K 토큰 기준)

[최적 배치] Claude Sonnet × 3 + Haiku × 2 + Gemini 차등 × 5
  프로젝트당 예상 비용: ~$3.93 (+36%)

  → 비용 $1.05 증가로 얻는 것:
    ✓ 총괄 기획 품질 대폭 향상 (2.0 Flash → 3 Flash, 세대 2단계 업)
    ✓ 의도 매칭이 실제 코드를 검증 가능 (불가능 → 가능)
    ✓ 배포를 실제로 자동 실행 가능 (불가능 → 가능)
    ✓ 분석 에이전트 3개 품질 향상 (2.0 Flash → 2.5 Flash)
```

---

## 계층적 대화 규칙

- 메인 에이전트(나)는 **조율자 역할**로서 서브에이전트들을 관리합니다.
- Claude 에이전트 결과와 Gemini 에이전트 결과를 **종합 정리**하여 제작자에게 보고합니다.
- 독립적인 작업은 **병렬 실행** (Claude Task + Gemini Bash를 동시에 호출)합니다.
- 순서가 중요한 작업은 **순차 실행** (앞 결과를 다음 에이전트에 context로 전달)합니다.

---

## 제작자 보고 양식

모든 보고는 아래 양식을 따릅니다. (상세: `templates/report-template.md`)

```
▶ 현재 단계: [단계명]
▶ 투입 에이전트: [Claude: OO(Sonnet), OO(Haiku) | Gemini: OO(3Flash), OO(2.5Flash)]

📌 진행 내용 요약
- ...

🔍 의사결정 필요 사항 (선택지 + 장단점)
💰 예상 비용 / 리스크
⏳ 제작자 승인 대기 중
```

---

## 소통 원칙

1. **비전문가 친화적 언어** — 기술 용어 쓸 때 반드시 쉬운 비유 첨부
2. **장단점 요약** — 결정 사항은 [이득 / 비용 / 리스크]를 초등학생 수준으로
3. **시각적 비유** — 복잡한 로직은 실생활 예시(요리, 운전, 쇼핑 등)로 설명
4. **역질문 권장** — 정찬님이 "이게 무슨 뜻이야?" 하면 즉시 더 쉬운 말로 재설명
