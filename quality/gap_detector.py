"""갭 탐지기 — .plan.md의 AC와 실제 파일을 대조하여 누락을 찾음.

표준 라이브러리만 사용. AI 파싱 없음 (명시적 > 자동 원칙).
AC 체크박스 형식: - [ ] AC-N: 설명 또는 - [x] AC-N: 설명
"""

import re
import os
import glob as globmod


def parse_plan(plan_path):
    """plan.md에서 AC 목록을 추출.

    Returns:
        list[dict]: [{"id": "AC-1", "desc": "...", "done": False}, ...]
    """
    if not os.path.exists(plan_path):
        return []

    with open(plan_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"- \[([ x])\] (AC-\d+):\s*(.+)"
    matches = re.findall(pattern, content)

    return [
        {"id": m[1], "desc": m[2].strip(), "done": m[0] == "x"}
        for m in matches
    ]


def scan_project_files(src_dir):
    """src/ 디렉토리에서 파일 목록과 내용 요약을 수집.

    Returns:
        dict: {"파일경로": {"lines": 줄수, "has_code": bool}}
    """
    if not os.path.exists(src_dir):
        return {}

    result = {}
    for filepath in globmod.glob(os.path.join(src_dir, "**"), recursive=True):
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                code_lines = [
                    l for l in lines
                    if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))
                ]
                result[filepath] = {
                    "lines": len(lines),
                    "has_code": len(code_lines) > 0,
                }
            except (UnicodeDecodeError, PermissionError):
                result[filepath] = {"lines": 0, "has_code": False}

    return result


def detect_gaps(plan_path, src_dir):
    """AC 대비 구현 갭을 탐지.

    Returns:
        dict: {
            "total_ac": int,
            "done_ac": int,
            "pending_ac": list[dict],
            "gap_percent": float,
            "file_count": int,
            "empty_files": list[str]
        }
    """
    acs = parse_plan(plan_path)
    files = scan_project_files(src_dir)

    done = [ac for ac in acs if ac["done"]]
    pending = [ac for ac in acs if not ac["done"]]
    empty = [f for f, info in files.items() if not info["has_code"]]

    total = len(acs) if acs else 1
    gap_percent = round((len(done) / total) * 100, 1)

    return {
        "total_ac": len(acs),
        "done_ac": len(done),
        "pending_ac": pending,
        "gap_percent": gap_percent,
        "file_count": len(files),
        "empty_files": empty,
    }


def format_report(gaps):
    """갭 탐지 결과를 읽기 쉬운 텍스트로 변환."""
    lines = []
    lines.append(f"## 갭 탐지 결과")
    lines.append(f"- AC 달성률: {gaps['gap_percent']}% ({gaps['done_ac']}/{gaps['total_ac']})")
    lines.append(f"- 파일 수: {gaps['file_count']}")

    if gaps["pending_ac"]:
        lines.append(f"\n### 미완료 AC ({len(gaps['pending_ac'])}개)")
        for ac in gaps["pending_ac"]:
            lines.append(f"- {ac['id']}: {ac['desc']}")

    if gaps["empty_files"]:
        lines.append(f"\n### 빈 파일 ({len(gaps['empty_files'])}개)")
        for f in gaps["empty_files"]:
            lines.append(f"- {f}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    plan = sys.argv[1] if len(sys.argv) > 1 else ".plan.md"
    src = sys.argv[2] if len(sys.argv) > 2 else "src"
    gaps = detect_gaps(plan, src)
    print(format_report(gaps))
