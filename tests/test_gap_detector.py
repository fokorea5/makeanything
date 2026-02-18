"""gap_detector 단위 테스트."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.gap_detector import parse_plan, scan_project_files, detect_gaps


class TestGapDetector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write(self, name, content):
        path = os.path.join(self.tmpdir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_parse_plan(self):
        plan = self._write("plan.md", """
# Plan
## AC
- [ ] AC-1: 로그인 구현
- [x] AC-2: DB 연결
- [ ] AC-3: 테스트 작성
""")
        acs = parse_plan(plan)
        self.assertEqual(len(acs), 3)
        self.assertFalse(acs[0]["done"])
        self.assertTrue(acs[1]["done"])
        self.assertEqual(acs[2]["id"], "AC-3")

    def test_parse_plan_missing(self):
        acs = parse_plan("/nonexistent/plan.md")
        self.assertEqual(acs, [])

    def test_scan_files(self):
        self._write("src/app.py", "print('hello')\n")
        self._write("src/empty.py", "# just a comment\n")

        files = scan_project_files(os.path.join(self.tmpdir, "src"))
        self.assertEqual(len(files), 2)

    def test_detect_gaps(self):
        plan = self._write("plan.md", """
- [x] AC-1: 완료
- [ ] AC-2: 미완료
""")
        self._write("src/main.py", "x = 1\n")

        gaps = detect_gaps(plan, os.path.join(self.tmpdir, "src"))
        self.assertEqual(gaps["total_ac"], 2)
        self.assertEqual(gaps["done_ac"], 1)
        self.assertEqual(len(gaps["pending_ac"]), 1)
        self.assertEqual(gaps["gap_percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
