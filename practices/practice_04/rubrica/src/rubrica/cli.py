"""CLI rubrica: валидирует вход, гоняет рубрику, печатает отчёт.

Коды возврата: 0 — все правила прошли, 1 — есть провалы без blocker'ов,
2 — blocker или отказ входа.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Report, audit
from .spec import SpecError, load_spec
from .validate import InputRejected, validate_all
from .narrative import NarrativeUnavailable, request_narrative

DEFAULT_SPEC = Path(__file__).resolve().parents[2] / "rubrics" / "practice_04.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rubrica", description="Аудит папки сдачи практики по рубрике.")
    parser.add_argument("target", help="путь к папке сдачи")
    parser.add_argument("--spec", default=None, help="путь к рубрике YAML (по умолчанию rubrics/practice_04.yaml)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="машиночитаемый вывод")
    parser.add_argument("--max-findings", type=int, default=200, help="потолок числа правил")
    # Optional narrative enrichment flags. Without --narrative dependency is never touched.
    parser.add_argument("--narrative", action="store_true", help="добавить текстовую рецензию (опционально)")
    parser.add_argument("--model", default=None, help="модель для OpenAI-совместимого endpoint")
    parser.add_argument("--timeout", type=float, default=None, help="таймаут обращения к endpoint, сек")
    parser.add_argument("--version", action="version", version=f"rubrica {__version__}")
    return parser


def render_text(report: Report, max_findings: int) -> str:
    lines = [
        f"rubrica {report.spec_id} · {report.spec_title}",
        f"цель:   {report.target}",
        f"баллы:  {report.score}/{report.max_score}   провалено: {len(report.failed)}   blocker'ов: {len(report.blockers)}",
        "",
    ]
    for finding in report.findings[:max_findings]:
        mark = "PASS" if finding.ok else "FAIL"
        lines.append(f"[{mark}] {finding.severity:<7} {finding.rule_id}: {finding.detail}")
    hidden = len(report.findings) - min(len(report.findings), max_findings)
    if hidden > 0:
        lines.append(f"... ещё {hidden} правил скрыто лимитом --max-findings")
    for warning in report.warnings:
        lines.append(f"ВНИМАНИЕ: {warning}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        validated = validate_all(
            args.target,
            spec_path=args.spec,
            json_output=args.json_output,
            max_findings=args.max_findings,
        )
    except InputRejected as exc:
        print(f"ОТКАЗ: {exc}", file=sys.stderr)
        return 2

    spec_path = validated.spec_path or DEFAULT_SPEC
    try:
        spec = load_spec(spec_path)
    except SpecError as exc:
        print(f"ОТКАЗ: рубрика непригодна — {exc}", file=sys.stderr)
        return 2

    report = audit(spec, validated.target)
    report.warnings.extend(validated.notes)

    # Optional narrative enrichment
    narrative_text: str | None = None
    narrative_error: str | None = None
    exit_code = report.exit_code
    if args.narrative:
        try:
            narrative_text = request_narrative(report.as_dict(), model=args.model, timeout=args.timeout)
        except NarrativeUnavailable as exc:
            # Per contract: audit result remains, but program returns code 3 to signal narrative unavailable
            narrative_error = str(exc)
            exit_code = 3

    if args.json_output:
        payload = report.as_dict()
        payload["narrative"] = narrative_text
        payload["narrative_error"] = narrative_error
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(report, args.max_findings))
        # Text mode: keep existing output format; we don't print narrative to avoid breaking expectations

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
