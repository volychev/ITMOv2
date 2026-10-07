import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.core import audit  # noqa: E402
from rubrica.spec import parse_spec  # noqa: E402


def build(rules):
    return parse_spec({"id": "t", "title": "T", "rules": rules})


class AuditTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text="x"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_file_exists_pass_and_fail(self):
        self.write("README.md")
        spec = build(
            [
                {"id": "has_readme", "kind": "file_exists", "path": "README.md"},
                {"id": "has_makefile", "kind": "file_exists", "path": "Makefile"},
            ]
        )
        report = audit(spec, self.root)
        self.assertEqual(report.score, 1)
        self.assertEqual(len(report.failed), 1)
        self.assertEqual(report.exit_code, 1)

    def test_blocker_sets_exit_code_two(self):
        spec = build([{"id": "has_agents_md", "kind": "file_exists", "path": "AGENTS.md", "severity": "blocker"}])
        report = audit(spec, self.root)
        self.assertEqual(report.exit_code, 2)
        self.assertEqual(len(report.blockers), 1)

    def test_all_pass_is_exit_zero(self):
        self.write("AGENTS.md")
        spec = build([{"id": "has_agents_md", "kind": "file_exists", "path": "AGENTS.md"}])
        report = audit(spec, self.root)
        self.assertEqual(report.exit_code, 0)
        self.assertEqual(report.score, report.max_score)

    def test_file_contains_reports_line_number(self):
        self.write("AGENTS.md", "line1\nпроверка: scripts/check.sh\n")
        spec = build(
            [{"id": "names_check", "kind": "file_contains", "path": "AGENTS.md", "pattern": r"scripts/check\.sh"}]
        )
        report = audit(spec, self.root)
        self.assertTrue(report.passed[0].ok)
        self.assertIn("строке 2", report.passed[0].detail)

    def test_file_contains_on_missing_file(self):
        spec = build([{"id": "names_check", "kind": "file_contains", "path": "nope.md", "pattern": "x"}])
        report = audit(spec, self.root)
        self.assertFalse(report.passed)
        self.assertIn("не найден", report.failed[0].detail)

    def test_file_contains_skips_binary(self):
        (self.root / "blob.md").write_bytes(b"\xff\xfe\x00binary")
        spec = build([{"id": "text_check", "kind": "file_contains", "path": "blob.md", "pattern": "x"}])
        report = audit(spec, self.root)
        self.assertFalse(report.passed)
        self.assertIn("не текст UTF-8", report.failed[0].detail)

    def test_file_missing_passes_when_absent(self):
        spec = build([{"id": "no_env_file", "kind": "file_missing", "path": "secret.env"}])
        report = audit(spec, self.root)
        self.assertTrue(report.passed)
        self.assertEqual(report.exit_code, 0)

    def test_file_missing_fails_when_present(self):
        self.write("secret.env")
        spec = build([{"id": "no_env_file", "kind": "file_missing", "path": "secret.env"}])
        report = audit(spec, self.root)
        self.assertFalse(report.passed)
        self.assertIn("не должен существовать", report.failed[0].detail)

    def test_dir_count_glob(self):
        self.write("evidence/a.md")
        self.write("evidence/b.md")
        spec = build([{"id": "evidence_logs", "kind": "dir_count", "glob": "evidence/*.md", "min_count": 2}])
        report = audit(spec, self.root)
        self.assertTrue(report.passed)
        self.assertIn("2 файлов", report.passed[0].detail)

    def test_dir_count_below_minimum(self):
        self.write("evidence/a.md")
        spec = build([{"id": "evidence_logs", "kind": "dir_count", "glob": "evidence/*.md", "min_count": 3}])
        report = audit(spec, self.root)
        self.assertFalse(report.passed)
        self.assertIn("нужно минимум 3", report.failed[0].detail)

    def test_weights_sum_into_score(self):
        self.write("AGENTS.md")
        spec = build(
            [
                {"id": "weighted_ok", "kind": "file_exists", "path": "AGENTS.md", "weight": 3},
                {"id": "weighted_no", "kind": "file_exists", "path": "nope.md", "weight": 2},
            ]
        )
        report = audit(spec, self.root)
        self.assertEqual(report.score, 3)
        self.assertEqual(report.max_score, 5)

    def test_detects_secret_patterns(self):
        # Токены собираются по частям, чтобы литералов sk-… не осталось в самом тесте:
        # аудит ищет токены в папке сдачи и не должен ругаться на собственные тесты.
        fake = "sk-" + "A" * 24 + " ghp_" + "B" * 30
        self.write("notes.md", f"key {fake}")
        spec = build([{"id": "anything_ok", "kind": "file_exists", "path": "notes.md"}])
        report = audit(spec, self.root)
        self.assertTrue(any("секрет" in w for w in report.warnings))

    def test_report_serialises_to_json_friendly_dict(self):
        self.write("AGENTS.md")
        spec = build([{"id": "has_agents_md", "kind": "file_exists", "path": "AGENTS.md"}])
        payload = audit(spec, self.root).as_dict()
        for key in ("spec", "score", "max_score", "findings", "exit_code", "warnings"):
            self.assertIn(key, payload)
        self.assertEqual(payload["findings"][0]["rule"], "has_agents_md")


if __name__ == "__main__":
    unittest.main()