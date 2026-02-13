#!/usr/bin/env python3
"""
Gemini 서브에이전트 실행 스크립트
비코딩 에이전트들을 Gemini API로 실행하여 토큰 비용을 절감합니다.

사용법:
  python3 scripts/gemini-agent.py --agent <에이전트번호> --request "<요청 내용>"
  python3 scripts/gemini-agent.py --agent 01 --request "할 일 관리 앱을 만들고 싶어"
  python3 scripts/gemini-agent.py --agent 02 --request "이 프로젝트의 비용을 분석해줘" --context "추가 컨텍스트"

환경변수:
  GEMINI_API_KEY: Gemini API 키 (필수)
  GEMINI_MODEL: 사용할 모델 (기본: gemini-2.0-flash)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Gemini로 실행할 에이전트 목록 (비코딩 역할)
GEMINI_AGENTS = {
    "01": "01-orchestrator.md",
    "02": "02-economist.md",
    "04": "04-designer.md",
    "07": "07-intent-auditor.md",
    "08": "08-intelligence.md",
    "09": "09-growth.md",
    "10": "10-deployment.md",
}

# Claude로 실행해야 하는 에이전트 (코딩 역할)
CLAUDE_AGENTS = {"03", "05", "06"}


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


def call_gemini(api_key, system_prompt, user_request, model=None):
    model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
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
    parser.add_argument("--agent", required=True, help="에이전트 번호 (01, 02, 04, 07, 08, 09, 10)")
    parser.add_argument("--request", required=True, help="제작자의 요청 내용")
    parser.add_argument("--context", default="", help="추가 컨텍스트 (이전 단계 결과 등)")
    parser.add_argument("--model", default=None, help="Gemini 모델 (기본: gemini-2.0-flash)")
    args = parser.parse_args()

    api_key = get_api_key()
    system_prompt = load_agent_prompt(args.agent)

    user_input = args.request
    if args.context:
        user_input += f"\n\n[이전 단계 결과/추가 정보]\n{args.context}"

    result = call_gemini(api_key, system_prompt, user_input, args.model)
    print(result)


if __name__ == "__main__":
    main()
