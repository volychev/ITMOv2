import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.cli import build_parser, main  # noqa: E402
from rubrica.narrative import NarrativeUnavailable  # noqa: E402
from rubrica.report_html import ExportRejected  # noqa: E402

RUBRIC = """id: demo
title: Demo rubric
rules:
  - id: has_readme
    kind: file_exists
    path: README.md
    severity: blocker
    title: README present
    weight: 2
  - id: has_agents
    kind: file_exists
    path: AGENTS.md
    severity: major
    title: AGENTS present
    weight: 1
  - id: no_env
    kind: file_missing
    path: .env
    severity: minor
    title: no env
    weight: 1
"""

MAJOR_RUBRIC = """id: major
title: Major only
rules:
  - id: has_missing
    kind: file_exists
    path: NOPE.md
    severity: major
    title: missing file
"""

BLOCKER_RUBRIC = """id: blocker
title: Blocker
rules:
  - id: has_missing
    kind: file_exists
    path: NOPE.md
    severity: blocker
    title: missing file
"""


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliHtmlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.submission = self.root / "submission"
        self.submission.mkdir()
        self.spec = self.root / "rubric.yaml"
        self.spec.write_text(RUBRIC, encoding="utf-8")
        self.html = self.root / "report.html"
        (self.submission / "README.md").write_text("ok", encoding="utf-8")
        (self.submission / "AGENTS.md").write_text("ok", encoding="utf-8")

    def test_html_flag_writes_file_and_keeps_stdout(self):
        code, out, err = run([str(self.submission), "--spec", str(self.spec), "--html", str(self.html)])

        self.assertEqual(code, 0)
        self.assertIn("PASS", out)
        self.assertIn("HTML-отчёт:", err)
        self.assertTrue(self.html.is_file())
        self.assertIn("has_readme", self.html.read_text(encoding="utf-8"))

    def test_json_and_html_produce_clean_json(self):
        code, out, err = run(
            [str(self.submission), "--spec", str(self.spec), "--json", "--html", str(self.html)]
        )

        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["score"], 4)
        self.assertNotIn("html", payload)
        self.assertTrue(self.html.is_file())
        self.assertIn("HTML-отчёт:", err)

    def test_max_findings_does_not_truncate_html(self):
        (self.submission / "README.md").unlink()
        (self.submission / "AGENTS.md").unlink()
        code, out, _ = run(
            [
                str(self.submission),
                "--spec",
                str(self.spec),
                "--max-findings",
                "1",
                "--html",
                str(self.html),
            ]
        )

        self.assertEqual(code, 2)
        self.assertIn("ещё 2 правил скрыто", out)
        page = self.html.read_text(encoding="utf-8")
        for rule in ("has_readme", "has_agents", "no_env"):
            self.assertIn(rule, page)

    def test_bad_html_path_fails_before_audit(self):
        with mock.patch("rubrica.cli.audit") as audit_mock:
            code, _, err = run(
                [
                    str(self.submission),
                    "--spec",
                    str(self.spec),
                    "--html",
                    str(self.root / "nope" / "report.html"),
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("ОТКАЗ: HTML-отчёт не записан", err)
        self.assertIn("родительская папка", err)
        audit_mock.assert_not_called()

    def test_bad_extension_fails_before_audit(self):
        with mock.patch("rubrica.cli.audit") as audit_mock:
            code, _, err = run(
                [str(self.submission), "--spec", str(self.spec), "--html", str(self.root / "report.txt")]
            )
        self.assertEqual(code, 2)
        self.assertIn(".html", err)
        audit_mock.assert_not_called()

    def test_directory_path_fails_before_audit(self):
        with mock.patch("rubrica.cli.audit") as audit_mock:
            code, _, err = run([str(self.submission), "--spec", str(self.spec), "--html", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("каталог", err)
        audit_mock.assert_not_called()

    def test_empty_html_path_fails_before_audit(self):
        with mock.patch("rubrica.cli.audit") as audit_mock:
            code, _, err = run([str(self.submission), "--spec", str(self.spec), "--html", ""])
        self.assertEqual(code, 2)
        self.assertIn("путь не указан", err)
        audit_mock.assert_not_called()

    def test_blocker_returns_two_and_writes_html(self):
        self.spec.write_text(BLOCKER_RUBRIC, encoding="utf-8")
        code, _, err = run([str(self.submission), "--spec", str(self.spec), "--html", str(self.html)])
        self.assertEqual(code, 2)
        self.assertIn("HTML-отчёт:", err)
        self.assertIn("Есть блокирующие провалы", self.html.read_text(encoding="utf-8"))

    def test_major_failure_returns_one_and_writes_html(self):
        self.spec.write_text(MAJOR_RUBRIC, encoding="utf-8")
        code, _, _ = run([str(self.submission), "--spec", str(self.spec), "--html", str(self.html)])
        self.assertEqual(code, 1)
        self.assertIn("Есть провалы без блокеров", self.html.read_text(encoding="utf-8"))

    def test_narrative_unavailable_returns_three_and_writes_html(self):
        with mock.patch("rubrica.cli.request_narrative") as narrative:
            narrative.side_effect = NarrativeUnavailable("нет ключа")
            code, out, err = run(
                [
                    str(self.submission),
                    "--spec",
                    str(self.spec),
                    "--narrative",
                    "--html",
                    str(self.html),
                ]
            )
        self.assertEqual(code, 3)
        self.assertIn("PASS", out)
        self.assertIn("HTML-отчёт:", err)
        page = self.html.read_text(encoding="utf-8")
        self.assertIn("Рецензия недоступна", page)
        self.assertIn("нет ключа", page)
        self.assertIn("Результат аудита не изменён", page)

    def test_narrative_unavailable_with_blocker_still_returns_three(self):
        self.spec.write_text(BLOCKER_RUBRIC, encoding="utf-8")
        with mock.patch("rubrica.cli.request_narrative") as narrative:
            narrative.side_effect = NarrativeUnavailable("нет ключа")
            code, _, _ = run(
                [str(self.submission), "--spec", str(self.spec), "--narrative", "--html", str(self.html)]
            )
        self.assertEqual(code, 3)
        page = self.html.read_text(encoding="utf-8")
        self.assertIn("Есть блокирующие провалы", page)
        self.assertIn("Рецензия недоступна", page)

    def test_export_failure_returns_two_after_printing_audit(self):
        with mock.patch("rubrica.report_html.os.replace", side_effect=OSError(28, "No space left")):
            code, out, err = run(
                [str(self.submission), "--spec", str(self.spec), "--html", str(self.html)]
            )
        self.assertEqual(code, 2)
        self.assertIn("PASS", out)
        self.assertIn("HTML-отчёт не записан", err)
        self.assertFalse(self.html.exists())

    def test_export_failure_wins_over_narrative_unavailable(self):
        with mock.patch("rubrica.cli.request_narrative") as narrative:
            narrative.side_effect = NarrativeUnavailable("нет ключа")
            with mock.patch("rubrica.report_html.os.replace", side_effect=OSError(28, "No space left")):
                code, _, err = run(
                    [
                        str(self.submission),
                        "--spec",
                        str(self.spec),
                        "--narrative",
                        "--html",
                        str(self.html),
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("HTML-отчёт не записан", err)

    def test_html_inside_target_is_allowed(self):
        path = self.submission / "report.html"
        code, _, _ = run([str(self.submission), "--spec", str(self.spec), "--html", str(path)])
        self.assertEqual(code, 0)
        self.assertTrue(path.is_file())

    def test_html_path_with_spaces_is_allowed(self):
        out_dir = self.root / "with space"
        out_dir.mkdir()
        path = out_dir / "report.html"
        code, _, _ = run([str(self.submission), "--spec", str(self.spec), "--html", str(path)])
        self.assertEqual(code, 0)
        self.assertTrue(path.is_file())

    def test_help_mentions_html(self):
        self.assertIn("--html", build_parser().format_help())


if __name__ == "__main__":
    unittest.main()
