import io
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.core import Report, Finding, audit  # noqa: E402
from rubrica.report_html import (  # noqa: E402
    ExportRejected,
    build_view,
    export_html,
    render_html,
    resolve_output_path,
)
from rubrica.spec import parse_spec  # noqa: E402

RULES = [
    {
        "id": "has_readme",
        "kind": "file_exists",
        "path": "README.md",
        "severity": "blocker",
        "title": "README на месте",
        "weight": 2,
    },
    {
        "id": "has_agents",
        "kind": "file_exists",
        "path": "AGENTS.md",
        "severity": "major",
        "title": "AGENTS на месте",
        "weight": 1,
    },
    {
        "id": "no_env",
        "kind": "file_missing",
        "path": ".env",
        "severity": "minor",
        "title": "Нет .env",
        "weight": 1,
    },
]


def spec_dict(rules=None):
    return {"id": "demo", "title": "Demo rubric", "rules": list(rules or RULES)}


class ReportHtmlModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text="x"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def report(self, rules=None):
        return audit(parse_spec(spec_dict(rules)), self.root)

    def test_build_view_copies_counts_order_and_warnings_without_mutation(self):
        self.write("README.md")
        report = self.report()
        before = report.as_dict()

        view = build_view(report)

        self.assertEqual(view.spec_id, "demo")
        self.assertEqual(view.spec_title, "Demo rubric")
        self.assertEqual(view.score, report.score)
        self.assertEqual(view.max_score, report.max_score)
        self.assertEqual(view.passed, len(report.passed))
        self.assertEqual(view.failed, len(report.failed))
        self.assertEqual(view.blockers, len(report.blockers))
        self.assertEqual(view.exit_code, report.exit_code)
        self.assertEqual([f.rule for f in view.findings], [r.id for r in parse_spec(spec_dict()).rules])
        self.assertEqual(view.findings[0].title, "README на месте")
        self.assertEqual(view.warnings, tuple(report.warnings))
        self.assertIsNone(view.narrative)
        self.assertIsNone(view.narrative_error)
        self.assertEqual(report.as_dict(), before)

    def test_view_has_no_time_or_hidden_findings(self):
        view = build_view(self.report())
        self.assertFalse(hasattr(view, "generated_at"))
        self.assertFalse(hasattr(view, "hidden_findings"))
        self.assertEqual(len(view.findings), 3)

    def test_build_view_passes_narrative_and_error_verbatim(self):
        view = build_view(self.report(), narrative="  текст\nрецензии  ", narrative_error="HTTP 500")
        self.assertEqual(view.narrative, "  текст\nрецензии  ")
        self.assertEqual(view.narrative_error, "HTTP 500")

    def test_render_contains_header_metrics_and_all_findings(self):
        self.write("README.md")
        view = build_view(self.report())
        page = render_html(view)

        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn('<html lang="ru">', page)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn("Отчёт аудита rubrica", page)
        self.assertIn("demo · Demo rubric", page)
        self.assertIn(f"Баллы: {view.score}/{view.max_score}", page)
        self.assertIn("Пройдено", page)
        self.assertIn("Провалено", page)
        self.assertIn("Блокеров", page)
        self.assertIn("Код аудита", page)
        for finding in view.findings:
            self.assertIn(finding.rule, page)
            self.assertIn(finding.title, page)
        self.assertIn('data-severity="blocker"', page)
        self.assertIn('data-ok="true"', page)
        self.assertIn('data-ok="false"', page)
        self.assertIn('data-weight="2"', page)
        self.assertIn("data-search=", page)
        self.assertIn('id="search"', page)
        self.assertIn('id="severity"', page)
        self.assertIn('id="failed-only"', page)
        self.assertIn('id="sort"', page)
        self.assertIn('id="reset"', page)
        self.assertIn('aria-live="polite"', page)
        self.assertIn("Показано 3 из 3", page)

    def test_render_has_verdict_banners(self):
        self.write("README.md")
        self.write("AGENTS.md")
        page_ok = render_html(build_view(self.report()))
        self.assertIn("Все правила пройдены", page_ok)
        self.assertIn("verdict-0", page_ok)

        major = [{"id": "has_missing", "kind": "file_exists", "path": "NOPE.md", "severity": "major"}]
        page_fail = render_html(build_view(self.report(major)))
        self.assertIn("Есть провалы без блокеров", page_fail)
        self.assertIn("verdict-1", page_fail)

        blocker = [{"id": "has_missing", "kind": "file_exists", "path": "NOPE.md", "severity": "blocker"}]
        page_blocker = render_html(build_view(self.report(blocker)))
        self.assertIn("Есть блокирующие провалы", page_blocker)
        self.assertIn("verdict-2", page_blocker)

    def test_render_has_three_narrative_states(self):
        page_none = render_html(build_view(self.report()))
        self.assertIn("Рецензия не запрашивалась", page_none)

        page_ok = render_html(build_view(self.report(), narrative="Рецензия: всё хорошо"))
        self.assertIn("Рецензия: всё хорошо", page_ok)

        page_err = render_html(
            build_view(self.report(), narrative=None, narrative_error="HTTP 503: сервис недоступен")
        )
        self.assertIn("Рецензия недоступна", page_err)
        self.assertIn("HTTP 503: сервис недоступен", page_err)
        self.assertIn("Результат аудита не изменён", page_err)

    def test_render_empty_report_does_not_crash(self):
        report = Report(spec_id="empty", spec_title="Empty", target="/tmp/x", findings=[], warnings=[])
        page = render_html(build_view(report))
        self.assertIn("Находок нет", page)
        self.assertIn("0/0", page)
        self.assertIn("Показано 0 из 0", page)

    def test_render_escapes_untrusted_text_and_attributes(self):
        finding = Finding(
            rule_id="evil_rule",
            kind="file_exists",
            severity="major",
            ok=False,
            title="<script>alert(1)</script>",
            detail='"><img src=x onerror=alert(1)>',
            weight=1,
        )
        report = Report(
            spec_id="<script>id</script>",
            spec_title='"><b>title</b>',
            target="/tmp/<script>target</script>",
            findings=[finding],
            warnings=["<script>warn</script>"],
        )
        page = render_html(build_view(report, narrative="<script>narr</script>"))

        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn("<script>warn</script>", page)
        self.assertNotIn("<script>narr</script>", page)
        self.assertNotIn("<img src=x", page)
        self.assertNotIn("<b>title</b>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("&quot;&gt;&lt;img src=x onerror=alert(1)&gt;", page)
        self.assertIn("&lt;script&gt;narr&lt;/script&gt;", page)

    def test_render_is_offline_and_has_csp(self):
        page = render_html(build_view(self.report()))
        lowered = page.lower()
        self.assertNotIn("<link", lowered)
        self.assertNotIn("<script src", lowered)
        self.assertNotIn("<img", lowered)
        self.assertNotIn("@import", lowered)
        self.assertNotIn("url(", lowered)
        self.assertIn("default-src 'none'", page)
        self.assertIn("style-src 'unsafe-inline'", page)
        self.assertIn("script-src 'unsafe-inline'", page)

    def test_render_is_deterministic(self):
        view = build_view(self.report())
        self.assertEqual(render_html(view), render_html(view))


class ReportHtmlPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_rejects_empty_path(self):
        for value in ("", "   "):
            with self.assertRaises(ExportRejected) as ctx:
                resolve_output_path(value)
            self.assertIn("путь не указан", str(ctx.exception))

    def test_rejects_wrong_extension(self):
        with self.assertRaises(ExportRejected) as ctx:
            resolve_output_path(self.root / "report.txt")
        self.assertIn(".html", str(ctx.exception))

    def test_rejects_existing_directory(self):
        with self.assertRaises(ExportRejected) as ctx:
            resolve_output_path(self.root)
        self.assertIn("каталог", str(ctx.exception))

    def test_rejects_missing_parent(self):
        with self.assertRaises(ExportRejected) as ctx:
            resolve_output_path(self.root / "nope" / "report.html")
        self.assertIn("родительская папка", str(ctx.exception))

    def test_rejects_parent_that_is_file(self):
        parent = self.root / "parent.txt"
        parent.write_text("x", encoding="utf-8")
        with self.assertRaises(ExportRejected) as ctx:
            resolve_output_path(parent / "report.html")
        self.assertIn("не каталог", str(ctx.exception))

    def test_rejects_target_symlink(self):
        real = self.root / "real.html"
        real.write_text("x", encoding="utf-8")
        link = self.root / "link.html"
        link.symlink_to(real)
        with self.assertRaises(ExportRejected) as ctx:
            resolve_output_path(link)
        self.assertIn("символическая ссылка", str(ctx.exception))

    def test_relative_path_becomes_absolute(self):
        old = os.getcwd()
        os.chdir(self.root)
        try:
            resolved = resolve_output_path("report.html")
        finally:
            os.chdir(old)
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved, self.root.resolve() / "report.html")

    def test_path_with_spaces_is_allowed(self):
        out = self.root / "with space"
        out.mkdir()
        resolved = resolve_output_path(out / "report.html")
        self.assertEqual(resolved, out.resolve() / "report.html")


class ReportHtmlExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.submission = self.root / "submission"
        self.submission.mkdir()
        (self.submission / "README.md").write_text("ok", encoding="utf-8")
        (self.submission / "AGENTS.md").write_text("ok", encoding="utf-8")
        self.report = audit(parse_spec(spec_dict()), self.submission)

    def test_export_writes_utf8_html_with_0600(self):
        path = self.root / "report.html"
        returned = export_html(self.report, path)

        self.assertEqual(returned, path.resolve())
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("<!DOCTYPE html>"))
        self.assertIn("has_readme", text)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_export_overwrites_existing_file(self):
        path = self.root / "report.html"
        path.write_text("OLD", encoding="utf-8")
        export_html(self.report, path)
        self.assertNotEqual(path.read_text(encoding="utf-8"), "OLD")

    def test_export_is_deterministic(self):
        first = self.root / "a.html"
        second = self.root / "b.html"
        export_html(self.report, first)
        export_html(self.report, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_write_failure_keeps_old_file_and_removes_temp(self):
        path = self.root / "report.html"
        path.write_text("OLD", encoding="utf-8")
        with mock.patch("rubrica.report_html.os.replace", side_effect=OSError(28, "No space left")):
            with self.assertRaises(ExportRejected) as ctx:
                export_html(self.report, path)
        self.assertIn("не удалось записать", str(ctx.exception))
        self.assertEqual(path.read_text(encoding="utf-8"), "OLD")
        self.assertEqual(list(self.root.glob(".*.tmp")), [])

    def test_export_rejects_bad_path_without_creating_file(self):
        with self.assertRaises(ExportRejected):
            export_html(self.report, self.root / "nope" / "report.html")
        self.assertFalse((self.root / "nope").exists())
