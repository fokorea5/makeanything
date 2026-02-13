#!/usr/bin/env python3
"""
Gemini 서브에이전트 실행 스크립트
텍스트 분석/기획 에이전트들을 Gemini API로 실행합니다.
에이전트별 최적 모델이 자동 선택됩니다 (차등 배정).

사용법:
  python3 scripts/gemini-agent.py --agent <에이전트번호> --request "<요청 내용>"
  python3 scripts/gemini-agent.py --agent 01 --request "할 일 관리 앱을 만들고 싶어"
  python3 scripts/gemini-agent.py --agent 02 --request "이 프로젝트의 비용을 분석해줘" --context "추가 컨텍스트"
  python3 scripts/gemini-agent.py --agent 01 --request "..." --model gemini-2.5-pro  # 모델 수동 지정

에이전트별 기본 모델:
  01 (총괄 기획):    gemini-3-flash-preview  ($0.50/$3)
  02 (경제성 검수):  gemini-2.5-flash        ($0.30/$2.50)
  04 (UI 디자인):    gemini-2.5-flash        ($0.30/$2.50)
  08 (외부 첩보):    gemini-2.0-flash        ($0.10/$0.40)
  09 (수익화 설계):  gemini-2.5-flash        ($0.30/$2.50)

환경변수:
  GEMINI_API_KEY: Gemini API 키 (필수)
  GEMINI_MODEL: 전체 기본 모델 오버라이드 (선택)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Gemini로 실행할 에이전트 목록 (텍스트 분석/기획 역할)
GEMINI_AGENTS = {
    "01": "01-orchestrator.md",
    "02": "02-economist.md",
    "04": "04-designer.md",
    "08": "08-intelligence.md",
    "09": "09-growth.md",
}

# 에이전트별 최적 Gemini 모델 매핑 (2026.02 기준)
# 역할 중요도에 따라 차등 배정하여 비용 대비 품질 극대화
AGENT_MODELS = {
    "01": "gemini-3-flash-preview",  # 총괄 기획: Pro급 추론 필요 → 3 Flash ($0.50/$3)
    "02": "gemini-2.5-flash",        # 경제성 검수: 분석력 필요 → 2.5 Flash ($0.30/$2.50)
    "04": "gemini-2.5-flash",        # UI 디자이너: 디자인 명세 → 2.5 Flash ($0.30/$2.50)
    "08": "gemini-2.0-flash",        # 외부 첩보: 정보 수집 → 2.0 Flash ($0.10/$0.40)
    "09": "gemini-2.5-flash",        # 수익화 설계: 비즈니스 분석 → 2.5 Flash ($0.30/$2.50)
}

# Claude로 실행해야 하는 에이전트 (코드 접근/실행 필요)
# Sonnet: 03(아키텍트), 05(개발자), 06(보안QA) — 코딩/설계/보안 분석
# Haiku:  07(의도매칭), 10(배포) — 코드 검증/배포 실행
CLAUDE_AGENTS = {"03", "05", "06", "07", "10"}


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        # .env 파일에서 읽기 시도
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not key:
        print("오류: GEMINI_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
        print("", file=sys.stderr)
        print("설정 방법:", file=sys.stderr)
        print("  export GEMINI_API_KEY='your-api-key'", file=sys.stderr)
        print("  또는 .env 파일에 GEMINI_API_KEY=your-api-key 추가", file=sys.stderr)
        sys.exit(1)
    return key


def load_agent_prompt(agent_id):
    agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
    filename = GEMINI_AGENTS.get(agent_id)
    if not filename:
        if agent_id in CLAUDE_AGENTS:
            print(f"오류: 에이전트 {agent_id}는 코딩 역할이므로 Claude(Task 도구)로 실행하세요.", file=sys.stderr)
            sys.exit(1)
        print(f"오류: 알 수 없는 에이전트 번호: {agent_id}", file=sys.stderr)
        sys.exit(1)

    filepath = os.path.join(agents_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def call_gemini(api_key, system_prompt, user_request, model=None, agent_id=None):
    model = model or os.environ.get("GEMINI_MODEL") or AGENT_MODELS.get(agent_id, "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n---\n\n제작자(정찬)의 요청:\n{user_request}"}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return "오류: Gemini로부터 응답을 받지 못했습니다."
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Gemini API 오류 ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"네트워크 오류: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gemini 서브에이전트 실행")
    parser.add_argument("--agent", required=True, help="에이전트 번호 (01, 02, 04, 08, 09)")
    parser.add_argument("--request", required=True, help="제작자의 요청 내용")
    parser.add_argument("--context", default="", help="추가 컨텍스트 (이전 단계 결과 등)")
    parser.add_argument("--model", default=None, help="Gemini 모델 (미지정시 에이전트별 최적 모델 자동 선택)")
    args = parser.parse_args()

    api_key = get_api_key()
    system_prompt = load_agent_prompt(args.agent)

    user_input = args.request
    if args.context:
        user_input += f"\n\n[이전 단계 결과/추가 정보]\n{args.context}"

    result = call_gemini(api_key, system_prompt, user_input, args.model, args.agent)
    print(result)


if __name__ == "__main__":
    main()
