"""증명서 생성기 — 코드 품질 기본 검증 (구문, import, 빈 함수 등).

표준 라이브러리만 사용. AI 파싱 없음.
QA 에이전트의 참고 자료용. 최종 판단은 QA가 직접.
"""

import ast
import os
import glob as globmod


def check_syntax(filepath):
    """Python 파일 구문 검사.

    Returns:
        dict: {"valid": bool, "error": str|None}
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {"valid": False, "error": f"Line {e.lineno}: {e.msg}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def check_empty_functions(filepath):
    """빈 함수/메서드 탐지 (pass만 있는 것 포함).

    Returns:
        list[str]: 빈 함수명 목록
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError):
        return []

    empty = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            # docstring만 있거나 pass만 있는 경우
            if len(body) == 1:
                stmt = body[0]
                if isinstance(stmt, ast.Pass):
                    empty.append(node.name)
                elif (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, (ast.Constant, ast.Str))
                ):
                    empty.append(node.name)
            elif len(body) == 2:
                # docstring + pass
                if (
                    isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, (ast.Constant, ast.Str))
                    and isinstance(body[1], ast.Pass)
                ):
                    empty.append(node.name)

    return empty


def generate_proof(src_dir):
    """프로젝트 전체 증명서 생성.

    Returns:
        dict: {
            "files_checked": int,
            "syntax_errors": list[dict],
            "empty_functions": dict[str, list],
            "all_valid": bool
        }
    """
    if not os.path.exists(src_dir):
        return {
            "files_checked": 0,
            "syntax_errors": [],
            "empty_functions": {},
            "all_valid": True,
        }

    py_files = globmod.glob(os.path.join(src_dir, "**", "*.py"), recursive=True)

    syntax_errors = []
    empty_funcs = {}

    for fp in py_files:
        # 구문 검사
        result = check_syntax(fp)
        if not result["valid"]:
            syntax_errors.append({"file": fp, "error": result["error"]})

        # 빈 함수 검사
        empties = check_empty_functions(fp)
        if empties:
            empty_funcs[fp] = empties

    return {
        "files_checked": len(py_files),
        "syntax_errors": syntax_errors,
        "empty_functions": empty_funcs,
        "all_valid": len(syntax_errors) == 0 and len(empty_funcs) == 0,
    }


def format_proof(proof):
    """증명서를 읽기 쉬운 텍스트로 변환."""
    lines = []
    lines.append("## 코드 증명서")
    lines.append(f"- 검사 파일: {proof['files_checked']}개")
    lines.append(f"- 전체 통과: {'YES' if proof['all_valid'] else 'NO'}")

    if proof["syntax_errors"]:
        lines.append(f"\n### 구문 오류 ({len(proof['syntax_errors'])}개)")
        for err in proof["syntax_errors"]:
            lines.append(f"- {err['file']}: {err['error']}")

    if proof["empty_functions"]:
        total = sum(len(v) for v in proof["empty_functions"].values())
        lines.append(f"\n### 빈 함수 ({total}개)")
        for fp, funcs in proof["empty_functions"].items():
            for fn in funcs:
                lines.append(f"- {fp}: {fn}()")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "src"
    proof = generate_proof(src)
    print(format_proof(proof))
