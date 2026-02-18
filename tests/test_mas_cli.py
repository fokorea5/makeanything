"""mas.py CLI 단위 테스트."""

import os
import sys
import tempfile
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMasCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_argv = sys.argv[:]
        self.orig_stdout = sys.stdout

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)
        sys.argv = self.orig_argv
        sys.stdout = self.orig_stdout

    def _capture(self, argv_list):
        sys.argv = ["mas.py"] + argv_list
        captured = StringIO()
        sys.stdout = captured
        from cli.mas import main
        main()
        sys.stdout = self.orig_stdout
        return captured.getvalue()

    def test_help(self):
        output = self._capture(["help"])
        self.assertIn("MAS", output)

    def test_gaps_no_plan(self):
        output = self._capture(["gaps", "/nonexistent/plan.md"])
        self.assertIn("갭 탐지", output)

    def test_proof_no_src(self):
        output = self._capture(["proof", "/nonexistent/src"])
        self.assertIn("증명서", output)

    def test_unknown_command(self):
        output = self._capture(["foobar"])
        self.assertIn("알 수 없는", output)

    def test_lessons_list_empty(self):
        output = self._capture(["lessons", "list"])
        self.assertIn("없습니다", output)


if __name__ == "__main__":
    unittest.main()
