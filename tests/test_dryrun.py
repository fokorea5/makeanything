"""드라이런 통합 테스트 — 5개 검증 항목.

모의 프로젝트(tests/dryrun/mock_project/)를 대상으로
에이전트 팀 아키텍처의 핵심 메커니즘을 실전 검증합니다.

1. 보고+소유권: 에이전트별 파일 소유권 규칙 준수 여부
2. 갭 탐지: AC 대비 실제 구현 갭 정확도
3. QA 판정: 증명서 기반 PASS/FAIL 판정 정확도
4. SOS 에스컬레이션: 에러 시나리오 → 디버거 소환 경로
5. 방향성 검증: plan AC vs 실제 결과 불일치 탐지
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MOCK_DIR = os.path.join(os.path.dirname(__file__), "dryrun", "mock_project")
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
CLAUDE_MD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CLAUDE.md")


class TestDryrun0_Bootstrap(unittest.TestCase):
    """드라이런 0: 오케스트레이터 부트스트랩 검증."""

    def setUp(self):
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_has_orchestrator_role(self):
        """메인 에이전트 역할이 명시되어 있는지."""
        self.assertIn("오케스트레이터", self.content)

    def test_has_activation_keywords(self):
        """가동 조건 키워드가 있는지."""
        for keyword in ["만들어", "개발해", "구현해"]:
            self.assertIn(keyword, self.content)

    def test_references_orchestrator_md(self):
        """orchestrator.md 참조가 있는지."""
        self.assertIn("prompts/agents/orchestrator.md", self.content)

    def test_has_pdca_flow(self):
        """PDCA 흐름이 명시되어 있는지."""
        self.assertIn("DISCOVER", self.content)
        self.assertIn("PLAN", self.content)
        self.assertIn("CHECK", self.content)

    def test_has_cell_differentiation(self):
        """세포 분화(규모별 편성) 규칙이 있는지."""
        self.assertIn("풀스택", self.content)
        self.assertIn("API", self.content)
        self.assertIn("스크립트", self.content)

    def test_has_approval_flow(self):
        """제작자 승인 흐름이 있는지."""
        self.assertIn("승인", self.content)

    def test_has_report_format(self):
        """보고 양식이 있는지."""
        self.assertIn("현재 단계", self.content)
        self.assertIn("투입 에이전트", self.content)


class TestDryrun1_ReportAndOwnership(unittest.TestCase):
    """드라이런 1: 보고+소유권 검증."""

    def test_agent_files_exist(self):
        """모든 에이전트 규칙 파일이 존재하는지."""
        agents = [
            "orchestrator", "architect", "developer-backend",
            "developer-frontend", "qa", "security", "debugger",
            "devops", "documenter", "oracle", "learner",
        ]
        for name in agents:
            path = os.path.join(PROMPTS_DIR, "agents", f"{name}.md")
            self.assertTrue(os.path.exists(path), f"누락: {name}.md")

    def test_backend_ownership_rules(self):
        """backend 에이전트의 소유권 규칙이 명확한지."""
        path = os.path.join(PROMPTS_DIR, "agents", "developer-backend.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 허용 범위가 명시되어 있는지
        self.assertIn("src/api/", content)
        self.assertIn("src/db/", content)
        self.assertIn("src/models/", content)

        # 금지 범위가 명시되어 있는지
        self.assertIn("금지", content)
        self.assertIn("src/ui/", content)
        self.assertIn("src/shared/", content)

    def test_frontend_ownership_rules(self):
        """frontend 에이전트의 소유권 규칙이 명확한지."""
        path = os.path.join(PROMPTS_DIR, "agents", "developer-frontend.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("src/ui/", content)
        self.assertIn("src/pages/", content)
        self.assertIn("금지", content)
        self.assertIn("src/api/", content)

    def test_qa_cannot_modify_src(self):
        """QA 에이전트가 src/ 수정 금지인지."""
        path = os.path.join(PROMPTS_DIR, "agents", "qa.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("src/ 읽기", content)
        self.assertIn("금지", content)
        self.assertIn("src/ 수정", content)

    def test_report_format_in_all_agents(self):
        """모든 코어 에이전트에 보고 지침이 있는지."""
        core_agents = [
            "developer-backend", "developer-frontend", "qa", "architect",
        ]
        for name in core_agents:
            path = os.path.join(PROMPTS_DIR, "agents", f"{name}.md")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("report", content.lower().replace("보고", "report"),
                          f"{name}: 보고 지침 누락")

    def test_orchestrator_no_coding(self):
        """오케스트레이터가 코딩 금지인지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("코드를 직접 작성하지", content)


class TestDryrun2_GapDetection(unittest.TestCase):
    """드라이런 2: 갭 탐지 검증."""

    def test_gap_detects_pending_acs(self):
        """미완료 AC를 정확히 탐지하는지."""
        from quality.gap_detector import detect_gaps

        plan = os.path.join(MOCK_DIR, ".plan.md")
        src = os.path.join(MOCK_DIR, "src")
        gaps = detect_gaps(plan, src)

        # AC-3, AC-4가 미완료
        self.assertEqual(gaps["total_ac"], 5)
        self.assertEqual(gaps["done_ac"], 3)
        self.assertEqual(len(gaps["pending_ac"]), 2)

        pending_ids = [ac["id"] for ac in gaps["pending_ac"]]
        self.assertIn("AC-3", pending_ids)
        self.assertIn("AC-4", pending_ids)

    def test_gap_percent_accuracy(self):
        """달성률 계산이 정확한지."""
        from quality.gap_detector import detect_gaps

        plan = os.path.join(MOCK_DIR, ".plan.md")
        src = os.path.join(MOCK_DIR, "src")
        gaps = detect_gaps(plan, src)

        self.assertEqual(gaps["gap_percent"], 60.0)  # 3/5

    def test_gap_finds_project_files(self):
        """프로젝트 파일을 정확히 스캔하는지."""
        from quality.gap_detector import scan_project_files

        src = os.path.join(MOCK_DIR, "src")
        files = scan_project_files(src)

        # routes.py, schema.py, todo_list.py, types.py
        self.assertGreaterEqual(len(files), 4)

    def test_gap_report_format(self):
        """갭 보고서 포맷이 올바른지."""
        from quality.gap_detector import detect_gaps, format_report

        plan = os.path.join(MOCK_DIR, ".plan.md")
        src = os.path.join(MOCK_DIR, "src")
        gaps = detect_gaps(plan, src)
        report = format_report(gaps)

        self.assertIn("갭 탐지 결과", report)
        self.assertIn("AC 달성률", report)
        self.assertIn("미완료 AC", report)
        self.assertIn("AC-3", report)


class TestDryrun3_QAJudgment(unittest.TestCase):
    """드라이런 3: QA 판정 검증."""

    def test_proof_detects_empty_functions(self):
        """빈 함수(pass만)를 정확히 잡는지."""
        from quality.proof_generator import generate_proof

        src = os.path.join(MOCK_DIR, "src")
        proof = generate_proof(src)

        # delete_todo()와 render_todo_list()가 pass만
        self.assertFalse(proof["all_valid"])
        all_empty = []
        for funcs in proof["empty_functions"].values():
            all_empty.extend(funcs)
        self.assertIn("delete_todo", all_empty)
        self.assertIn("render_todo_list", all_empty)

    def test_proof_valid_files_pass(self):
        """정상 파일은 구문 오류 없는지."""
        from quality.proof_generator import generate_proof

        src = os.path.join(MOCK_DIR, "src")
        proof = generate_proof(src)

        self.assertEqual(len(proof["syntax_errors"]), 0)

    def test_proof_report_format(self):
        """증명서 포맷이 올바른지."""
        from quality.proof_generator import generate_proof, format_proof

        src = os.path.join(MOCK_DIR, "src")
        proof = generate_proof(src)
        report = format_proof(proof)

        self.assertIn("코드 증명서", report)
        self.assertIn("NO", report)  # all_valid = False
        self.assertIn("빈 함수", report)

    def test_qa_guide_exists_and_complete(self):
        """QA 가이드에 신뢰 범위가 명시되어 있는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "qa_guide.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("보장", content)
        self.assertIn("미보장", content)
        self.assertIn("비즈니스 로직", content)


class TestDryrun4_SOSEscalation(unittest.TestCase):
    """드라이런 4: SOS 에스컬레이션 검증."""

    def test_backend_has_sos_rule(self):
        """backend에 3회 실패 → SOS 규칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "developer-backend.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("2회", content)
        self.assertIn("3회", content)
        self.assertIn("SOS", content)
        self.assertIn("디버거", content)

    def test_frontend_has_sos_rule(self):
        """frontend에도 SOS 규칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "developer-frontend.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("SOS", content)

    def test_debugger_playbook_exists(self):
        """디버거 playbook에 SOS 수신 절차가 있는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "debugger.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("SOS", content)
        self.assertIn("QA 재검증", content)

    def test_debugger_agent_has_qa_recheck(self):
        """디버거 에이전트에 QA 재검증 필수 규칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "debugger.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("QA 재검증", content)

    def test_sos_escalation_chain(self):
        """SOS 체인: 개발자 → 오케스트레이터 → 디버거 → QA."""
        # backend: SOS → 오케스트레이터
        backend = os.path.join(PROMPTS_DIR, "agents", "developer-backend.md")
        with open(backend, "r", encoding="utf-8") as f:
            self.assertIn("오케스트레이터", f.read())

        # orchestrator: SOS → debugger playbook
        orch = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(orch, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("SOS", content)
            self.assertIn("debugger", content.lower().replace("디버거", "debugger"))

        # debugger playbook: → QA 재검증
        dbg = os.path.join(PROMPTS_DIR, "playbook", "debugger.md")
        with open(dbg, "r", encoding="utf-8") as f:
            self.assertIn("QA 재검증", f.read())


class TestDryrun5_DirectionVerification(unittest.TestCase):
    """드라이런 5: 방향성 검증."""

    def test_orchestrator_has_direction_check(self):
        """오케스트레이터에 CHECK 후 방향성 검증이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("사용자 원문", content)
        self.assertIn("직접 비교", content)

    def test_plan_template_has_ac_format(self):
        """plan 템플릿에 AC 체크박스 형식이 있는지."""
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates"
        )
        path = os.path.join(templates_dir, "plan.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # - [ ] AC-N: 형식이 있는지
        self.assertRegex(content, r"- \[ \] AC-\d+:")

    def test_freeze_playbook_has_recovery(self):
        """FREEZE playbook에 복구 절차가 있는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "freeze.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("DESIGN.md 반영", content)
        self.assertIn("QA", content)
        self.assertIn("작업 재개", content)

    def test_change_request_playbook(self):
        """CR playbook에 변경 관리 절차가 있는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "change_request.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("영향 범위", content)
        self.assertIn("DESIGN.md", content)
        self.assertIn("3회", content)

    def test_gap_detects_direction_mismatch(self):
        """갭 탐지기가 AC 불일치를 잡는지 (방향성 = 원래 요구 vs 현재 상태)."""
        from quality.gap_detector import detect_gaps

        plan = os.path.join(MOCK_DIR, ".plan.md")
        src = os.path.join(MOCK_DIR, "src")
        gaps = detect_gaps(plan, src)

        # 60%만 완료 → 방향성 확인 필요 신호
        self.assertLess(gaps["gap_percent"], 90)
        self.assertGreater(len(gaps["pending_ac"]), 0)

    def test_risk_tags_in_mock_code(self):
        """@risk 태그가 있는 코드가 보안 소환 트리거가 되는지 확인."""
        routes = os.path.join(MOCK_DIR, "src", "api", "routes.py")
        with open(routes, "r", encoding="utf-8") as f:
            content = f.read()

        # @risk: auth 태그 존재
        self.assertIn("@risk: auth", content)

        # 오케스트레이터 규칙에 auth → 보안 소환이 있는지
        orch = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(orch, "r", encoding="utf-8") as f:
            orch_content = f.read()
        self.assertIn("auth", orch_content)
        self.assertIn("보안", orch_content)


class TestDryrun6_V54Changes(unittest.TestCase):
    """드라이런 6: v5.4 핵심 변경사항 검증."""

    def test_qa_attacker_mindset(self):
        """QA에 능동적 공격자 마인드셋이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "qa.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("공격자", content)
        self.assertIn("실패하는 경우", content)
        self.assertIn("실패하는 입력", content)

    def test_qa_has_verification_steps(self):
        """QA에 7단계 검증 순서가 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "qa.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("검증 순서", content)
        self.assertIn("테스트 작성", content)
        self.assertIn("판정", content)

    def test_debugger_root_cause(self):
        """디버거에 근본 원인 분석이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "debugger.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("근본 원인", content)
        self.assertIn("디버깅 순서", content)

    def test_debugger_environment_separation(self):
        """디버거에 환경 문제 구분이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "debugger.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("환경 문제", content)
        self.assertIn("즉시 보고", content)

    def test_orchestrator_model_assignment(self):
        """오케스트레이터에 모델 배치 규칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("모델 배치", content)
        self.assertIn("opus", content)
        self.assertIn("sonnet", content)
        self.assertIn("haiku", content)

    def test_orchestrator_info_delivery(self):
        """오케스트레이터에 정보 전달 원칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("정보 전달 원칙", content)
        self.assertIn("DESIGN.md", content)

    def test_security_checklist(self):
        """보안 에이전트에 4관점 체크리스트가 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "security.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("인증", content)
        self.assertIn("입력", content)
        self.assertIn("저장", content)
        self.assertIn("노출", content)

    def test_claude_md_has_reference_section(self):
        """CLAUDE.md에 참조 파일 섹션이 있는지."""
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("참조 파일", content)

    def test_claude_md_freeze_description_v54(self):
        """CLAUDE.md의 FREEZE 설명이 v5.4 형식인지."""
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("코드 수정만으로 고칠 수 없고", content)


class TestDryrun7_V55Changes(unittest.TestCase):
    """드라이런 7: v5.5 핵심 변경사항 검증."""

    def test_claude_md_error_retry_unified(self):
        """CLAUDE.md 에러 횟수가 3회로 통일되었는지."""
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("3회 재시도 후 미해결", content)
        self.assertNotIn("2회 재시도 후 미해결", content)

    def test_cell_differentiation_expanded(self):
        """세포 분화에 프론트만/패키징이 추가되었는지."""
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("프론트만", content)
        self.assertIn("패키징", content)

    def test_orchestrator_cell_differentiation_v55(self):
        """오케스트레이터 PLAN에 세포 분화가 반영되었는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("세포 분화", content)
        self.assertIn("프론트만", content)

    def test_orchestrator_delivery_method(self):
        """오케스트레이터에 전달 방식 판단 섹션이 있는지."""
        path = os.path.join(PROMPTS_DIR, "agents", "orchestrator.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("전달 방식 판단", content)
        self.assertIn("HTML 전달", content)
        self.assertIn("실행 스크립트", content)

    def test_discover_five_questions(self):
        """DISCOVER 체크리스트가 5개 질문으로 구성되었는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "discover.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("핵심 기능", content)
        self.assertIn("어디서 쓸 건가요", content)
        self.assertIn("서버가 필요한가요", content)
        self.assertIn("기술 선호", content)
        self.assertIn("어떻게 받으실래요", content)

    def test_discover_skip_known_items(self):
        """DISCOVER에 이미 명시된 항목 건너뛰기 규칙이 있는지."""
        path = os.path.join(PROMPTS_DIR, "playbook", "discover.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("이미 명시된 항목은 건너뜁니다", content)


if __name__ == "__main__":
    unittest.main()
