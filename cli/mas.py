"""MAS (Multi-Agent Studio) CLI — 에이전트 팀 유틸리티.

표준 라이브러리만 사용. 외부 의존성 없음.

사용법:
  python cli/mas.py gaps [plan_path] [src_dir]     갭 탐지
  python cli/mas.py proof [src_dir]                 증명서 생성
  python cli/mas.py lessons list                    교훈 목록
  python cli/mas.py lessons add <project> <cat> <title> <detail>
  python cli/mas.py lessons search <keyword>
  python cli/mas.py status                          프로젝트 상태 요약
"""

import sys
import os

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def cmd_gaps(args):
    from quality.gap_detector import detect_gaps, format_report

    plan = args[0] if args else os.path.join(PROJECT_ROOT, ".plan.md")
    src = args[1] if len(args) > 1 else os.path.join(PROJECT_ROOT, "src")
    gaps = detect_gaps(plan, src)
    print(format_report(gaps))


def cmd_proof(args):
    from quality.proof_generator import generate_proof, format_proof

    src = args[0] if args else os.path.join(PROJECT_ROOT, "src")
    proof = generate_proof(src)
    print(format_proof(proof))


def cmd_lessons(args):
    from memory.lessons_db import (
        add_lesson,
        search_lessons,
        get_all_lessons,
        init_db,
    )

    if not args:
        print("사용법: mas.py lessons [list|add|search]")
        return

    subcmd = args[0]

    if subcmd == "list":
        lessons = get_all_lessons()
        if not lessons:
            print("저장된 교훈이 없습니다.")
            return
        for l in lessons:
            print(f"[{l['id']}] [{l['category']}] {l['project']}: {l['title']}")

    elif subcmd == "add":
        if len(args) < 5:
            print("사용법: mas.py lessons add <project> <category> <title> <detail>")
            return
        lid = add_lesson(args[1], args[2], args[3], args[4])
        print(f"교훈 #{lid} 저장 완료.")

    elif subcmd == "search":
        if len(args) < 2:
            print("사용법: mas.py lessons search <keyword>")
            return
        results = search_lessons(keyword=args[1])
        if not results:
            print("검색 결과 없음.")
            return
        for l in results:
            print(f"[{l['id']}] [{l['category']}] {l['project']}: {l['title']}")
            print(f"  {l['detail'][:100]}...")

    else:
        print(f"알 수 없는 하위 명령: {subcmd}")


def cmd_status(args):
    from quality.gap_detector import detect_gaps
    from quality.proof_generator import generate_proof

    plan = os.path.join(PROJECT_ROOT, ".plan.md")
    src = os.path.join(PROJECT_ROOT, "src")

    print("=== 프로젝트 상태 ===\n")

    # 갭
    gaps = detect_gaps(plan, src)
    print(f"AC 달성률: {gaps['gap_percent']}% ({gaps['done_ac']}/{gaps['total_ac']})")
    if gaps["pending_ac"]:
        print(f"미완료: {', '.join(ac['id'] for ac in gaps['pending_ac'])}")

    # 증명서
    proof = generate_proof(src)
    print(f"\n코드 파일: {proof['files_checked']}개")
    print(f"품질: {'PASS' if proof['all_valid'] else 'FAIL'}")
    if proof["syntax_errors"]:
        print(f"구문 오류: {len(proof['syntax_errors'])}개")
    if proof["empty_functions"]:
        total = sum(len(v) for v in proof["empty_functions"].values())
        print(f"빈 함수: {total}개")

    # reports 확인
    reports_dir = os.path.join(PROJECT_ROOT, "workspace", "reports")
    if os.path.exists(reports_dir):
        reports = [f for f in os.listdir(reports_dir) if f.endswith(".md")]
        if reports:
            print(f"\n보고서: {len(reports)}개")
            for r in sorted(reports):
                print(f"  - {r}")


COMMANDS = {
    "gaps": cmd_gaps,
    "proof": cmd_proof,
    "lessons": cmd_lessons,
    "status": cmd_status,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"알 수 없는 명령: {cmd}")
        print(f"사용 가능: {', '.join(COMMANDS.keys())}")
        return

    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
