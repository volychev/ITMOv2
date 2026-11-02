"""Автономный HTML-отчёт аудита.

Модуль не знает о сети и не меняет результат аудита: он получает готовый
``Report``, строит неизменяемую view model, рендерит один HTML-файл и пишет его
атомарно. Вся работа с внешним миром остаётся в ``narrative.py``.
"""

from __future__ import annotations

import html
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .core import Finding, Report

HTML_EXTENSIONS = {".html", ".htm"}
_CSP = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:"


class ExportRejected(Exception):
    """HTML-отчёт не создан.

    Сообщение называет путь и причину, чтобы CLI мог показать его человеку
    без дополнительных запросов.
    """


@dataclass(frozen=True)
class FindingView:
    """Одна находка в форме, пригодной для рендера."""

    rule: str
    kind: str
    severity: str
    ok: bool
    title: str
    detail: str
    weight: int


@dataclass(frozen=True)
class ReportView:
    """Неизменяемая модель отчёта для HTML-слоя."""

    spec_id: str
    spec_title: str
    target: str
    score: int
    max_score: int
    passed: int
    failed: int
    blockers: int
    exit_code: int
    findings: tuple[FindingView, ...]
    warnings: tuple[str, ...]
    narrative: str | None = None
    narrative_error: str | None = None


def _finding_view(finding: Finding) -> FindingView:
    return FindingView(
        rule=finding.rule_id,
        kind=finding.kind,
        severity=finding.severity,
        ok=finding.ok,
        title=finding.title,
        detail=finding.detail,
        weight=finding.weight,
    )


def build_view(
    report: Report,
    *,
    narrative: str | None = None,
    narrative_error: str | None = None,
) -> ReportView:
    """Строит view model из готового отчёта, не мутируя его."""
    return ReportView(
        spec_id=report.spec_id,
        spec_title=report.spec_title,
        target=report.target,
        score=report.score,
        max_score=report.max_score,
        passed=len(report.passed),
        failed=len(report.failed),
        blockers=len(report.blockers),
        exit_code=report.exit_code,
        findings=tuple(_finding_view(finding) for finding in report.findings),
        warnings=tuple(report.warnings),
        narrative=narrative,
        narrative_error=narrative_error,
    )


def resolve_output_path(raw: str | Path) -> Path:
    """Проверяет путь ``--html`` и возвращает абсолютный путь к файлу."""
    text = str(raw).strip()
    if not text:
        raise ExportRejected("--html: путь не указан")

    path = Path(text).expanduser()
    if path.is_symlink():
        raise ExportRejected(f"--html: {path} — символическая ссылка, укажите реальный путь")
    if path.exists() and path.is_dir():
        raise ExportRejected(f"--html: {path} — это каталог, нужен путь к файлу")

    suffix = path.suffix.lower()
    if suffix not in HTML_EXTENSIONS:
        raise ExportRejected(
            f"--html: нужен файл .html или .htm, получено {path.suffix or 'без расширения'!r}"
        )

    parent = path.parent
    if not parent.exists():
        raise ExportRejected(f"--html: родительская папка {parent} не существует")
    if not parent.is_dir():
        raise ExportRejected(f"--html: родитель {parent} — не каталог")

    return parent.resolve() / path.name


def write_atomic(path: Path, text: str) -> None:
    """Пишет текст UTF-8 атомарно: temp в той же папке, затем ``os.replace``."""
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        reason = exc.strerror or str(exc)
        raise ExportRejected(f"не удалось записать {path}: {reason}") from exc


def export_html(
    report: Report,
    raw_path: str | Path,
    *,
    narrative: str | None = None,
    narrative_error: str | None = None,
) -> Path:
    """Единственная точка входа CLI: проверка пути, рендер и запись."""
    path = resolve_output_path(raw_path)
    view = build_view(report, narrative=narrative, narrative_error=narrative_error)
    write_atomic(path, render_html(view))
    return path


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _verdict(exit_code: int) -> tuple[str, str]:
    if exit_code == 0:
        return "Все правила пройдены", "verdict-0"
    if exit_code == 1:
        return "Есть провалы без блокеров", "verdict-1"
    return "Есть блокирующие провалы", "verdict-2"


def _render_finding(finding: FindingView) -> str:
    status = "PASS" if finding.ok else "FAIL"
    status_class = "status-pass" if finding.ok else "status-fail"
    search = f"{finding.rule} {finding.title} {finding.detail}".replace("\n", " ")
    return f"""      <li class="finding {'is-pass' if finding.ok else 'is-fail'}" data-ok="{str(finding.ok).lower()}" data-severity="{_escape(finding.severity)}" data-weight="{int(finding.weight)}" data-search="{_escape(search)}">
        <div class="finding-line">
          <span class="status {status_class}">{status}</span>
          <span class="severity severity-{_escape(finding.severity)}">{_escape(finding.severity)}</span>
          <code class="rule">{_escape(finding.rule)}</code>
          <span class="weight">вес: {int(finding.weight)}</span>
        </div>
        <p class="finding-title">{_escape(finding.title)}</p>
        <p class="finding-detail">{_escape(finding.detail)}</p>
      </li>"""


def _render_warnings(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return '<p class="empty">Предупреждений нет</p>'
    items = "\n".join(f"        <li>{_escape(warning)}</li>" for warning in warnings)
    return f"""<ul class="warning-list">
{items}
      </ul>"""


def _render_narrative(view: ReportView) -> str:
    if view.narrative is not None:
        return f'<p class="narrative-text">{_escape(view.narrative)}</p>'
    if view.narrative_error is not None:
        return f"""<p class="badge badge-warning">Рецензия недоступна</p>
      <p class="narrative-error">{_escape(view.narrative_error)}</p>
      <p class="hint">Результат аудита не изменён.</p>"""
    return '<p class="empty">Рецензия не запрашивалась</p>'


_CSS = """
:root {
  color-scheme: light;
  --bg: #f4f6fa;
  --surface: #ffffff;
  --text: #182033;
  --muted: #52607a;
  --border: #d6deeb;
  --accent: #1f5fbf;
  --pass: #17663a;
  --pass-bg: #e7f6ec;
  --fail: #a3261f;
  --fail-bg: #fdecea;
  --warn: #7a5200;
  --warn-bg: #fff4d6;
  --blocker: #a3261f;
  --major: #7a5200;
  --minor: #35578a;
}
* { box-sizing: border-box; }
html { font-size: 16px; }
body {
  margin: 0;
  padding: 2rem 1rem 3rem;
  color: var(--text);
  background: var(--bg);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  line-height: 1.5;
}
.report-header, main, footer { max-width: 1120px; margin: 0 auto; }
.eyebrow {
  margin: 0 0 .25rem;
  color: var(--muted);
  font-size: .8rem;
  letter-spacing: .08em;
  text-transform: uppercase;
}
h1 { margin: 0 0 .35rem; font-size: clamp(1.6rem, 3vw, 2.25rem); line-height: 1.2; }
h2 { margin: 0; font-size: 1.15rem; }
.spec { margin: 0 0 .35rem; font-weight: 600; }
.target { margin: 0 0 1rem; color: var(--muted); overflow-wrap: anywhere; }
code, .rule {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
.target code { background: #e9eef7; padding: .1rem .35rem; border-radius: .3rem; }
.verdict {
  display: inline-block;
  margin: 0 0 .75rem;
  padding: .65rem .9rem;
  border-left: 6px solid currentColor;
  border-radius: .35rem;
  font-weight: 700;
}
.verdict-0 { color: var(--pass); background: var(--pass-bg); }
.verdict-1 { color: var(--warn); background: var(--warn-bg); }
.verdict-2 { color: var(--fail); background: var(--fail-bg); }
.badge {
  display: inline-block;
  margin: 0 .4rem .75rem 0;
  padding: .25rem .55rem;
  border-radius: 999px;
  font-size: .85rem;
  font-weight: 700;
}
.badge-warning { color: var(--warn); background: var(--warn-bg); border: 1px solid #e7cc8a; }
.score-line { margin: .5rem 0 .75rem; font-weight: 600; }
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: .5rem;
  margin: 0 0 1.5rem;
}
.metrics div {
  padding: .55rem .7rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: .45rem;
}
.metrics dt { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }
.metrics dd { margin: .1rem 0 0; font-size: 1.2rem; font-weight: 700; }
.controls {
  display: none;
  margin: 0 0 1.25rem;
  padding: 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: .6rem;
}
.js .controls { display: block; }
.controls h2 { margin-bottom: .75rem; }
.controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: .75rem;
  align-items: end;
}
.field { display: flex; flex-direction: column; gap: .3rem; font-size: .9rem; font-weight: 600; }
.field-check { flex-direction: row; align-items: center; gap: .45rem; padding-bottom: .45rem; }
input, select, button {
  min-height: 2.4rem;
  padding: .45rem .6rem;
  color: var(--text);
  background: #fff;
  border: 1px solid #9ca9be;
  border-radius: .4rem;
  font: inherit;
}
input[type="checkbox"] { min-height: auto; width: 1.1rem; height: 1.1rem; }
button {
  cursor: pointer;
  color: #fff;
  background: var(--accent);
  border-color: var(--accent);
  font-weight: 700;
}
button:hover { filter: brightness(.95); }
:focus-visible { outline: 3px solid #0b57d0; outline-offset: 2px; }
.noscript {
  margin: 0 0 1rem;
  padding: .7rem .9rem;
  color: var(--warn);
  background: var(--warn-bg);
  border: 1px solid #e7cc8a;
  border-radius: .45rem;
}
section { margin: 0 0 1.5rem; }
.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: .5rem;
  margin-bottom: .6rem;
}
.count { margin: 0; color: var(--muted); font-size: .9rem; }
.findings-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .6rem; }
.finding {
  padding: .8rem .9rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 5px solid var(--border);
  border-radius: .5rem;
}
.finding.is-pass { border-left-color: var(--pass); }
.finding.is-fail { border-left-color: var(--fail); }
.finding-line { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.status, .severity, .weight {
  padding: .1rem .45rem;
  border-radius: 999px;
  font-size: .78rem;
  font-weight: 700;
}
.status-pass { color: var(--pass); background: var(--pass-bg); }
.status-fail { color: var(--fail); background: var(--fail-bg); }
.severity-blocker { color: var(--blocker); background: var(--fail-bg); }
.severity-major { color: var(--major); background: var(--warn-bg); }
.severity-minor { color: var(--minor); background: #e8eef9; }
.weight { color: var(--muted); background: #eef2f8; }
.rule { padding: .1rem .35rem; background: #eef2f8; border-radius: .3rem; font-size: .88rem; }
.finding-title { margin: .45rem 0 .15rem; font-weight: 700; overflow-wrap: anywhere; }
.finding-detail { margin: 0; color: var(--muted); white-space: pre-wrap; overflow-wrap: anywhere; }
.empty { margin: .35rem 0; color: var(--muted); font-style: italic; }
.warning-list { margin: 0; padding-left: 1.25rem; color: var(--warn); }
.warning-list li { overflow-wrap: anywhere; }
.narrative-text, .narrative-error {
  margin: 0 0 .5rem;
  padding: .75rem .9rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: .5rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.narrative-error { color: var(--fail); }
.hint { margin: 0; color: var(--muted); font-size: .9rem; }
footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: .88rem; }
[hidden] { display: none !important; }
@media (max-width: 640px) {
  body { padding: 1.25rem .75rem 2rem; }
  .controls-grid { grid-template-columns: 1fr; }
}
@media print {
  body { padding: 0; background: #fff; }
  .controls, .noscript { display: none !important; }
  .finding { break-inside: avoid; }
}
"""

_JS = """
document.documentElement.classList.add('js');
(function () {
  'use strict';
  var list = document.getElementById('findings-list');
  if (!list) { return; }
  var items = Array.prototype.slice.call(list.querySelectorAll('.finding'));
  var search = document.getElementById('search');
  var severity = document.getElementById('severity');
  var failedOnly = document.getElementById('failed-only');
  var sort = document.getElementById('sort');
  var reset = document.getElementById('reset');
  var count = document.getElementById('visible-count');
  var empty = document.getElementById('empty-filter');
  if (!search || !severity || !failedOnly || !sort || !reset || !count || !empty) { return; }
  var total = items.length;
  var severityRank = { blocker: 0, major: 1, minor: 2 };

  function normalize(value) {
    return (value || '').toLocaleLowerCase().replace(/^\\s+|\\s+$/g, '');
  }

  function matches(item) {
    var query = normalize(search.value);
    var haystack = normalize(item.getAttribute('data-search'));
    if (query && haystack.indexOf(query) === -1) { return false; }
    if (severity.value !== 'all' && item.getAttribute('data-severity') !== severity.value) { return false; }
    if (failedOnly.checked && item.getAttribute('data-ok') !== 'false') { return false; }
    return true;
  }

  function sortItems(visible) {
    var mode = sort.value;
    var decorated = visible.map(function (item, index) {
      return { item: item, index: index };
    });
    decorated.sort(function (left, right) {
      var result = 0;
      if (mode === 'failed-first') {
        var leftFailed = left.item.getAttribute('data-ok') === 'false' ? 0 : 1;
        var rightFailed = right.item.getAttribute('data-ok') === 'false' ? 0 : 1;
        result = leftFailed - rightFailed;
      } else if (mode === 'severity') {
        result = severityRank[left.item.getAttribute('data-severity')] -
          severityRank[right.item.getAttribute('data-severity')];
      } else if (mode === 'rule') {
        var leftRule = left.item.querySelector('.rule');
        var rightRule = right.item.querySelector('.rule');
        result = (leftRule ? leftRule.textContent : '').localeCompare(
          rightRule ? rightRule.textContent : '', 'ru'
        );
      } else if (mode === 'weight') {
        result = Number(right.item.getAttribute('data-weight')) -
          Number(left.item.getAttribute('data-weight'));
      }
      return result !== 0 ? result : left.index - right.index;
    });
    return decorated.map(function (entry) { return entry.item; });
  }

  function render() {
    var visible = items.filter(matches);
    var ordered = sortItems(visible);
    items.forEach(function (item) { item.hidden = true; });
    ordered.forEach(function (item) {
      item.hidden = false;
      list.appendChild(item);
    });
    count.textContent = 'Показано ' + visible.length + ' из ' + total;
    empty.textContent = total === 0 ? 'Находок нет' : 'Ничего не найдено. Измените запрос или сбросьте фильтры.';
    empty.hidden = visible.length !== 0;
  }

  [search, severity, failedOnly, sort].forEach(function (control) {
    control.addEventListener('input', render);
  });
  [severity, sort].forEach(function (control) {
    control.addEventListener('change', render);
  });
  reset.addEventListener('click', function () {
    search.value = '';
    severity.value = 'all';
    failedOnly.checked = false;
    sort.value = 'rubric';
    render();
    search.focus();
  });
  render();
})();
"""


def render_html(view: ReportView) -> str:
    """Рендерит один самодостаточный HTML-файл. Чистая функция без I/O."""
    verdict_text, verdict_class = _verdict(view.exit_code)
    findings = "\n".join(_render_finding(finding) for finding in view.findings)
    if not findings:
        findings = ""
    warnings = _render_warnings(view.warnings)
    narrative = _render_narrative(view)
    badge = (
        '<p class="badge badge-warning">Рецензия недоступна</p>'
        if view.narrative_error is not None
        else ""
    )
    empty_filter = (
        '<p id="empty-filter" class="empty">Находок нет</p>'
        if not view.findings
        else '<p id="empty-filter" class="empty" hidden>Ничего не найдено. Измените запрос или сбросьте фильтры.</p>'
    )
    total = len(view.findings)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{_CSP}">
<title>Отчёт аудита rubrica — {_escape(view.spec_id)}</title>
<style>{_CSS}</style>
</head>
<body>
<header class="report-header">
  <p class="eyebrow">rubrica · аудит сдачи</p>
  <h1>Отчёт аудита rubrica</h1>
  <p class="spec">{_escape(view.spec_id)} · {_escape(view.spec_title)}</p>
  <p class="target">Цель: <code>{_escape(view.target)}</code></p>
  <p class="verdict {verdict_class}">{verdict_text}</p>
  {badge}
  <p class="score-line">Баллы: {view.score}/{view.max_score}</p>
  <dl class="metrics">
    <div><dt>Пройдено</dt><dd>{view.passed}</dd></div>
    <div><dt>Провалено</dt><dd>{view.failed}</dd></div>
    <div><dt>Блокеров</dt><dd>{view.blockers}</dd></div>
    <div><dt>Код аудита</dt><dd>{view.exit_code}</dd></div>
  </dl>
</header>
<main>
  <section class="controls" aria-labelledby="controls-title">
    <h2 id="controls-title">Поиск и фильтры</h2>
    <div class="controls-grid">
      <label class="field" for="search">Поиск по находкам
        <input id="search" type="search" placeholder="rule id, заголовок или детали" autocomplete="off">
      </label>
      <label class="field" for="severity">Severity
        <select id="severity">
          <option value="all">все</option>
          <option value="blocker">blocker</option>
          <option value="major">major</option>
          <option value="minor">minor</option>
        </select>
      </label>
      <label class="field field-check" for="failed-only">
        <input id="failed-only" type="checkbox"> Только провалы
      </label>
      <label class="field" for="sort">Сортировка
        <select id="sort">
          <option value="rubric">порядок рубрики</option>
          <option value="failed-first">провалы сначала</option>
          <option value="severity">severity: blocker → minor</option>
          <option value="rule">rule id</option>
          <option value="weight">вес: больше сначала</option>
        </select>
      </label>
      <button id="reset" type="button">Сбросить</button>
    </div>
  </section>
  <noscript><p class="noscript">Фильтры недоступны без JavaScript. Ниже полный список находок.</p></noscript>
  <section class="findings" aria-labelledby="findings-title">
    <div class="section-head">
      <h2 id="findings-title">Находки</h2>
      <p id="visible-count" class="count" aria-live="polite" aria-atomic="true">Показано {total} из {total}</p>
    </div>
    <ul id="findings-list" class="findings-list">
{findings}
    </ul>
    {empty_filter}
  </section>
  <section class="warnings" aria-labelledby="warnings-title">
    <div class="section-head">
      <h2 id="warnings-title">Предупреждения</h2>
      <span class="count">({len(view.warnings)})</span>
    </div>
    {warnings}
  </section>
  <section class="narrative" aria-labelledby="narrative-title">
    <div class="section-head"><h2 id="narrative-title">Рецензия</h2></div>
    {narrative}
  </section>
</main>
<footer>rubrica · {_escape(view.spec_id)}</footer>
<script>{_JS}</script>
</body>
</html>
"""
