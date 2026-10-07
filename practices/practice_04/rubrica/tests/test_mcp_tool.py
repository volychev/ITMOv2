import json
import sys
import unittest
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parents[1] / "mcp"
sys.path.insert(0, str(MCP_DIR))

from rubrica_mcp.server import rubrica_audit  # noqa: E402

RUBRIC = """id: mcp_demo
title: MCP demo rubric
rules:
  - id: has_readme
    kind: file_exists
    path: README.md
    severity: blocker
  - id: has_agents_md
    kind: file_exists
    path: AGENTS.md
    severity: major
"""


class McpToolTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.submission = self.root / "submission"
        self.submission.mkdir()
        self.spec = self.root / "r.yaml"
        self.spec.write_text(RUBRIC, encoding="utf-8")

    def test_successful_audit_returns_structured_verdict(self):
        (self.submission / "README.md").write_text("ok", encoding="utf-8")
        (self.submission / "AGENTS.md").write_text("ok", encoding="utf-8")
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.spec)))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["score"], 2)
        self.assertEqual(payload["max_score"], 2)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["findings"][0]["rule"], "has_readme")
        self.assertEqual(payload["fix_hints"], [])

    def test_partial_audit_is_not_ok_but_keeps_verdict(self):
        (self.submission / "README.md").write_text("ok", encoding="utf-8")
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.spec)))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["score"], 1)
        self.assertEqual(payload["exit_code"], 1)

    def test_audit_on_empty_submission_reports_blocker(self):
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.spec)))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["blockers"], 1)
        self.assertIn("blocker", payload["fix_hints"][0])

    def test_missing_target_returns_structured_error(self):
        """Ошибка возвращается данными: MCP-клиент не показывает текст исключения."""
        payload = json.loads(rubrica_audit(target=str(self.root / "nowhere"), spec=str(self.spec)))
        self.assertFalse(payload["ok"])
        self.assertIn("не существует", payload["error"])
        self.assertEqual(payload["findings"], [])
        self.assertEqual(payload["fix_hints"], ["исправь вход и повтори вызов"])

    def test_bad_spec_path_returns_structured_error(self):
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.root / "nope.yaml")))
        self.assertFalse(payload["ok"])
        self.assertIn("не найден", payload["error"])
        self.assertEqual(payload["spec"], str(self.root / "nope.yaml"))

    def test_invalid_rubric_content_returns_structured_error(self):
        bad = self.root / "bad.yaml"
        bad.write_text("id: x\ntitle: t\nrules: []\n", encoding="utf-8")
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(bad)))
        self.assertFalse(payload["ok"])
        self.assertIn("рубрика", payload["error"].lower())

    def test_empty_target_returns_structured_error(self):
        payload = json.loads(rubrica_audit(target="", spec=str(self.spec)))
        self.assertFalse(payload["ok"])
        self.assertIn("не указан", payload["error"])

    def test_error_payload_has_same_shape_as_success(self):
        """Агент должен разбирать оба ответа по одному набору полей."""
        bad = json.loads(rubrica_audit(target="/nope"))
        good = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.spec)))
        for key in ("ok", "spec", "score", "max_score", "findings", "fix_hints"):
            self.assertIn(key, bad)
            self.assertIn(key, good)

    def test_secret_warning_present_in_payload(self):
        leaked = "sk-" + "A" * 24
        (self.submission / "leak.md").write_text(leaked, encoding="utf-8")
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=str(self.spec)))
        self.assertTrue(any("секрет" in w for w in payload["warnings"]))

    def test_default_spec_is_used_when_spec_blank(self):
        payload = json.loads(rubrica_audit(target=str(self.submission), spec=""))
        self.assertTrue(payload["spec_path"].endswith("rubrics/practice_04.yaml"))
        self.assertEqual(payload["spec"], "practice_04")


if __name__ == "__main__":
    unittest.main()