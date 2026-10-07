import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.cli import main  # noqa: E402

RUBRIC = """id: demo
title: Demo rubric
rules:
  - id: has_readme
    kind: file_exists
    path: README.md
    severity: blocker
    title: README present
"""


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.spec = self.root / "r.yaml"
        self.spec.write_text(RUBRIC, encoding="utf-8")
        self.submission = self.root / "submission"
        self.submission.mkdir()

    def test_bad_target_exits_two_without_reading_rubric(self):
        code, _, err = run([str(self.root / "nowhere")])
        self.assertEqual(code, 2)
        self.assertIn("ОТКАЗ", err)

    def test_bad_spec_exits_two(self):
        self.spec.write_text("id: x\ntitle: t\nrules: []\n", encoding="utf-8")
        code, _, err = run([str(self.submission), "--spec", str(self.spec)])
        self.assertEqual(code, 2)
        self.assertIn("рубрика", err.lower())

    def test_failure_reports_exit_one(self):
        self.spec.write_text(RUBRIC.replace("severity: blocker", "severity: major"), encoding="utf-8")
        code, out, _ = run([str(self.submission), "--spec", str(self.spec)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_success_exits_zero(self):
        (self.submission / "README.md").write_text("hi", encoding="utf-8")
        code, out, _ = run([str(self.submission), "--spec", str(self.spec)])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_json_output_is_parseable(self):
        (self.submission / "README.md").write_text("hi", encoding="utf-8")
        code, out, _ = run([str(self.submission), "--spec", str(self.spec), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["spec"], "demo")
        self.assertEqual(payload["score"], 1)

    def test_max_findings_flag_is_validated(self):
        code, _, err = run([str(self.submission), "--spec", str(self.spec), "--max-findings", "0"])
        self.assertEqual(code, 2)
        self.assertIn("max-findings", err)


if __name__ == "__main__":
    unittest.main()