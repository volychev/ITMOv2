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

DEFAULT_SPEC = Path(__file__).resolve().parents[2] / "rubrics" / "practice_04.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rubrica", description="Аудит папки сдачи практики по рубрике.")
    parser.add_argument("target", help="путь к папке сдачи")
    parser.add_argument("--spec", default=None, help="путь к рубрике YAML (по умолчанию rubrics/practice_04.yaml)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="машиночитаемый вывод")
    parser.add_argument("--max-findings", type=int, default=200, help="потолок числа правил")
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

    if args.json_output:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_text(report, args.max_findings))

    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())