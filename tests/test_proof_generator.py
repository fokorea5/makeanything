"""proof_generator 단위 테스트."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.proof_generator import check_syntax, check_empty_functions, generate_proof


class TestProofGenerator(unittest.TestCase):
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

    def test_valid_syntax(self):
        fp = self._write("good.py", "x = 1\nprint(x)\n")
        result = check_syntax(fp)
        self.assertTrue(result["valid"])

    def test_invalid_syntax(self):
        fp = self._write("bad.py", "def foo(\n")
        result = check_syntax(fp)
        self.assertFalse(result["valid"])
        self.assertIn("Line", result["error"])

    def test_empty_function_pass(self):
        fp = self._write("empty.py", "def todo():\n    pass\n")
        empties = check_empty_functions(fp)
        self.assertEqual(empties, ["todo"])

    def test_empty_function_docstring_only(self):
        fp = self._write("doc.py", 'def stub():\n    """나중에 구현"""\n')
        empties = check_empty_functions(fp)
        self.assertEqual(empties, ["stub"])

    def test_non_empty_function(self):
        fp = self._write("real.py", "def add(a, b):\n    return a + b\n")
        empties = check_empty_functions(fp)
        self.assertEqual(empties, [])

    def test_generate_proof_all_valid(self):
        self._write("src/main.py", "def run():\n    print('ok')\n")
        proof = generate_proof(os.path.join(self.tmpdir, "src"))
        self.assertTrue(proof["all_valid"])
        self.assertEqual(proof["files_checked"], 1)

    def test_generate_proof_with_issues(self):
        self._write("src/bad.py", "def oops(\n")
        self._write("src/stub.py", "def later():\n    pass\n")
        proof = generate_proof(os.path.join(self.tmpdir, "src"))
        self.assertFalse(proof["all_valid"])
        self.assertEqual(len(proof["syntax_errors"]), 1)
        self.assertIn(
            os.path.join(self.tmpdir, "src", "stub.py"),
            proof["empty_functions"],
        )


if __name__ == "__main__":
    unittest.main()
